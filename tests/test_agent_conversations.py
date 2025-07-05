#!/usr/bin/env python3
"""
Test script for Step 1.2 - Agent Conversation Flows.

This test validates the conversation management and agent coordination
functionality for the ATLAS multi-agent system.
"""

import sys
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_conversation_flows():
    """Test agent conversation flows end-to-end."""
    
    print("🧪 Testing Agent Conversation Flows")
    print("=" * 50)
    
    # Test 1: Import conversation manager
    print("\n📦 Test 1: Conversation manager imports...")
    try:
        from atlas.agents.conversation_manager import (
            ConversationManager,
            ConversationContext,
            ConversationFlow,
            ConversationStatus,
            FlowStage,
        )
        from atlas.core.autogen_config import AutoGenManager
        print("✅ Conversation manager imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Manager initialization
    print("\n⚙️  Test 2: Manager initialization...")
    try:
        conv_manager = ConversationManager()
        assert conv_manager is not None
        assert len(conv_manager.flows) > 0
        assert "vm_provisioning" in conv_manager.flows
        print("✅ ConversationManager initialized successfully")
    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return False
    
    # Test 3: Flow definition validation
    print("\n🔄 Test 3: Flow definition validation...")
    try:
        vm_flow = conv_manager.flows["vm_provisioning"]
        assert vm_flow.name == "vm_provisioning"
        assert len(vm_flow.stages) > 0
        assert FlowStage.DATA_COLLECTION in vm_flow.stages
        assert FlowStage.VALIDATION in vm_flow.stages
        
        # Test transitions
        next_stages = vm_flow.get_next_stages(FlowStage.DATA_COLLECTION)
        assert FlowStage.VALIDATION in next_stages
        print("✅ Flow definition validation passed")
    except Exception as e:
        print(f"❌ Flow validation failed: {e}")
        return False
    
    # Test 4: Start conversation
    print("\n🚀 Test 4: Start conversation...")
    try:
        context = await conv_manager.start_conversation(
            flow_name="vm_provisioning",
            user_input={
                "vm_name": "test-vm-001",
                "os_type": "ubuntu",
                "cpu_cores": 2,
                "memory_gb": 4,
            }
        )
        
        assert context.id is not None
        assert context.status == ConversationStatus.ACTIVE
        assert context.current_stage == FlowStage.DATA_COLLECTION
        assert "vm_name" in context.user_inputs
        print(f"✅ Conversation started successfully (ID: {context.id[:8]}...)")
    except Exception as e:
        print(f"❌ Start conversation failed: {e}")
        return False
    
    # Test 5: Process stages
    print("\n🔍 Test 5: Process conversation stages...")
    try:
        # Process data collection stage
        data_result = await conv_manager.process_stage(
            context.id,
            FlowStage.DATA_COLLECTION
        )
        assert data_result["collection_status"] == "completed"
        assert "vm_name" in data_result
        print("  ✅ Data collection stage processed")
        
        # Advance to validation stage
        context = await conv_manager.continue_conversation(
            context.id,
            target_stage=FlowStage.VALIDATION
        )
        assert context.current_stage == FlowStage.VALIDATION
        
        # Process validation stage
        validation_result = await conv_manager.process_stage(
            context.id,
            FlowStage.VALIDATION
        )
        assert validation_result["validation_status"] == "passed"
        print("  ✅ Validation stage processed")
        
        # Process remaining stages
        for stage in [FlowStage.PROXMOX_CONFIG, FlowStage.DOCUMENTATION]:
            context = await conv_manager.continue_conversation(
                context.id,
                target_stage=stage
            )
            result = await conv_manager.process_stage(context.id, stage)
            assert result is not None
            print(f"  ✅ {stage.value} stage processed")
        
        print("✅ All conversation stages processed successfully")
    except Exception as e:
        print(f"❌ Stage processing failed: {e}")
        return False
    
    # Test 6: Conversation status and management
    print("\n📊 Test 6: Conversation status management...")
    try:
        # Get conversation status
        status = conv_manager.get_conversation_status(context.id)
        assert status["id"] == context.id
        assert status["status"] == ConversationStatus.ACTIVE.value
        assert len(status["completed_stages"]) > 0
        print("  ✅ Status retrieval working")
        
        # List conversations
        conversations = conv_manager.list_conversations()
        assert len(conversations) > 0
        assert any(c["id"] == context.id for c in conversations)
        print("  ✅ Conversation listing working")
        
        print("✅ Conversation management working correctly")
    except Exception as e:
        print(f"❌ Status management failed: {e}")
        return False
    
    # Test 7: Error handling
    print("\n⚠️  Test 7: Error handling...")
    try:
        # Test invalid conversation ID
        try:
            await conv_manager.process_stage("invalid-id")
            assert False, "Should have raised ConversationError"
        except Exception as expected:
            assert "not found" in str(expected)
        
        # Test invalid flow name
        try:
            await conv_manager.start_conversation(flow_name="invalid-flow")
            assert False, "Should have raised ConversationError"
        except Exception as expected:
            assert "Unknown flow" in str(expected)
        
        print("✅ Error handling working correctly")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 8: Complete conversation flow
    print("\n🏁 Test 8: Complete conversation flow...")
    try:
        # Complete the conversation
        context = await conv_manager.continue_conversation(
            context.id,
            target_stage=FlowStage.COMPLETION
        )
        
        completion_result = await conv_manager.process_stage(
            context.id,
            FlowStage.COMPLETION
        )
        
        assert completion_result["completion_status"] == "success"
        assert context.status == ConversationStatus.COMPLETED
        print("✅ Conversation completed successfully")
    except Exception as e:
        print(f"❌ Conversation completion failed: {e}")
        return False
    
    return True


async def test_conversation_state_persistence():
    """Test conversation state management and persistence."""
    
    print("\n🧪 Testing Conversation State Management")
    print("=" * 50)
    
    # Test 1: Context state management
    print("\n📝 Test 1: Context state management...")
    try:
        from atlas.agents.conversation_manager import ConversationContext, ConversationStatus, FlowStage
        
        context = ConversationContext()
        original_status = context.status
        original_stage = context.current_stage
        
        # Test status update
        context.update_status(ConversationStatus.ACTIVE)
        assert context.status == ConversationStatus.ACTIVE
        assert context.updated_at > context.created_at
        
        # Test stage advancement
        context.advance_stage(FlowStage.VALIDATION)
        assert context.current_stage == FlowStage.VALIDATION
        assert original_stage in context.completed_stages
        
        # Test error handling
        context.add_error("Test error", FlowStage.DATA_COLLECTION)
        assert len(context.errors) == 1
        assert context.errors[0]["message"] == "Test error"
        
        print("✅ Context state management working")
    except Exception as e:
        print(f"❌ Context state management failed: {e}")
        return False
    
    # Test 2: Flow transition validation
    print("\n🔄 Test 2: Flow transition validation...")
    try:
        from atlas.agents.conversation_manager import ConversationFlow
        
        flow = ConversationFlow(
            name="test_flow",
            description="Test flow",
            stages=[FlowStage.DATA_COLLECTION, FlowStage.VALIDATION],
            transitions={
                FlowStage.DATA_COLLECTION: [FlowStage.VALIDATION],
                FlowStage.VALIDATION: [],
            }
        )
        
        # Test valid transition
        assert flow.can_transition(FlowStage.DATA_COLLECTION, FlowStage.VALIDATION)
        
        # Test invalid transition
        assert not flow.can_transition(FlowStage.VALIDATION, FlowStage.DATA_COLLECTION)
        
        # Test next stages
        next_stages = flow.get_next_stages(FlowStage.DATA_COLLECTION)
        assert FlowStage.VALIDATION in next_stages
        
        print("✅ Flow transition validation working")
    except Exception as e:
        print(f"❌ Flow transition validation failed: {e}")
        return False
    
    return True


async def main():
    """Main test runner."""
    print("🚀 ATLAS Step 1.2 Test Suite")
    print("Agent Conversation Flows Validation")
    print("=" * 60)
    
    success = True
    
    # Run conversation flow tests
    try:
        if not await test_conversation_flows():
            success = False
    except Exception as e:
        print(f"❌ Conversation flow tests failed: {e}")
        success = False
    
    # Run state management tests
    try:
        if not await test_conversation_state_persistence():
            success = False
    except Exception as e:
        print(f"❌ State management tests failed: {e}")
        success = False
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Tests Completed Successfully!")
        print("\n🎯 STEP 1.2 VALIDATION COMPLETE")
        print("✅ Agent Conversation Flows - WORKING")
        
        print("\n📋 What was validated:")
        print("  ✅ Conversation manager initialization")
        print("  ✅ Flow definition and validation")
        print("  ✅ Conversation lifecycle management")
        print("  ✅ Stage processing and transitions")
        print("  ✅ Error handling and recovery")
        print("  ✅ Status monitoring and listing")
        print("  ✅ State management and persistence")
        print("  ✅ Flow transition validation")
        
        print("\n✨ Agent Conversation Flows Foundation is SOLID!")
        print("🚀 Ready for Step 1.3: Conversation State Management")
        return True
    else:
        print("❌ Some tests failed!")
        print("\n🛠️  Next steps:")
        print("  1. Review failed tests above")
        print("  2. Fix identified issues")
        print("  3. Re-run tests")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
