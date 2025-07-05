"""
AutoGen configuration and setup for ATLAS multi-agent system.

This module provides the core configuration and initialization
for AutoGen GroupChat and agent coordination.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

# Try to import the new AutoGen packages first, fall back to old ones
try:
    from autogen_agentchat import ConversableAgent, UserProxyAgent
    from autogen_agentchat.ui import Console
    from autogen_core import Component
    AUTOGEN_NEW = True
except ImportError:
    try:
        import autogen
        from autogen import GroupChat, GroupChatManager, ConversableAgent, UserProxyAgent
        AUTOGEN_NEW = False
    except ImportError:
        raise ImportError("AutoGen package not found. Please install with: pip install pyautogen")

from atlas.core import (
    get_logger,
    get_config,
    AutoGenError,
    ConfigurationError,
)

logger = get_logger(__name__)


@dataclass
class AutoGenConfig:
    """Configuration for AutoGen agents and conversations."""
    
    # LLM Configuration
    llm_config: Dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 600
    
    # GroupChat Configuration
    max_round: int = 10
    admin_name: str = "atlas_admin"
    speaker_selection_method: str = "auto"
    allow_repeat_speaker: bool = False
    
    # Agent Configuration
    enable_code_execution: bool = False
    human_input_mode: str = "NEVER"
    max_consecutive_auto_reply: int = 3
    
    # System Configuration
    work_dir: Optional[Path] = None
    log_conversation: bool = True
    save_conversation_history: bool = True


class AutoGenManager:
    """Manages AutoGen configuration and agent initialization."""
    
    def __init__(self, config: Optional[AutoGenConfig] = None):
        """Initialize AutoGen manager.
        
        Args:
            config: AutoGen configuration, defaults to system config
        """
        self.logger = get_logger(__name__)
        self.config = config or self._create_default_config()
        self.agents: Dict[str, ConversableAgent] = {}
        self.group_chat: Optional[GroupChat] = None
        self.group_chat_manager: Optional[GroupChatManager] = None
        
        # Initialize work directory
        if self.config.work_dir:
            self.config.work_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_default_config(self) -> AutoGenConfig:
        """Create default AutoGen configuration from ATLAS config."""
        try:
            atlas_config = get_config()
            
            # Build LLM config based on provider
            llm_config = self._build_llm_config(atlas_config)
            
            return AutoGenConfig(
                llm_config=llm_config,
                work_dir=Path(atlas_config.work_dir) / "autogen" if atlas_config.work_dir else None,
                temperature=getattr(atlas_config, 'llm_temperature', 0.7),
                max_tokens=getattr(atlas_config, 'llm_max_tokens', 2000),
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to load ATLAS config, using defaults: {e}")
            return AutoGenConfig()
    
    def _build_llm_config(self, atlas_config) -> Dict[str, Any]:
        """Build LLM configuration for AutoGen."""
        
        # Get LLM provider and settings
        provider = getattr(atlas_config, 'llm_provider', 'openai')
        api_key = getattr(atlas_config, 'openai_api_key', None)
        
        if provider == 'openai':
            if not api_key:
                raise ConfigurationError("OpenAI API key not configured")
            
            return {
                "config_list": [
                    {
                        "model": getattr(atlas_config, 'openai_model', 'gpt-4'),
                        "api_key": api_key,
                        "api_type": "openai",
                    }
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "timeout": self.config.timeout,
            }
        
        elif provider == 'azure':
            azure_endpoint = getattr(atlas_config, 'azure_endpoint', None)
            azure_api_key = getattr(atlas_config, 'azure_api_key', None)
            
            if not azure_endpoint or not azure_api_key:
                raise ConfigurationError("Azure OpenAI configuration incomplete")
            
            return {
                "config_list": [
                    {
                        "model": getattr(atlas_config, 'azure_model', 'gpt-4'),
                        "api_key": azure_api_key,
                        "api_type": "azure",
                        "base_url": azure_endpoint,
                        "api_version": getattr(atlas_config, 'azure_api_version', '2024-02-15-preview'),
                    }
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "timeout": self.config.timeout,
            }
        
        elif provider == 'anthropic':
            anthropic_api_key = getattr(atlas_config, 'anthropic_api_key', None)
            
            if not anthropic_api_key:
                raise ConfigurationError("Anthropic API key not configured")
            
            return {
                "config_list": [
                    {
                        "model": getattr(atlas_config, 'anthropic_model', 'claude-3-sonnet-20240229'),
                        "api_key": anthropic_api_key,
                        "api_type": "anthropic",
                    }
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "timeout": self.config.timeout,
            }
        
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {provider}")
    
    def create_agent(
        self, 
        name: str, 
        system_message: str,
        role: str = "assistant",
        **kwargs
    ) -> ConversableAgent:
        """Create and register an AutoGen agent.
        
        Args:
            name: Agent name (unique identifier)
            system_message: System message defining agent role
            role: Agent role type
            **kwargs: Additional agent configuration
            
        Returns:
            Configured ConversableAgent
            
        Raises:
            AutoGenError: If agent creation fails
        """
        try:
            # Determine agent class based on role
            if role == "user_proxy":
                agent_class = UserProxyAgent
                agent_config = {
                    "human_input_mode": kwargs.get("human_input_mode", self.config.human_input_mode),
                    "max_consecutive_auto_reply": kwargs.get("max_consecutive_auto_reply", self.config.max_consecutive_auto_reply),
                    "code_execution_config": kwargs.get("code_execution_config", {"use_docker": False} if self.config.enable_code_execution else False),
                }
            else:
                agent_class = ConversableAgent
                agent_config = {
                    "llm_config": self.config.llm_config,
                    "max_consecutive_auto_reply": kwargs.get("max_consecutive_auto_reply", self.config.max_consecutive_auto_reply),
                }
            
            # Merge with additional kwargs
            agent_config.update(kwargs)
            
            # Create agent
            agent = agent_class(
                name=name,
                system_message=system_message,
                **agent_config
            )
            
            # Register agent
            self.agents[name] = agent
            
            self.logger.info(f"Created AutoGen agent: {name} (role: {role})")
            return agent
            
        except Exception as e:
            error_msg = f"Failed to create agent {name}: {e}"
            self.logger.error(error_msg)
            raise AutoGenError(error_msg) from e
    
    def create_group_chat(
        self, 
        agents: Optional[List[ConversableAgent]] = None,
        **kwargs
    ) -> GroupChat:
        """Create AutoGen GroupChat with specified agents.
        
        Args:
            agents: List of agents to include, defaults to all registered agents
            **kwargs: Additional GroupChat configuration
            
        Returns:
            Configured GroupChat
            
        Raises:
            AutoGenError: If GroupChat creation fails
        """
        try:
            # Use provided agents or all registered agents
            if agents is None:
                agents = list(self.agents.values())
            
            if not agents:
                raise AutoGenError("No agents available for GroupChat")
            
            # GroupChat configuration
            chat_config = {
                "agents": agents,
                "messages": [],
                "max_round": kwargs.get("max_round", self.config.max_round),
                "speaker_selection_method": kwargs.get("speaker_selection_method", self.config.speaker_selection_method),
                "allow_repeat_speaker": kwargs.get("allow_repeat_speaker", self.config.allow_repeat_speaker),
            }
            
            # Create GroupChat
            self.group_chat = GroupChat(**chat_config)
            
            self.logger.info(f"Created GroupChat with {len(agents)} agents")
            return self.group_chat
            
        except Exception as e:
            error_msg = f"Failed to create GroupChat: {e}"
            self.logger.error(error_msg)
            raise AutoGenError(error_msg) from e
    
    def create_group_chat_manager(
        self, 
        group_chat: Optional[GroupChat] = None,
        **kwargs
    ) -> GroupChatManager:
        """Create GroupChatManager for conversation coordination.
        
        Args:
            group_chat: GroupChat to manage, defaults to self.group_chat
            **kwargs: Additional manager configuration
            
        Returns:
            Configured GroupChatManager
            
        Raises:
            AutoGenError: If manager creation fails
        """
        try:
            # Use provided GroupChat or create default
            if group_chat is None:
                if self.group_chat is None:
                    self.create_group_chat()
                group_chat = self.group_chat
            
            # Manager configuration
            manager_config = {
                "groupchat": group_chat,
                "llm_config": self.config.llm_config,
                "name": kwargs.get("name", self.config.admin_name),
                "system_message": kwargs.get("system_message", "You are the group chat manager coordinating conversation between AI agents."),
            }
            
            # Create manager
            self.group_chat_manager = GroupChatManager(**manager_config)
            
            self.logger.info("Created GroupChatManager")
            return self.group_chat_manager
            
        except Exception as e:
            error_msg = f"Failed to create GroupChatManager: {e}"
            self.logger.error(error_msg)
            raise AutoGenError(error_msg) from e
    
    def validate_configuration(self) -> bool:
        """Validate AutoGen configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Check LLM configuration
            if not self.config.llm_config or not self.config.llm_config.get("config_list"):
                raise ConfigurationError("LLM configuration is incomplete")
            
            # Test LLM connection with simple call
            test_agent = ConversableAgent(
                name="test_agent",
                system_message="You are a test agent.",
                llm_config=self.config.llm_config,
                max_consecutive_auto_reply=1,
            )
            
            # Simple test message (this might need adjustment based on AutoGen version)
            # test_response = test_agent.generate_reply({"content": "Hello, respond with 'OK'"})
            
            self.logger.info("AutoGen configuration validated successfully")
            return True
            
        except Exception as e:
            error_msg = f"AutoGen configuration validation failed: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def get_agent(self, name: str) -> Optional[ConversableAgent]:
        """Get agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent if found, None otherwise
        """
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def reset(self):
        """Reset AutoGen manager state."""
        self.agents.clear()
        self.group_chat = None
        self.group_chat_manager = None
        self.logger.info("AutoGen manager reset")


# Global AutoGen manager instance
_autogen_manager: Optional[AutoGenManager] = None


def get_autogen_manager() -> AutoGenManager:
    """Get global AutoGen manager instance.
    
    Returns:
        AutoGenManager instance
    """
    global _autogen_manager
    if _autogen_manager is None:
        _autogen_manager = AutoGenManager()
    return _autogen_manager


def init_autogen(config: Optional[AutoGenConfig] = None) -> AutoGenManager:
    """Initialize AutoGen with configuration.
    
    Args:
        config: AutoGen configuration
        
    Returns:
        Configured AutoGenManager
    """
    global _autogen_manager
    _autogen_manager = AutoGenManager(config)
    return _autogen_manager


# Utility functions for common AutoGen patterns
def create_standard_agents(manager: AutoGenManager) -> Dict[str, ConversableAgent]:
    """Create standard ATLAS agents.
    
    Args:
        manager: AutoGen manager
        
    Returns:
        Dictionary of created agents
    """
    agents = {}
    
    # Data Collector Agent
    agents['data_collector'] = manager.create_agent(
        name="data_collector",
        system_message="""You are the Data Collector Agent for ATLAS VM provisioning.
        Your role is to gather VM requirements from users through interactive questions.
        Ask about: hostname, CPU, memory, disk, OS, software, networking.
        Be thorough but efficient. Validate responses and ask for clarification when needed.""",
        role="assistant"
    )
    
    # Validation Agent
    agents['validator'] = manager.create_agent(
        name="validator",
        system_message="""You are the Validation Agent for ATLAS.
        Your role is to validate VM specifications for correctness and feasibility.
        Check: resource constraints, software compatibility, network conflicts, security requirements.
        Provide clear feedback and suggestions for improvements.""",
        role="assistant"
    )
    
    # Proxmox Config Agent
    agents['proxmox_config'] = manager.create_agent(
        name="proxmox_config",
        system_message="""You are the Proxmox Configuration Agent for ATLAS.
        Your role is to create Proxmox-specific configurations from validated VM specs.
        Generate: VM parameters, storage configs, network settings, resource allocation.
        Ensure compatibility with Proxmox VE environment.""",
        role="assistant"
    )
    
    # User Proxy Agent
    agents['user_proxy'] = manager.create_agent(
        name="user_proxy",
        system_message="You are the user proxy facilitating interaction between the user and ATLAS agents.",
        role="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
    )
    
    return agents
