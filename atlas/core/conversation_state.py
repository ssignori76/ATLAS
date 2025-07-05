"""
Conversation State Management for ATLAS Multi-Agent System.

This module provides persistence and state management capabilities
for conversation sessions, enabling conversation resume, history tracking,
and multi-session management.
"""

import json
import sqlite3
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager

from atlas.core import (
    get_logger,
    get_config,
    ConversationError,
    FileOperationError,
    log_function_call,
)

from atlas.agents.conversation_manager import (
    ConversationContext,
    ConversationStatus,
    FlowStage,
)


logger = get_logger(__name__)


class PersistenceBackend:
    """Abstract base for persistence backends."""
    
    async def save_context(self, context: ConversationContext) -> None:
        """Save conversation context."""
        raise NotImplementedError
    
    async def load_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load conversation context by ID."""
        raise NotImplementedError
    
    async def list_contexts(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversation contexts with optional filtering."""
        raise NotImplementedError
    
    async def delete_context(self, conversation_id: str) -> bool:
        """Delete conversation context."""
        raise NotImplementedError
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
        """Clean up old contexts."""
        raise NotImplementedError


class JSONPersistenceBackend(PersistenceBackend):
    """JSON file-based persistence backend."""
    
    def __init__(self, storage_dir: Union[str, Path] = None):
        """Initialize JSON persistence backend."""
        self.storage_dir = Path(storage_dir or Path.home() / ".atlas" / "conversations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(self.__class__.__name__)
        
        # Create index file if it doesn't exist
        self.index_file = self.storage_dir / "index.json"
        if not self.index_file.exists():
            self._save_index({})
        
        self.logger.info(f"JSON persistence initialized: {self.storage_dir}")
    
    def _get_context_file(self, conversation_id: str) -> Path:
        """Get file path for conversation context."""
        return self.storage_dir / f"{conversation_id}.json"
    
    def _load_index(self) -> Dict[str, Any]:
        """Load conversation index."""
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load index: {e}")
            return {}
    
    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save conversation index."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save index: {e}")
            raise FileOperationError(f"Failed to save index: {e}")
    
    def _context_to_dict(self, context: ConversationContext) -> Dict[str, Any]:
        """Convert context to serializable dictionary."""
        data = asdict(context)
        
        # Convert enums to strings
        data['status'] = context.status.value
        data['current_stage'] = context.current_stage.value
        data['completed_stages'] = [stage.value for stage in context.completed_stages]
        
        # Convert datetime objects to ISO strings
        data['created_at'] = context.created_at.isoformat()
        data['updated_at'] = context.updated_at.isoformat()
        
        return data
    
    def _dict_to_context(self, data: Dict[str, Any]) -> ConversationContext:
        """Convert dictionary to ConversationContext."""
        # Convert string enums back to enum objects
        data['status'] = ConversationStatus(data['status'])
        data['current_stage'] = FlowStage(data['current_stage'])
        data['completed_stages'] = [FlowStage(stage) for stage in data['completed_stages']]
        
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return ConversationContext(**data)
    
    async def save_context(self, context: ConversationContext) -> None:
        """Save conversation context to JSON file."""
        try:
            # Ensure storage directory exists
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Save context file
            context_file = self._get_context_file(context.id)
            data = self._context_to_dict(context)
            
            with open(context_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Update index
            index = self._load_index()
            index[context.id] = {
                'id': context.id,
                'status': context.status.value,
                'current_stage': context.current_stage.value,
                'flow_name': context.metadata.get('flow_name'),
                'created_at': context.created_at.isoformat(),
                'updated_at': context.updated_at.isoformat(),
                'file': str(context_file),
            }
            self._save_index(index)
            
            self.logger.debug(f"Saved context {context.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save context {context.id}: {e}")
            raise FileOperationError(f"Failed to save context: {e}")
    
    async def load_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load conversation context from JSON file."""
        try:
            context_file = self._get_context_file(conversation_id)
            
            if not context_file.exists():
                self.logger.warning(f"Context file not found: {context_file}")
                return None
            
            with open(context_file, 'r') as f:
                data = json.load(f)
            
            context = self._dict_to_context(data)
            self.logger.debug(f"Loaded context {conversation_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to load context {conversation_id}: {e}")
            raise FileOperationError(f"Failed to load context: {e}")
    
    async def list_contexts(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversation contexts with optional filtering."""
        try:
            index = self._load_index()
            contexts = list(index.values())
            
            # Filter by status if specified
            if status:
                contexts = [ctx for ctx in contexts if ctx['status'] == status.value]
            
            # Sort by updated_at (most recent first)
            contexts.sort(key=lambda x: x['updated_at'], reverse=True)
            
            # Apply pagination
            if limit:
                contexts = contexts[offset:offset + limit]
            
            return contexts
            
        except Exception as e:
            self.logger.error(f"Failed to list contexts: {e}")
            raise FileOperationError(f"Failed to list contexts: {e}")
    
    async def delete_context(self, conversation_id: str) -> bool:
        """Delete conversation context."""
        try:
            # Remove context file
            context_file = self._get_context_file(conversation_id)
            if context_file.exists():
                context_file.unlink()
            
            # Remove from index
            index = self._load_index()
            if conversation_id in index:
                del index[conversation_id]
                self._save_index(index)
                self.logger.info(f"Deleted context {conversation_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete context {conversation_id}: {e}")
            raise FileOperationError(f"Failed to delete context: {e}")
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
        """Clean up old contexts."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            index = self._load_index()
            
            contexts_to_remove = []
            for conv_id, ctx_info in index.items():
                updated_at = datetime.fromisoformat(ctx_info['updated_at'])
                status = ConversationStatus(ctx_info['status'])
                
                if (status in [ConversationStatus.COMPLETED, ConversationStatus.CANCELLED] 
                    and updated_at < cutoff_time):
                    contexts_to_remove.append(conv_id)
            
            removed_count = 0
            for conv_id in contexts_to_remove:
                if await self.delete_context(conv_id):
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old contexts")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old contexts: {e}")
            return 0


class SQLitePersistenceBackend(PersistenceBackend):
    """SQLite database persistence backend."""
    
    def __init__(self, db_path: Union[str, Path] = None):
        """Initialize SQLite persistence backend."""
        if db_path:
            # If db_path is provided, use it as a directory and create db file inside
            if isinstance(db_path, str):
                db_path = Path(db_path)
            if db_path.is_dir() or not db_path.suffix:
                # It's a directory, create db file inside it
                self.db_path = db_path / "conversations.db"
            else:
                # It's a file path
                self.db_path = db_path
        else:
            # Default location
            self.db_path = Path.home() / ".atlas" / "conversations.db"
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(self.__class__.__name__)
        self._db_initialized = False
        
        self.logger.info(f"SQLite persistence initialized: {self.db_path}")
    
    async def _ensure_database(self) -> None:
        """Ensure database is initialized."""
        if not self._db_initialized:
            await self._init_database()
            self._db_initialized = True
    
    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    flow_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    user_inputs TEXT,
                    agent_outputs TEXT,
                    vm_spec TEXT,
                    validation_results TEXT,
                    completed_stages TEXT,
                    errors TEXT,
                    metadata TEXT
                )
            """)
            
            # Create index for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_status 
                ON conversations(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
                ON conversations(updated_at)
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.debug("Database schema initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise FileOperationError(f"Failed to initialize database: {e}")
    
    def _context_to_db_row(self, context: ConversationContext) -> Dict[str, Any]:
        """Convert context to database row."""
        return {
            'id': context.id,
            'status': context.status.value,
            'current_stage': context.current_stage.value,
            'flow_name': context.metadata.get('flow_name'),
            'created_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat(),
            'user_inputs': json.dumps(context.user_inputs),
            'agent_outputs': json.dumps(context.agent_outputs),
            'vm_spec': json.dumps(context.vm_spec) if context.vm_spec else None,
            'validation_results': json.dumps(context.validation_results),
            'completed_stages': json.dumps([stage.value for stage in context.completed_stages]),
            'errors': json.dumps(context.errors),
            'metadata': json.dumps(context.metadata),
        }
    
    def _db_row_to_context(self, row: sqlite3.Row) -> ConversationContext:
        """Convert database row to ConversationContext."""
        return ConversationContext(
            id=row['id'],
            status=ConversationStatus(row['status']),
            current_stage=FlowStage(row['current_stage']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            user_inputs=json.loads(row['user_inputs']),
            agent_outputs=json.loads(row['agent_outputs']),
            vm_spec=json.loads(row['vm_spec']) if row['vm_spec'] else None,
            validation_results=json.loads(row['validation_results']),
            completed_stages=[FlowStage(stage) for stage in json.loads(row['completed_stages'])],
            errors=json.loads(row['errors']),
            metadata=json.loads(row['metadata']),
        )
    
    async def save_context(self, context: ConversationContext) -> None:
        """Save conversation context to SQLite database."""
        try:
            await self._ensure_database()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            row_data = self._context_to_db_row(context)
            
            # Use INSERT OR REPLACE for upsert behavior
            cursor.execute("""
                INSERT OR REPLACE INTO conversations (
                    id, status, current_stage, flow_name, created_at, updated_at,
                    user_inputs, agent_outputs, vm_spec, validation_results,
                    completed_stages, errors, metadata
                ) VALUES (
                    :id, :status, :current_stage, :flow_name, :created_at, :updated_at,
                    :user_inputs, :agent_outputs, :vm_spec, :validation_results,
                    :completed_stages, :errors, :metadata
                )
            """, row_data)
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Saved context {context.id} to database")
            
        except Exception as e:
            self.logger.error(f"Failed to save context {context.id}: {e}")
            raise FileOperationError(f"Failed to save context: {e}")
    
    async def load_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load conversation context from SQLite database."""
        try:
            await self._ensure_database()
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                context = self._db_row_to_context(row)
                self.logger.debug(f"Loaded context {conversation_id} from database")
                return context
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load context {conversation_id}: {e}")
            raise FileOperationError(f"Failed to load context: {e}")
    
    async def list_contexts(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversation contexts with optional filtering."""
        try:
            await self._ensure_database()
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT id, status, current_stage, flow_name, created_at, updated_at FROM conversations"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status.value)
            
            query += " ORDER BY updated_at DESC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            contexts = []
            for row in rows:
                contexts.append({
                    'id': row['id'],
                    'status': row['status'],
                    'current_stage': row['current_stage'],
                    'flow_name': row['flow_name'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                })
            
            return contexts
            
        except Exception as e:
            self.logger.error(f"Failed to list contexts: {e}")
            raise FileOperationError(f"Failed to list contexts: {e}")
    
    async def delete_context(self, conversation_id: str) -> bool:
        """Delete conversation context from database."""
        try:
            await self._ensure_database()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                self.logger.info(f"Deleted context {conversation_id} from database")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete context {conversation_id}: {e}")
            raise FileOperationError(f"Failed to delete context: {e}")
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
        """Clean up old contexts from database."""
        try:
            await self._ensure_database()
            
            cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM conversations 
                WHERE (status IN ('completed', 'cancelled')) 
                AND updated_at < ?
            """, (cutoff_time,))
            
            removed_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old contexts from database")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old contexts: {e}")
            return 0


@dataclass
class ConversationStateConfig:
    """Configuration for conversation state management."""
    
    backend_type: str = "json"  # "json" or "sqlite"
    storage_path: Optional[str] = None
    auto_save: bool = True
    auto_cleanup_hours: int = 24
    max_contexts_in_memory: int = 100


class ConversationStateManager:
    """Manages conversation state persistence and recovery."""
    
    def __init__(self, config: Optional[ConversationStateConfig] = None):
        """Initialize conversation state manager."""
        self.config = config or ConversationStateConfig()
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize persistence backend
        if self.config.backend_type == "sqlite":
            self.backend = SQLitePersistenceBackend(self.config.storage_path)
        else:
            self.backend = JSONPersistenceBackend(self.config.storage_path)
        
        # In-memory cache for active contexts
        self.cached_contexts: Dict[str, ConversationContext] = {}
        
        self.logger.info(f"ConversationStateManager initialized with {self.config.backend_type} backend")
    
    async def save_conversation(self, context: ConversationContext) -> None:
        """Save conversation context to persistent storage."""
        try:
            # Save to backend
            await self.backend.save_context(context)
            
            # Update cache
            self.cached_contexts[context.id] = context
            
            # Manage cache size
            if len(self.cached_contexts) > self.config.max_contexts_in_memory:
                # Remove oldest cached context
                oldest_id = min(self.cached_contexts.keys(), 
                              key=lambda x: self.cached_contexts[x].updated_at)
                del self.cached_contexts[oldest_id]
                self.logger.debug(f"Evicted context {oldest_id} from cache")
            
            self.logger.debug(f"Saved conversation {context.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save conversation {context.id}: {e}")
            raise ConversationError(f"Failed to save conversation: {e}")
    
    async def load_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load conversation context from storage."""
        try:
            # Check cache first
            if conversation_id in self.cached_contexts:
                self.logger.debug(f"Loaded conversation {conversation_id} from cache")
                return self.cached_contexts[conversation_id]
            
            # Load from backend
            context = await self.backend.load_context(conversation_id)
            
            # Cache if found
            if context:
                self.cached_contexts[conversation_id] = context
                
                # Manage cache size
                if len(self.cached_contexts) > self.config.max_contexts_in_memory:
                    # Remove oldest cached context
                    oldest_id = min(self.cached_contexts.keys(), 
                                  key=lambda x: self.cached_contexts[x].updated_at)
                    del self.cached_contexts[oldest_id]
                    self.logger.debug(f"Evicted context {oldest_id} from cache")
                
                self.logger.debug(f"Loaded and cached conversation {conversation_id}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to load conversation {conversation_id}: {e}")
            raise ConversationError(f"Failed to load conversation: {e}")
    
    async def list_conversations(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations with optional filtering."""
        try:
            return await self.backend.list_contexts(status, limit, offset)
        except Exception as e:
            self.logger.error(f"Failed to list conversations: {e}")
            raise ConversationError(f"Failed to list conversations: {e}")
    
    async def resume_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Resume a conversation by loading its context."""
        try:
            context = await self.load_conversation(conversation_id)
            
            if not context:
                self.logger.warning(f"Cannot resume conversation {conversation_id}: not found")
                return None
            
            if context.status in [ConversationStatus.COMPLETED, ConversationStatus.CANCELLED]:
                self.logger.warning(f"Cannot resume conversation {conversation_id}: already {context.status.value}")
                return None
            
            # Update status to active if paused
            if context.status == ConversationStatus.PAUSED:
                context.status = ConversationStatus.ACTIVE
                context.updated_at = datetime.now()
                await self.save_conversation(context)
            
            self.logger.info(f"Resumed conversation {conversation_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to resume conversation {conversation_id}: {e}")
            raise ConversationError(f"Failed to resume conversation: {e}")
    
    async def pause_conversation(self, conversation_id: str) -> bool:
        """Pause an active conversation."""
        try:
            context = await self.load_conversation(conversation_id)
            
            if not context:
                self.logger.warning(f"Cannot pause conversation {conversation_id}: not found")
                return False
            
            if context.status != ConversationStatus.ACTIVE:
                self.logger.warning(f"Cannot pause conversation {conversation_id}: not active")
                return False
            
            context.status = ConversationStatus.PAUSED
            context.updated_at = datetime.now()
            await self.save_conversation(context)
            
            self.logger.info(f"Paused conversation {conversation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause conversation {conversation_id}: {e}")
            raise ConversationError(f"Failed to pause conversation: {e}")
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation from storage."""
        try:
            # Remove from cache
            if conversation_id in self.cached_contexts:
                del self.cached_contexts[conversation_id]
            
            # Delete from backend
            success = await self.backend.delete_context(conversation_id)
            
            if success:
                self.logger.info(f"Deleted conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise ConversationError(f"Failed to delete conversation: {e}")
    
    async def cleanup_old_conversations(self, max_age_hours: Optional[int] = None) -> int:
        """Clean up old completed/cancelled conversations."""
        try:
            max_age = max_age_hours or self.config.auto_cleanup_hours
            removed_count = await self.backend.cleanup_old_contexts(max_age)
            
            # Also clean up cache
            cutoff_time = datetime.now() - timedelta(hours=max_age)
            cache_removals = []
            
            for conv_id, context in self.cached_contexts.items():
                if (context.status in [ConversationStatus.COMPLETED, ConversationStatus.CANCELLED] 
                    and context.updated_at < cutoff_time):
                    cache_removals.append(conv_id)
            
            for conv_id in cache_removals:
                del self.cached_contexts[conv_id]
            
            if cache_removals:
                self.logger.debug(f"Cleaned up {len(cache_removals)} contexts from cache")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old conversations: {e}")
            return 0
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history and state changes."""
        try:
            context = await self.load_conversation(conversation_id)
            
            if not context:
                return []
            
            # Build history from context data
            history = []
            
            # Add creation event
            history.append({
                "event": "conversation_created",
                "timestamp": context.created_at.isoformat(),
                "stage": context.current_stage.value,
                "data": {
                    "flow_name": context.metadata.get("flow_name"),
                    "initial_inputs": context.user_inputs,
                }
            })
            
            # Add stage completions
            for stage in context.completed_stages:
                stage_output = context.agent_outputs.get(stage.value)
                if stage_output:
                    history.append({
                        "event": "stage_completed",
                        "timestamp": stage_output.get("timestamp", context.updated_at.isoformat()),
                        "stage": stage.value,
                        "data": stage_output,
                    })
            
            # Add errors
            for error in context.errors:
                history.append({
                    "event": "error_occurred",
                    "timestamp": error["timestamp"],
                    "stage": error["stage"],
                    "data": {"message": error["message"]},
                })
            
            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"])
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history for {conversation_id}: {e}")
            raise ConversationError(f"Failed to get conversation history: {e}")
    
    def clear_cache(self) -> None:
        """Clear in-memory context cache."""
        self.cached_contexts.clear()
        self.logger.info("Conversation cache cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get conversation system statistics."""
        try:
            all_conversations = await self.list_conversations()
            
            # Count by status
            status_counts = {}
            for conv in all_conversations:
                status = conv.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            stats = {
                'total_conversations': len(all_conversations),
                'cached_conversations': len(self.cached_contexts),
                'backend_type': self.config.backend_type,
                'status_counts': status_counts,
                'max_cache_size': self.config.max_contexts_in_memory,
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {
                'error': str(e),
                'cached_conversations': len(self.cached_contexts),
                'backend_type': self.config.backend_type,
            }


# Global state manager instance
_state_manager: Optional[ConversationStateManager] = None


def get_state_manager(config: Optional[ConversationStateConfig] = None) -> ConversationStateManager:
    """Get or create global conversation state manager."""
    global _state_manager
    
    if _state_manager is None:
        _state_manager = ConversationStateManager(config)
    
    return _state_manager


def reset_state_manager() -> None:
    """Reset global state manager (mainly for testing)."""
    global _state_manager
    _state_manager = None
