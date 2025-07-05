"""
Software version management utilities for ATLAS.

This module provides utilities for resolving software versions,
managing package repositories, and handling version constraints.
"""

import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from atlas.core import get_logger, AtlasError

logger = get_logger(__name__)


class VersionResolutionError(AtlasError):
    """Error in version resolution."""
    pass


class PackageSource(str, Enum):
    """Supported package sources."""
    APT = "apt"
    SNAP = "snap"
    DOCKER = "docker"
    DOCKER_HUB = "docker.io"
    NPM = "npm"
    PIP = "pip"
    CUSTOM = "custom"


@dataclass
class ResolvedVersion:
    """Resolved software version information."""
    
    package_name: str
    requested_version: Optional[str]
    resolved_version: str
    source: PackageSource
    download_url: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = None


class VersionResolver:
    """Resolves software versions from various sources."""
    
    def __init__(self):
        self.cache: Dict[str, ResolvedVersion] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def resolve_version(
        self, 
        package_name: str, 
        version_spec: Optional[str] = None,
        source: Optional[PackageSource] = None
    ) -> ResolvedVersion:
        """
        Resolve a software version specification to a concrete version.
        
        Args:
            package_name: Name of the package
            version_spec: Version specification (None = latest)
            source: Package source (auto-detected if None)
            
        Returns:
            ResolvedVersion with concrete version information
        """
        # Create cache key
        cache_key = f"{package_name}:{version_spec}:{source}"
        
        if cache_key in self.cache:
            logger.debug(f"Using cached version for {cache_key}")
            return self.cache[cache_key]
        
        # Auto-detect source if not specified
        if source is None:
            source = self._detect_package_source(package_name)
        
        # Resolve version based on source
        try:
            if source == PackageSource.APT:
                resolved = await self._resolve_apt_version(package_name, version_spec)
            elif source == PackageSource.DOCKER:
                resolved = await self._resolve_docker_version(package_name, version_spec)
            elif source == PackageSource.SNAP:
                resolved = await self._resolve_snap_version(package_name, version_spec)
            elif source == PackageSource.NPM:
                resolved = await self._resolve_npm_version(package_name, version_spec)
            else:
                # For custom or unknown sources, return as-is
                resolved = ResolvedVersion(
                    package_name=package_name,
                    requested_version=version_spec,
                    resolved_version=version_spec or "latest",
                    source=source
                )
            
            # Cache the result
            self.cache[cache_key] = resolved
            return resolved
            
        except Exception as e:
            logger.error(f"Failed to resolve version for {package_name}: {e}")
            raise VersionResolutionError(f"Cannot resolve version for {package_name}: {e}")
    
    def _detect_package_source(self, package_name: str) -> PackageSource:
        """Auto-detect the package source based on package name."""
        
        # Docker images (contain / or are common container names)
        docker_patterns = [
            r".*/.+",  # registry/image format
            r"^(nginx|redis|postgres|mysql|mongodb|elasticsearch)$"
        ]
        
        for pattern in docker_patterns:
            if re.match(pattern, package_name):
                return PackageSource.DOCKER
        
        # Snap packages (common snap packages)
        snap_packages = [
            "node", "code", "discord", "spotify", "slack",
            "docker", "kubectl", "helm", "terraform"
        ]
        
        if package_name in snap_packages:
            return PackageSource.SNAP
        
        # Default to APT for most packages
        return PackageSource.APT
    
    async def _resolve_apt_version(
        self, 
        package_name: str, 
        version_spec: Optional[str]
    ) -> ResolvedVersion:
        """Resolve APT package version."""
        
        if version_spec is None or version_spec == "latest":
            # For APT, we'll use the default version available
            resolved_version = "latest"
        else:
            # Validate version format for APT
            resolved_version = self._normalize_apt_version(version_spec)
        
        return ResolvedVersion(
            package_name=package_name,
            requested_version=version_spec,
            resolved_version=resolved_version,
            source=PackageSource.APT,
            metadata={"package_manager": "apt"}
        )
    
    async def _resolve_docker_version(
        self, 
        package_name: str, 
        version_spec: Optional[str]
    ) -> ResolvedVersion:
        """Resolve Docker image version from Docker Hub."""
        
        if not self.session:
            raise VersionResolutionError("HTTP session not initialized")
        
        try:
            # Query Docker Hub API for available tags
            if "/" not in package_name:
                # Official image (e.g., nginx -> library/nginx)
                image_name = f"library/{package_name}"
            else:
                image_name = package_name
            
            url = f"https://registry.hub.docker.com/v2/repositories/{image_name}/tags/"
            
            async with self.session.get(url, params={"page_size": 100}) as response:
                if response.status == 200:
                    data = await response.json()
                    available_tags = [tag["name"] for tag in data.get("results", [])]
                    
                    resolved_version = self._select_best_version(
                        available_tags, version_spec
                    )
                else:
                    # Fallback if API fails
                    resolved_version = version_spec or "latest"
            
        except Exception as e:
            logger.warning(f"Failed to query Docker Hub for {package_name}: {e}")
            resolved_version = version_spec or "latest"
        
        return ResolvedVersion(
            package_name=package_name,
            requested_version=version_spec,
            resolved_version=resolved_version,
            source=PackageSource.DOCKER,
            download_url=f"docker.io/{package_name}:{resolved_version}",
            metadata={"registry": "docker.io"}
        )
    
    async def _resolve_snap_version(
        self, 
        package_name: str, 
        version_spec: Optional[str]
    ) -> ResolvedVersion:
        """Resolve Snap package version."""
        
        # For snap packages, we typically use channels
        if version_spec is None or version_spec == "latest":
            resolved_version = "latest/stable"
        elif version_spec in ["stable", "candidate", "beta", "edge"]:
            resolved_version = f"latest/{version_spec}"
        else:
            # Specific version
            resolved_version = version_spec
        
        return ResolvedVersion(
            package_name=package_name,
            requested_version=version_spec,
            resolved_version=resolved_version,
            source=PackageSource.SNAP,
            metadata={"channel": resolved_version}
        )
    
    async def _resolve_npm_version(
        self, 
        package_name: str, 
        version_spec: Optional[str]
    ) -> ResolvedVersion:
        """Resolve NPM package version."""
        
        if not self.session:
            raise VersionResolutionError("HTTP session not initialized")
        
        try:
            # Query NPM registry
            url = f"https://registry.npmjs.org/{package_name}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    latest_version = data.get("dist-tags", {}).get("latest", "latest")
                    
                    if version_spec is None or version_spec == "latest":
                        resolved_version = latest_version
                    else:
                        # Validate against available versions
                        available_versions = list(data.get("versions", {}).keys())
                        resolved_version = self._select_best_version(
                            available_versions, version_spec
                        )
                else:
                    resolved_version = version_spec or "latest"
                    
        except Exception as e:
            logger.warning(f"Failed to query NPM registry for {package_name}: {e}")
            resolved_version = version_spec or "latest"
        
        return ResolvedVersion(
            package_name=package_name,
            requested_version=version_spec,
            resolved_version=resolved_version,
            source=PackageSource.NPM,
            metadata={"registry": "npmjs.org"}
        )
    
    def _normalize_apt_version(self, version_spec: str) -> str:
        """Normalize APT version specification."""
        
        # Handle common version patterns
        if version_spec in ["latest", "stable", "lts"]:
            return version_spec
        
        # Handle version ranges (convert to APT format)
        if version_spec.startswith("~"):
            # ~1.2 -> 1.2*
            return version_spec[1:] + "*"
        elif version_spec.startswith("^"):
            # ^1.2 -> 1.*
            major = version_spec[1:].split(".")[0]
            return f"{major}.*"
        
        # Return as-is for specific versions
        return version_spec
    
    def _select_best_version(
        self, 
        available_versions: List[str], 
        version_spec: Optional[str]
    ) -> str:
        """Select the best matching version from available versions."""
        
        if not available_versions:
            return version_spec or "latest"
        
        if version_spec is None or version_spec == "latest":
            # Return the latest semantic version
            return self._get_latest_semver(available_versions)
        
        # Handle version ranges
        if version_spec.startswith("~") or version_spec.startswith("^"):
            return self._find_compatible_version(available_versions, version_spec)
        
        # Exact match
        if version_spec in available_versions:
            return version_spec
        
        # Partial match (e.g., "1.2" matches "1.2.3")
        matches = [v for v in available_versions if v.startswith(version_spec)]
        if matches:
            return self._get_latest_semver(matches)
        
        # No match found, return as-is
        return version_spec
    
    def _get_latest_semver(self, versions: List[str]) -> str:
        """Get the latest semantic version from a list."""
        
        # Filter out non-semver versions
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+')
        semver_versions = [v for v in versions if semver_pattern.match(v)]
        
        if not semver_versions:
            # Return first version if no semver found
            return versions[0] if versions else "latest"
        
        # Sort by semantic version
        try:
            from packaging import version
            sorted_versions = sorted(semver_versions, key=version.parse, reverse=True)
            return sorted_versions[0]
        except ImportError:
            # Fallback to string sorting
            return sorted(semver_versions, reverse=True)[0]
    
    def _find_compatible_version(
        self, 
        available_versions: List[str], 
        version_spec: str
    ) -> str:
        """Find compatible version based on range specification."""
        
        try:
            from packaging import version, specifiers
            
            # Convert our range format to packaging format
            if version_spec.startswith("~"):
                # ~1.2.3 -> ~=1.2.3
                spec = f"~={version_spec[1:]}"
            elif version_spec.startswith("^"):
                # ^1.2.3 -> >=1.2.3,<2.0.0
                base_version = version_spec[1:]
                major = base_version.split(".")[0]
                next_major = str(int(major) + 1)
                spec = f">={base_version},<{next_major}.0.0"
            else:
                spec = version_spec
            
            spec_set = specifiers.SpecifierSet(spec)
            
            # Find compatible versions
            compatible_versions = [
                v for v in available_versions 
                if version.parse(v) in spec_set
            ]
            
            if compatible_versions:
                return self._get_latest_semver(compatible_versions)
                
        except ImportError:
            logger.warning("packaging library not available, using fallback version selection")
        
        # Fallback: return as-is
        return version_spec


# Global resolver instance
_resolver: Optional[VersionResolver] = None


async def get_version_resolver() -> VersionResolver:
    """Get or create global version resolver."""
    global _resolver
    if _resolver is None:
        _resolver = VersionResolver()
        await _resolver.__aenter__()
    return _resolver


async def resolve_software_versions(
    software_list: List[Dict[str, Any]]
) -> List[ResolvedVersion]:
    """
    Resolve versions for a list of software packages.
    
    Args:
        software_list: List of software specifications
        
    Returns:
        List of resolved versions
    """
    resolver = await get_version_resolver()
    resolved_versions = []
    
    for software in software_list:
        if isinstance(software, str):
            # Simple string format
            resolved = await resolver.resolve_version(software)
        else:
            # Dictionary format
            name = software.get("name")
            version = software.get("version")
            source = software.get("source")
            
            if source:
                source = PackageSource(source)
            
            resolved = await resolver.resolve_version(name, version, source)
        
        resolved_versions.append(resolved)
    
    return resolved_versions
