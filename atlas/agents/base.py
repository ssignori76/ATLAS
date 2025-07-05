"""
Base agent class for the ATLAS multi-agent system.

This module provides the foundational BaseAgent class that all ATLAS agents
inherit from, implementing common functionality like configuration management,
logging, error handling, and communication protocols.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from atlas.core import (
    get_logger,
    get_config,
    AtlasError,
    AgentError,
    log_function_call,
    log_performance,
)


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class MessageType(str, Enum):
    """Agent message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentMessage:
    """Message structure for agent communication."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.REQUEST
    sender: str = ""
    recipient: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    content: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expires_at: Optional[datetime] = None
    priority: int = 0  # Higher number = higher priority


@dataclass
class AgentCapabilities:
    """Agent capabilities definition."""
    
    name: str
    version: str
    description: str
    supported_operations: List[str]
    input_types: List[str]
    output_types: List[str]
    dependencies: List[str] = field(default_factory=list)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    concurrent_requests: int = 1


class BaseAgent(ABC):
    """Base class for all ATLAS agents.
    
    This class provides common functionality including:
    - Configuration management
    - Logging
    - Message handling
    - Error handling
    - Status management
    - Health monitoring
    """
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            config: Agent-specific configuration overrides
        """
        self.agent_id = agent_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.logger = get_logger(f"agents.{self.__class__.__name__}")
        self.config = config or {}
        
        # Agent state
        self._status = AgentStatus.INITIALIZING
        self._last_heartbeat = datetime.utcnow()
        self._error_count = 0
        self._max_errors = self.config.get('max_errors', 10)
        
        # Message handling
        self._message_handlers: Dict[MessageType, callable] = {}
        self._active_requests: Dict[str, AgentMessage] = {}
        
        # Performance metrics
        self._start_time = datetime.utcnow()
        self._processed_messages = 0
        self._failed_messages = 0
        
        # Initialize agent
        self._setup_default_handlers()
        self.logger.info(f"Agent {self.agent_id} initializing")
    
    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status
    
    @property
    def capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        return self._get_capabilities()
    
    @property
    def uptime(self) -> timedelta:
        """Get agent uptime."""
        return datetime.utcnow() - self._start_time
    
    @property
    def health_score(self) -> float:
        """Calculate agent health score (0.0 - 1.0)."""
        if self._processed_messages == 0:
            return 1.0
        
        success_rate = 1.0 - (self._failed_messages / self._processed_messages)
        error_penalty = min(self._error_count / self._max_errors, 1.0)
        
        return max(0.0, success_rate - error_penalty)
    
    @abstractmethod
    def _get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request. Must be implemented by subclasses.
        
        Args:
            request: Request data to process
            
        Returns:
            Response data
            
        Raises:
            AgentError: If processing fails
        """
        pass
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        try:
            self.logger.info(f"Initializing agent {self.agent_id}")
            
            # Load system configuration
            system_config = get_config()
            
            # Perform agent-specific initialization
            await self._initialize_agent()
            
            # Update status
            self._status = AgentStatus.READY
            self.logger.info(f"Agent {self.agent_id} ready")
            
        except Exception as e:
            self._status = AgentStatus.ERROR
            self._error_count += 1
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            raise AgentError(f"Agent initialization failed: {e}", self.agent_id, "initialize")
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        try:
            self.logger.info(f"Shutting down agent {self.agent_id}")
            
            # Cancel active requests
            for request_id in list(self._active_requests.keys()):
                await self._cancel_request(request_id)
            
            # Perform agent-specific cleanup
            await self._cleanup_agent()
            
            self._status = AgentStatus.STOPPED
            self.logger.info(f"Agent {self.agent_id} stopped")
            
        except Exception as e:
            self.logger.error(f"Error during agent shutdown: {e}")
            raise
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming message.
        
        Args:
            message: Incoming message to handle
            
        Returns:
            Response message if applicable
        """
        try:
            self.logger.debug(f"Handling message {message.id} from {message.sender}")
            
            # Check if message has expired
            if message.expires_at and datetime.utcnow() > message.expires_at:
                self.logger.warning(f"Message {message.id} has expired")
                return self._create_error_response(message, "Message expired")
            
            # Update heartbeat
            self._last_heartbeat = datetime.utcnow()
            
            # Route message to appropriate handler
            handler = self._message_handlers.get(message.type)
            if not handler:
                return self._create_error_response(message, f"No handler for message type {message.type}")
            
            # Track active request
            if message.type == MessageType.REQUEST:
                self._active_requests[message.id] = message
            
            try:
                response = await handler(message)
                self._processed_messages += 1
                return response
                
            finally:
                # Remove from active requests
                self._active_requests.pop(message.id, None)
        
        except Exception as e:
            self._failed_messages += 1
            self._error_count += 1
            self.logger.error(f"Error handling message {message.id}: {e}")
            return self._create_error_response(message, str(e))
    
    async def send_request(self, recipient: str, content: Dict[str, Any], 
                          timeout: int = 30) -> Dict[str, Any]:
        """Send a request to another agent.
        
        Args:
            recipient: Target agent ID
            content: Request content
            timeout: Request timeout in seconds
            
        Returns:
            Response content
            
        Raises:
            AgentError: If request fails
        """
        # TODO: Implement inter-agent communication
        # This would integrate with a message bus like RabbitMQ, Redis, or similar
        raise NotImplementedError("Inter-agent communication not yet implemented")
    
    async def send_notification(self, recipients: List[str], content: Dict[str, Any]) -> None:
        """Send notification to multiple agents.
        
        Args:
            recipients: List of recipient agent IDs
            content: Notification content
        """
        # TODO: Implement notification broadcasting
        raise NotImplementedError("Agent notifications not yet implemented")
    
    def _setup_default_handlers(self) -> None:
        """Setup default message handlers."""
        self._message_handlers[MessageType.REQUEST] = self._handle_request
        self._message_handlers[MessageType.HEARTBEAT] = self._handle_heartbeat
        self._message_handlers[MessageType.ERROR] = self._handle_error
    
    async def _handle_request(self, message: AgentMessage) -> AgentMessage:
        """Handle request message."""
        try:
            # Update status
            old_status = self._status
            self._status = AgentStatus.BUSY
            
            try:
                # Process the request
                response_content = await self.process_request(message.content)
                
                # Create response message
                response = AgentMessage(
                    type=MessageType.RESPONSE,
                    sender=self.agent_id,
                    recipient=message.sender,
                    content=response_content,
                    correlation_id=message.id,
                )
                
                return response
                
            finally:
                # Restore status
                self._status = old_status
        
        except Exception as e:
            return self._create_error_response(message, str(e))
    
    async def _handle_heartbeat(self, message: AgentMessage) -> AgentMessage:
        """Handle heartbeat message."""
        return AgentMessage(
            type=MessageType.RESPONSE,
            sender=self.agent_id,
            recipient=message.sender,
            content={
                "status": self._status.value,
                "health_score": self.health_score,
                "uptime": self.uptime.total_seconds(),
                "processed_messages": self._processed_messages,
                "error_count": self._error_count,
            },
            correlation_id=message.id,
        )
    
    async def _handle_error(self, message: AgentMessage) -> None:
        """Handle error message."""
        self.logger.error(f"Received error from {message.sender}: {message.content}")
    
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create error response message."""
        return AgentMessage(
            type=MessageType.ERROR,
            sender=self.agent_id,
            recipient=original_message.sender,
            content={"error": error, "original_message_id": original_message.id},
            correlation_id=original_message.id,
        )
    
    async def _cancel_request(self, request_id: str) -> None:
        """Cancel an active request."""
        if request_id in self._active_requests:
            del self._active_requests[request_id]
            self.logger.info(f"Cancelled request {request_id}")
    
    async def _initialize_agent(self) -> None:
        """Agent-specific initialization. Override in subclasses."""
        pass
    
    async def _cleanup_agent(self) -> None:
        """Agent-specific cleanup. Override in subclasses."""
        pass
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}({self.agent_id}, status={self._status.value})"
    
    def __repr__(self) -> str:
        """Detailed representation of the agent."""
        return (
            f"{self.__class__.__name__}("
            f"agent_id='{self.agent_id}', "
            f"status='{self._status.value}', "
            f"uptime={self.uptime}, "
            f"health_score={self.health_score:.2f})"
        )
