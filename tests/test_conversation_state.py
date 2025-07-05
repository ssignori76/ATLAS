#!/usr/bin/env python3
"""
Test script for Step 1.3 - Conversation State Management.

This test validates conversation persistence, resume capability,
and state management functionality for the ATLAS system.
"""

import sys
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_conversation_state_persistence():
    """Test conversation state save/load functionality."""
    
    print("🧪 Testing Conversation State Persistence")
    print("=" * 50)
    
    # Test 1: Import state management modules
    print("\n📦 Test 1: State management imports...")
    try:
        from atlas.core.conversation_state import (
            ConversationStateManager,
            ConversationStateConfig,
            JSONPersistenceBackend,
            SQLitePersistenceBackend,
            PersistenceBackend,
        )
        from atlas.agents.conversation_manager import (
            ConversationContext,
            ConversationStatus,
            FlowStage,
        )
        print("✅ State management modules imported successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: JSON persistence backend
    print("\n💾 Test 2: JSON persistence backend...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = JSONPersistenceBackend(temp_dir)
            
            # Create test context
            context = ConversationContext()
            context.user_inputs = {"vm_name": "test-vm", "os_type": "ubuntu"}
            context.current_stage = FlowStage.VALIDATION
            context.completed_stages = [FlowStage.DATA_COLLECTION]
            
            # Save context
            await backend.save_context(context)
            
            # Load context
            loaded_context = await backend.load_context(context.id)
            assert loaded_context is not None
            assert loaded_context.id == context.id
            assert loaded_context.user_inputs == context.user_inputs
            assert loaded_context.current_stage == context.current_stage
            
            # List contexts
            contexts = await backend.list_contexts()
            assert len(contexts) == 1
            assert contexts[0]["id"] == context.id
            
            print("✅ JSON persistence backend working")
    except Exception as e:
        print(f"❌ JSON persistence failed: {e}")
        return False
    
    # Test 3: SQLite persistence backend
    print("\n🗄️  Test 3: SQLite persistence backend...")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            backend = SQLitePersistenceBackend(db_path)
            
            # Wait for database initialization
            await asyncio.sleep(0.1)
            
            # Create test context
            context = ConversationContext()
            context.user_inputs = {"vm_name": "test-vm-sqlite", "os_type": "debian"}
            context.current_stage = FlowStage.PROXMOX_CONFIG
            context.completed_stages = [FlowStage.DATA_COLLECTION, FlowStage.VALIDATION]
            
            # Save context
            await backend.save_context(context)
            
            # Load context
            loaded_context = await backend.load_context(context.id)
            assert loaded_context is not None
            assert loaded_context.id == context.id
            assert loaded_context.user_inputs == context.user_inputs
            assert loaded_context.current_stage == context.current_stage
            assert len(loaded_context.completed_stages) == 2
            
            # List contexts
            contexts = await backend.list_contexts()
            assert len(contexts) == 1
            assert contexts[0]["id"] == context.id
            
            print("✅ SQLite persistence backend working")
    except Exception as e:
        print(f"❌ SQLite persistence failed: {e}")
        return False
    
    return True


async def test_conversation_resume_capability():
    """Test conversation resume and pause functionality."""
    
    print("\n🧪 Testing Conversation Resume Capability")
    print("=" * 50)
    
    # Test 1: State manager initialization
    print("\n⚙️  Test 1: State manager initialization...")
    try:
        from atlas.core.conversation_state import (
            ConversationStateManager,
            ConversationStateConfig,
            get_state_manager,
            reset_state_manager,
        )
        from atlas.agents.conversation_manager import (
            ConversationContext,
            ConversationStatus,
            FlowStage,
        )
        
        # Reset global state manager for clean test
        reset_state_manager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConversationStateConfig(
                backend_type="json",
                storage_path=temp_dir,
                auto_save=True,
            )
            
            state_manager = ConversationStateManager(config)
            assert state_manager is not None
            
            print("✅ State manager initialized successfully")
    except Exception as e:
        print(f"❌ State manager initialization failed: {e}")
        return False
    
    # Test 2: Save and load conversation
    print("\n💿 Test 2: Save and load conversation...")
    try:
        # Create test conversation
        context = ConversationContext()
        context.status = ConversationStatus.ACTIVE
        context.current_stage = FlowStage.VALIDATION
        context.user_inputs = {"vm_name": "resume-test-vm"}
        context.metadata = {"flow_name": "vm_provisioning"}
        
        # Save conversation
        await state_manager.save_conversation(context)
        
        # Load conversation
        loaded_context = await state_manager.load_conversation(context.id)
        assert loaded_context is not None
        assert loaded_context.id == context.id
        assert loaded_context.status == ConversationStatus.ACTIVE
        assert loaded_context.user_inputs == context.user_inputs
        
        print(f"✅ Conversation saved and loaded (ID: {context.id[:8]}...)")
    except Exception as e:
        print(f"❌ Save/load conversation failed: {e}")
        return False
    
    # Test 3: Pause and resume conversation
    print("\n⏸️  Test 3: Pause and resume conversation...")
    try:
        # Pause conversation
        pause_success = await state_manager.pause_conversation(context.id)
        assert pause_success == True
        
        # Verify paused status
        paused_context = await state_manager.load_conversation(context.id)
        assert paused_context.status == ConversationStatus.PAUSED
        
        # Resume conversation
        resumed_context = await state_manager.resume_conversation(context.id)
        assert resumed_context is not None
        assert resumed_context.status == ConversationStatus.ACTIVE
        
        print("✅ Pause and resume working correctly")
    except Exception as e:
        print(f"❌ Pause/resume failed: {e}")
        return False
    
    # Test 4: List conversations with filtering
    print("\n📋 Test 4: List conversations with filtering...")
    try:
        # Create additional test conversations
        context2 = ConversationContext()
        context2.status = ConversationStatus.COMPLETED
        context2.metadata = {"flow_name": "vm_provisioning"}
        await state_manager.save_conversation(context2)
        
        context3 = ConversationContext()
        context3.status = ConversationStatus.ACTIVE
        context3.metadata = {"flow_name": "vm_provisioning"}
        await state_manager.save_conversation(context3)
        
        # List all conversations
        all_conversations = await state_manager.list_conversations()
        assert len(all_conversations) >= 3
        
        # List only active conversations
        active_conversations = await state_manager.list_conversations(
            status=ConversationStatus.ACTIVE
        )
        assert len(active_conversations) >= 2
        
        # List with limit
        limited_conversations = await state_manager.list_conversations(limit=2)
        assert len(limited_conversations) == 2
        
        print("✅ Conversation listing and filtering working")
    except Exception as e:
        print(f"❌ Conversation listing failed: {e}")
        return False
    
    return True


async def test_conversation_history_tracking():
    """Test conversation history and context management."""
    
    print("\n🧪 Testing Conversation History Tracking")
    print("=" * 50)
    
    # Test 1: Conversation history generation
    print("\n📜 Test 1: Conversation history generation...")
    try:
        from atlas.core.conversation_state import ConversationStateManager, ConversationStateConfig
        from atlas.agents.conversation_manager import ConversationContext, ConversationStatus, FlowStage
        from datetime import datetime
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConversationStateConfig(backend_type="json", storage_path=temp_dir)
            state_manager = ConversationStateManager(config)
            
            # Create conversation with history
            context = ConversationContext()
            context.status = ConversationStatus.COMPLETED
            context.current_stage = FlowStage.COMPLETION
            context.user_inputs = {"vm_name": "history-test"}
            context.metadata = {"flow_name": "vm_provisioning"}
            context.completed_stages = [FlowStage.DATA_COLLECTION, FlowStage.VALIDATION]
            
            # Add some agent outputs with timestamps
            context.agent_outputs = {
                "data_collection": {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                },
                "validation": {
                    "status": "passed", 
                    "timestamp": datetime.now().isoformat(),
                },
            }
            
            # Add an error
            context.add_error("Test validation warning", FlowStage.VALIDATION)
            
            await state_manager.save_conversation(context)
            
            # Get conversation history
            history = await state_manager.get_conversation_history(context.id)
            assert len(history) >= 3  # creation + 2 stages + 1 error
            
            # Verify history structure
            creation_event = next((h for h in history if h["event"] == "conversation_created"), None)
            assert creation_event is not None
            assert creation_event["data"]["flow_name"] == "vm_provisioning"
            
            stage_events = [h for h in history if h["event"] == "stage_completed"]
            assert len(stage_events) == 2
            
            error_events = [h for h in history if h["event"] == "error_occurred"]
            assert len(error_events) == 1
            
            print("✅ Conversation history tracking working")
            
            # Test 2: Context retention and caching (within same temporary directory)
            print("\n🧠 Test 2: Context retention and caching...")
            
            # Test cache functionality
            cache_size_before = len(state_manager.cached_contexts)
            
            # Load conversation (should be cached)
            cached_context = await state_manager.load_conversation(context.id)
            assert cached_context is not None
            
            cache_size_after = len(state_manager.cached_contexts)
            assert cache_size_after >= cache_size_before
            
            # Clear cache and test
            state_manager.clear_cache()
            assert len(state_manager.cached_contexts) == 0
            
            # Load again (should reload from storage)
            reloaded_context = await state_manager.load_conversation(context.id)
            assert reloaded_context is not None
            assert reloaded_context.id == context.id
            
            print("✅ Context retention and caching working")
            
            # Test 3: Cleanup functionality (within same temporary directory)
            print("\n🧹 Test 3: Cleanup functionality...")
            
            # Test immediate cleanup (0 hours max age)
            removed_count = await state_manager.cleanup_old_conversations(max_age_hours=0)
            assert removed_count >= 0  # Should not fail
            
            # Test stats
            stats = await state_manager.get_stats()
            assert "total_conversations" in stats
            assert "status_counts" in stats
            assert "backend_type" in stats
            assert stats["backend_type"] == "json"
            
            print("✅ Cleanup functionality working")
            
    except Exception as e:
        print(f"❌ History tracking failed: {e}")
        return False
    
    return True


async def test_error_handling_and_edge_cases():
    """Test error handling and edge cases."""
    
    print("\n🧪 Testing Error Handling and Edge Cases")
    print("=" * 50)
    
    # Test 1: Non-existent conversation handling
    print("\n❓ Test 1: Non-existent conversation handling...")
    try:
        from atlas.core.conversation_state import ConversationStateManager, ConversationStateConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConversationStateConfig(backend_type="json", storage_path=temp_dir)
            state_manager = ConversationStateManager(config)
            
            # Try to load non-existent conversation
            missing_context = await state_manager.load_conversation("non-existent-id")
            assert missing_context is None
            
            # Try to resume non-existent conversation
            missing_resume = await state_manager.resume_conversation("non-existent-id")
            assert missing_resume is None
            
            # Try to pause non-existent conversation
            pause_result = await state_manager.pause_conversation("non-existent-id")
            assert pause_result == False
            
            print("✅ Non-existent conversation handling working")
    except Exception as e:
        print(f"❌ Non-existent conversation handling failed: {e}")
        return False
    
    # Test 2: Invalid state transitions
    print("\n🔄 Test 2: Invalid state transitions...")
    try:
        from atlas.agents.conversation_manager import ConversationContext, ConversationStatus
        
        # Create completed conversation
        completed_context = ConversationContext()
        completed_context.status = ConversationStatus.COMPLETED
        await state_manager.save_conversation(completed_context)
        
        # Try to resume completed conversation
        resume_result = await state_manager.resume_conversation(completed_context.id)
        assert resume_result is None  # Should not resume completed conversation
        
        # Create cancelled conversation
        cancelled_context = ConversationContext()
        cancelled_context.status = ConversationStatus.CANCELLED
        await state_manager.save_conversation(cancelled_context)
        
        # Try to resume cancelled conversation
        resume_result = await state_manager.resume_conversation(cancelled_context.id)
        assert resume_result is None  # Should not resume cancelled conversation
        
        print("✅ Invalid state transitions handled correctly")
    except Exception as e:
        print(f"❌ Invalid state transitions test failed: {e}")
        return False
    
    # Test 3: Backend switching
    print("\n🔄 Test 3: Backend compatibility...")
    try:
        # Test that both backends work with same interface
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test JSON backend
            json_config = ConversationStateConfig(backend_type="json", storage_path=temp_dir)
            json_manager = ConversationStateManager(json_config)
            
            context1 = ConversationContext()
            await json_manager.save_conversation(context1)
            loaded1 = await json_manager.load_conversation(context1.id)
            assert loaded1 is not None
            
            # Test SQLite backend (use a specific file path within temp_dir)
            sqlite_path = Path(temp_dir) / "test_conversations.db"
            sqlite_config = ConversationStateConfig(backend_type="sqlite", storage_path=str(sqlite_path))
            sqlite_manager = ConversationStateManager(sqlite_config)
            
            context2 = ConversationContext()
            await sqlite_manager.save_conversation(context2)
            loaded2 = await sqlite_manager.load_conversation(context2.id)
            assert loaded2 is not None
            
            print("✅ Backend compatibility working")
    except Exception as e:
        print(f"❌ Backend compatibility test failed: {e}")
        return False
    
    return True


async def main():
    """Main test runner."""
    print("🚀 ATLAS Step 1.3 Test Suite")
    print("Conversation State Management Validation")
    print("=" * 60)
    
    success = True
    
    # Run persistence tests
    try:
        if not await test_conversation_state_persistence():
            success = False
    except Exception as e:
        print(f"❌ State persistence tests failed: {e}")
        success = False
    
    # Run resume capability tests
    try:
        if not await test_conversation_resume_capability():
            success = False
    except Exception as e:
        print(f"❌ Resume capability tests failed: {e}")
        success = False
    
    # Run history tracking tests
    try:
        if not await test_conversation_history_tracking():
            success = False
    except Exception as e:
        print(f"❌ History tracking tests failed: {e}")
        success = False
    
    # Run error handling tests
    try:
        if not await test_error_handling_and_edge_cases():
            success = False
    except Exception as e:
        print(f"❌ Error handling tests failed: {e}")
        success = False
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Tests Completed Successfully!")
        print("\n🎯 STEP 1.3 VALIDATION COMPLETE")
        print("✅ Conversation State Management - WORKING")
        
        print("\n📋 What was validated:")
        print("  ✅ JSON and SQLite persistence backends")
        print("  ✅ Conversation save/load functionality") 
        print("  ✅ Pause and resume capabilities")
        print("  ✅ Conversation listing and filtering")
        print("  ✅ History tracking and context retention")
        print("  ✅ Caching and performance optimization")
        print("  ✅ Cleanup and maintenance operations")
        print("  ✅ Error handling and edge cases")
        print("  ✅ Backend compatibility and switching")
        
        print("\n✨ Conversation State Management Foundation is SOLID!")
        print("🚀 Ready for Milestone Test 1: Interactive Conversation System")
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
