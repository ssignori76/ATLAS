"""
Terraform configuration generator for the ATLAS system.

This module generates Terraform configurations for VM provisioning on Proxmox,
including resource definitions, variables, outputs, and provider configurations.
"""

import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, Template

from atlas.core import (
    get_logger,
    GenerationError,
    TemplateError,
    VMSpec,
    NetworkConfig,
    DiskConfig,
    TerraformConfig,
)


@dataclass
class TerraformGenerationOptions:
    """Options for Terraform generation."""
    
    output_dir: Path = Path("./terraform")
    include_variables: bool = True
    include_outputs: bool = True
    include_provider: bool = True
    use_modules: bool = False
    format_code: bool = True
    create_workspace: bool = False
    workspace_name: Optional[str] = None


class TerraformGenerator:
    """Generates Terraform configurations for Proxmox VM provisioning."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the Terraform generator.
        
        Args:
            templates_dir: Directory containing Terraform templates
        """
        self.logger = get_logger(__name__)
        
        # Setup Jinja2 environment
        if templates_dir and templates_dir.exists():
            self.jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))
        else:
            # Use built-in templates
            self.jinja_env = Environment(loader=FileSystemLoader('.'))
            self._setup_builtin_templates()
        
        # Template cache
        self._template_cache: Dict[str, Template] = {}
    
    def generate_vm_configuration(self, vm_spec: VMSpec, 
                                 proxmox_config: Dict[str, Any],
                                 options: Optional[TerraformGenerationOptions] = None) -> TerraformConfig:
        """Generate Terraform configuration for a VM.
        
        Args:
            vm_spec: VM specification
            proxmox_config: Proxmox connection configuration
            options: Generation options
            
        Returns:
            Generated Terraform configuration
        """
        self.logger.info(f"Generating Terraform configuration for VM: {vm_spec.name}")
        
        options = options or TerraformGenerationOptions()
        
        try:
            # Generate main VM resource
            vm_resource = self._generate_vm_resource(vm_spec)
            
            # Generate provider configuration
            provider_config = self._generate_provider_config(proxmox_config) if options.include_provider else {}
            
            # Generate variables
            variables = self._generate_variables(vm_spec) if options.include_variables else {}
            
            # Generate outputs
            outputs = self._generate_outputs(vm_spec) if options.include_outputs else {}
            
            # Create Terraform configuration
            terraform_config = TerraformConfig(
                version=">=1.0",
                providers=provider_config,
                variables=variables,
                outputs=outputs,
                resources={'proxmox_vm_qemu': {vm_spec.name: vm_resource}},
            )
            
            return terraform_config
            
        except Exception as e:
            self.logger.error(f"Failed to generate Terraform configuration: {e}")
            raise GenerationError(f"Terraform generation failed: {e}", "terraform", "vm_config")
    
    def generate_files(self, terraform_config: TerraformConfig, 
                      output_dir: Path,
                      options: Optional[TerraformGenerationOptions] = None) -> Dict[str, Path]:
        """Generate Terraform files from configuration.
        
        Args:
            terraform_config: Terraform configuration
            output_dir: Output directory
            options: Generation options
            
        Returns:
            Dictionary mapping file types to file paths
        """
        options = options or TerraformGenerationOptions()
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        try:
            # Generate main configuration file
            main_tf = self._generate_main_tf(terraform_config)
            main_file = output_dir / "main.tf"
            with open(main_file, 'w') as f:
                f.write(main_tf)
            generated_files['main'] = main_file
            
            # Generate variables file
            if terraform_config.variables:
                variables_tf = self._generate_variables_tf(terraform_config.variables)
                variables_file = output_dir / "variables.tf"
                with open(variables_file, 'w') as f:
                    f.write(variables_tf)
                generated_files['variables'] = variables_file
            
            # Generate outputs file
            if terraform_config.outputs:
                outputs_tf = self._generate_outputs_tf(terraform_config.outputs)
                outputs_file = output_dir / "outputs.tf"
                with open(outputs_file, 'w') as f:
                    f.write(outputs_tf)
                generated_files['outputs'] = outputs_file
            
            # Generate terraform.tfvars file
            tfvars_content = self._generate_tfvars(terraform_config)
            tfvars_file = output_dir / "terraform.tfvars"
            with open(tfvars_file, 'w') as f:
                f.write(tfvars_content)
            generated_files['tfvars'] = tfvars_file
            
            # Generate versions file
            versions_tf = self._generate_versions_tf(terraform_config)
            versions_file = output_dir / "versions.tf"
            with open(versions_file, 'w') as f:
                f.write(versions_tf)
            generated_files['versions'] = versions_file
            
            self.logger.info(f"Generated {len(generated_files)} Terraform files in {output_dir}")
            return generated_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate Terraform files: {e}")
            raise GenerationError(f"File generation failed: {e}", "terraform", "files")
    
    def _generate_vm_resource(self, vm_spec: VMSpec) -> Dict[str, Any]:
        """Generate VM resource configuration."""
        resource = {
            'name': vm_spec.name,
            'target_node': '${var.proxmox_node}',
            'clone': '${var.template_name}' if vm_spec.template_id else None,
            'vmid': vm_spec.vmid,
            'desc': vm_spec.description,
            'tags': ','.join(vm_spec.tags) if vm_spec.tags else None,
            
            # Hardware
            'memory': vm_spec.memory,
            'cores': vm_spec.cores,
            'sockets': vm_spec.sockets,
            'cpu': vm_spec.cpu_type,
            'numa': vm_spec.numa,
            'balloon': vm_spec.ballooning,
            
            # OS
            'os_type': self._map_os_type(vm_spec.os_type),
            
            # Lifecycle
            'onboot': vm_spec.start_at_boot,
            'protection': vm_spec.protection,
        }
        
        # Add disks
        disks = {}
        for i, disk in enumerate(vm_spec.disks):
            disk_config = self._generate_disk_config(disk)
            if i == 0:
                # First disk is usually scsi0 or ide0
                key = disk.interface or 'scsi0'
            else:
                key = disk.interface or f'scsi{i}'
            disks[key] = disk_config
        
        if disks:
            resource.update(disks)
        
        # Add networks
        networks = {}
        for i, network in enumerate(vm_spec.networks):
            network_config = self._generate_network_config(network)
            key = network.interface or f'net{i}'
            networks[key] = network_config
        
        if networks:
            resource.update(networks)
        
        # Add cloud-init if enabled
        if vm_spec.cloud_init:
            cloud_init_config = self._generate_cloud_init_config(vm_spec)
            resource.update(cloud_init_config)
        
        # Remove None values
        return {k: v for k, v in resource.items() if v is not None}
    
    def _generate_disk_config(self, disk: DiskConfig) -> str:
        """Generate disk configuration string."""
        config_parts = [
            f"{disk.storage}:{disk.size}",
            f"format={disk.format}",
            f"cache={disk.cache}",
        ]
        
        if disk.backup:
            config_parts.append("backup=1")
        else:
            config_parts.append("backup=0")
        
        if disk.replicate:
            config_parts.append("replicate=1")
        
        if disk.ssd:
            config_parts.append("ssd=1")
        
        return ','.join(config_parts)
    
    def _generate_network_config(self, network: NetworkConfig) -> str:
        """Generate network configuration string."""
        config_parts = [
            f"{network.model}",
            f"bridge={network.bridge}",
        ]
        
        if network.firewall:
            config_parts.append("firewall=1")
        
        if network.vlan_tag:
            config_parts.append(f"tag={network.vlan_tag}")
        
        return ','.join(config_parts)
    
    def _generate_cloud_init_config(self, vm_spec: VMSpec) -> Dict[str, Any]:
        """Generate cloud-init configuration."""
        config = {}
        
        # SSH keys
        if vm_spec.ssh_keys:
            config['sshkeys'] = '\\n'.join(vm_spec.ssh_keys)
        
        # User configuration
        if vm_spec.user:
            config['ciuser'] = vm_spec.user
        
        if vm_spec.password:
            config['cipassword'] = vm_spec.password
        
        # IP configuration
        for i, network in enumerate(vm_spec.networks):
            if network.ip_address:
                ip_config = f"{network.ip_address}/{self._cidr_from_netmask(network.netmask)}"
                if network.gateway:
                    ip_config += f",gw={network.gateway}"
                config[f'ipconfig{i}'] = ip_config
        
        return config
    
    def _generate_provider_config(self, proxmox_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate provider configuration."""
        return {
            'proxmox': {
                'version': '~> 2.9',
                'pm_api_url': f"https://{proxmox_config['host']}:{proxmox_config.get('port', 8006)}/api2/json",
                'pm_user': proxmox_config['user'],
                'pm_password': proxmox_config.get('password'),
                'pm_tls_insecure': not proxmox_config.get('verify_ssl', False),
                'pm_api_token_id': proxmox_config.get('token_name'),
                'pm_api_token_secret': proxmox_config.get('token_value'),
            }
        }
    
    def _generate_variables(self, vm_spec: VMSpec) -> Dict[str, Any]:
        """Generate variable definitions."""
        variables = {
            'proxmox_node': {
                'description': 'Proxmox node to deploy to',
                'type': 'string',
                'default': 'pve',
            },
            'vm_name': {
                'description': 'Name of the VM',
                'type': 'string',
                'default': vm_spec.name,
            },
        }
        
        if vm_spec.template_id:
            variables['template_name'] = {
                'description': 'Template to clone from',
                'type': 'string',
                'default': f'template-{vm_spec.template_id}',
            }
        
        return variables
    
    def _generate_outputs(self, vm_spec: VMSpec) -> Dict[str, Any]:
        """Generate output definitions."""
        return {
            'vm_id': {
                'description': 'ID of the created VM',
                'value': f'${{proxmox_vm_qemu.{vm_spec.name}.id}}',
            },
            'vm_name': {
                'description': 'Name of the created VM',
                'value': f'${{proxmox_vm_qemu.{vm_spec.name}.name}}',
            },
            'default_ipv4_address': {
                'description': 'Default IPv4 address of the VM',
                'value': f'${{proxmox_vm_qemu.{vm_spec.name}.default_ipv4_address}}',
            },
        }
    
    def _generate_main_tf(self, config: TerraformConfig) -> str:
        """Generate main.tf content."""
        lines = []
        
        # Resources
        if config.resources:
            for resource_type, resources in config.resources.items():
                for resource_name, resource_config in resources.items():
                    lines.append(f'resource "{resource_type}" "{resource_name}" {{')
                    for key, value in resource_config.items():
                        if isinstance(value, str):
                            lines.append(f'  {key} = "{value}"')
                        elif isinstance(value, bool):
                            lines.append(f'  {key} = {str(value).lower()}')
                        elif isinstance(value, (int, float)):
                            lines.append(f'  {key} = {value}')
                        elif value is not None:
                            lines.append(f'  {key} = {json.dumps(value)}')
                    lines.append('}')
                    lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_variables_tf(self, variables: Dict[str, Any]) -> str:
        """Generate variables.tf content."""
        lines = []
        
        for var_name, var_config in variables.items():
            lines.append(f'variable "{var_name}" {{')
            for key, value in var_config.items():
                if isinstance(value, str):
                    lines.append(f'  {key} = "{value}"')
                else:
                    lines.append(f'  {key} = {json.dumps(value)}')
            lines.append('}')
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_outputs_tf(self, outputs: Dict[str, Any]) -> str:
        """Generate outputs.tf content."""
        lines = []
        
        for output_name, output_config in outputs.items():
            lines.append(f'output "{output_name}" {{')
            for key, value in output_config.items():
                if key == 'value':
                    lines.append(f'  {key} = {value}')
                else:
                    lines.append(f'  {key} = "{value}"')
            lines.append('}')
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_versions_tf(self, config: TerraformConfig) -> str:
        """Generate versions.tf content."""
        lines = ['terraform {']
        lines.append(f'  required_version = "{config.version}"')
        
        if config.providers:
            lines.append('  required_providers {')
            for provider_name, provider_config in config.providers.items():
                if isinstance(provider_config, dict) and 'version' in provider_config:
                    lines.append(f'    {provider_name} = {{')
                    lines.append(f'      source  = "Telmate/{provider_name}"')
                    lines.append(f'      version = "{provider_config["version"]}"')
                    lines.append('    }')
            lines.append('  }')
        
        lines.append('}')
        lines.append('')
        
        # Provider configurations
        if config.providers:
            for provider_name, provider_config in config.providers.items():
                lines.append(f'provider "{provider_name}" {{')
                for key, value in provider_config.items():
                    if key != 'version':
                        if isinstance(value, str):
                            lines.append(f'  {key} = "{value}"')
                        elif isinstance(value, bool):
                            lines.append(f'  {key} = {str(value).lower()}')
                        else:
                            lines.append(f'  {key} = {value}')
                lines.append('}')
                lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_tfvars(self, config: TerraformConfig) -> str:
        """Generate terraform.tfvars content."""
        lines = ['# Terraform variables']
        lines.append('# Customize these values for your environment')
        lines.append('')
        
        # Generate sample values for variables
        if config.variables:
            for var_name, var_config in config.variables.items():
                description = var_config.get('description', '')
                default_value = var_config.get('default')
                
                if description:
                    lines.append(f'# {description}')
                
                if default_value is not None:
                    if isinstance(default_value, str):
                        lines.append(f'{var_name} = "{default_value}"')
                    else:
                        lines.append(f'{var_name} = {json.dumps(default_value)}')
                else:
                    lines.append(f'# {var_name} = ""')
                
                lines.append('')
        
        return '\n'.join(lines)
    
    def _map_os_type(self, os_type) -> str:
        """Map OSType to Proxmox OS type."""
        from atlas.core.models import OSType
        
        mapping = {
            OSType.UBUNTU_20_04: 'l26',
            OSType.UBUNTU_22_04: 'l26',
            OSType.CENTOS_7: 'l26',
            OSType.CENTOS_8: 'l26',
            OSType.DEBIAN_11: 'l26',
            OSType.DEBIAN_12: 'l26',
            OSType.WINDOWS_2019: 'win10',
            OSType.WINDOWS_2022: 'win11',
        }
        
        return mapping.get(os_type, 'l26')
    
    def _cidr_from_netmask(self, netmask: str) -> int:
        """Convert netmask to CIDR notation."""
        if netmask.startswith('/'):
            return int(netmask[1:])
        
        # Convert dotted decimal to CIDR
        import ipaddress
        try:
            network = ipaddress.IPv4Network(f'0.0.0.0/{netmask}', strict=False)
            return network.prefixlen
        except ValueError:
            return 24  # Default to /24
    
    def _setup_builtin_templates(self) -> None:
        """Setup built-in templates."""
        # This would contain built-in Jinja2 templates for complex scenarios
        pass
