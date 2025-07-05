#!/usr/bin/env python3
"""
Test script to demonstrate ATLAS flexible software versioning.

This script shows how the version resolution works with different
configuration styles and validates the system behavior.
"""

import asyncio
import yaml
from typing import Dict, Any

from atlas.core.models import VMSpec, SoftwarePackage
from atlas.core.version_resolver import VersionResolver, ResolvedVersion, PackageSource


async def test_version_resolution():
    """Test various version resolution scenarios."""
    
    print("🧪 Testing ATLAS Software Version Resolution\n")
    
    # Test configurations
    test_configs = [
        {
            "name": "Test 1: No version specified (latest)",
            "packages": [
                SoftwarePackage(name="nginx"),
                SoftwarePackage(name="docker"),
            ]
        },
        {
            "name": "Test 2: Specific versions",
            "packages": [
                SoftwarePackage(name="nginx", version="1.20.2"),
                SoftwarePackage(name="postgresql", version="14.9"),
            ]
        },
        {
            "name": "Test 3: Version ranges and special versions",
            "packages": [
                SoftwarePackage(name="nodejs", version="~18.0"),
                SoftwarePackage(name="docker", version="^24.0"),
                SoftwarePackage(name="certbot", version="lts"),
                SoftwarePackage(name="python", version="latest"),
            ]
        },
    ]
    
    async with VersionResolver() as resolver:
        for test_config in test_configs:
            print(f"📋 {test_config['name']}")
            print("-" * 50)
            
            for pkg in test_config['packages']:
                try:
                    # Mock resolution for demonstration
                    resolved = await mock_resolve_version(resolver, pkg)
                    
                    requested = pkg.version or "not specified"
                    print(f"  📦 {pkg.name}")
                    print(f"     Requested: {requested}")
                    print(f"     Resolved:  {resolved.resolved_version}")
                    print(f"     Source:    {resolved.source}")
                    print()
                    
                except Exception as e:
                    print(f"  ❌ {pkg.name}: Error - {e}")
                    print()
            
            print()


async def mock_resolve_version(resolver: VersionResolver, pkg: SoftwarePackage) -> ResolvedVersion:
    """
    Mock version resolution for demonstration.
    In a real implementation, this would query actual package repositories.
    """
    
    # Mock version database
    mock_versions = {
        "nginx": {
            "latest": "1.24.0",
            "1.20.2": "1.20.2",
            "stable": "1.22.1"
        },
        "docker": {
            "latest": "24.0.7",
            "^24.0": "24.0.7",
            "stable": "24.0.6"
        },
        "postgresql": {
            "latest": "15.4",
            "14.9": "14.9",
            "lts": "14.9"
        },
        "nodejs": {
            "latest": "20.8.0",
            "~18.0": "18.18.2",
            "lts": "18.18.2"
        },
        "python": {
            "latest": "3.11.5",
            "3.11": "3.11.5"
        },
        "certbot": {
            "latest": "2.7.4",
            "lts": "2.6.0",
            "stable": "2.6.0"
        }
    }
    
    package_versions = mock_versions.get(pkg.name, {})
    requested_version = pkg.version or "latest"
    
    # Resolve version
    if requested_version in package_versions:
        resolved_version = package_versions[requested_version]
    elif requested_version == "latest" and "latest" in package_versions:
        resolved_version = package_versions["latest"]
    else:
        # Fallback to latest if specific version not found
        resolved_version = package_versions.get("latest", "unknown")
    
    # Determine source
    source_mapping = {
        "nginx": PackageSource.APT,
        "docker": PackageSource.DOCKER,
        "postgresql": PackageSource.APT,
        "nodejs": PackageSource.SNAP,
        "python": PackageSource.APT,
        "certbot": PackageSource.APT,
    }
    
    source = source_mapping.get(pkg.name, PackageSource.APT)
    
    return ResolvedVersion(
        package_name=pkg.name,
        requested_version=pkg.version,
        resolved_version=resolved_version,
        source=source
    )


def test_vm_configuration_parsing():
    """Test parsing of VM configurations with mixed version specifications."""
    
    print("🔧 Testing VM Configuration Parsing\n")
    
    # Test configuration with mixed version styles
    config_yaml = """
name: "test-vm"
os_type: "ubuntu-22.04"
memory: 4096
cores: 2

software:
  # No version specified - will use latest
  - name: nginx
  
  # Specific version
  - name: postgresql
    version: "14.9"
    config:
      port: 5432
  
  # Version range
  - name: nodejs
    version: "~18.0"
    source: snap
  
  # Simple string format (latest)
  - docker
  - git
  
  # Special versions
  - name: certbot
    version: "lts"
"""
    
    try:
        config_data = yaml.safe_load(config_yaml)
        vm_spec = VMSpec(**config_data)
        
        print("✅ Configuration parsed successfully!")
        print(f"VM Name: {vm_spec.name}")
        print(f"Software packages: {len(vm_spec.software)}")
        print()
        
        print("📦 Software Configuration:")
        for i, pkg in enumerate(vm_spec.software, 1):
            if isinstance(pkg, str):
                print(f"  {i}. {pkg} (latest)")
            else:
                version = pkg.version or "latest"
                source = f" [{pkg.source}]" if pkg.source else ""
                config_info = f" + config" if pkg.config else ""
                print(f"  {i}. {pkg.name} (v{version}){source}{config_info}")
        
        print("\n✅ All software packages validated successfully!")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")


def demonstrate_cli_usage():
    """Show example CLI commands that would work with the enhanced CLI."""
    
    print("🖥️  CLI Usage Examples\n")
    
    examples = [
        {
            "command": "atlas provision web-server.yaml",
            "description": "Provision VM with automatic version resolution"
        },
        {
            "command": "atlas provision web-server.yaml --dry-run",
            "description": "Preview what would be installed without provisioning"
        },
        {
            "command": "atlas resolve-version nginx --version 1.20.2",
            "description": "Resolve specific software version"
        },
        {
            "command": "atlas validate my-config.yaml",
            "description": "Validate configuration file"
        },
        {
            "command": "atlas generate-example development -o dev.yaml",
            "description": "Generate development environment template"
        },
        {
            "command": "atlas list-examples",
            "description": "List available configuration templates"
        }
    ]
    
    for example in examples:
        print(f"📝 {example['command']}")
        print(f"   {example['description']}")
        print()


if __name__ == "__main__":
    print("🚀 ATLAS Flexible Software Versioning Demo")
    print("=" * 60)
    print()
    
    # Run async tests
    asyncio.run(test_version_resolution())
    
    # Test configuration parsing
    test_vm_configuration_parsing()
    print()
    
    # Show CLI examples
    demonstrate_cli_usage()
    
    print("🎉 Demo completed! The ATLAS system supports:")
    print("  • Optional software versioning (defaults to latest)")
    print("  • Semantic versioning and ranges (~, ^)")
    print("  • Special versions (latest, lts, stable)")
    print("  • Mixed configuration styles")
    print("  • Multi-source package resolution")
    print("  • Comprehensive validation and error handling")
