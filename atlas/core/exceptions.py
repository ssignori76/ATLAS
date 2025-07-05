"""
Custom exceptions for the ATLAS system.

This module defines all custom exceptions used throughout the ATLAS system,
providing clear error handling and debugging information.
"""


class AtlasError(Exception):
    """Base exception for all ATLAS errors."""
    
    def __init__(self, message: str, error_code: str = None):
        """Initialize with message and optional error code."""
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


class ConfigurationError(AtlasError):
    """Raised when there are configuration-related errors."""
    pass


class ValidationError(AtlasError):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: str = None, value=None):
        """Initialize with validation details."""
        super().__init__(message)
        self.field = field
        self.value = value


class ProxmoxError(AtlasError):
    """Raised when Proxmox operations fail."""
    
    def __init__(self, message: str, status_code: int = None, response_data=None):
        """Initialize with Proxmox-specific details."""
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ProxmoxConnectionError(ProxmoxError):
    """Raised when connection to Proxmox fails."""
    pass


class ProxmoxAuthenticationError(ProxmoxError):
    """Raised when Proxmox authentication fails."""
    pass


class ProxmoxResourceNotFoundError(ProxmoxError):
    """Raised when requested Proxmox resource is not found."""
    pass


class VMProvisioningError(AtlasError):
    """Raised when VM provisioning fails."""
    
    def __init__(self, message: str, vm_id: int = None, operation: str = None):
        """Initialize with VM provisioning details."""
        super().__init__(message)
        self.vm_id = vm_id
        self.operation = operation


class TerraformError(AtlasError):
    """Raised when Terraform operations fail."""
    
    def __init__(self, message: str, exit_code: int = None, stdout: str = None, stderr: str = None):
        """Initialize with Terraform execution details."""
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class AnsibleError(AtlasError):
    """Raised when Ansible operations fail."""
    
    def __init__(self, message: str, exit_code: int = None, stdout: str = None, stderr: str = None):
        """Initialize with Ansible execution details."""
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class AgentError(AtlasError):
    """Raised when agent operations fail."""
    
    def __init__(self, message: str, agent_name: str = None, agent_operation: str = None):
        """Initialize with agent details."""
        super().__init__(message)
        self.agent_name = agent_name
        self.agent_operation = agent_operation


class WorkflowError(AtlasError):
    """Raised when workflow execution fails."""
    
    def __init__(self, message: str, step: str = None, workflow: str = None):
        """Initialize with workflow details."""
        super().__init__(message)
        self.step = step
        self.workflow = workflow


class GenerationError(AtlasError):
    """Raised when code/config generation fails."""
    
    def __init__(self, message: str, generator: str = None, template: str = None):
        """Initialize with generation details."""
        super().__init__(message)
        self.generator = generator
        self.template = template


class TemplateError(GenerationError):
    """Raised when template processing fails."""
    pass


class FileOperationError(AtlasError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        """Initialize with file operation details."""
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation


class DependencyError(AtlasError):
    """Raised when external dependencies are missing or invalid."""
    
    def __init__(self, message: str, dependency: str = None, required_version: str = None):
        """Initialize with dependency details."""
        super().__init__(message)
        self.dependency = dependency
        self.required_version = required_version


class NetworkError(AtlasError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, endpoint: str = None, timeout: int = None):
        """Initialize with network details."""
        super().__init__(message)
        self.endpoint = endpoint
        self.timeout = timeout


class SecurityError(AtlasError):
    """Raised when security validations fail."""
    
    def __init__(self, message: str, security_check: str = None, severity: str = "medium"):
        """Initialize with security details."""
        super().__init__(message)
        self.security_check = security_check
        self.severity = severity


class ResourceError(AtlasError):
    """Raised when resource allocation or management fails."""
    
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        """Initialize with resource details."""
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class LockError(AtlasError):
    """Raised when resource locking fails."""
    
    def __init__(self, message: str, lock_id: str = None, lock_type: str = None):
        """Initialize with lock details."""
        super().__init__(message)
        self.lock_id = lock_id
        self.lock_type = lock_type


class TimeoutError(AtlasError):
    """Raised when operations timeout."""
    
    def __init__(self, message: str, timeout_seconds: int = None, operation: str = None):
        """Initialize with timeout details."""
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class CancellationError(AtlasError):
    """Raised when operations are cancelled."""
    
    def __init__(self, message: str, operation: str = None, reason: str = None):
        """Initialize with cancellation details."""
        super().__init__(message)
        self.operation = operation
        self.reason = reason


def handle_exception(exception: Exception, context: str = None) -> AtlasError:
    """Convert generic exceptions to ATLAS exceptions with context."""
    if isinstance(exception, AtlasError):
        return exception
    
    message = str(exception)
    if context:
        message = f"{context}: {message}"
    
    # Map common exception types
    if isinstance(exception, FileNotFoundError):
        return FileOperationError(message, operation="read")
    elif isinstance(exception, PermissionError):
        return FileOperationError(message, operation="permission")
    elif isinstance(exception, ConnectionError):
        return NetworkError(message)
    elif isinstance(exception, TimeoutError):
        return TimeoutError(message)
    elif isinstance(exception, ValueError):
        return ValidationError(message)
    elif isinstance(exception, KeyError):
        return ConfigurationError(f"Missing required configuration: {message}")
    else:
        return AtlasError(message, error_code="UNKNOWN_ERROR")
