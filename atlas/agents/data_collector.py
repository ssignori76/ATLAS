"""
Data collection agent for the ATLAS system.

This agent is responsible for gathering and validating input parameters
for VM provisioning, including interactive data collection from users,
validation of inputs, and preparation of structured data for other agents.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from atlas.core import (
    get_logger,
    ValidationError,
    VMSpec,
    OSType,
    VMSize,
    NetworkConfig,
    DiskConfig,
    ValidationResult,
)
from .base import BaseAgent, AgentCapabilities


@dataclass
class DataCollectionRequest:
    """Request for data collection."""
    
    collection_type: str  # 'interactive', 'file', 'api'
    parameters: Dict[str, Any]
    validation_rules: Optional[List[str]] = None
    auto_validate: bool = True


@dataclass
class CollectedData:
    """Container for collected data."""
    
    vm_spec: VMSpec
    metadata: Dict[str, Any]
    collection_method: str
    collected_at: datetime
    validation_result: Optional[ValidationResult] = None


class DataCollectorAgent(BaseAgent):
    """Agent responsible for collecting and validating VM provisioning data."""
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the data collector agent."""
        super().__init__(agent_id, config)
        
        # Data collection state
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._collection_templates: Dict[str, Dict[str, Any]] = {}
        
        # Default validation rules
        self._validation_rules = self._setup_default_validation_rules()
    
    def _get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        return AgentCapabilities(
            name="DataCollectorAgent",
            version="1.0.0",
            description="Collects and validates VM provisioning parameters",
            supported_operations=[
                "collect_interactive",
                "collect_from_file",
                "collect_from_api",
                "validate_data",
                "get_templates",
                "create_template",
            ],
            input_types=["DataCollectionRequest", "VMSpec", "dict"],
            output_types=["CollectedData", "ValidationResult", "VMSpec"],
            dependencies=["validation_service"],
            resource_requirements={"memory": "256MB", "cpu": "0.1"},
            concurrent_requests=5,
        )
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process data collection request."""
        operation = request.get('operation')
        
        if operation == 'collect_interactive':
            return await self._collect_interactive(request.get('parameters', {}))
        elif operation == 'collect_from_file':
            return await self._collect_from_file(request.get('file_path'))
        elif operation == 'collect_from_api':
            return await self._collect_from_api(request.get('api_data'))
        elif operation == 'validate_data':
            return await self._validate_data(request.get('data'))
        elif operation == 'get_templates':
            return await self._get_templates()
        elif operation == 'create_template':
            return await self._create_template(request.get('template_data'))
        else:
            raise ValidationError(f"Unknown operation: {operation}")
    
    async def _collect_interactive(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data through interactive session."""
        self.logger.info("Starting interactive data collection")
        
        # Create collection session
        session_id = f"session_{datetime.utcnow().timestamp()}"
        self._active_sessions[session_id] = {
            'start_time': datetime.utcnow(),
            'collected_data': {},
            'step': 'basic_info',
        }
        
        try:
            # Collect basic VM information
            vm_data = await self._collect_basic_info(session_id, parameters)
            
            # Collect hardware configuration
            hardware_data = await self._collect_hardware_config(session_id, vm_data)
            
            # Collect network configuration
            network_data = await self._collect_network_config(session_id, hardware_data)
            
            # Collect storage configuration
            storage_data = await self._collect_storage_config(session_id, network_data)
            
            # Create VM specification
            vm_spec = self._create_vm_spec(storage_data)
            
            # Validate collected data
            validation_result = await self._validate_vm_spec(vm_spec)
            
            # Create collected data object
            collected_data = CollectedData(
                vm_spec=vm_spec,
                metadata={
                    'session_id': session_id,
                    'collection_method': 'interactive',
                    'user_inputs': storage_data,
                },
                collection_method='interactive',
                collected_at=datetime.utcnow(),
                validation_result=validation_result,
            )
            
            return {
                'success': True,
                'data': collected_data.vm_spec.dict(),
                'metadata': collected_data.metadata,
                'validation': validation_result.dict() if validation_result else None,
            }
        
        finally:
            # Clean up session
            self._active_sessions.pop(session_id, None)
    
    async def _collect_basic_info(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Collect basic VM information."""
        self.logger.debug(f"Collecting basic info for session {session_id}")
        
        # Initialize with parameters or prompt for input
        vm_data = {
            'name': parameters.get('name') or await self._prompt_for_input("VM Name", str, required=True),
            'description': parameters.get('description') or await self._prompt_for_input("Description", str),
            'os_type': parameters.get('os_type') or await self._prompt_for_choice(
                "Operating System",
                [os.value for os in OSType],
                default=OSType.UBUNTU_22_04.value
            ),
            'tags': parameters.get('tags', []),
        }
        
        # Update session
        session = self._active_sessions[session_id]
        session['collected_data'].update(vm_data)
        session['step'] = 'hardware_config'
        
        return vm_data
    
    async def _collect_hardware_config(self, session_id: str, vm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect hardware configuration."""
        self.logger.debug(f"Collecting hardware config for session {session_id}")
        
        # Check if size preset is specified
        size_preset = await self._prompt_for_choice(
            "VM Size Preset (or 'custom' for manual configuration)",
            [size.value for size in VMSize] + ['custom'],
            default=VMSize.MEDIUM.value
        )
        
        if size_preset != 'custom':
            # Use preset configuration
            size_configs = {
                VMSize.MICRO.value: {"memory": 512, "cores": 1},
                VMSize.SMALL.value: {"memory": 1024, "cores": 1},
                VMSize.MEDIUM.value: {"memory": 2048, "cores": 2},
                VMSize.LARGE.value: {"memory": 4096, "cores": 4},
                VMSize.XLARGE.value: {"memory": 8192, "cores": 8},
            }
            
            config = size_configs[size_preset]
            hardware_data = {
                **vm_data,
                'size_preset': VMSize(size_preset),
                'memory': config['memory'],
                'cores': config['cores'],
                'sockets': 1,
            }
        else:
            # Custom configuration
            hardware_data = {
                **vm_data,
                'memory': await self._prompt_for_input("Memory (MB)", int, default=2048),
                'cores': await self._prompt_for_input("CPU Cores", int, default=2),
                'sockets': await self._prompt_for_input("CPU Sockets", int, default=1),
            }
        
        # Update session
        session = self._active_sessions[session_id]
        session['collected_data'].update(hardware_data)
        session['step'] = 'network_config'
        
        return hardware_data
    
    async def _collect_network_config(self, session_id: str, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect network configuration."""
        self.logger.debug(f"Collecting network config for session {session_id}")
        
        # Basic network configuration
        network_config = NetworkConfig()
        
        # Check if custom network configuration is needed
        use_defaults = await self._prompt_for_confirmation(
            "Use default network configuration? (bridge: vmbr0, DHCP)",
            default=True
        )
        
        if not use_defaults:
            network_config.bridge = await self._prompt_for_input(
                "Network Bridge", str, default="vmbr0"
            )
            
            use_static_ip = await self._prompt_for_confirmation("Use static IP?", default=False)
            if use_static_ip:
                network_config.ip_address = await self._prompt_for_input("IP Address", str)
                network_config.gateway = await self._prompt_for_input("Gateway", str)
                network_config.netmask = await self._prompt_for_input(
                    "Netmask", str, default="255.255.255.0"
                )
        
        network_data = {
            **hardware_data,
            'networks': [network_config],
        }
        
        # Update session
        session = self._active_sessions[session_id]
        session['collected_data'].update(network_data)
        session['step'] = 'storage_config'
        
        return network_data
    
    async def _collect_storage_config(self, session_id: str, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect storage configuration."""
        self.logger.debug(f"Collecting storage config for session {session_id}")
        
        # Basic disk configuration
        disk_size = await self._prompt_for_input("Disk Size (e.g., 20G)", str, default="20G")
        storage_backend = await self._prompt_for_input("Storage Backend", str, default="local-lvm")
        
        disk_config = DiskConfig(
            size=disk_size,
            storage=storage_backend,
        )
        
        storage_data = {
            **network_data,
            'disks': [disk_config],
        }
        
        # Cloud-init configuration
        use_cloud_init = await self._prompt_for_confirmation("Enable cloud-init?", default=True)
        if use_cloud_init:
            ssh_keys = await self._prompt_for_multiple_inputs(
                "SSH Public Keys (one per line, empty line to finish)"
            )
            default_user = await self._prompt_for_input("Default Username", str, default="ubuntu")
            
            storage_data.update({
                'cloud_init': True,
                'ssh_keys': ssh_keys,
                'user': default_user,
            })
        
        # Update session
        session = self._active_sessions[session_id]
        session['collected_data'].update(storage_data)
        session['step'] = 'complete'
        
        return storage_data
    
    async def _collect_from_file(self, file_path: str) -> Dict[str, Any]:
        """Collect data from file."""
        self.logger.info(f"Collecting data from file: {file_path}")
        
        try:
            import yaml
            from pathlib import Path
            
            file_obj = Path(file_path)
            if not file_obj.exists():
                raise ValidationError(f"File not found: {file_path}")
            
            # Load file based on extension
            if file_obj.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
            elif file_obj.suffix.lower() == '.json':
                import json
                with open(file_path, 'r') as f:
                    data = json.load(f)
            else:
                raise ValidationError(f"Unsupported file format: {file_obj.suffix}")
            
            # Create VM specification
            vm_spec = VMSpec(**data)
            
            # Validate
            validation_result = await self._validate_vm_spec(vm_spec)
            
            return {
                'success': True,
                'data': vm_spec.dict(),
                'metadata': {
                    'collection_method': 'file',
                    'source_file': file_path,
                },
                'validation': validation_result.dict() if validation_result else None,
            }
        
        except Exception as e:
            self.logger.error(f"Error collecting data from file {file_path}: {e}")
            raise ValidationError(f"Failed to load data from file: {e}")
    
    async def _collect_from_api(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data from API call."""
        self.logger.info("Collecting data from API")
        
        try:
            # Create VM specification from API data
            vm_spec = VMSpec(**api_data)
            
            # Validate
            validation_result = await self._validate_vm_spec(vm_spec)
            
            return {
                'success': True,
                'data': vm_spec.dict(),
                'metadata': {
                    'collection_method': 'api',
                    'api_timestamp': datetime.utcnow().isoformat(),
                },
                'validation': validation_result.dict() if validation_result else None,
            }
        
        except Exception as e:
            self.logger.error(f"Error collecting data from API: {e}")
            raise ValidationError(f"Failed to process API data: {e}")
    
    async def _validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate collected data."""
        try:
            vm_spec = VMSpec(**data)
            validation_result = await self._validate_vm_spec(vm_spec)
            
            return {
                'success': True,
                'validation': validation_result.dict(),
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    async def _validate_vm_spec(self, vm_spec: VMSpec) -> ValidationResult:
        """Validate VM specification."""
        errors = []
        warnings = []
        
        # Validate required fields
        if not vm_spec.name:
            errors.append("VM name is required")
        
        if vm_spec.name and len(vm_spec.name) > 50:
            errors.append("VM name must be 50 characters or less")
        
        # Validate hardware limits
        if vm_spec.memory < 128:
            errors.append("Memory must be at least 128MB")
        elif vm_spec.memory < 512:
            warnings.append("Memory less than 512MB may cause performance issues")
        
        if vm_spec.cores < 1:
            errors.append("At least 1 CPU core is required")
        elif vm_spec.cores > 16:
            warnings.append("More than 16 cores may not be efficiently utilized")
        
        # Validate storage
        if not vm_spec.disks:
            warnings.append("No disks configured, adding default disk")
        
        # Validate network
        if not vm_spec.networks:
            warnings.append("No network interfaces configured, adding default interface")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _create_vm_spec(self, data: Dict[str, Any]) -> VMSpec:
        """Create VM specification from collected data."""
        # Convert data to VMSpec
        vm_spec_data = {
            'name': data['name'],
            'description': data.get('description'),
            'os_type': OSType(data['os_type']),
            'memory': data['memory'],
            'cores': data['cores'],
            'sockets': data.get('sockets', 1),
            'disks': data.get('disks', [DiskConfig(size="20G")]),
            'networks': data.get('networks', [NetworkConfig()]),
            'tags': data.get('tags', []),
            'cloud_init': data.get('cloud_init', True),
            'ssh_keys': data.get('ssh_keys', []),
            'user': data.get('user'),
        }
        
        # Remove None values
        vm_spec_data = {k: v for k, v in vm_spec_data.items() if v is not None}
        
        return VMSpec(**vm_spec_data)
    
    async def _prompt_for_input(self, prompt: str, input_type: type, 
                               default: Any = None, required: bool = False) -> Any:
        """Simulate user input prompt (would be replaced with actual UI)."""
        # This is a placeholder - in a real implementation, this would
        # interface with a web UI, CLI, or other interface
        
        if default is not None:
            return default
        elif input_type == str:
            return "example_value"
        elif input_type == int:
            return 1
        elif input_type == bool:
            return True
        else:
            return None
    
    async def _prompt_for_choice(self, prompt: str, choices: List[str], 
                                default: str = None) -> str:
        """Simulate choice prompt."""
        return default or choices[0]
    
    async def _prompt_for_confirmation(self, prompt: str, default: bool = False) -> bool:
        """Simulate confirmation prompt."""
        return default
    
    async def _prompt_for_multiple_inputs(self, prompt: str) -> List[str]:
        """Simulate multiple input prompt."""
        return []  # Return empty list for simulation
    
    async def _get_templates(self) -> Dict[str, Any]:
        """Get available data collection templates."""
        return {
            'success': True,
            'templates': list(self._collection_templates.keys()),
        }
    
    async def _create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new data collection template."""
        template_name = template_data.get('name')
        if not template_name:
            raise ValidationError("Template name is required")
        
        self._collection_templates[template_name] = template_data
        
        return {
            'success': True,
            'template_name': template_name,
        }
    
    def _setup_default_validation_rules(self) -> Dict[str, Any]:
        """Setup default validation rules."""
        return {
            'required_fields': ['name', 'os_type'],
            'memory_min': 128,
            'memory_max': 65536,
            'cores_min': 1,
            'cores_max': 32,
            'name_max_length': 50,
            'name_pattern': r'^[a-zA-Z][a-zA-Z0-9_-]*$',
        }
