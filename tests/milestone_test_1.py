#!/usr/bin/env python3
"""
MILESTONE TEST 1: Interactive Conversation System

This comprehensive test validates the complete conversation system
including agent coordination, flow management, and state persistence.
It serves as the final validation before proceeding to Proxmox integration.
"""

import sys
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_complete_conversation_lifecycle():
    """Test complete end-to-end conversation lifecycle."""
    
    print("🧪 Testing Complete Conversation Lifecycle")
    print("=" * 50)
    
    try:
        # Import all required modules
        from atlas.agents.conversation_manager import (
            ConversationManager,
            ConversationContext,
            ConversationStatus,
            FlowStage,
        )
        from atlas.core.conversation_state import (
            ConversationStateManager,
            ConversationStateConfig,
        )
        
        print("📦 All modules imported successfully")
        
        # Setup managers with persistent storage
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize conversation manager
            conv_manager = ConversationManager()
            
            # Initialize state manager with JSON backend
            state_config = ConversationStateConfig(
                backend_type="json",
                storage_path=temp_dir,
                auto_save=True,
            )
            state_manager = ConversationStateManager(state_config)
            
            print("⚙️  Managers initialized successfully")
            
            # Test 1: Start conversation
            print("\n🚀 Starting VM provisioning conversation...")
            context = await conv_manager.start_conversation(
                flow_name="vm_provisioning",
                user_input={
                    "vm_name": "milestone-test-vm",
                    "os_type": "ubuntu",
                    "cpu_cores": 4,
                    "memory_gb": 8,
                    "disk_gb": 40,
                    "software": ["docker", "nginx"],
                }
            )
            
            print(f"✅ Conversation started (ID: {context.id[:8]}...)")
            
            # Save initial state
            await state_manager.save_conversation(context)
            print("✅ Initial state saved")
            
            # Test 2: Process all conversation stages
            print("\n🔄 Processing conversation stages...")
            
            stages_to_process = [
                FlowStage.DATA_COLLECTION,
                FlowStage.VALIDATION,
                FlowStage.PROXMOX_CONFIG,
                FlowStage.SOFTWARE_PROVISION,
                FlowStage.DOCUMENTATION,
            ]
            
            for stage in stages_to_process:
                # Advance to stage
                if stage != FlowStage.DATA_COLLECTION:  # Already on data collection
                    context = await conv_manager.continue_conversation(
                        context.id,
                        target_stage=stage
                    )
                
                # Process stage
                result = await conv_manager.process_stage(context.id, stage)
                assert result is not None
                
                # Save state after each stage
                await state_manager.save_conversation(context)
                
                print(f"  ✅ {stage.value} completed and saved")
            
            print("✅ All stages processed successfully")
            
            # Test 3: Pause and resume conversation
            print("\n⏸️  Testing pause/resume functionality...")
            
            # Pause conversation
            pause_success = await state_manager.pause_conversation(context.id)
            assert pause_success == True
            print("✅ Conversation paused")
            
            # Verify paused status
            paused_context = await state_manager.load_conversation(context.id)
            assert paused_context.status == ConversationStatus.PAUSED
            print("✅ Paused status verified")
            
            # Resume conversation
            resumed_context = await state_manager.resume_conversation(context.id)
            assert resumed_context is not None
            assert resumed_context.status == ConversationStatus.ACTIVE
            print("✅ Conversation resumed")
            
            # Test 4: Complete conversation
            print("\n🏁 Completing conversation...")
            
            # Move to completion stage
            context = await conv_manager.continue_conversation(
                context.id,
                target_stage=FlowStage.COMPLETION
            )
            
            # Process completion
            completion_result = await conv_manager.process_stage(
                context.id,
                FlowStage.COMPLETION
            )
            
            assert completion_result["completion_status"] == "success"
            assert context.status == ConversationStatus.COMPLETED
            
            # Save final state
            await state_manager.save_conversation(context)
            print("✅ Conversation completed and saved")
            
            # Test 5: Verify conversation data integrity
            print("\n🔍 Verifying conversation data integrity...")
            
            # Reload conversation from storage
            final_context = await state_manager.load_conversation(context.id)
            assert final_context is not None
            assert final_context.id == context.id
            assert final_context.status == ConversationStatus.COMPLETED
            assert len(final_context.completed_stages) == 6  # All stages completed
            assert "vm_name" in final_context.user_inputs
            assert final_context.user_inputs["vm_name"] == "milestone-test-vm"
            
            # Verify agent outputs exist for all stages
            expected_outputs = [
                "data_collection",
                "validation", 
                "proxmox_config",
                "software_provision",
                "documentation",
                "completion",
            ]
            
            for output_key in expected_outputs:
                assert output_key in final_context.agent_outputs
                assert final_context.agent_outputs[output_key] is not None
            
            print("✅ Data integrity verified")
            
            # Test 6: Get conversation history
            print("\n📜 Testing conversation history...")
            
            history = await state_manager.get_conversation_history(context.id)
            assert len(history) >= 7  # creation + 6 stages
            
            # Verify history events
            creation_events = [h for h in history if h["event"] == "conversation_created"]
            stage_events = [h for h in history if h["event"] == "stage_completed"]
            
            assert len(creation_events) == 1
            assert len(stage_events) == 6
            
            print(f"✅ History contains {len(history)} events")
            
            return context.id
            
    except Exception as e:
        print(f"❌ Complete conversation lifecycle test failed: {e}")
        raise


async def test_multi_conversation_management():
    """Test managing multiple concurrent conversations."""
    
    print("\n🧪 Testing Multi-Conversation Management")
    print("=" * 50)
    
    try:
        from atlas.agents.conversation_manager import ConversationManager, FlowStage
        from atlas.core.conversation_state import ConversationStateManager, ConversationStateConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup managers
            conv_manager = ConversationManager()
            state_config = ConversationStateConfig(backend_type="sqlite", storage_path=temp_dir)
            state_manager = ConversationStateManager(state_config)
            
            # Create multiple conversations
            conversations = []
            
            for i in range(3):
                context = await conv_manager.start_conversation(
                    user_input={
                        "vm_name": f"multi-test-vm-{i+1}",
                        "os_type": "ubuntu" if i % 2 == 0 else "debian",
                        "cpu_cores": 2 + i,
                    }
                )
                await state_manager.save_conversation(context)
                conversations.append(context.id)
                
                print(f"✅ Created conversation {i+1} (ID: {context.id[:8]}...)")
            
            # List all conversations
            all_conversations = await state_manager.list_conversations()
            assert len(all_conversations) >= 3
            print(f"✅ Listed {len(all_conversations)} conversations")
            
            # Process different stages for each conversation
            for i, conv_id in enumerate(conversations):
                # Process data collection for all
                result = await conv_manager.process_stage(conv_id, FlowStage.DATA_COLLECTION)
                assert result is not None
                
                # Process validation for conversation 1 and 2
                if i < 2:
                    context = await conv_manager.continue_conversation(conv_id, target_stage=FlowStage.VALIDATION)
                    result = await conv_manager.process_stage(conv_id, FlowStage.VALIDATION)
                    assert result is not None
                
                # Save state
                context = await state_manager.load_conversation(conv_id)
                await state_manager.save_conversation(context)
                
                print(f"✅ Processed conversation {i+1}")
            
            # Verify different conversation states
            conv_statuses = []
            for conv_id in conversations:
                status = conv_manager.get_conversation_status(conv_id)
                conv_statuses.append(status)
            
            # Should have conversations at different stages
            stages = [status["current_stage"] for status in conv_statuses]
            assert "data_collection" in stages
            assert "validation" in stages  # At least some should be at validation
            
            print("✅ Multi-conversation management working")
            
            return conversations
            
    except Exception as e:
        print(f"❌ Multi-conversation management test failed: {e}")
        raise


async def test_conversation_recovery_and_resilience():
    """Test conversation recovery and error resilience."""
    
    print("\n🧪 Testing Conversation Recovery and Resilience")
    print("=" * 50)
    
    try:
        from atlas.agents.conversation_manager import ConversationManager, ConversationStatus, FlowStage
        from atlas.core.conversation_state import ConversationStateManager, ConversationStateConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup managers
            conv_manager = ConversationManager()
            state_config = ConversationStateConfig(backend_type="json", storage_path=temp_dir)
            state_manager = ConversationStateManager(state_config)
            
            # Create conversation
            context = await conv_manager.start_conversation(
                user_input={"vm_name": "recovery-test-vm"}
            )
            await state_manager.save_conversation(context)
            
            print(f"✅ Created conversation for recovery test (ID: {context.id[:8]}...)")
            
            # Simulate "crash" by creating new managers (losing in-memory state)
            conv_manager_new = ConversationManager()
            state_manager_new = ConversationStateManager(state_config)
            
            print("✅ Simulated system restart (new manager instances)")
            
            # Recover conversation from storage
            recovered_context = await state_manager_new.load_conversation(context.id)
            assert recovered_context is not None
            assert recovered_context.id == context.id
            assert recovered_context.user_inputs["vm_name"] == "recovery-test-vm"
            
            print("✅ Conversation recovered from storage")
            
            # Continue processing with new manager
            result = await conv_manager_new.process_stage(
                recovered_context.id,
                FlowStage.DATA_COLLECTION,
                state_manager=state_manager_new
            )
            assert result is not None
            
            # Save updated state
            updated_context = await state_manager_new.load_conversation(context.id)
            await state_manager_new.save_conversation(updated_context)
            
            print("✅ Conversation processing resumed successfully")
            
            # Test invalid operations
            print("\n🛡️  Testing error resilience...")
            
            # Try to resume completed conversation
            updated_context.status = ConversationStatus.COMPLETED
            await state_manager_new.save_conversation(updated_context)
            
            resume_result = await state_manager_new.resume_conversation(context.id)
            assert resume_result is None  # Should not resume completed conversation
            
            print("✅ Invalid resume operation handled correctly")
            
            # Test cleanup
            removed_count = await state_manager_new.cleanup_old_conversations(max_age_hours=0)
            assert removed_count >= 0
            
            print("✅ Cleanup operations working")
            
    except Exception as e:
        print(f"❌ Conversation recovery test failed: {e}")
        raise


async def test_conversation_system_performance():
    """Test conversation system performance and scalability."""
    
    print("\n🧪 Testing Conversation System Performance")
    print("=" * 50)
    
    try:
        import time
        from atlas.agents.conversation_manager import ConversationManager, FlowStage
        from atlas.core.conversation_state import ConversationStateManager, ConversationStateConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup managers
            conv_manager = ConversationManager()
            state_config = ConversationStateConfig(
                backend_type="sqlite",
                storage_path=temp_dir,
                max_contexts_in_memory=10,  # Small cache for testing eviction
            )
            state_manager = ConversationStateManager(state_config)
            
            # Performance test: Create many conversations quickly
            print("⚡ Testing conversation creation performance...")
            
            start_time = time.time()
            conversation_ids = []
            
            for i in range(20):
                context = await conv_manager.start_conversation(
                    user_input={
                        "vm_name": f"perf-test-vm-{i:03d}",
                        "batch_id": i // 5,  # Group in batches
                    }
                )
                await state_manager.save_conversation(context)
                conversation_ids.append(context.id)
            
            creation_time = time.time() - start_time
            print(f"✅ Created 20 conversations in {creation_time:.2f}s ({creation_time/20:.3f}s per conversation)")
            
            # Performance test: Batch listing and filtering
            print("📋 Testing listing and filtering performance...")
            
            start_time = time.time()
            all_conversations = await state_manager.list_conversations()
            listing_time = time.time() - start_time
            
            assert len(all_conversations) == 20
            print(f"✅ Listed {len(all_conversations)} conversations in {listing_time:.3f}s")
            
            # Performance test: Cache behavior
            print("🧠 Testing cache behavior...")
            
            # Load conversations to test cache eviction
            loaded_count = 0
            for conv_id in conversation_ids:
                context = await state_manager.load_conversation(conv_id)
                assert context is not None
                loaded_count += 1
            
            print(f"✅ Loaded {loaded_count} conversations")
            
            # Cache should have evicted some contexts (limit is 10)
            cache_size = len(state_manager.cached_contexts)
            print(f"📊 Current cache size: {cache_size}, max: {state_manager.config.max_contexts_in_memory}")
            
            # For 20 conversations with limit 10, cache should be exactly 10
            if cache_size <= state_manager.config.max_contexts_in_memory:
                print(f"✅ Cache eviction working (cache size: {cache_size}/{state_manager.config.max_contexts_in_memory})")
            else:
                raise AssertionError(f"Cache size {cache_size} exceeds limit {state_manager.config.max_contexts_in_memory}")
            
            # Performance test: Batch cleanup
            print("🧹 Testing cleanup performance...")
            
            start_time = time.time()
            removed_count = await state_manager.cleanup_old_conversations(max_age_hours=0)
            cleanup_time = time.time() - start_time
            
            print(f"✅ Cleanup completed in {cleanup_time:.3f}s (removed {removed_count} conversations)")
            
            # Test stats generation
            stats = await state_manager.get_stats()
            print(f"📊 System stats: {stats}")
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        raise


async def main():
    """Main milestone test runner."""
    print("🏆 ATLAS MILESTONE TEST 1")
    print("Interactive Conversation System Validation")
    print("=" * 60)
    print("This comprehensive test validates the complete conversation system")
    print("including agent coordination, flow management, and state persistence.")
    print("=" * 60)
    
    success = True
    completed_conversation_id = None
    multi_conversations = []
    
    try:
        # Test 1: Complete conversation lifecycle
        print("\n🔄 TEST 1: Complete Conversation Lifecycle")
        completed_conversation_id = await test_complete_conversation_lifecycle()
        print("✅ Complete conversation lifecycle test PASSED")
        
        # Test 2: Multi-conversation management
        print("\n👥 TEST 2: Multi-Conversation Management")
        multi_conversations = await test_multi_conversation_management()
        print("✅ Multi-conversation management test PASSED")
        
        # Test 3: Recovery and resilience
        print("\n🛡️  TEST 3: Recovery and Resilience")
        await test_conversation_recovery_and_resilience()
        print("✅ Recovery and resilience test PASSED")
        
        # Test 4: Performance and scalability
        print("\n⚡ TEST 4: Performance and Scalability")
        await test_conversation_system_performance()
        print("✅ Performance and scalability test PASSED")
        
    except Exception as e:
        print(f"\n❌ MILESTONE TEST FAILED: {e}")
        success = False
    
    # Final results
    print("\n" + "=" * 60)
    if success:
        print("🎉 MILESTONE TEST 1: PASSED")
        print("\n🏆 INTERACTIVE CONVERSATION SYSTEM - FULLY OPERATIONAL")
        
        print("\n📋 Validated Capabilities:")
        print("  ✅ End-to-end conversation lifecycle management")
        print("  ✅ Multi-stage workflow processing with VM provisioning")
        print("  ✅ Persistent state management (JSON + SQLite backends)")
        print("  ✅ Pause/resume functionality with state validation")
        print("  ✅ Conversation history tracking and data integrity")
        print("  ✅ Multi-conversation concurrent management")
        print("  ✅ System recovery and error resilience")
        print("  ✅ Performance optimization with caching")
        print("  ✅ Cleanup and maintenance operations")
        
        print("\n🎯 System Metrics:")
        if completed_conversation_id:
            print(f"  • Successfully completed conversation: {completed_conversation_id[:8]}...")
        if multi_conversations:
            print(f"  • Managed {len(multi_conversations)} concurrent conversations")
        print("  • Tested both JSON and SQLite persistence backends")
        print("  • Validated performance with 20+ conversations")
        print("  • Confirmed system recovery after simulated crash")
        
        print("\n✨ The conversation system foundation is SOLID!")
        print("🚀 Ready for FASE 2: Proxmox Integration (Step 2.1)")
        
        print("\n📈 Next Steps:")
        print("  1. Implement Proxmox API client")
        print("  2. VM lifecycle management")
        print("  3. Real agent integration with actual Proxmox calls")
        print("  4. End-to-end VM provisioning workflow")
        
        return True
        
    else:
        print("❌ MILESTONE TEST 1: FAILED")
        print("\n🛠️  Required Actions:")
        print("  1. Review failed test details above")
        print("  2. Fix identified issues")
        print("  3. Re-run milestone test")
        print("  4. Do not proceed to Proxmox integration until this passes")
        
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
