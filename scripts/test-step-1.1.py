#!/usr/bin/env python3
"""
Test script for Step 1.1 - AutoGen Setup & Configuration.

This script validates that the AutoGen integration is working correctly
without requiring actual LLM API calls.
"""

import sys
import tempfile
from pathlib import Path
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_step_1_1():
    """Test Step 1.1 implementation."""
    
    print("🧪 Testing Step 1.1: AutoGen Setup & Configuration")
    print("=" * 60)
    
    # Test 1: Import AutoGen modules
    print("\n📦 Test 1: Import AutoGen modules...")
    try:
        from atlas.core.autogen_config import (
            AutoGenConfig,
            AutoGenManager,
            get_autogen_manager,
            init_autogen,
            create_standard_agents,
        )
        from atlas.core import AutoGenError, ConversationError, AgentError
        print("✅ All AutoGen modules imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Create AutoGen configuration
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
    
    # Test 3: Initialize AutoGen manager
    print("\n🎯 Test 3: Initialize AutoGen manager...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config.work_dir = Path(temp_dir)
            manager = AutoGenManager(config)
            
            assert manager.config == config
            assert len(manager.agents) == 0
            assert manager.group_chat is None
            assert config.work_dir.exists()
            print("✅ AutoGen manager initialized successfully")
    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return False
    
    # Test 4: Test agent creation (mock)
    print("\n🤖 Test 4: Test agent creation...")
    try:
        from unittest.mock import patch, MagicMock
        
        with patch('atlas.core.autogen_config.ConversableAgent') as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance
            
            agent = manager.create_agent(
                name="test_agent",
                system_message="Test agent system message",
                role="assistant"
            )
            
            assert agent == mock_instance
            assert "test_agent" in manager.agents
            assert manager.get_agent("test_agent") == mock_instance
            print("✅ Agent creation working correctly")
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False
    
    # Test 5: Test GroupChat creation (mock)
    print("\n💬 Test 5: Test GroupChat creation...")
    try:
        with patch('atlas.core.autogen_config.GroupChat') as mock_group_chat:
            mock_chat_instance = MagicMock()
            mock_group_chat.return_value = mock_chat_instance
            
            # Create mock agents for the chat
            mock_agents = [MagicMock(), MagicMock()]
            
            group_chat = manager.create_group_chat(agents=mock_agents)
            
            assert group_chat == mock_chat_instance
            assert manager.group_chat == mock_chat_instance
            print("✅ GroupChat creation working correctly")
    except Exception as e:
        print(f"❌ GroupChat creation failed: {e}")
        return False
    
    # Test 6: Test standard agents creation (mock)
    print("\n👥 Test 6: Test standard agents creation...")
    try:
        with patch.object(manager, 'create_agent') as mock_create:
            mock_agent = MagicMock()
            mock_create.return_value = mock_agent
            
            agents = create_standard_agents(manager)
            
            expected_agents = ['data_collector', 'validator', 'proxmox_config', 'user_proxy']
            assert set(agents.keys()) == set(expected_agents)
            assert mock_create.call_count == len(expected_agents)
            print("✅ Standard agents creation working correctly")
    except Exception as e:
        print(f"❌ Standard agents creation failed: {e}")
        return False
    
    # Test 7: Test error handling
    print("\n⚠️  Test 7: Test error handling...")
    try:
        # Test AutoGenError
        error = AutoGenError("Test error", agent_name="test_agent")
        assert error.agent_name == "test_agent"
        assert str(error) == "Test error"
        
        # Test configuration validation error
        invalid_config = AutoGenConfig(llm_config={})
        invalid_manager = AutoGenManager(invalid_config)
        
        from atlas.core import ConfigurationError
        try:
            invalid_manager.validate_configuration()
            print("❌ Validation should have failed")
            return False
        except ConfigurationError:
            print("✅ Error handling working correctly")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 8: Test global manager singleton
    print("\n🌍 Test 8: Test global manager singleton...")
    try:
        manager1 = get_autogen_manager()
        manager2 = get_autogen_manager()
        
        assert manager1 is manager2
        
        # Test initialization
        new_manager = init_autogen(config)
        manager3 = get_autogen_manager()
        
        assert new_manager is manager3
        print("✅ Global manager singleton working correctly")
    except Exception as e:
        print(f"❌ Global manager test failed: {e}")
        return False
    
    print("\n🎉 Step 1.1 Tests Completed Successfully!")
    print("✅ AutoGen setup and configuration is working correctly")
    return True


def run_pytest_tests():
    """Run the comprehensive pytest test suite."""
    print("\n🔬 Running comprehensive pytest test suite...")
    print("=" * 60)
    
    test_file = project_root / "tests" / "test_autogen_setup.py"
    
    # Run pytest with verbose output
    result = pytest.main([
        str(test_file),
        "-v",
        "--tb=short",
        "--no-header"
    ])
    
    if result == 0:
        print("\n✅ All pytest tests passed!")
        return True
    else:
        print("\n❌ Some pytest tests failed!")
        return False


if __name__ == "__main__":
    print("🚀 ATLAS Step 1.1 Test Suite")
    print("AutoGen Setup & Configuration Validation")
    print("=" * 60)
    
    # Run basic validation tests
    basic_tests_passed = test_step_1_1()
    
    if not basic_tests_passed:
        print("\n❌ Basic tests failed. Skipping pytest suite.")
        sys.exit(1)
    
    # Run comprehensive pytest tests
    pytest_passed = run_pytest_tests()
    
    if basic_tests_passed and pytest_passed:
        print("\n🎯 STEP 1.1 VALIDATION COMPLETE")
        print("✅ AutoGen Setup & Configuration - ALL TESTS PASSED")
        print("\nNext step: Implement agent conversation flows")
        sys.exit(0)
    else:
        print("\n❌ STEP 1.1 VALIDATION FAILED")
        print("Some tests did not pass. Please review and fix issues.")
        sys.exit(1)
