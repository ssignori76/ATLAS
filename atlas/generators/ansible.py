"""
Ansible configuration generator for the ATLAS system.

This module generates Ansible playbooks, inventories, and configuration files
for VM post-provisioning configuration and management.
"""

import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, Template

from atlas.core import (
    get_logger,
    GenerationError,
    TemplateError,
    VMSpec,
    OSType,
    InventoryEntry,
)


@dataclass
class AnsibleGenerationOptions:
    """Options for Ansible generation."""
    
    output_dir: Path = Path("./ansible")
    include_inventory: bool = True
    include_group_vars: bool = True
    include_host_vars: bool = True
    create_roles: bool = False
    use_collections: bool = True
    generate_requirements: bool = True
    vault_encrypt: bool = False


@dataclass
class PlaybookTask:
    """Represents an Ansible task."""
    
    name: str
    module: str
    parameters: Dict[str, Any]
    when: Optional[str] = None
    become: bool = False
    tags: List[str] = None
    register: Optional[str] = None


@dataclass
class PlaybookPlay:
    """Represents an Ansible play."""
    
    name: str
    hosts: str
    become: bool = False
    gather_facts: bool = True
    vars: Dict[str, Any] = None
    tasks: List[PlaybookTask] = None
    handlers: List[PlaybookTask] = None
    pre_tasks: List[PlaybookTask] = None
    post_tasks: List[PlaybookTask] = None


class AnsibleGenerator:
    """Generates Ansible configurations for VM management."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the Ansible generator.
        
        Args:
            templates_dir: Directory containing Ansible templates
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
        
        # Task templates for different OS types
        self._os_task_templates = self._setup_os_task_templates()
    
    def generate_vm_playbook(self, vm_spec: VMSpec,
                            configuration_type: str = "basic",
                            options: Optional[AnsibleGenerationOptions] = None) -> Dict[str, Any]:
        """Generate Ansible playbook for VM configuration.
        
        Args:
            vm_spec: VM specification
            configuration_type: Type of configuration (basic, web, database, etc.)
            options: Generation options
            
        Returns:
            Generated playbook data structure
        """
        self.logger.info(f"Generating Ansible playbook for VM: {vm_spec.name}")
        
        options = options or AnsibleGenerationOptions()
        
        try:
            # Create main play
            main_play = self._create_main_play(vm_spec, configuration_type)
            
            # Create playbook structure
            playbook = [main_play.to_dict()]
            
            return {
                'playbook': playbook,
                'playbook_name': f"{vm_spec.name}-config.yml",
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ansible playbook: {e}")
            raise GenerationError(f"Ansible playbook generation failed: {e}", "ansible", "playbook")
    
    def generate_inventory(self, vm_specs: List[VMSpec],
                          ip_mappings: Dict[str, str] = None,
                          options: Optional[AnsibleGenerationOptions] = None) -> Dict[str, Any]:
        """Generate Ansible inventory for VMs.
        
        Args:
            vm_specs: List of VM specifications
            ip_mappings: Mapping of VM names to IP addresses
            options: Generation options
            
        Returns:
            Generated inventory data structure
        """
        self.logger.info(f"Generating Ansible inventory for {len(vm_specs)} VMs")
        
        ip_mappings = ip_mappings or {}
        
        try:
            inventory = {
                'all': {
                    'children': {
                        'atlas_managed': {
                            'children': {}
                        }
                    }
                }
            }
            
            # Group VMs by OS type
            os_groups = {}
            for vm_spec in vm_specs:
                os_group = self._get_os_group_name(vm_spec.os_type)
                if os_group not in os_groups:
                    os_groups[os_group] = []
                os_groups[os_group].append(vm_spec)
            
            # Create groups and hosts
            for os_group, vms in os_groups.items():
                group_config = {
                    'hosts': {},
                    'vars': self._get_group_vars(os_group)
                }
                
                for vm_spec in vms:
                    host_config = self._create_host_config(vm_spec, ip_mappings.get(vm_spec.name))
                    group_config['hosts'][vm_spec.name] = host_config
                
                inventory['all']['children']['atlas_managed']['children'][os_group] = group_config
            
            return {
                'inventory': inventory,
                'inventory_file': 'inventory.yml',
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ansible inventory: {e}")
            raise GenerationError(f"Ansible inventory generation failed: {e}", "ansible", "inventory")
    
    def generate_files(self, playbook_data: Dict[str, Any],
                      inventory_data: Dict[str, Any] = None,
                      output_dir: Path = None,
                      options: Optional[AnsibleGenerationOptions] = None) -> Dict[str, Path]:
        """Generate Ansible files from data structures.
        
        Args:
            playbook_data: Playbook data
            inventory_data: Inventory data
            output_dir: Output directory
            options: Generation options
            
        Returns:
            Dictionary mapping file types to file paths
        """
        options = options or AnsibleGenerationOptions()
        output_dir = output_dir or options.output_dir
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        try:
            # Generate playbook file
            if playbook_data:
                playbook_content = yaml.dump(
                    playbook_data['playbook'],
                    default_flow_style=False,
                    indent=2,
                    sort_keys=False
                )
                
                playbook_file = output_dir / playbook_data['playbook_name']
                with open(playbook_file, 'w') as f:
                    f.write(playbook_content)
                generated_files['playbook'] = playbook_file
            
            # Generate inventory file
            if inventory_data and options.include_inventory:
                inventory_content = yaml.dump(
                    inventory_data['inventory'],
                    default_flow_style=False,
                    indent=2
                )
                
                inventory_file = output_dir / inventory_data['inventory_file']
                with open(inventory_file, 'w') as f:
                    f.write(inventory_content)
                generated_files['inventory'] = inventory_file
            
            # Generate ansible.cfg
            ansible_cfg = self._generate_ansible_cfg()
            cfg_file = output_dir / "ansible.cfg"
            with open(cfg_file, 'w') as f:
                f.write(ansible_cfg)
            generated_files['config'] = cfg_file
            
            # Generate requirements file
            if options.generate_requirements:
                requirements = self._generate_requirements()
                req_file = output_dir / "requirements.yml"
                with open(req_file, 'w') as f:
                    f.write(yaml.dump(requirements, default_flow_style=False))
                generated_files['requirements'] = req_file
            
            # Generate group_vars directory structure
            if options.include_group_vars:
                group_vars_dir = output_dir / "group_vars"
                group_vars_dir.mkdir(exist_ok=True)
                
                # Create all.yml
                all_vars = self._generate_all_group_vars()
                all_file = group_vars_dir / "all.yml"
                with open(all_file, 'w') as f:
                    f.write(yaml.dump(all_vars, default_flow_style=False))
                
                generated_files['group_vars'] = group_vars_dir
            
            # Generate host_vars directory structure
            if options.include_host_vars:
                host_vars_dir = output_dir / "host_vars"
                host_vars_dir.mkdir(exist_ok=True)
                generated_files['host_vars'] = host_vars_dir
            
            self.logger.info(f"Generated {len(generated_files)} Ansible files in {output_dir}")
            return generated_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ansible files: {e}")
            raise GenerationError(f"File generation failed: {e}", "ansible", "files")
    
    def _create_main_play(self, vm_spec: VMSpec, configuration_type: str) -> PlaybookPlay:
        """Create the main play for VM configuration."""
        tasks = []
        
        # Add basic system tasks
        tasks.extend(self._get_basic_system_tasks(vm_spec))
        
        # Add OS-specific tasks
        tasks.extend(self._get_os_specific_tasks(vm_spec))
        
        # Add configuration-type specific tasks
        tasks.extend(self._get_configuration_tasks(vm_spec, configuration_type))
        
        # Add custom tasks based on VM spec
        tasks.extend(self._get_custom_tasks(vm_spec))
        
        play = PlaybookPlay(
            name=f"Configure {vm_spec.name}",
            hosts=vm_spec.name,
            become=True,
            gather_facts=True,
            vars=self._get_play_vars(vm_spec),
            tasks=[task.to_dict() for task in tasks],
        )
        
        return play
    
    def _get_basic_system_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get basic system configuration tasks."""
        tasks = []
        
        # Update package cache
        if self._is_debian_based(vm_spec.os_type):
            tasks.append(PlaybookTask(
                name="Update apt cache",
                module="apt",
                parameters={
                    "update_cache": True,
                    "cache_valid_time": 3600
                },
                when="ansible_os_family == 'Debian'"
            ))
        elif self._is_redhat_based(vm_spec.os_type):
            tasks.append(PlaybookTask(
                name="Update yum cache",
                module="yum",
                parameters={
                    "update_cache": True
                },
                when="ansible_os_family == 'RedHat'"
            ))
        
        # Install basic packages
        basic_packages = self._get_basic_packages(vm_spec.os_type)
        if basic_packages:
            tasks.append(PlaybookTask(
                name="Install basic packages",
                module="package",
                parameters={
                    "name": basic_packages,
                    "state": "present"
                }
            ))
        
        # Configure timezone
        tasks.append(PlaybookTask(
            name="Set timezone",
            module="timezone",
            parameters={
                "name": "{{ timezone | default('UTC') }}"
            }
        ))
        
        # Configure NTP
        tasks.append(PlaybookTask(
            name="Ensure NTP is running",
            module="service",
            parameters={
                "name": "{{ ntp_service }}",
                "state": "started",
                "enabled": True
            }
        ))
        
        return tasks
    
    def _get_os_specific_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get OS-specific configuration tasks."""
        tasks = []
        
        if self._is_windows(vm_spec.os_type):
            # Windows-specific tasks
            tasks.extend(self._get_windows_tasks(vm_spec))
        else:
            # Linux-specific tasks
            tasks.extend(self._get_linux_tasks(vm_spec))
        
        return tasks
    
    def _get_linux_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get Linux-specific tasks."""
        tasks = []
        
        # Configure SSH
        if vm_spec.ssh_keys:
            tasks.append(PlaybookTask(
                name="Configure authorized SSH keys",
                module="authorized_key",
                parameters={
                    "user": vm_spec.user or "{{ ansible_user }}",
                    "key": "{{ item }}",
                    "state": "present"
                },
                # This would be a loop in actual Ansible
            ))
        
        # Configure sudo
        if vm_spec.user and vm_spec.user != "root":
            tasks.append(PlaybookTask(
                name="Configure sudo for user",
                module="user",
                parameters={
                    "name": vm_spec.user,
                    "groups": "sudo",
                    "append": True
                },
                when="ansible_os_family == 'Debian'"
            ))
            
            tasks.append(PlaybookTask(
                name="Configure sudo for user (RHEL)",
                module="user",
                parameters={
                    "name": vm_spec.user,
                    "groups": "wheel",
                    "append": True
                },
                when="ansible_os_family == 'RedHat'"
            ))
        
        # Configure firewall
        tasks.append(PlaybookTask(
            name="Configure basic firewall",
            module="firewalld",
            parameters={
                "service": "ssh",
                "permanent": True,
                "state": "enabled",
                "immediate": True
            },
            when="ansible_os_family == 'RedHat'"
        ))
        
        tasks.append(PlaybookTask(
            name="Configure UFW (Ubuntu/Debian)",
            module="ufw",
            parameters={
                "rule": "allow",
                "port": "22",
                "proto": "tcp"
            },
            when="ansible_os_family == 'Debian'"
        ))
        
        return tasks
    
    def _get_windows_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get Windows-specific tasks."""
        tasks = []
        
        # Configure WinRM
        tasks.append(PlaybookTask(
            name="Configure WinRM",
            module="win_service",
            parameters={
                "name": "WinRM",
                "state": "started",
                "start_mode": "auto"
            }
        ))
        
        # Install Chocolatey
        tasks.append(PlaybookTask(
            name="Install Chocolatey",
            module="win_chocolatey",
            parameters={
                "name": "chocolatey",
                "state": "present"
            }
        ))
        
        # Configure Windows Updates
        tasks.append(PlaybookTask(
            name="Install Windows Updates",
            module="win_updates",
            parameters={
                "category_names": ["SecurityUpdates", "CriticalUpdates"],
                "state": "installed"
            }
        ))
        
        return tasks
    
    def _get_configuration_tasks(self, vm_spec: VMSpec, configuration_type: str) -> List[PlaybookTask]:
        """Get configuration-type specific tasks."""
        tasks = []
        
        if configuration_type == "web":
            tasks.extend(self._get_web_server_tasks(vm_spec))
        elif configuration_type == "database":
            tasks.extend(self._get_database_tasks(vm_spec))
        elif configuration_type == "docker":
            tasks.extend(self._get_docker_tasks(vm_spec))
        elif configuration_type == "kubernetes":
            tasks.extend(self._get_kubernetes_tasks(vm_spec))
        
        return tasks
    
    def _get_web_server_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get web server configuration tasks."""
        tasks = []
        
        # Install nginx
        tasks.append(PlaybookTask(
            name="Install nginx",
            module="package",
            parameters={
                "name": "nginx",
                "state": "present"
            }
        ))
        
        # Start and enable nginx
        tasks.append(PlaybookTask(
            name="Start and enable nginx",
            module="service",
            parameters={
                "name": "nginx",
                "state": "started",
                "enabled": True
            }
        ))
        
        # Configure firewall for HTTP/HTTPS
        tasks.append(PlaybookTask(
            name="Allow HTTP traffic",
            module="firewalld",
            parameters={
                "service": "http",
                "permanent": True,
                "state": "enabled",
                "immediate": True
            },
            when="ansible_os_family == 'RedHat'"
        ))
        
        return tasks
    
    def _get_database_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get database configuration tasks."""
        tasks = []
        
        # Install PostgreSQL
        tasks.append(PlaybookTask(
            name="Install PostgreSQL",
            module="package",
            parameters={
                "name": ["postgresql", "postgresql-contrib"],
                "state": "present"
            }
        ))
        
        # Start and enable PostgreSQL
        tasks.append(PlaybookTask(
            name="Start and enable PostgreSQL",
            module="service",
            parameters={
                "name": "postgresql",
                "state": "started",
                "enabled": True
            }
        ))
        
        return tasks
    
    def _get_docker_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get Docker configuration tasks."""
        tasks = []
        
        # Install Docker
        tasks.append(PlaybookTask(
            name="Install Docker",
            module="package",
            parameters={
                "name": "docker.io",
                "state": "present"
            }
        ))
        
        # Start and enable Docker
        tasks.append(PlaybookTask(
            name="Start and enable Docker",
            module="service",
            parameters={
                "name": "docker",
                "state": "started",
                "enabled": True
            }
        ))
        
        return tasks
    
    def _get_kubernetes_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get Kubernetes configuration tasks."""
        tasks = []
        
        # This would include kubeadm, kubelet, kubectl installation and configuration
        # Simplified for this example
        
        return tasks
    
    def _get_custom_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get custom tasks based on VM specification."""
        tasks = []
        
        # Add tasks based on VM tags
        if "monitoring" in vm_spec.tags:
            tasks.extend(self._get_monitoring_tasks(vm_spec))
        
        if "backup" in vm_spec.tags:
            tasks.extend(self._get_backup_tasks(vm_spec))
        
        return tasks
    
    def _get_monitoring_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get monitoring configuration tasks."""
        return [
            PlaybookTask(
                name="Install node_exporter",
                module="package",
                parameters={
                    "name": "prometheus-node-exporter",
                    "state": "present"
                }
            )
        ]
    
    def _get_backup_tasks(self, vm_spec: VMSpec) -> List[PlaybookTask]:
        """Get backup configuration tasks."""
        return [
            PlaybookTask(
                name="Install backup tools",
                module="package",
                parameters={
                    "name": ["rsync", "cron"],
                    "state": "present"
                }
            )
        ]
    
    def _create_host_config(self, vm_spec: VMSpec, ip_address: str = None) -> Dict[str, Any]:
        """Create host configuration for inventory."""
        config = {}
        
        if ip_address:
            config['ansible_host'] = ip_address
        
        # Set connection parameters based on OS
        if self._is_windows(vm_spec.os_type):
            config.update({
                'ansible_connection': 'winrm',
                'ansible_winrm_server_cert_validation': 'ignore',
                'ansible_winrm_transport': 'basic',
                'ansible_winrm_port': 5985,
            })
        else:
            config.update({
                'ansible_connection': 'ssh',
                'ansible_port': 22,
                'ansible_user': vm_spec.user or 'root',
            })
        
        # Add VM-specific variables
        config.update({
            'vm_memory': vm_spec.memory,
            'vm_cores': vm_spec.cores,
            'vm_os_type': vm_spec.os_type.value,
            'vm_tags': vm_spec.tags,
        })
        
        return config
    
    def _get_play_vars(self, vm_spec: VMSpec) -> Dict[str, Any]:
        """Get variables for the play."""
        vars_dict = {
            'vm_name': vm_spec.name,
            'vm_description': vm_spec.description or '',
            'timezone': 'UTC',
        }
        
        # OS-specific variables
        if self._is_debian_based(vm_spec.os_type):
            vars_dict['ntp_service'] = 'ntp'
        elif self._is_redhat_based(vm_spec.os_type):
            vars_dict['ntp_service'] = 'chronyd'
        
        return vars_dict
    
    def _get_group_vars(self, group_name: str) -> Dict[str, Any]:
        """Get group variables."""
        return {
            'group_name': group_name,
            'managed_by': 'atlas',
        }
    
    def _generate_all_group_vars(self) -> Dict[str, Any]:
        """Generate variables for all group."""
        return {
            'atlas_managed': True,
            'timezone': 'UTC',
            'ntp_servers': [
                '0.pool.ntp.org',
                '1.pool.ntp.org',
                '2.pool.ntp.org',
                '3.pool.ntp.org',
            ],
        }
    
    def _generate_ansible_cfg(self) -> str:
        """Generate ansible.cfg content."""
        return """[defaults]
inventory = inventory.yml
host_key_checking = False
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts_cache
fact_caching_timeout = 86400
stdout_callback = yaml
callback_whitelist = timer, profile_tasks

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
pipelining = True
"""
    
    def _generate_requirements(self) -> Dict[str, Any]:
        """Generate requirements.yml content."""
        return {
            'collections': [
                'community.general',
                'ansible.posix',
                'community.docker',
                'kubernetes.core',
            ]
        }
    
    def _get_basic_packages(self, os_type: OSType) -> List[str]:
        """Get basic packages for OS type."""
        if self._is_debian_based(os_type):
            return ['curl', 'wget', 'vim', 'htop', 'git', 'rsync']
        elif self._is_redhat_based(os_type):
            return ['curl', 'wget', 'vim', 'htop', 'git', 'rsync']
        elif self._is_windows(os_type):
            return []  # Windows packages handled differently
        else:
            return []
    
    def _get_os_group_name(self, os_type: OSType) -> str:
        """Get group name for OS type."""
        if self._is_debian_based(os_type):
            return 'debian'
        elif self._is_redhat_based(os_type):
            return 'redhat'
        elif self._is_windows(os_type):
            return 'windows'
        else:
            return 'other'
    
    def _is_debian_based(self, os_type: OSType) -> bool:
        """Check if OS is Debian-based."""
        return os_type in [OSType.UBUNTU_20_04, OSType.UBUNTU_22_04, OSType.DEBIAN_11, OSType.DEBIAN_12]
    
    def _is_redhat_based(self, os_type: OSType) -> bool:
        """Check if OS is RedHat-based."""
        return os_type in [OSType.CENTOS_7, OSType.CENTOS_8]
    
    def _is_windows(self, os_type: OSType) -> bool:
        """Check if OS is Windows."""
        return os_type in [OSType.WINDOWS_2019, OSType.WINDOWS_2022]
    
    def _setup_builtin_templates(self) -> None:
        """Setup built-in templates."""
        # This would contain built-in Jinja2 templates
        pass
    
    def _setup_os_task_templates(self) -> Dict[str, Any]:
        """Setup OS-specific task templates."""
        return {}


# Helper classes
class PlaybookTask:
    """Represents an Ansible task."""
    
    def __init__(self, name: str, module: str, parameters: Dict[str, Any],
                 when: str = None, become: bool = False, tags: List[str] = None,
                 register: str = None):
        self.name = name
        self.module = module
        self.parameters = parameters
        self.when = when
        self.become = become
        self.tags = tags or []
        self.register = register
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        task_dict = {
            'name': self.name,
            self.module: self.parameters
        }
        
        if self.when:
            task_dict['when'] = self.when
        
        if self.become:
            task_dict['become'] = self.become
        
        if self.tags:
            task_dict['tags'] = self.tags
        
        if self.register:
            task_dict['register'] = self.register
        
        return task_dict


class PlaybookPlay:
    """Represents an Ansible play."""
    
    def __init__(self, name: str, hosts: str, become: bool = False,
                 gather_facts: bool = True, vars: Dict[str, Any] = None,
                 tasks: List[Dict[str, Any]] = None, handlers: List[Dict[str, Any]] = None,
                 pre_tasks: List[Dict[str, Any]] = None, post_tasks: List[Dict[str, Any]] = None):
        self.name = name
        self.hosts = hosts
        self.become = become
        self.gather_facts = gather_facts
        self.vars = vars or {}
        self.tasks = tasks or []
        self.handlers = handlers or []
        self.pre_tasks = pre_tasks or []
        self.post_tasks = post_tasks or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert play to dictionary."""
        play_dict = {
            'name': self.name,
            'hosts': self.hosts,
            'become': self.become,
            'gather_facts': self.gather_facts,
        }
        
        if self.vars:
            play_dict['vars'] = self.vars
        
        if self.pre_tasks:
            play_dict['pre_tasks'] = self.pre_tasks
        
        if self.tasks:
            play_dict['tasks'] = self.tasks
        
        if self.handlers:
            play_dict['handlers'] = self.handlers
        
        if self.post_tasks:
            play_dict['post_tasks'] = self.post_tasks
        
        return play_dict
