"""
Conversation Manager for ATLAS Multi-Agent System.

This module provides conversation flow orchestration and management
for the ATLAS agent ecosystem, enabling structured multi-agent interactions
for VM provisioning workflows.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from atlas.core import (
    get_logger,
    get_config,
    ConversationError,
    AgentError,
    log_function_call,
    log_performance,
)

from atlas.core.autogen_config import AutoGenManager, AutoGenConfig


logger = get_logger(__name__)


class ConversationStatus(str, Enum):
    """Conversation status enumeration."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlowStage(str, Enum):
    """Conversation flow stages."""
    DATA_COLLECTION = "data_collection"
    VALIDATION = "validation"
    PROXMOX_CONFIG = "proxmox_config"
    SOFTWARE_PROVISION = "software_provision"
    DOCUMENTATION = "documentation"
    COMPLETION = "completion"


@dataclass
class ConversationContext:
    """Context and state for a conversation session."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ConversationStatus = ConversationStatus.INITIALIZING
    current_stage: FlowStage = FlowStage.DATA_COLLECTION
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Conversation data
    user_inputs: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    vm_spec: Optional[Dict[str, Any]] = None
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Flow control
    completed_stages: List[FlowStage] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_status(self, status: ConversationStatus) -> None:
        """Update conversation status with timestamp."""
        self.status = status
        self.updated_at = datetime.now()
        logger.info(f"Conversation {self.id} status updated to {status}")
    
    def advance_stage(self, stage: FlowStage) -> None:
        """Advance to next conversation stage."""
        if self.current_stage not in self.completed_stages:
            self.completed_stages.append(self.current_stage)
        
        self.current_stage = stage
        self.updated_at = datetime.now()
        logger.info(f"Conversation {self.id} advanced to stage {stage}")
    
    def add_error(self, error: str, stage: Optional[FlowStage] = None) -> None:
        """Add error to conversation context."""
        error_data = {
            "message": error,
            "stage": stage or self.current_stage,
            "timestamp": datetime.now().isoformat(),
        }
        self.errors.append(error_data)
        logger.error(f"Conversation {self.id} error in {stage}: {error}")


@dataclass
class ConversationFlow:
    """Defines a conversation flow with stages and transitions."""
    
    name: str
    description: str
    stages: List[FlowStage] = field(default_factory=list)
    stage_configs: Dict[FlowStage, Dict[str, Any]] = field(default_factory=dict)
    transitions: Dict[FlowStage, List[FlowStage]] = field(default_factory=dict)
    
    def can_transition(self, from_stage: FlowStage, to_stage: FlowStage) -> bool:
        """Check if transition between stages is allowed."""
        return to_stage in self.transitions.get(from_stage, [])
    
    def get_next_stages(self, current_stage: FlowStage) -> List[FlowStage]:
        """Get possible next stages from current stage."""
        return self.transitions.get(current_stage, [])


class ConversationManager:
    """Manages conversation flows and agent coordination."""
    
    def __init__(self, autogen_manager: Optional[AutoGenManager] = None):
        """Initialize conversation manager."""
        self.logger = get_logger(self.__class__.__name__)
        self.autogen_manager = autogen_manager or AutoGenManager()
        
        # Active conversations
        self.active_conversations: Dict[str, ConversationContext] = {}
        
        # Flow definitions
        self.flows: Dict[str, ConversationFlow] = {}
        
        # Initialize default flows
        self._initialize_default_flows()
        
        self.logger.info("ConversationManager initialized")
    
    def _initialize_default_flows(self) -> None:
        """Initialize default conversation flows."""
        
        # Standard VM provisioning flow
        vm_provision_flow = ConversationFlow(
            name="vm_provisioning",
            description="Standard VM provisioning workflow",
            stages=[
                FlowStage.DATA_COLLECTION,
                FlowStage.VALIDATION,
                FlowStage.PROXMOX_CONFIG,
                FlowStage.SOFTWARE_PROVISION,
                FlowStage.DOCUMENTATION,
                FlowStage.COMPLETION,
            ],
            stage_configs={
                FlowStage.DATA_COLLECTION: {
                    "timeout": 300,  # 5 minutes
                    "max_rounds": 10,
                    "required_fields": ["vm_name", "os_type", "resources"],
                },
                FlowStage.VALIDATION: {
                    "timeout": 120,  # 2 minutes
                    "max_rounds": 5,
                    "validation_rules": ["resource_limits", "naming_convention", "network_config"],
                },
                FlowStage.PROXMOX_CONFIG: {
                    "timeout": 180,  # 3 minutes
                    "max_rounds": 8,
                    "config_sections": ["compute", "storage", "network"],
                },
                FlowStage.SOFTWARE_PROVISION: {
                    "timeout": 240,  # 4 minutes
                    "max_rounds": 10,
                    "optional": True,  # Can be skipped
                },
                FlowStage.DOCUMENTATION: {
                    "timeout": 120,  # 2 minutes
                    "max_rounds": 5,
                    "output_formats": ["markdown", "yaml"],
                },
            },
            transitions={
                FlowStage.DATA_COLLECTION: [FlowStage.VALIDATION],
                FlowStage.VALIDATION: [FlowStage.DATA_COLLECTION, FlowStage.PROXMOX_CONFIG],
                FlowStage.PROXMOX_CONFIG: [FlowStage.SOFTWARE_PROVISION, FlowStage.DOCUMENTATION],
                FlowStage.SOFTWARE_PROVISION: [FlowStage.DOCUMENTATION],
                FlowStage.DOCUMENTATION: [FlowStage.COMPLETION],
            }
        )
        
        self.flows["vm_provisioning"] = vm_provision_flow
        self.logger.info("Default conversation flows initialized")
    
    async def start_conversation(
        self,
        flow_name: str = "vm_provisioning",
        user_input: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ConversationContext:
        """Start a new conversation session."""
        
        if flow_name not in self.flows:
            raise ConversationError(f"Unknown flow: {flow_name}")
        
        # Create conversation context
        context = ConversationContext()
        context.metadata.update({
            "flow_name": flow_name,
            "start_kwargs": kwargs,
        })
        
        if user_input:
            context.user_inputs.update(user_input)
        
        # Update status and store
        context.update_status(ConversationStatus.ACTIVE)
        self.active_conversations[context.id] = context
        
        self.logger.info(f"Started conversation {context.id} with flow {flow_name}")
        return context
    
    async def continue_conversation(
        self,
        conversation_id: str,
        user_input: Optional[Dict[str, Any]] = None,
        target_stage: Optional[FlowStage] = None,
    ) -> ConversationContext:
        """Continue an existing conversation."""
        
        if conversation_id not in self.active_conversations:
            raise ConversationError(f"Conversation {conversation_id} not found")
        
        context = self.active_conversations[conversation_id]
        flow = self.flows[context.metadata["flow_name"]]
        
        if user_input:
            context.user_inputs.update(user_input)
        
        # Handle stage transition if requested
        if target_stage:
            if flow.can_transition(context.current_stage, target_stage):
                context.advance_stage(target_stage)
            else:
                raise ConversationError(
                    f"Invalid transition from {context.current_stage} to {target_stage}"
                )
        
        context.updated_at = datetime.now()
        self.logger.info(f"Continued conversation {conversation_id}")
        return context
    
    async def process_stage(
        self,
        conversation_id: str,
        stage: Optional[FlowStage] = None,
    ) -> Dict[str, Any]:
        """Process a specific conversation stage with appropriate agents."""
        
        if conversation_id not in self.active_conversations:
            raise ConversationError(f"Conversation {conversation_id} not found")
        
        context = self.active_conversations[conversation_id]
        target_stage = stage or context.current_stage
        flow = self.flows[context.metadata["flow_name"]]
        
        stage_config = flow.stage_configs.get(target_stage, {})
        
        try:
            # Route to appropriate stage processor
            if target_stage == FlowStage.DATA_COLLECTION:
                result = await self._process_data_collection(context, stage_config)
            elif target_stage == FlowStage.VALIDATION:
                result = await self._process_validation(context, stage_config)
            elif target_stage == FlowStage.PROXMOX_CONFIG:
                result = await self._process_proxmox_config(context, stage_config)
            elif target_stage == FlowStage.SOFTWARE_PROVISION:
                result = await self._process_software_provision(context, stage_config)
            elif target_stage == FlowStage.DOCUMENTATION:
                result = await self._process_documentation(context, stage_config)
            elif target_stage == FlowStage.COMPLETION:
                result = await self._process_completion(context, stage_config)
            else:
                raise ConversationError(f"Unknown stage: {target_stage}")
            
            # Store result and update context
            context.agent_outputs[target_stage.value] = result
            context.updated_at = datetime.now()
            
            self.logger.info(f"Processed stage {target_stage} for conversation {conversation_id}")
            return result
            
        except Exception as e:
            context.add_error(str(e), target_stage)
            raise ConversationError(f"Stage processing failed: {e}") from e
    
    async def _process_data_collection(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data collection stage."""
        # Placeholder implementation - will be enhanced with actual agents
        self.logger.info(f"Processing data collection for conversation {context.id}")
        
        # Simulate data collection
        collected_data = {
            "vm_name": context.user_inputs.get("vm_name", "atlas-vm-001"),
            "os_type": context.user_inputs.get("os_type", "ubuntu"),
            "cpu_cores": context.user_inputs.get("cpu_cores", 2),
            "memory_gb": context.user_inputs.get("memory_gb", 4),
            "disk_gb": context.user_inputs.get("disk_gb", 20),
            "collection_status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
        
        return collected_data
    
    async def _process_validation(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process validation stage."""
        self.logger.info(f"Processing validation for conversation {context.id}")
        
        # Get data from previous stage
        data_collection = context.agent_outputs.get("data_collection", {})
        
        # Simulate validation
        validation_result = {
            "validation_status": "passed",
            "issues": [],
            "warnings": [],
            "validated_fields": list(data_collection.keys()),
            "timestamp": datetime.now().isoformat(),
        }
        
        return validation_result
    
    async def _process_proxmox_config(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Proxmox configuration stage."""
        self.logger.info(f"Processing Proxmox config for conversation {context.id}")
        
        # Simulate Proxmox configuration generation
        proxmox_config = {
            "vm_id": 1001,
            "node": "proxmox-node1",
            "template": "ubuntu-cloud",
            "config_status": "generated",
            "timestamp": datetime.now().isoformat(),
        }
        
        return proxmox_config
    
    async def _process_software_provision(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process software provisioning stage."""
        self.logger.info(f"Processing software provisioning for conversation {context.id}")
        
        # Simulate software provisioning
        provision_result = {
            "software_packages": context.user_inputs.get("software", []),
            "provision_status": "planned",
            "ansible_playbook": "generated",
            "timestamp": datetime.now().isoformat(),
        }
        
        return provision_result
    
    async def _process_documentation(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process documentation generation stage."""
        self.logger.info(f"Processing documentation for conversation {context.id}")
        
        # Simulate documentation generation
        doc_result = {
            "documentation_status": "generated",
            "formats": ["markdown", "yaml"],
            "files": ["vm-setup-guide.md", "vm-config.yaml"],
            "timestamp": datetime.now().isoformat(),
        }
        
        return doc_result
    
    async def _process_completion(
        self,
        context: ConversationContext,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process conversation completion stage."""
        self.logger.info(f"Processing completion for conversation {context.id}")
        
        # Update conversation status
        context.update_status(ConversationStatus.COMPLETED)
        context.advance_stage(FlowStage.COMPLETION)
        
        # Generate completion summary
        completion_result = {
            "completion_status": "success",
            "total_stages": len(context.completed_stages),
            "duration": (context.updated_at - context.created_at).total_seconds(),
            "outputs": list(context.agent_outputs.keys()),
            "timestamp": datetime.now().isoformat(),
        }
        
        return completion_result
    
    def get_conversation_status(self, conversation_id: str) -> Dict[str, Any]:
        """Get status of a conversation."""
        if conversation_id not in self.active_conversations:
            raise ConversationError(f"Conversation {conversation_id} not found")
        
        context = self.active_conversations[conversation_id]
        flow = self.flows[context.metadata["flow_name"]]
        
        return {
            "id": context.id,
            "status": context.status.value,
            "current_stage": context.current_stage.value,
            "completed_stages": [stage.value for stage in context.completed_stages],
            "next_stages": [stage.value for stage in flow.get_next_stages(context.current_stage)],
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "errors": context.errors,
            "progress": len(context.completed_stages) / len(flow.stages) * 100,
        }
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all active conversations."""
        conversations = []
        for conv_id, context in self.active_conversations.items():
            conversations.append({
                "id": conv_id,
                "status": context.status.value,
                "current_stage": context.current_stage.value,
                "flow": context.metadata.get("flow_name"),
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
            })
        return conversations
    
    async def cancel_conversation(self, conversation_id: str) -> None:
        """Cancel an active conversation."""
        if conversation_id not in self.active_conversations:
            raise ConversationError(f"Conversation {conversation_id} not found")
        
        context = self.active_conversations[conversation_id]
        context.update_status(ConversationStatus.CANCELLED)
        
        # Could add cleanup logic here
        self.logger.info(f"Cancelled conversation {conversation_id}")
    
    def cleanup_completed_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up old completed conversations."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        conversations_to_remove = []
        for conv_id, context in self.active_conversations.items():
            if (context.status in [ConversationStatus.COMPLETED, ConversationStatus.CANCELLED] 
                and context.updated_at < cutoff_time):
                conversations_to_remove.append(conv_id)
        
        for conv_id in conversations_to_remove:
            del self.active_conversations[conv_id]
            removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old conversations")
        
        return removed_count
