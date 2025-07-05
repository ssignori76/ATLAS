"""
Core module initialization.

This module provides the core functionality for the ATLAS system,
including configuration management, logging, data models, and exceptions.
"""

from .config import (
    AtlasConfig,
    ProxmoxConfig,
    VMDefaults,
    SystemConfig,
    ConfigManager,
    get_config,
    get_config_manager,
    reload_config,
)

from .exceptions import (
    AtlasError,
    ConfigurationError,
    ValidationError,
    ProxmoxError,
    ProxmoxConnectionError,
    ProxmoxAuthenticationError,
    ProxmoxResourceNotFoundError,
    VMProvisioningError,
    TerraformError,
    AnsibleError,
    AgentError,
    WorkflowError,
    GenerationError,
    TemplateError,
    FileOperationError,
    DependencyError,
    NetworkError,
    SecurityError,
    ResourceError,
    LockError,
    TimeoutError,
    CancellationError,
    handle_exception,
)

from .logging import (
    setup_logging,
    get_logger,
    log_function_call,
    log_performance,
    LogContext,
    AtlasFormatter,
)

from .models import (
    VMSize,
    OSType,
    NetworkConfig,
    DiskConfig,
    VMSpec,
    ProvisioningRequest,
    ProvisioningStatus,
    ProvisioningResult,
    WorkflowStep,
    WorkflowConfig,
    ValidationRule,
    ValidationResult,
    InventoryEntry,
    TerraformConfig,
)

# Version information
__version__ = "0.1.0"
__author__ = "ATLAS Development Team"
__description__ = "Multi-agent AI system for automated VM provisioning on Proxmox"

# Package-level configuration
__all__ = [
    # Config
    "AtlasConfig",
    "ProxmoxConfig", 
    "VMDefaults",
    "SystemConfig",
    "ConfigManager",
    "get_config",
    "get_config_manager",
    "reload_config",
    
    # Exceptions
    "AtlasError",
    "ConfigurationError",
    "ValidationError",
    "ProxmoxError",
    "ProxmoxConnectionError",
    "ProxmoxAuthenticationError",
    "ProxmoxResourceNotFoundError",
    "VMProvisioningError",
    "TerraformError",
    "AnsibleError",
    "AgentError",
    "WorkflowError",
    "GenerationError",
    "TemplateError",
    "FileOperationError",
    "DependencyError",
    "NetworkError",
    "SecurityError",
    "ResourceError",
    "LockError",
    "TimeoutError",
    "CancellationError",
    "handle_exception",
    
    # Logging
    "setup_logging",
    "get_logger",
    "log_function_call",
    "log_performance",
    "LogContext",
    "AtlasFormatter",
    
    # Models
    "VMSize",
    "OSType",
    "NetworkConfig",
    "DiskConfig",
    "VMSpec",
    "ProvisioningRequest",
    "ProvisioningStatus",
    "ProvisioningResult",
    "WorkflowStep",
    "WorkflowConfig",
    "ValidationRule",
    "ValidationResult",
    "InventoryEntry",
    "TerraformConfig",
    
    # Package info
    "__version__",
    "__author__",
    "__description__",
]


def initialize_atlas():
    """Initialize the ATLAS system."""
    # Setup logging
    setup_logging()
    
    # Log system startup
    logger = get_logger(__name__)
    logger.info(f"Initializing ATLAS v{__version__}")
    
    try:
        # Load and validate configuration
        config = get_config()
        logger.info("Configuration loaded successfully")
        logger.debug(f"Work directory: {config.system.work_dir}")
        logger.debug(f"Proxmox host: {config.proxmox.host}")
        
    except Exception as e:
        logger.warning(f"Configuration not available during initialization: {e}")
        logger.info("ATLAS will use default settings")


# Initialize when module is imported
initialize_atlas()
