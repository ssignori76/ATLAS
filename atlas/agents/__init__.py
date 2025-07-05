"""
Agents module initialization.

This module provides the agent infrastructure for the ATLAS system,
including base agent functionality and specialized agents for different
aspects of VM provisioning.
"""

from .base import (
    BaseAgent,
    AgentStatus,
    MessageType,
    AgentMessage,
    AgentCapabilities,
)

from .data_collector import (
    DataCollectorAgent,
    DataCollectionRequest,
    CollectedData,
)

from .validation import (
    ValidationAgent,
    ValidationContext,
    ValidationIssue,
)

from .orchestrator import (
    OrchestrationAgent,
    WorkflowExecution,
    WorkflowStepStatus,
)

# Agent registry for dynamic loading
AGENT_REGISTRY = {
    'base': BaseAgent,
    'data_collector': DataCollectorAgent,
    'validation': ValidationAgent,
    'orchestrator': OrchestrationAgent,
}

# Export all public classes
__all__ = [
    # Base agent
    'BaseAgent',
    'AgentStatus',
    'MessageType',
    'AgentMessage',
    'AgentCapabilities',
    
    # Data collector
    'DataCollectorAgent',
    'DataCollectionRequest',
    'CollectedData',
    
    # Validation
    'ValidationAgent',
    'ValidationContext',
    'ValidationIssue',
    
    # Orchestrator
    'OrchestrationAgent',
    'WorkflowExecution',
    'WorkflowStepStatus',
    
    # Registry
    'AGENT_REGISTRY',
]


def create_agent(agent_type: str, agent_id: str = None, config: dict = None) -> BaseAgent:
    """Create an agent instance by type.
    
    Args:
        agent_type: Type of agent to create
        agent_id: Optional agent ID
        config: Optional configuration
        
    Returns:
        Agent instance
        
    Raises:
        ValueError: If agent type is unknown
    """
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    agent_class = AGENT_REGISTRY[agent_type]
    return agent_class(agent_id=agent_id, config=config)


def get_available_agents() -> list:
    """Get list of available agent types.
    
    Returns:
        List of agent type names
    """
    return list(AGENT_REGISTRY.keys())


def get_agent_info(agent_type: str) -> dict:
    """Get information about an agent type.
    
    Args:
        agent_type: Agent type to get info for
        
    Returns:
        Dictionary with agent information
        
    Raises:
        ValueError: If agent type is unknown
    """
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    agent_class = AGENT_REGISTRY[agent_type]
    
    # Create temporary instance to get capabilities
    temp_agent = agent_class()
    capabilities = temp_agent._get_capabilities()
    
    return {
        'name': agent_class.__name__,
        'module': agent_class.__module__,
        'capabilities': capabilities.__dict__,
        'description': agent_class.__doc__ or "No description available",
    }
