"""
Validation agent for the ATLAS system.

This agent provides comprehensive validation services for VM specifications,
configurations, and system requirements. It performs both syntactic and
semantic validation to ensure configurations are correct and viable.
"""

import re
import ipaddress
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from atlas.core import (
    get_logger,
    ValidationError,
    ProxmoxError,
    VMSpec,
    OSType,
    NetworkConfig,
    DiskConfig,
    ValidationResult,
    ValidationRule,
)
from .base import BaseAgent, AgentCapabilities


@dataclass
class ValidationContext:
    """Context for validation operations."""
    
    operation_type: str  # 'create', 'update', 'clone'
    target_node: Optional[str] = None
    existing_vms: List[Dict[str, Any]] = None
    available_resources: Dict[str, Any] = None
    network_config: Dict[str, Any] = None
    storage_config: Dict[str, Any] = None


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    
    severity: str  # 'error', 'warning', 'info'
    code: str
    message: str
    field_path: Optional[str] = None
    suggested_fix: Optional[str] = None


class ValidationAgent(BaseAgent):
    """Agent responsible for validating VM specifications and configurations."""
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the validation agent."""
        super().__init__(agent_id, config)
        
        # Validation rules and constraints
        self._validation_rules: Dict[str, ValidationRule] = {}
        self._setup_default_rules()
        
        # Cache for external validation data
        self._resource_cache: Dict[str, Any] = {}
        self._cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes
    
    def _get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        return AgentCapabilities(
            name="ValidationAgent",
            version="1.0.0",
            description="Validates VM specifications and configurations",
            supported_operations=[
                "validate_vm_spec",
                "validate_hardware",
                "validate_network",
                "validate_storage",
                "validate_resources",
                "validate_naming",
                "validate_dependencies",
                "check_conflicts",
                "suggest_fixes",
            ],
            input_types=["VMSpec", "ValidationContext", "dict"],
            output_types=["ValidationResult", "ValidationIssue"],
            dependencies=["proxmox_api"],
            resource_requirements={"memory": "512MB", "cpu": "0.2"},
            concurrent_requests=10,
        )
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process validation request."""
        operation = request.get('operation')
        
        if operation == 'validate_vm_spec':
            return await self._validate_vm_spec_request(request)
        elif operation == 'validate_hardware':
            return await self._validate_hardware_request(request)
        elif operation == 'validate_network':
            return await self._validate_network_request(request)
        elif operation == 'validate_storage':
            return await self._validate_storage_request(request)
        elif operation == 'validate_resources':
            return await self._validate_resources_request(request)
        elif operation == 'check_conflicts':
            return await self._check_conflicts_request(request)
        else:
            raise ValidationError(f"Unknown validation operation: {operation}")
    
    async def validate_vm_spec(self, vm_spec: VMSpec, 
                              context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate a complete VM specification.
        
        Args:
            vm_spec: VM specification to validate
            context: Validation context with additional information
            
        Returns:
            Validation result with errors, warnings, and suggestions
        """
        self.logger.info(f"Validating VM specification: {vm_spec.name}")
        
        issues = []
        
        # Basic validation
        issues.extend(await self._validate_basic_fields(vm_spec))
        
        # Hardware validation
        issues.extend(await self._validate_hardware(vm_spec, context))
        
        # Network validation
        issues.extend(await self._validate_networks(vm_spec, context))
        
        # Storage validation
        issues.extend(await self._validate_storage(vm_spec, context))
        
        # Resource validation
        if context and context.target_node:
            issues.extend(await self._validate_node_resources(vm_spec, context))
        
        # Naming and conflicts validation
        issues.extend(await self._validate_naming_and_conflicts(vm_spec, context))
        
        # OS-specific validation
        issues.extend(await self._validate_os_configuration(vm_spec))
        
        # Cloud-init validation
        if vm_spec.cloud_init:
            issues.extend(await self._validate_cloud_init(vm_spec))
        
        # Separate errors and warnings
        errors = [issue.message for issue in issues if issue.severity == 'error']
        warnings = [issue.message for issue in issues if issue.severity == 'warning']
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details={'issues': [issue.__dict__ for issue in issues]}
        )
    
    async def _validate_vm_spec_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle VM spec validation request."""
        try:
            vm_spec_data = request.get('vm_spec')
            context_data = request.get('context')
            
            vm_spec = VMSpec(**vm_spec_data) if isinstance(vm_spec_data, dict) else vm_spec_data
            context = ValidationContext(**context_data) if context_data else None
            
            result = await self.validate_vm_spec(vm_spec, context)
            
            return {
                'success': True,
                'validation_result': result.dict(),
            }
        
        except Exception as e:
            self.logger.error(f"VM spec validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    async def _validate_basic_fields(self, vm_spec: VMSpec) -> List[ValidationIssue]:
        """Validate basic VM specification fields."""
        issues = []
        
        # VM name validation
        if not vm_spec.name:
            issues.append(ValidationIssue(
                severity='error',
                code='NAME_REQUIRED',
                message='VM name is required',
                field_path='name'
            ))
        elif len(vm_spec.name) > 50:
            issues.append(ValidationIssue(
                severity='error',
                code='NAME_TOO_LONG',
                message='VM name must be 50 characters or less',
                field_path='name',
                suggested_fix=f'Shorten name to: {vm_spec.name[:47]}...'
            ))
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', vm_spec.name):
            issues.append(ValidationIssue(
                severity='error',
                code='NAME_INVALID_FORMAT',
                message='VM name must start with a letter and contain only letters, numbers, underscores, and hyphens',
                field_path='name'
            ))
        
        # VM ID validation
        if vm_spec.vmid is not None:
            if vm_spec.vmid < 100 or vm_spec.vmid > 999999999:
                issues.append(ValidationIssue(
                    severity='error',
                    code='VMID_OUT_OF_RANGE',
                    message='VM ID must be between 100 and 999999999',
                    field_path='vmid'
                ))
        
        # Description validation
        if vm_spec.description and len(vm_spec.description) > 500:
            issues.append(ValidationIssue(
                severity='warning',
                code='DESCRIPTION_TOO_LONG',
                message='VM description is very long (>500 characters)',
                field_path='description'
            ))
        
        return issues
    
    async def _validate_hardware(self, vm_spec: VMSpec, 
                                context: Optional[ValidationContext] = None) -> List[ValidationIssue]:
        """Validate hardware configuration."""
        issues = []
        
        # Memory validation
        if vm_spec.memory < 128:
            issues.append(ValidationIssue(
                severity='error',
                code='MEMORY_TOO_LOW',
                message='Memory must be at least 128MB',
                field_path='memory',
                suggested_fix='Set memory to at least 128MB'
            ))
        elif vm_spec.memory < 512:
            issues.append(ValidationIssue(
                severity='warning',
                code='MEMORY_LOW',
                message='Memory less than 512MB may cause performance issues',
                field_path='memory'
            ))
        elif vm_spec.memory > 1048576:  # 1TB
            issues.append(ValidationIssue(
                severity='warning',
                code='MEMORY_VERY_HIGH',
                message='Memory allocation is very high (>1TB)',
                field_path='memory'
            ))
        
        # CPU validation
        if vm_spec.cores < 1:
            issues.append(ValidationIssue(
                severity='error',
                code='CORES_TOO_LOW',
                message='At least 1 CPU core is required',
                field_path='cores',
                suggested_fix='Set cores to at least 1'
            ))
        elif vm_spec.cores > 128:
            issues.append(ValidationIssue(
                severity='warning',
                code='CORES_VERY_HIGH',
                message='Very high core count (>128) may not be efficiently utilized',
                field_path='cores'
            ))
        
        if vm_spec.sockets < 1:
            issues.append(ValidationIssue(
                severity='error',
                code='SOCKETS_TOO_LOW',
                message='At least 1 CPU socket is required',
                field_path='sockets',
                suggested_fix='Set sockets to at least 1'
            ))
        elif vm_spec.sockets > 4:
            issues.append(ValidationIssue(
                severity='warning',
                code='SOCKETS_HIGH',
                message='High socket count (>4) may not be optimal for most workloads',
                field_path='sockets'
            ))
        
        # CPU type validation
        valid_cpu_types = ['host', 'kvm64', 'qemu64', 'Conroe', 'Penryn', 'Nehalem', 
                          'Westmere', 'SandyBridge', 'IvyBridge', 'Haswell', 'Broadwell', 
                          'Skylake-Client', 'Skylake-Server', 'Cascadelake-Server']
        
        if vm_spec.cpu_type not in valid_cpu_types:
            issues.append(ValidationIssue(
                severity='warning',
                code='CPU_TYPE_UNKNOWN',
                message=f'Unknown CPU type: {vm_spec.cpu_type}',
                field_path='cpu_type',
                suggested_fix=f'Consider using one of: {", ".join(valid_cpu_types[:5])}'
            ))
        
        return issues
    
    async def _validate_networks(self, vm_spec: VMSpec, 
                                context: Optional[ValidationContext] = None) -> List[ValidationIssue]:
        """Validate network configuration."""
        issues = []
        
        if not vm_spec.networks:
            issues.append(ValidationIssue(
                severity='warning',
                code='NO_NETWORKS',
                message='No network interfaces configured',
                field_path='networks',
                suggested_fix='Add at least one network interface'
            ))
            return issues
        
        used_interfaces = set()
        
        for i, network in enumerate(vm_spec.networks):
            field_prefix = f'networks[{i}]'
            
            # Interface name validation
            if network.interface in used_interfaces:
                issues.append(ValidationIssue(
                    severity='error',
                    code='DUPLICATE_INTERFACE',
                    message=f'Duplicate network interface: {network.interface}',
                    field_path=f'{field_prefix}.interface'
                ))
            used_interfaces.add(network.interface)
            
            # IP address validation
            if network.ip_address:
                try:
                    ip = ipaddress.ip_address(network.ip_address)
                    if ip.is_loopback:
                        issues.append(ValidationIssue(
                            severity='error',
                            code='IP_LOOPBACK',
                            message='Cannot use loopback IP address',
                            field_path=f'{field_prefix}.ip_address'
                        ))
                    elif ip.is_multicast:
                        issues.append(ValidationIssue(
                            severity='error',
                            code='IP_MULTICAST',
                            message='Cannot use multicast IP address',
                            field_path=f'{field_prefix}.ip_address'
                        ))
                except ValueError:
                    issues.append(ValidationIssue(
                        severity='error',
                        code='IP_INVALID',
                        message=f'Invalid IP address: {network.ip_address}',
                        field_path=f'{field_prefix}.ip_address'
                    ))
            
            # Gateway validation
            if network.gateway:
                try:
                    ipaddress.ip_address(network.gateway)
                except ValueError:
                    issues.append(ValidationIssue(
                        severity='error',
                        code='GATEWAY_INVALID',
                        message=f'Invalid gateway IP address: {network.gateway}',
                        field_path=f'{field_prefix}.gateway'
                    ))
            
            # VLAN validation
            if network.vlan_tag is not None:
                if network.vlan_tag < 1 or network.vlan_tag > 4094:
                    issues.append(ValidationIssue(
                        severity='error',
                        code='VLAN_OUT_OF_RANGE',
                        message='VLAN tag must be between 1 and 4094',
                        field_path=f'{field_prefix}.vlan_tag'
                    ))
        
        return issues
    
    async def _validate_storage(self, vm_spec: VMSpec, 
                               context: Optional[ValidationContext] = None) -> List[ValidationIssue]:
        """Validate storage configuration."""
        issues = []
        
        if not vm_spec.disks:
            issues.append(ValidationIssue(
                severity='warning',
                code='NO_DISKS',
                message='No disks configured',
                field_path='disks',
                suggested_fix='Add at least one disk'
            ))
            return issues
        
        used_interfaces = set()
        
        for i, disk in enumerate(vm_spec.disks):
            field_prefix = f'disks[{i}]'
            
            # Interface validation
            if disk.interface in used_interfaces:
                issues.append(ValidationIssue(
                    severity='error',
                    code='DUPLICATE_DISK_INTERFACE',
                    message=f'Duplicate disk interface: {disk.interface}',
                    field_path=f'{field_prefix}.interface'
                ))
            used_interfaces.add(disk.interface)
            
            # Size validation
            size_match = re.match(r'^(\d+)([KMGT]?)$', disk.size.upper())
            if not size_match:
                issues.append(ValidationIssue(
                    severity='error',
                    code='DISK_SIZE_INVALID',
                    message=f'Invalid disk size format: {disk.size}',
                    field_path=f'{field_prefix}.size',
                    suggested_fix='Use format like "20G", "512M", etc.'
                ))
            else:
                size_num, size_unit = size_match.groups()
                size_bytes = int(size_num)
                
                if size_unit == 'K':
                    size_bytes *= 1024
                elif size_unit == 'M':
                    size_bytes *= 1024 * 1024
                elif size_unit == 'G':
                    size_bytes *= 1024 * 1024 * 1024
                elif size_unit == 'T':
                    size_bytes *= 1024 * 1024 * 1024 * 1024
                
                # Check minimum size (100MB)
                if size_bytes < 100 * 1024 * 1024:
                    issues.append(ValidationIssue(
                        severity='warning',
                        code='DISK_SIZE_SMALL',
                        message=f'Disk size is very small: {disk.size}',
                        field_path=f'{field_prefix}.size'
                    ))
                
                # Check maximum size (reasonable limit: 100TB)
                elif size_bytes > 100 * 1024 * 1024 * 1024 * 1024:
                    issues.append(ValidationIssue(
                        severity='warning',
                        code='DISK_SIZE_LARGE',
                        message=f'Disk size is very large: {disk.size}',
                        field_path=f'{field_prefix}.size'
                    ))
            
            # Format validation
            valid_formats = ['raw', 'qcow2', 'vmdk']
            if disk.format not in valid_formats:
                issues.append(ValidationIssue(
                    severity='warning',
                    code='DISK_FORMAT_UNKNOWN',
                    message=f'Unknown disk format: {disk.format}',
                    field_path=f'{field_prefix}.format',
                    suggested_fix=f'Consider using: {", ".join(valid_formats)}'
                ))
            
            # Cache validation
            valid_cache = ['none', 'writethrough', 'writeback', 'unsafe', 'directsync']
            if disk.cache not in valid_cache:
                issues.append(ValidationIssue(
                    severity='warning',
                    code='DISK_CACHE_UNKNOWN',
                    message=f'Unknown cache mode: {disk.cache}',
                    field_path=f'{field_prefix}.cache'
                ))
        
        return issues
    
    async def _validate_node_resources(self, vm_spec: VMSpec, 
                                      context: ValidationContext) -> List[ValidationIssue]:
        """Validate that node has sufficient resources."""
        issues = []
        
        # This would check against actual Proxmox node resources
        # For now, we'll simulate some basic checks
        
        # Memory check (assume node has limited memory)
        if vm_spec.memory > 32768:  # 32GB
            issues.append(ValidationIssue(
                severity='warning',
                code='HIGH_MEMORY_USAGE',
                message='VM requires high memory allocation',
                field_path='memory'
            ))
        
        # Storage check
        total_disk_size = 0
        for disk in vm_spec.disks:
            # Parse disk size (simplified)
            size_match = re.match(r'^(\d+)([KMGT]?)$', disk.size.upper())
            if size_match:
                size_num, size_unit = size_match.groups()
                multipliers = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
                total_disk_size += int(size_num) * multipliers.get(size_unit, 1)
        
        if total_disk_size > 1024**4:  # 1TB
            issues.append(ValidationIssue(
                severity='warning',
                code='HIGH_STORAGE_USAGE',
                message='VM requires high storage allocation',
                field_path='disks'
            ))
        
        return issues
    
    async def _validate_naming_and_conflicts(self, vm_spec: VMSpec, 
                                           context: Optional[ValidationContext] = None) -> List[ValidationIssue]:
        """Validate naming conventions and check for conflicts."""
        issues = []
        
        # Check for reserved names
        reserved_names = ['proxmox', 'pve', 'localhost', 'router', 'gateway', 'dns']
        if vm_spec.name.lower() in reserved_names:
            issues.append(ValidationIssue(
                severity='warning',
                code='RESERVED_NAME',
                message=f'VM name "{vm_spec.name}" is a reserved name',
                field_path='name'
            ))
        
        # Naming convention checks
        if vm_spec.name.startswith('test-') or vm_spec.name.startswith('tmp-'):
            issues.append(ValidationIssue(
                severity='info',
                code='TEMPORARY_NAME',
                message='VM name suggests this is a temporary VM',
                field_path='name'
            ))
        
        # TODO: Check against existing VMs in Proxmox
        # This would require integration with Proxmox API
        
        return issues
    
    async def _validate_os_configuration(self, vm_spec: VMSpec) -> List[ValidationIssue]:
        """Validate OS-specific configuration."""
        issues = []
        
        # Windows-specific validations
        if vm_spec.os_type in [OSType.WINDOWS_2019, OSType.WINDOWS_2022]:
            if vm_spec.memory < 2048:
                issues.append(ValidationIssue(
                    severity='warning',
                    code='WINDOWS_LOW_MEMORY',
                    message='Windows VMs should have at least 2GB of RAM',
                    field_path='memory',
                    suggested_fix='Increase memory to at least 2048MB'
                ))
            
            # Windows typically needs more disk space
            for i, disk in enumerate(vm_spec.disks):
                size_match = re.match(r'^(\d+)([KMGT]?)$', disk.size.upper())
                if size_match:
                    size_num, size_unit = size_match.groups()
                    if size_unit == 'G' and int(size_num) < 40:
                        issues.append(ValidationIssue(
                            severity='warning',
                            code='WINDOWS_SMALL_DISK',
                            message='Windows VMs typically need at least 40GB disk space',
                            field_path=f'disks[{i}].size'
                        ))
        
        # Linux-specific validations
        else:
            if vm_spec.memory < 512:
                issues.append(ValidationIssue(
                    severity='info',
                    code='LINUX_LOW_MEMORY',
                    message='Consider increasing memory for better performance',
                    field_path='memory'
                ))
        
        return issues
    
    async def _validate_cloud_init(self, vm_spec: VMSpec) -> List[ValidationIssue]:
        """Validate cloud-init configuration."""
        issues = []
        
        # SSH keys validation
        for i, ssh_key in enumerate(vm_spec.ssh_keys):
            if not ssh_key.strip():
                issues.append(ValidationIssue(
                    severity='warning',
                    code='EMPTY_SSH_KEY',
                    message=f'Empty SSH key at index {i}',
                    field_path=f'ssh_keys[{i}]'
                ))
                continue
            
            # Basic SSH key format validation
            if not (ssh_key.startswith('ssh-rsa ') or 
                   ssh_key.startswith('ssh-ed25519 ') or 
                   ssh_key.startswith('ssh-dss ') or
                   ssh_key.startswith('ecdsa-sha2-')):
                issues.append(ValidationIssue(
                    severity='warning',
                    code='INVALID_SSH_KEY_FORMAT',
                    message=f'SSH key at index {i} may have invalid format',
                    field_path=f'ssh_keys[{i}]'
                ))
        
        # Username validation
        if vm_spec.user:
            if not re.match(r'^[a-z][a-z0-9_-]*$', vm_spec.user):
                issues.append(ValidationIssue(
                    severity='warning',
                    code='INVALID_USERNAME',
                    message='Username should start with lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens',
                    field_path='user'
                ))
            
            if vm_spec.user in ['root', 'admin', 'administrator']:
                issues.append(ValidationIssue(
                    severity='info',
                    code='PRIVILEGED_USERNAME',
                    message='Using privileged username - ensure this is intentional',
                    field_path='user'
                ))
        
        return issues
    
    async def _validate_hardware_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hardware validation request."""
        # Implementation for specific hardware validation
        return {'success': True, 'message': 'Hardware validation not yet implemented'}
    
    async def _validate_network_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle network validation request."""
        # Implementation for specific network validation
        return {'success': True, 'message': 'Network validation not yet implemented'}
    
    async def _validate_storage_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle storage validation request."""
        # Implementation for specific storage validation
        return {'success': True, 'message': 'Storage validation not yet implemented'}
    
    async def _validate_resources_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource validation request."""
        # Implementation for resource validation
        return {'success': True, 'message': 'Resource validation not yet implemented'}
    
    async def _check_conflicts_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conflict checking request."""
        # Implementation for conflict checking
        return {'success': True, 'message': 'Conflict checking not yet implemented'}
    
    def _setup_default_rules(self) -> None:
        """Setup default validation rules."""
        # This would load validation rules from configuration
        # For now, we implement the rules directly in the validation methods
        pass
