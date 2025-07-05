"""
Generators module initialization.

This module provides configuration and code generators for the ATLAS system,
including Terraform and Ansible configuration generation.
"""

from .terraform import (
    TerraformGenerator,
    TerraformGenerationOptions,
)

from .ansible import (
    AnsibleGenerator,
    AnsibleGenerationOptions,
    PlaybookTask,
    PlaybookPlay,
)

# Generator registry
GENERATOR_REGISTRY = {
    'terraform': TerraformGenerator,
    'ansible': AnsibleGenerator,
}

# Export all public classes
__all__ = [
    # Terraform
    'TerraformGenerator',
    'TerraformGenerationOptions',
    
    # Ansible
    'AnsibleGenerator',
    'AnsibleGenerationOptions',
    'PlaybookTask',
    'PlaybookPlay',
    
    # Registry
    'GENERATOR_REGISTRY',
]


def create_generator(generator_type: str, templates_dir=None):
    """Create a generator instance by type.
    
    Args:
        generator_type: Type of generator to create
        templates_dir: Optional templates directory
        
    Returns:
        Generator instance
        
    Raises:
        ValueError: If generator type is unknown
    """
    if generator_type not in GENERATOR_REGISTRY:
        raise ValueError(f"Unknown generator type: {generator_type}")
    
    generator_class = GENERATOR_REGISTRY[generator_type]
    return generator_class(templates_dir=templates_dir)


def get_available_generators() -> list:
    """Get list of available generator types.
    
    Returns:
        List of generator type names
    """
    return list(GENERATOR_REGISTRY.keys())
