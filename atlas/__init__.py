"""
ATLAS - Automated Template-based Logic for Administration Systems
A multi-agent system for automated Proxmox VM provisioning.
"""

__version__ = "0.1.0"
__author__ = "ATLAS Development Team"
__description__ = "AI-powered Proxmox VM provisioning system"

from .core.config import ATLASConfig
from .core.exceptions import ATLASError, ValidationError, ProxmoxError

__all__ = [
    "ATLASConfig",
    "ATLASError", 
    "ValidationError",
    "ProxmoxError"
]
