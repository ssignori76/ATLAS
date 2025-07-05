#!/usr/bin/env python3
"""
Simplified test script for Step 1.1 - AutoGen Setup & Configuration.

This script validates the basic configuration and setup without
requiring complex AutoGen integration.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_configuration():
    """Test basic configuration setup."""
    
    print("🧪 Testing Basic Configuration Setup")
    print("=" * 50)
    
    # Test 1: Import core modules
    print("\n📦 Test 1: Import core modules...")
    try:
        from atlas.core.autogen_config import AutoGenConfig, AutoGenManager
        from atlas.core import AutoGenError, ConversationError, AgentError, AtlasConfig
        print("✅ Core modules imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Create configuration
    print("\n⚙️  Test 2: Create AutoGen configuration...")
    try:
        config = AutoGenConfig(
            llm_config={
                "config_list": [
                    {
                        "model": "gpt-4",
                        "api_key": "test_key_mock",
                        "api_type": "openai",
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            temperature=0.8,
            max_round=5
        )
        
        assert config.temperature == 0.8
        assert config.max_round == 5
        assert "config_list" in config.llm_config
        print("✅ AutoGen configuration created successfully")
    except Exception as e:
        print(f"❌ Configuration creation failed: {e}")
        return False
    
    # Test 3: Initialize manager
    print("\n🎯 Test 3: Initialize AutoGen manager...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config.work_dir = Path(temp_dir)
            manager = AutoGenManager(config)
            
            assert manager.config == config
            assert len(manager.agents) == 0
            assert config.work_dir.exists()
            print("✅ AutoGen manager initialized successfully")
    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return False
    
    # Test 4: Test configuration validation
    print("\n🔍 Test 4: Test configuration validation...")
    try:
        # Test valid config
        valid_config = AutoGenConfig(
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
        
        valid_manager = AutoGenManager(valid_config)
        # Skip actual validation for now since it requires real API
        print("✅ Configuration validation structure working")
        
        # Test invalid config
        invalid_config = AutoGenConfig(llm_config={})
        invalid_manager = AutoGenManager(invalid_config)
        
        try:
            invalid_manager.validate_configuration()
            print("❌ Should have failed validation")
            return False
        except Exception:
            print("✅ Invalid configuration properly rejected")
            
    except Exception as e:
        print(f"❌ Configuration validation test failed: {e}")
        return False
    
    # Test 5: Test error classes
    print("\n⚠️  Test 5: Test error handling...")
    try:
        # Test AutoGenError
        error = AutoGenError("Test error", agent_name="test_agent")
        assert error.agent_name == "test_agent"
        assert str(error) == "Test error"
        
        # Test ConversationError
        conv_error = ConversationError("Conversation failed")
        assert isinstance(conv_error, AutoGenError)
        
        # Test AgentError
        agent_error = AgentError("Agent failed")
        assert isinstance(agent_error, AutoGenError)
        
        print("✅ Error handling working correctly")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    print("\n🎉 Basic Configuration Tests Completed Successfully!")
    return True


def test_manager_functionality():
    """Test manager basic functionality."""
    
    print("\n🔧 Testing Manager Functionality")
    print("=" * 50)
    
    try:
        from atlas.core.autogen_config import AutoGenManager, AutoGenConfig
        from atlas.core import AtlasConfig
        
        # Create test config
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
        
        # Test agent management
        print("\n👥 Testing agent management...")
        
        # Initially no agents
        assert len(manager.list_agents()) == 0
        assert manager.get_agent("nonexistent") is None
        
        # Test reset
        manager.reset()
        assert len(manager.agents) == 0
        assert manager.group_chat is None
        assert manager.group_chat_manager is None
        
        print("✅ Manager functionality working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Manager functionality test failed: {e}")
        return False


def test_llm_config_builder():
    """Test LLM configuration builder for different providers."""
    
    print("\n🔗 Testing LLM Configuration Builder")
    print("=" * 50)
    
    try:
        from atlas.core.autogen_config import AutoGenManager
        from unittest.mock import MagicMock
        
        # Test OpenAI config
        print("\n🔑 Testing OpenAI configuration...")
        mock_atlas_config = MagicMock()
        mock_atlas_config.llm_provider = 'openai'
        mock_atlas_config.openai_api_key = 'test_openai_key'
        mock_atlas_config.openai_model = 'gpt-4'
        mock_atlas_config.work_dir = None
        
        manager = AutoGenManager()
        llm_config = manager._build_llm_config(mock_atlas_config)
        
        assert 'config_list' in llm_config
        assert llm_config['config_list'][0]['api_key'] == 'test_openai_key'
        assert llm_config['config_list'][0]['model'] == 'gpt-4'
        print("✅ OpenAI configuration working")
        
        # Test Azure config
        print("\n🔵 Testing Azure configuration...")
        mock_atlas_config.llm_provider = 'azure'
        mock_atlas_config.azure_endpoint = 'https://test.openai.azure.com'
        mock_atlas_config.azure_api_key = 'test_azure_key'
        mock_atlas_config.azure_model = 'gpt-4'
        mock_atlas_config.azure_api_version = '2024-02-15-preview'
        
        llm_config = manager._build_llm_config(mock_atlas_config)
        
        assert llm_config['config_list'][0]['api_key'] == 'test_azure_key'
        assert llm_config['config_list'][0]['api_type'] == 'azure'
        print("✅ Azure configuration working")
        
        # Test invalid provider
        print("\n❌ Testing invalid provider...")
        mock_atlas_config.llm_provider = 'invalid_provider'
        
        try:
            manager._build_llm_config(mock_atlas_config)
            print("❌ Should have failed for invalid provider")
            return False
        except Exception:
            print("✅ Invalid provider properly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM config builder test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 ATLAS Step 1.1 Simplified Test Suite")
    print("AutoGen Setup & Configuration Validation")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run basic configuration tests
    if not test_basic_configuration():
        all_tests_passed = False
    
    # Run manager functionality tests
    if not test_manager_functionality():
        all_tests_passed = False
    
    # Run LLM config builder tests
    if not test_llm_config_builder():
        all_tests_passed = False
    
    if all_tests_passed:
        print("\n🎯 STEP 1.1 VALIDATION COMPLETE")
        print("✅ AutoGen Setup & Configuration - ALL TESTS PASSED")
        print("\n📋 What was validated:")
        print("  ✅ Core module imports")
        print("  ✅ Configuration creation and validation")
        print("  ✅ Manager initialization")
        print("  ✅ Error handling")
        print("  ✅ LLM provider configurations")
        print("\n🎁 Ready for next step: Agent conversation flows")
        sys.exit(0)
    else:
        print("\n❌ STEP 1.1 VALIDATION FAILED")
        print("Some tests did not pass. Please review and fix issues.")
        sys.exit(1)
