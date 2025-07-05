"""
Test suite for AutoGen setup and configuration.

This module tests the AutoGen integration including configuration,
agent creation, and basic communication setup.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from atlas.core.autogen_config import (
    AutoGenConfig,
    AutoGenManager,
    get_autogen_manager,
    init_autogen,
    create_standard_agents,
)
from atlas.core import AutoGenError, ConfigurationError


class TestAutoGenConfig:
    """Test AutoGenConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AutoGenConfig()
        
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.timeout == 600
        assert config.max_round == 10
        assert config.admin_name == "atlas_admin"
        assert config.speaker_selection_method == "auto"
        assert config.allow_repeat_speaker is False
        assert config.enable_code_execution is False
        assert config.human_input_mode == "NEVER"
        assert config.max_consecutive_auto_reply == 3
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AutoGenConfig(
            temperature=0.5,
            max_tokens=1000,
            max_round=5,
            admin_name="custom_admin"
        )
        
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.max_round == 5
        assert config.admin_name == "custom_admin"


class TestAutoGenManager:
    """Test AutoGenManager class."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Create temporary work directory
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock configuration to avoid requiring real API keys
        self.mock_config = AutoGenConfig(
            llm_config={
                "config_list": [
                    {
                        "model": "gpt-4",
                        "api_key": "test_key",
                        "api_type": "openai",
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            work_dir=self.temp_dir
        )
    
    def teardown_method(self):
        """Cleanup after each test method."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_manager_initialization(self):
        """Test AutoGenManager initialization."""
        manager = AutoGenManager(self.mock_config)
        
        assert manager.config == self.mock_config
        assert manager.agents == {}
        assert manager.group_chat is None
        assert manager.group_chat_manager is None
        assert self.temp_dir.exists()
    
    @patch('atlas.core.autogen_config.get_config')
    def test_default_config_creation(self, mock_get_config):
        """Test creation of default config from ATLAS config."""
        # Mock ATLAS config
        mock_atlas_config = MagicMock()
        mock_atlas_config.llm_provider = 'openai'
        mock_atlas_config.openai_api_key = 'test_openai_key'
        mock_atlas_config.openai_model = 'gpt-4'
        mock_atlas_config.work_dir = str(self.temp_dir)
        mock_get_config.return_value = mock_atlas_config
        
        manager = AutoGenManager()
        
        assert manager.config is not None
        assert 'config_list' in manager.config.llm_config
        assert manager.config.llm_config['config_list'][0]['api_key'] == 'test_openai_key'
        assert manager.config.llm_config['config_list'][0]['model'] == 'gpt-4'
    
    @patch('atlas.core.autogen_config.ConversableAgent')
    def test_create_agent(self, mock_agent_class):
        """Test agent creation."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        manager = AutoGenManager(self.mock_config)
        
        # Create agent
        agent = manager.create_agent(
            name="test_agent",
            system_message="Test system message",
            role="assistant"
        )
        
        # Verify agent creation
        assert agent == mock_agent
        assert "test_agent" in manager.agents
        assert manager.agents["test_agent"] == mock_agent
        
        # Verify agent was called with correct parameters
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        assert call_args[1]['name'] == "test_agent"
        assert call_args[1]['system_message'] == "Test system message"
        assert 'llm_config' in call_args[1]
    
    @patch('atlas.core.autogen_config.UserProxyAgent')
    def test_create_user_proxy_agent(self, mock_agent_class):
        """Test user proxy agent creation."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        manager = AutoGenManager(self.mock_config)
        
        # Create user proxy agent
        agent = manager.create_agent(
            name="user_proxy",
            system_message="User proxy message",
            role="user_proxy"
        )
        
        # Verify user proxy creation
        assert agent == mock_agent
        assert "user_proxy" in manager.agents
        
        # Verify correct class was used
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        assert 'human_input_mode' in call_args[1]
        assert 'code_execution_config' in call_args[1]
    
    def test_create_agent_failure(self):
        """Test agent creation failure handling."""
        manager = AutoGenManager(self.mock_config)
        
        # Mock agent creation to raise exception
        with patch('atlas.core.autogen_config.ConversableAgent', side_effect=Exception("Test error")):
            with pytest.raises(AutoGenError, match="Failed to create agent test_agent"):
                manager.create_agent(
                    name="test_agent",
                    system_message="Test message",
                    role="assistant"
                )
    
    @patch('atlas.core.autogen_config.GroupChat')
    def test_create_group_chat(self, mock_group_chat_class):
        """Test GroupChat creation."""
        # Setup mock
        mock_group_chat = MagicMock()
        mock_group_chat_class.return_value = mock_group_chat
        
        manager = AutoGenManager(self.mock_config)
        
        # Create mock agents
        mock_agents = [MagicMock(), MagicMock()]
        
        # Create group chat
        group_chat = manager.create_group_chat(agents=mock_agents)
        
        # Verify group chat creation
        assert group_chat == mock_group_chat
        assert manager.group_chat == mock_group_chat
        
        # Verify GroupChat was called with correct parameters
        mock_group_chat_class.assert_called_once()
        call_args = mock_group_chat_class.call_args[1]
        assert call_args['agents'] == mock_agents
        assert call_args['max_round'] == self.mock_config.max_round
        assert call_args['speaker_selection_method'] == self.mock_config.speaker_selection_method
    
    def test_create_group_chat_no_agents(self):
        """Test GroupChat creation with no agents."""
        manager = AutoGenManager(self.mock_config)
        
        with pytest.raises(AutoGenError, match="No agents available for GroupChat"):
            manager.create_group_chat()
    
    @patch('atlas.core.autogen_config.GroupChatManager')
    def test_create_group_chat_manager(self, mock_manager_class):
        """Test GroupChatManager creation."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        manager = AutoGenManager(self.mock_config)
        
        # Create mock group chat
        mock_group_chat = MagicMock()
        
        # Create group chat manager
        chat_manager = manager.create_group_chat_manager(group_chat=mock_group_chat)
        
        # Verify manager creation
        assert chat_manager == mock_manager
        assert manager.group_chat_manager == mock_manager
        
        # Verify GroupChatManager was called with correct parameters
        mock_manager_class.assert_called_once()
        call_args = mock_manager_class.call_args[1]
        assert call_args['groupchat'] == mock_group_chat
        assert 'llm_config' in call_args
        assert call_args['name'] == self.mock_config.admin_name
    
    def test_get_agent(self):
        """Test agent retrieval."""
        manager = AutoGenManager(self.mock_config)
        
        # Add mock agent
        mock_agent = MagicMock()
        manager.agents["test_agent"] = mock_agent
        
        # Test retrieval
        assert manager.get_agent("test_agent") == mock_agent
        assert manager.get_agent("nonexistent") is None
    
    def test_list_agents(self):
        """Test agent listing."""
        manager = AutoGenManager(self.mock_config)
        
        # Add mock agents
        manager.agents["agent1"] = MagicMock()
        manager.agents["agent2"] = MagicMock()
        
        # Test listing
        agent_names = manager.list_agents()
        assert set(agent_names) == {"agent1", "agent2"}
    
    def test_reset(self):
        """Test manager reset."""
        manager = AutoGenManager(self.mock_config)
        
        # Add some state
        manager.agents["test"] = MagicMock()
        manager.group_chat = MagicMock()
        manager.group_chat_manager = MagicMock()
        
        # Reset
        manager.reset()
        
        # Verify reset
        assert manager.agents == {}
        assert manager.group_chat is None
        assert manager.group_chat_manager is None


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_autogen_manager_singleton(self):
        """Test global AutoGen manager singleton."""
        # First call creates instance
        manager1 = get_autogen_manager()
        assert manager1 is not None
        
        # Second call returns same instance
        manager2 = get_autogen_manager()
        assert manager1 is manager2
    
    def test_init_autogen(self):
        """Test AutoGen initialization."""
        config = AutoGenConfig(temperature=0.5)
        
        manager = init_autogen(config)
        
        assert manager is not None
        assert manager.config.temperature == 0.5
        
        # Verify it becomes the global instance
        global_manager = get_autogen_manager()
        assert manager is global_manager
    
    @patch('atlas.core.autogen_config.AutoGenManager.create_agent')
    def test_create_standard_agents(self, mock_create_agent):
        """Test standard agents creation."""
        # Setup mock
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        manager = MagicMock()
        manager.create_agent = mock_create_agent
        
        # Create standard agents
        agents = create_standard_agents(manager)
        
        # Verify all standard agents were created
        expected_agents = ['data_collector', 'validator', 'proxmox_config', 'user_proxy']
        assert set(agents.keys()) == set(expected_agents)
        
        # Verify create_agent was called for each
        assert mock_create_agent.call_count == len(expected_agents)
        
        # Verify specific agent configurations
        call_args_list = mock_create_agent.call_args_list
        
        # Check data collector agent
        data_collector_call = next(call for call in call_args_list if call[1]['name'] == 'data_collector')
        assert 'Data Collector Agent' in data_collector_call[1]['system_message']
        assert data_collector_call[1]['role'] == 'assistant'
        
        # Check user proxy agent
        user_proxy_call = next(call for call in call_args_list if call[1]['name'] == 'user_proxy')
        assert user_proxy_call[1]['role'] == 'user_proxy'
        assert user_proxy_call[1]['human_input_mode'] == 'NEVER'


class TestConfigurationErrors:
    """Test configuration error handling."""
    
    def test_invalid_llm_provider(self):
        """Test handling of invalid LLM provider."""
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_atlas_config = MagicMock()
            mock_atlas_config.llm_provider = 'invalid_provider'
            mock_get_config.return_value = mock_atlas_config
            
            with pytest.raises(ConfigurationError, match="Unsupported LLM provider"):
                AutoGenManager()
    
    def test_missing_openai_key(self):
        """Test handling of missing OpenAI API key."""
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_atlas_config = MagicMock()
            mock_atlas_config.llm_provider = 'openai'
            mock_atlas_config.openai_api_key = None
            mock_get_config.return_value = mock_atlas_config
            
            with pytest.raises(ConfigurationError, match="OpenAI API key not configured"):
                AutoGenManager()
    
    def test_missing_azure_config(self):
        """Test handling of incomplete Azure configuration."""
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_atlas_config = MagicMock()
            mock_atlas_config.llm_provider = 'azure'
            mock_atlas_config.azure_endpoint = None
            mock_atlas_config.azure_api_key = 'test_key'
            mock_get_config.return_value = mock_atlas_config
            
            with pytest.raises(ConfigurationError, match="Azure OpenAI configuration incomplete"):
                AutoGenManager()
    
    @patch('atlas.core.autogen_config.ConversableAgent')
    def test_validate_configuration(self, mock_agent_class):
        """Test configuration validation."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        config = AutoGenConfig(
            llm_config={
                "config_list": [
                    {
                        "model": "gpt-4",
                        "api_key": "test_key",
                        "api_type": "openai",
                    }
                ]
            }
        )
        
        manager = AutoGenManager(config)
        
        # Should not raise exception
        result = manager.validate_configuration()
        assert result is True
    
    def test_validate_configuration_invalid(self):
        """Test configuration validation with invalid config."""
        config = AutoGenConfig(llm_config={})  # Empty config
        manager = AutoGenManager(config)
        
        with pytest.raises(ConfigurationError, match="LLM configuration is incomplete"):
            manager.validate_configuration()


if __name__ == "__main__":
    pytest.main([__file__])
