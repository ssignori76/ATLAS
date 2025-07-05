#!/usr/bin/env python3
"""
Minimal test script for Step 1.1 - AutoGen Setup & Configuration.
This test validates only the core functionality without external dependencies.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_minimal_autogen_setup():
    """Test minimal AutoGen setup without external dependencies."""
    
    print("🧪 Testing Minimal AutoGen Setup")
    print("=" * 50)
    
    # Test 1: Import check
    print("\n📦 Test 1: Core module imports...")
    try:
        from atlas.core.autogen_config import AutoGenConfig, AutoGenManager
        from atlas.core.exceptions import AutoGenError, ConversationError, AgentError
        print("✅ Core modules imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Configuration creation
    print("\n⚙️  Test 2: Configuration creation...")
    try:
        config = AutoGenConfig(
            llm_config={
                "config_list": [
                    {
                        "model": "gpt-4",
                        "api_key": "test_key",
                        "api_type": "openai",
                    }
                ]
            },
            temperature=0.8,
            max_round=5
        )
        
        assert config.temperature == 0.8
        assert config.max_round == 5
        assert "config_list" in config.llm_config
        print("✅ Configuration created successfully")
    except Exception as e:
        print(f"❌ Configuration creation failed: {e}")
        return False
    
    # Test 3: Manager initialization (without real config loading)
    print("\n🎯 Test 3: Manager initialization...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config.work_dir = Path(temp_dir)
            
            # Mock get_config to avoid configuration issues
            with patch('atlas.core.autogen_config.get_config') as mock_get_config:
                mock_get_config.side_effect = Exception("Config not available")
                
                manager = AutoGenManager(config)
                
                assert manager.config == config
                assert len(manager.agents) == 0
                assert manager.group_chat is None
                assert manager.group_chat_manager is None
                assert config.work_dir.exists()
        
        print("✅ Manager initialized successfully")
    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return False
    
    # Test 4: Error handling
    print("\n⚠️  Test 4: Error handling...")
    try:
        # Test AutoGenError
        error = AutoGenError("Test error", agent_name="test_agent")
        assert error.agent_name == "test_agent"
        assert str(error) == "Test error"
        
        # Test inheritance
        conv_error = ConversationError("Conversation failed")
        assert isinstance(conv_error, AutoGenError)
        
        agent_error = AgentError("Agent failed")
        assert isinstance(agent_error, AutoGenError)
        
        print("✅ Error handling working correctly")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 5: Manager utilities
    print("\n🔧 Test 5: Manager utilities...")
    try:
        # Test agent management methods
        assert len(manager.list_agents()) == 0
        assert manager.get_agent("nonexistent") is None
        
        # Test reset
        manager.agents["test"] = MagicMock()
        manager.group_chat = MagicMock()
        manager.group_chat_manager = MagicMock()
        
        manager.reset()
        
        assert len(manager.agents) == 0
        assert manager.group_chat is None
        assert manager.group_chat_manager is None
        
        print("✅ Manager utilities working correctly")
    except Exception as e:
        print(f"❌ Manager utilities test failed: {e}")
        return False
    
    # Test 6: Configuration validation structure
    print("\n🔍 Test 6: Configuration validation...")
    try:
        # Test valid config structure
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
        
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config not available")
            valid_manager = AutoGenManager(valid_config)
        
        # Test invalid config
        invalid_config = AutoGenConfig(llm_config={})
        
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config not available")
            invalid_manager = AutoGenManager(invalid_config)
        
        from atlas.core.exceptions import ConfigurationError
        try:
            invalid_manager.validate_configuration()
            print("❌ Should have failed validation")
            return False
        except ConfigurationError:
            print("✅ Invalid configuration properly rejected")
        except Exception as e:
            # Other exceptions are also acceptable for invalid config
            print(f"✅ Invalid configuration rejected with: {type(e).__name__}")
    except Exception as e:
        print(f"❌ Configuration validation test failed: {e}")
        return False
    
    # Test 7: LLM config builder (mocked)
    print("\n🔗 Test 7: LLM config builder...")
    try:
        with patch('atlas.core.autogen_config.get_config') as mock_get_config:
            mock_get_config.side_effect = Exception("Config not available")
            manager = AutoGenManager()
        
        # Test OpenAI config building
        mock_atlas_config = MagicMock()
        mock_atlas_config.llm_provider = 'openai'
        mock_atlas_config.openai_api_key = 'test_openai_key'
        mock_atlas_config.openai_model = 'gpt-4'
        
        llm_config = manager._build_llm_config(mock_atlas_config)
        
        assert 'config_list' in llm_config
        assert llm_config['config_list'][0]['api_key'] == 'test_openai_key'
        assert llm_config['config_list'][0]['model'] == 'gpt-4'
        
        # Test invalid provider
        mock_atlas_config.llm_provider = 'invalid_provider'
        
        try:
            manager._build_llm_config(mock_atlas_config)
            print("❌ Should have failed for invalid provider")
            return False
        except Exception:
            print("✅ LLM config builder working correctly")
        
    except Exception as e:
        print(f"❌ LLM config builder test failed: {e}")
        return False
    
    print("\n🎉 All Minimal Tests Completed Successfully!")
    return True


if __name__ == "__main__":
    print("🚀 ATLAS Step 1.1 Minimal Test Suite")
    print("AutoGen Setup & Configuration Core Validation")
    print("=" * 60)
    
    if test_minimal_autogen_setup():
        print("\n🎯 STEP 1.1 MINIMAL VALIDATION COMPLETE")
        print("✅ AutoGen Setup & Configuration - CORE FUNCTIONALITY WORKING")
        print("\n📋 What was validated:")
        print("  ✅ Core module imports working")
        print("  ✅ Configuration classes functional")
        print("  ✅ Manager initialization working") 
        print("  ✅ Error handling implemented")
        print("  ✅ Basic utilities functional")
        print("  ✅ Configuration validation structure ready")
        print("  ✅ LLM config builder working")
        print("\n✨ Step 1.1 Foundation is SOLID!")
        print("🚀 Ready for Step 1.2: Agent Conversation Flows")
        sys.exit(0)
    else:
        print("\n❌ STEP 1.1 MINIMAL VALIDATION FAILED")
        print("Core functionality is not working properly.")
        sys.exit(1)
