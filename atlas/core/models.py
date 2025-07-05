"""
Data models for the ATLAS system.

This module defines Pydantic models for data validation and serialization
throughout the ATLAS system, including VM specifications, provisioning
parameters, and workflow configurations.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import IPvAnyAddress, PositiveInt


class VMSize(str, Enum):
    """Predefined VM sizes."""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class OSType(str, Enum):
    """Supported operating system types."""
    UBUNTU_20_04 = "ubuntu-20.04"
    UBUNTU_22_04 = "ubuntu-22.04"
    CENTOS_7 = "centos-7"
    CENTOS_8 = "centos-8"
    DEBIAN_11 = "debian-11"
    DEBIAN_12 = "debian-12"
    WINDOWS_2019 = "windows-2019"
    WINDOWS_2022 = "windows-2022"


class NetworkConfig(BaseModel):
    """Network configuration for a VM."""
    
    interface: str = Field(default="net0", description="Network interface name")
    bridge: str = Field(default="vmbr0", description="Bridge to connect to")
    model: str = Field(default="virtio", description="Network model")
    firewall: bool = Field(default=True, description="Enable firewall")
    ip_address: Optional[IPvAnyAddress] = Field(None, description="Static IP address")
    gateway: Optional[IPvAnyAddress] = Field(None, description="Gateway IP")
    netmask: str = Field(default="255.255.255.0", description="Network mask")
    vlan_tag: Optional[PositiveInt] = Field(None, description="VLAN tag")
    
    @validator('netmask')
    def validate_netmask(cls, v):
        """Validate netmask format."""
        # Allow CIDR notation or dotted decimal
        if '.' in v:
            parts = v.split('.')
            if len(parts) != 4 or not all(0 <= int(p) <= 255 for p in parts):
                raise ValueError("Invalid netmask format")
        elif v.startswith('/'):
            cidr = int(v[1:])
            if not 0 <= cidr <= 32:
                raise ValueError("Invalid CIDR notation")
        else:
            raise ValueError("Netmask must be in dotted decimal or CIDR format")
        return v


class DiskConfig(BaseModel):
    """Disk configuration for a VM."""
    
    interface: str = Field(default="scsi0", description="Disk interface")
    size: str = Field(description="Disk size (e.g., '20G', '100M')")
    storage: str = Field(default="local-lvm", description="Storage backend")
    format: str = Field(default="raw", description="Disk format")
    cache: str = Field(default="none", description="Cache mode")
    backup: bool = Field(default=True, description="Include in backups")
    replicate: bool = Field(default=False, description="Enable replication")
    ssd: bool = Field(default=False, description="SSD emulation")
    
    @validator('size')
    def validate_size(cls, v):
        """Validate disk size format."""
        import re
        if not re.match(r'^\d+[KMGT]?$', v.upper()):
            raise ValueError("Disk size must be in format like '20G', '512M', etc.")
        return v


class SoftwarePackage(BaseModel):
    """Software package specification with optional versioning."""
    
    name: str = Field(description="Package name (e.g., 'nginx', 'postgresql', 'docker')")
    version: Optional[str] = Field(None, description="Specific version (e.g., '1.20.2', 'latest', '~14.0')")
    source: Optional[str] = Field(None, description="Package source (e.g., 'apt', 'snap', 'docker', 'custom')")
    config: Optional[Dict[str, Any]] = Field(None, description="Package-specific configuration")
    enabled: bool = Field(default=True, description="Enable/start service after installation")
    
    @validator('version')
    def validate_version(cls, v):
        """Validate version format."""
        if v is None:
            return v
        
        # Allow common version patterns
        valid_patterns = [
            'latest', 'stable', 'lts',  # Special versions
        ]
        
        if v in valid_patterns:
            return v
        
        # Allow semantic versioning and ranges
        import re
        semver_pattern = r'^[~^]?\d+(\.\d+)*(-\w+)?(\+\w+)?$'
        if re.match(semver_pattern, v):
            return v
        
        raise ValueError(f"Invalid version format: {v}. Use semantic versioning, ranges (~1.2, ^2.0), or 'latest'")
    
    @root_validator
    def set_default_source(cls, values):
        """Set default source based on package name."""
        name = values.get('name')
        source = values.get('source')
        
        if source is None and name:
            # Default source mapping
            source_mapping = {
                'nginx': 'apt',
                'apache2': 'apt', 
                'postgresql': 'apt',
                'mysql': 'apt',
                'docker': 'docker.io',
                'nodejs': 'snap',
                'python': 'apt',
                'redis': 'apt',
                'mongodb': 'apt',
                'elasticsearch': 'apt',
                'kibana': 'apt',
                'grafana': 'apt',
                'prometheus': 'apt',
            }
            values['source'] = source_mapping.get(name.lower(), 'apt')
        
        return values


class SecurityConfig(BaseModel):
    """Security configuration for VM."""
    
    firewall_enabled: bool = Field(default=True, description="Enable host firewall")
    ssh_port: PositiveInt = Field(default=22, description="SSH port")
    fail2ban: bool = Field(default=True, description="Install and configure fail2ban")
    automatic_updates: bool = Field(default=True, description="Enable automatic security updates")
    allowed_ssh_users: List[str] = Field(default_factory=list, description="Users allowed to SSH")
    sudo_users: List[str] = Field(default_factory=list, description="Users with sudo access")
    
    # Advanced security options
    disable_root_login: bool = Field(default=True, description="Disable root SSH login")
    password_authentication: bool = Field(default=False, description="Allow password authentication")
    ufw_rules: List[str] = Field(default_factory=list, description="Custom UFW firewall rules")


class VMSpec(BaseModel):
    """Complete VM specification."""
    
    # Basic identification
    name: str = Field(description="VM name")
    vmid: Optional[PositiveInt] = Field(None, description="VM ID (auto-assigned if None)")
    description: Optional[str] = Field(None, description="VM description")
    tags: List[str] = Field(default_factory=list, description="VM tags")
    
    # Hardware configuration
    memory: PositiveInt = Field(default=2048, description="RAM in MB")
    cores: PositiveInt = Field(default=2, description="CPU cores")
    sockets: PositiveInt = Field(default=1, description="CPU sockets")
    numa: bool = Field(default=False, description="Enable NUMA")
    cpu_type: str = Field(default="kvm64", description="CPU type")
    
    # Operating system
    os_type: OSType = Field(description="Operating system type")
    template_id: Optional[PositiveInt] = Field(None, description="Template VM ID to clone")
    iso_path: Optional[str] = Field(None, description="ISO file path for manual installation")
    
    # Storage configuration
    disks: List[DiskConfig] = Field(default_factory=list, description="Disk configurations")
    
    # Network configuration
    networks: List[NetworkConfig] = Field(default_factory=list, description="Network configurations")
    
    # Cloud-init configuration
    cloud_init: bool = Field(default=True, description="Enable cloud-init")
    ssh_keys: List[str] = Field(default_factory=list, description="SSH public keys")
    user: Optional[str] = Field(None, description="Default user name")
    password: Optional[str] = Field(None, description="Default user password")
    
    # Software configuration
    software: List[SoftwarePackage] = Field(default_factory=list, description="Software packages to install")
    
    # Security configuration
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security settings")
    
    # Advanced options
    start_at_boot: bool = Field(default=False, description="Start VM at boot")
    protection: bool = Field(default=False, description="Prevent accidental removal")
    ballooning: bool = Field(default=True, description="Enable memory ballooning")
    
    # Size preset (alternative to manual hardware config)
    size_preset: Optional[VMSize] = Field(None, description="Use predefined size")
    
    @root_validator
    def validate_os_config(cls, values):
        """Validate OS configuration consistency."""
        template_id = values.get('template_id')
        iso_path = values.get('iso_path')
        
        if not template_id and not iso_path:
            raise ValueError("Either template_id or iso_path must be specified")
        
        if template_id and iso_path:
            raise ValueError("Cannot specify both template_id and iso_path")
        
        return values
    
    @root_validator
    def apply_size_preset(cls, values):
        """Apply size preset if specified."""
        size_preset = values.get('size_preset')
        if not size_preset:
            return values
        
        # Size configurations
        size_configs = {
            VMSize.MICRO: {"memory": 512, "cores": 1},
            VMSize.SMALL: {"memory": 1024, "cores": 1},
            VMSize.MEDIUM: {"memory": 2048, "cores": 2},
            VMSize.LARGE: {"memory": 4096, "cores": 4},
            VMSize.XLARGE: {"memory": 8192, "cores": 8},
        }
        
        config = size_configs[size_preset]
        
        # Only override if not explicitly set
        if values.get('memory') == 2048:  # Default value
            values['memory'] = config['memory']
        if values.get('cores') == 2:  # Default value
            values['cores'] = config['cores']
        
        return values
    
    def get_default_disk(self) -> DiskConfig:
        """Get default disk configuration."""
        return DiskConfig(size="20G")
    
    def get_default_network(self) -> NetworkConfig:
        """Get default network configuration."""
        return NetworkConfig()


class ProvisioningRequest(BaseModel):
    """Request for VM provisioning."""
    
    vm_spec: VMSpec = Field(description="VM specification")
    node: str = Field(description="Proxmox node to provision on")
    start_vm: bool = Field(default=True, description="Start VM after creation")
    wait_for_ip: bool = Field(default=True, description="Wait for VM to get IP")
    timeout: PositiveInt = Field(default=300, description="Timeout in seconds")
    
    # Ansible configuration
    ansible_playbook: Optional[str] = Field(None, description="Ansible playbook to run")
    ansible_vars: Dict[str, Any] = Field(default_factory=dict, description="Ansible variables")
    
    # Post-provisioning scripts
    post_scripts: List[str] = Field(default_factory=list, description="Scripts to run after provisioning")
    
    # Metadata
    created_by: str = Field(description="User who created the request")
    project: Optional[str] = Field(None, description="Project name")
    environment: str = Field(default="development", description="Environment")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ProvisioningStatus(str, Enum):
    """Provisioning status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProvisioningResult(BaseModel):
    """Result of VM provisioning."""
    
    request_id: str = Field(description="Unique request ID")
    vm_spec: VMSpec = Field(description="VM specification used")
    status: ProvisioningStatus = Field(description="Provisioning status")
    
    # Result details
    vm_id: Optional[PositiveInt] = Field(None, description="Assigned VM ID")
    ip_address: Optional[IPvAnyAddress] = Field(None, description="VM IP address")
    node: str = Field(description="Proxmox node used")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    # Error information
    error_message: Optional[str] = Field(None)
    error_details: Optional[Dict[str, Any]] = Field(None)
    
    # Generated files
    terraform_config: Optional[str] = Field(None, description="Generated Terraform config")
    ansible_playbook: Optional[str] = Field(None, description="Generated Ansible playbook")
    
    # Logs and output
    logs: List[str] = Field(default_factory=list, description="Provisioning logs")
    
    @property
    def duration(self) -> Optional[float]:
        """Get provisioning duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_running(self) -> bool:
        """Check if provisioning is currently running."""
        return self.status == ProvisioningStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if provisioning completed successfully."""
        return self.status == ProvisioningStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if provisioning failed."""
        return self.status == ProvisioningStatus.FAILED


class WorkflowStep(BaseModel):
    """Individual workflow step."""
    
    name: str = Field(description="Step name")
    agent: str = Field(description="Agent responsible for this step")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Step inputs")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Step outputs")
    depends_on: List[str] = Field(default_factory=list, description="Dependencies")
    timeout: PositiveInt = Field(default=600, description="Step timeout in seconds")
    retry_count: int = Field(default=0, description="Number of retries")
    max_retries: int = Field(default=3, description="Maximum retries")


class WorkflowConfig(BaseModel):
    """Workflow configuration."""
    
    name: str = Field(description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: List[WorkflowStep] = Field(description="Workflow steps")
    
    # Global settings
    parallel_execution: bool = Field(default=True, description="Allow parallel execution")
    fail_fast: bool = Field(default=True, description="Stop on first failure")
    timeout: PositiveInt = Field(default=3600, description="Total workflow timeout")
    
    # Validation
    @validator('steps')
    def validate_dependencies(cls, steps):
        """Validate step dependencies form a valid DAG."""
        step_names = {step.name for step in steps}
        
        for step in steps:
            for dep in step.depends_on:
                if dep not in step_names:
                    raise ValueError(f"Step '{step.name}' depends on unknown step '{dep}'")
        
        # TODO: Add cycle detection
        return steps


class ValidationRule(BaseModel):
    """Validation rule definition."""
    
    name: str = Field(description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    field_path: str = Field(description="JSONPath to field to validate")
    rule_type: str = Field(description="Type of validation rule")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters")
    severity: str = Field(default="error", description="Severity level")
    custom_message: Optional[str] = Field(None, description="Custom error message")


class ValidationResult(BaseModel):
    """Result of validation."""
    
    is_valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class InventoryEntry(BaseModel):
    """Ansible inventory entry."""
    
    hostname: str = Field(description="Host name")
    ip_address: IPvAnyAddress = Field(description="IP address")
    ssh_user: str = Field(default="root", description="SSH user")
    ssh_port: PositiveInt = Field(default=22, description="SSH port")
    ssh_key_path: Optional[Path] = Field(None, description="SSH key file path")
    groups: List[str] = Field(default_factory=list, description="Ansible groups")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Host variables")


class TerraformConfig(BaseModel):
    """Terraform configuration."""
    
    version: str = Field(default=">=1.0", description="Required Terraform version")
    providers: Dict[str, Any] = Field(default_factory=dict, description="Provider configurations")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Input variables")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output definitions")
    resources: Dict[str, Any] = Field(default_factory=dict, description="Resource definitions")
    
    firewall_enabled: bool = Field(default=True, description="Enable host firewall")
    ssh_port: PositiveInt = Field(default=22, description="SSH port")
    fail2ban: bool = Field(default=True, description="Install and configure fail2ban")
    automatic_updates: bool = Field(default=True, description="Enable automatic security updates")
    allowed_ssh_users: List[str] = Field(default_factory=list, description="Users allowed to SSH")
    sudo_users: List[str] = Field(default_factory=list, description="Users with sudo access")
    
    # Advanced security options
    disable_root_login: bool = Field(default=True, description="Disable root SSH login")
    password_authentication: bool = Field(default=False, description="Allow password authentication")
    ufw_rules: List[str] = Field(default_factory=list, description="Custom UFW firewall rules")
