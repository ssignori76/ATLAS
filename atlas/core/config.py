"""
Configuration management module for ATLAS.

This module handles loading, validation, and management of configuration
settings for the ATLAS system, including Proxmox connection parameters,
default VM settings, and system preferences.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from .exceptions import ConfigurationError


@dataclass
class ProxmoxConfig:
    """Configuration for Proxmox connection."""
    
    host: str
    port: int = 8006
    user: str = "root@pam"
    password: Optional[str] = None
    token_name: Optional[str] = None
    token_value: Optional[str] = None
    verify_ssl: bool = False
    timeout: int = 30


@dataclass
class VMDefaults:
    """Default VM configuration settings."""
    
    memory: int = 2048  # MB
    cores: int = 2
    disk_size: str = "20G"
    disk_storage: str = "local-lvm"
    network_bridge: str = "vmbr0"
    os_type: str = "l26"  # Linux 2.6+
    template_id: Optional[int] = None
    
    
@dataclass
class LLMConfig:
    """Configuration for LLM services (OpenAI, Azure OpenAI, etc.)."""
    
    provider: str = "openai"  # openai, azure, anthropic, local
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60
    
    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_name: Optional[str] = None
    
    # Local model settings
    local_model_path: Optional[str] = None
    local_api_port: int = 8000


@dataclass
class SystemConfig:
    """System-wide configuration settings."""
    
    work_dir: Path = field(default_factory=lambda: Path.home() / ".atlas")
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    terraform_path: str = "terraform"
    ansible_path: str = "ansible-playbook"
    backup_configs: bool = True
    dry_run_default: bool = False


@dataclass
class AtlasConfig:
    """Main ATLAS configuration container."""
    
    proxmox: ProxmoxConfig = field(default_factory=ProxmoxConfig)
    vm_defaults: VMDefaults = field(default_factory=VMDefaults)
    llm: LLMConfig = field(default_factory=LLMConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate the configuration settings."""
        # Validate Proxmox authentication
        if not (self.proxmox.password or 
                (self.proxmox.token_name and self.proxmox.token_value)):
            raise ConfigurationError(
                "Either password or token authentication must be configured"
            )
        
        # Validate LLM configuration
        if self.llm.provider in ["openai", "anthropic"] and not self.llm.api_key:
            raise ConfigurationError(
                f"API key is required for {self.llm.provider} provider"
            )
        
        if self.llm.provider == "azure" and not (
            self.llm.api_key and self.llm.azure_endpoint and self.llm.azure_deployment_name
        ):
            raise ConfigurationError(
                "Azure OpenAI requires api_key, azure_endpoint, and azure_deployment_name"
            )
        
        if self.llm.provider == "local" and not self.llm.local_model_path:
            raise ConfigurationError(
                "Local provider requires local_model_path"
            )
        
        # Validate work directory
        if not self.system.work_dir.exists():
            try:
                self.system.work_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigurationError(f"Cannot create work directory: {e}")


class ConfigManager:
    """Manages configuration loading, saving, and validation."""
    
    DEFAULT_CONFIG_FILE = "atlas.yaml"
    DEFAULT_CONFIG_PATHS = [
        Path.cwd() / DEFAULT_CONFIG_FILE,
        Path.home() / ".atlas" / DEFAULT_CONFIG_FILE,
        Path("/etc/atlas") / DEFAULT_CONFIG_FILE,
    ]
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Optional specific config file path
        """
        self.config_file = config_file
        self._config: Optional[AtlasConfig] = None
    
    def load_config(self) -> AtlasConfig:
        """Load configuration from file or environment.
        
        Returns:
            Loaded and validated configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or is invalid
        """
        if self._config is not None:
            return self._config
        
        # Load .env file if available
        if DOTENV_AVAILABLE:
            env_files = [
                Path.cwd() / ".env",
                Path.home() / ".atlas" / ".env",
            ]
            for env_file in env_files:
                if env_file.exists():
                    load_dotenv(env_file)
                    break
        
        config_data = {}
        
        # Try to load from file
        config_file = self._find_config_file()
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                raise ConfigurationError(f"Error loading config file {config_file}: {e}")
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create configuration object
        try:
            self._config = self._create_config_from_dict(config_data)
        except Exception as e:
            raise ConfigurationError(f"Error creating configuration: {e}")
        
        return self._config
    
    def save_config(self, config: AtlasConfig, config_file: Optional[Path] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save
            config_file: Optional specific file path
        """
        target_file = config_file or self.config_file or self.DEFAULT_CONFIG_PATHS[0]
        
        # Ensure directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        config_dict = self._config_to_dict(config)
        
        try:
            with open(target_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationError(f"Error saving config to {target_file}: {e}")
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in default locations."""
        if self.config_file and self.config_file.exists():
            return self.config_file
        
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        
        return None
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            # Proxmox settings
            'ATLAS_PROXMOX_HOST': ['proxmox', 'host'],
            'ATLAS_PROXMOX_PORT': ['proxmox', 'port'],
            'ATLAS_PROXMOX_USER': ['proxmox', 'user'],
            'ATLAS_PROXMOX_PASSWORD': ['proxmox', 'password'],
            'ATLAS_PROXMOX_TOKEN_NAME': ['proxmox', 'token_name'],
            'ATLAS_PROXMOX_TOKEN_VALUE': ['proxmox', 'token_value'],
            'ATLAS_PROXMOX_VERIFY_SSL': ['proxmox', 'verify_ssl'],
            
            # LLM settings
            'ATLAS_LLM_PROVIDER': ['llm', 'provider'],
            'ATLAS_LLM_API_KEY': ['llm', 'api_key'],
            'ATLAS_LLM_API_BASE_URL': ['llm', 'api_base_url'],
            'ATLAS_LLM_MODEL_NAME': ['llm', 'model_name'],
            'ATLAS_LLM_TEMPERATURE': ['llm', 'temperature'],
            'ATLAS_LLM_MAX_TOKENS': ['llm', 'max_tokens'],
            'ATLAS_LLM_AZURE_ENDPOINT': ['llm', 'azure_endpoint'],
            'ATLAS_LLM_AZURE_DEPLOYMENT_NAME': ['llm', 'azure_deployment_name'],
            'ATLAS_LLM_LOCAL_MODEL_PATH': ['llm', 'local_model_path'],
            
            # OpenAI compatibility
            'OPENAI_API_KEY': ['llm', 'api_key'],
            'OPENAI_BASE_URL': ['llm', 'api_base_url'],
            'AZURE_OPENAI_ENDPOINT': ['llm', 'azure_endpoint'],
            'AZURE_OPENAI_API_KEY': ['llm', 'api_key'],
            
            # System settings
            'ATLAS_LOG_LEVEL': ['system', 'log_level'],
            'ATLAS_WORK_DIR': ['system', 'work_dir'],
        }
        
        for env_var, key_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to the correct nested dict
                current = config_data
                for key in key_path[:-1]:
                    current = current.setdefault(key, {})
                
                # Convert value to appropriate type
                if key_path[-1] in ['port', 'timeout', 'max_tokens', 'local_api_port']:
                    value = int(value)
                elif key_path[-1] in ['verify_ssl']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif key_path[-1] in ['temperature']:
                    value = float(value)
                elif key_path[-1] == 'work_dir':
                    value = Path(value)
                
                current[key_path[-1]] = value
        
        return config_data
    
    def _create_config_from_dict(self, data: Dict[str, Any]) -> AtlasConfig:
        """Create configuration object from dictionary."""
        # Create Proxmox config
        proxmox_data = data.get('proxmox', {})
        proxmox_config = ProxmoxConfig(**proxmox_data)
        
        # Create VM defaults
        vm_data = data.get('vm_defaults', {})
        vm_defaults = VMDefaults(**vm_data)
        
        # Create LLM config
        llm_data = data.get('llm', {})
        llm_config = LLMConfig(**llm_data)
        
        # Create system config
        system_data = data.get('system', {})
        if 'work_dir' in system_data and isinstance(system_data['work_dir'], str):
            system_data['work_dir'] = Path(system_data['work_dir'])
        if 'log_file' in system_data and isinstance(system_data['log_file'], str):
            system_data['log_file'] = Path(system_data['log_file'])
        system_config = SystemConfig(**system_data)
        
        return AtlasConfig(
            proxmox=proxmox_config,
            vm_defaults=vm_defaults,
            llm=llm_config,
            system=system_config
        )
    
    def _config_to_dict(self, config: AtlasConfig) -> Dict[str, Any]:
        """Convert configuration object to dictionary."""
        return {
            'proxmox': {
                'host': config.proxmox.host,
                'port': config.proxmox.port,
                'user': config.proxmox.user,
                'password': config.proxmox.password,
                'token_name': config.proxmox.token_name,
                'token_value': config.proxmox.token_value,
                'verify_ssl': config.proxmox.verify_ssl,
                'timeout': config.proxmox.timeout,
            },
            'vm_defaults': {
                'memory': config.vm_defaults.memory,
                'cores': config.vm_defaults.cores,
                'disk_size': config.vm_defaults.disk_size,
                'disk_storage': config.vm_defaults.disk_storage,
                'network_bridge': config.vm_defaults.network_bridge,
                'os_type': config.vm_defaults.os_type,
                'template_id': config.vm_defaults.template_id,
            },
            'llm': {
                'provider': config.llm.provider,
                'api_key': config.llm.api_key,
                'api_base_url': config.llm.api_base_url,
                'model_name': config.llm.model_name,
                'temperature': config.llm.temperature,
                'max_tokens': config.llm.max_tokens,
                'timeout': config.llm.timeout,
                'azure_endpoint': config.llm.azure_endpoint,
                'azure_api_version': config.llm.azure_api_version,
                'azure_deployment_name': config.llm.azure_deployment_name,
                'local_model_path': config.llm.local_model_path,
                'local_api_port': config.llm.local_api_port,
            },
            'system': {
                'work_dir': str(config.system.work_dir),
                'log_level': config.system.log_level,
                'log_file': str(config.system.log_file) if config.system.log_file else None,
                'terraform_path': config.system.terraform_path,
                'ansible_path': config.system.ansible_path,
                'backup_configs': config.system.backup_configs,
                'dry_run_default': config.system.dry_run_default,
            }
        }


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[Path] = None) -> ConfigManager:
    """Get or create global configuration manager instance."""
    global _config_manager
    if _config_manager is None or config_file is not None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> AtlasConfig:
    """Get current configuration."""
    return get_config_manager().load_config()


def reload_config(config_file: Optional[Path] = None) -> AtlasConfig:
    """Reload configuration from file."""
    global _config_manager
    _config_manager = None
    return get_config_manager(config_file).load_config()
