"""
Session Management for Multi-User Chatbot
Handles user sessions, conversation threads, and state persistence
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from threading import RLock

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""
    timestamp: datetime
    user_message: str
    bot_response: str
    sql_query: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserSession:
    """User session data"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    user_context: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def add_turn(self, user_message: str, bot_response: str, 
                 sql_query: Optional[str] = None, confidence: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        """Add a conversation turn"""
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_message=user_message,
            bot_response=bot_response,
            sql_query=sql_query,
            confidence=confidence,
            metadata=metadata or {}
        )
        self.conversation_history.append(turn)
        self.last_activity = datetime.now()
    
    def get_recent_context(self, max_turns: int = 5) -> List[Dict[str, str]]:
        """Get recent conversation context for LLM"""
        recent_turns = self.conversation_history[-max_turns:] if self.conversation_history else []
        context = []
        for turn in recent_turns:
            context.append({"role": "user", "content": turn.user_message})
            context.append({"role": "assistant", "content": turn.bot_response})
        return context
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session has expired"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


class SessionManager:
    """
    Manages user sessions and conversation threads for the chatbot
    Thread-safe implementation with automatic cleanup
    """
    
    def __init__(self, session_timeout_minutes: int = 60, cleanup_interval_minutes: int = 10):
        self.sessions: Dict[str, UserSession] = {}
        self.user_to_session: Dict[str, str] = {}  # Maps user_id to active session_id
        self.session_timeout_minutes = session_timeout_minutes
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self._lock = RLock()
        self._cleanup_task = None
        self._is_running = False
    
    async def start(self):
        """Start the session manager and cleanup task"""
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Session manager started")
    
    async def stop(self):
        """Stop the session manager and cleanup task"""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session manager stopped")
    
    def create_session(self, user_id: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session for a user"""
        with self._lock:
            # Close any existing session for this user
            if user_id in self.user_to_session:
                old_session_id = self.user_to_session[user_id]
                if old_session_id in self.sessions:
                    self.sessions[old_session_id].is_active = False
            
            # Create new session
            session_id = str(uuid.uuid4())
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                user_context=user_context or {}
            )
            
            self.sessions[session_id] = session
            self.user_to_session[user_id] = session_id
            
            logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired(self.session_timeout_minutes):
                session.last_activity = datetime.now()
                return session
            return None
    
    def get_user_session(self, user_id: str) -> Optional[UserSession]:
        """Get active session for a user"""
        with self._lock:
            session_id = self.user_to_session.get(user_id)
            if session_id:
                return self.get_session(session_id)
            return None
    
    def add_conversation_turn(self, session_id: str, user_message: str, 
                            bot_response: str, sql_query: Optional[str] = None,
                            confidence: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a conversation turn to a session"""
        with self._lock:
            session = self.get_session(session_id)
            if session:
                session.add_turn(user_message, bot_response, sql_query, confidence, metadata)
                logger.debug(f"Added conversation turn to session {session_id}")
                return True
            return False
    
    def update_user_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update user context in a session"""
        with self._lock:
            session = self.get_session(session_id)
            if session:
                session.user_context.update(context_updates)
                session.last_activity = datetime.now()
                return True
            return False
    
    def get_conversation_history(self, session_id: str, max_turns: int = 10) -> List[ConversationTurn]:
        """Get conversation history for a session"""
        with self._lock:
            session = self.get_session(session_id)
            if session:
                return session.conversation_history[-max_turns:] if session.conversation_history else []
            return []
    
    def close_session(self, session_id: str) -> bool:
        """Close a session"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.is_active = False
                # Remove from user mapping
                if session.user_id in self.user_to_session:
                    if self.user_to_session[session.user_id] == session_id:
                        del self.user_to_session[session.user_id]
                logger.info(f"Closed session {session_id}")
                return True
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        with self._lock:
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active)
            total_sessions = len(self.sessions)
            total_conversations = sum(len(s.conversation_history) for s in self.sessions.values())
            
            return {
                "active_sessions": active_sessions,
                "total_sessions": total_sessions,
                "total_conversation_turns": total_conversations,
                "unique_users": len(set(s.user_id for s in self.sessions.values()))
            }
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while self._is_running:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self._lock:
            expired_sessions = []
            
            for session_id, session in self.sessions.items():
                if session.is_expired(self.session_timeout_minutes) or not session.is_active:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                session = self.sessions.pop(session_id, None)
                if session and session.user_id in self.user_to_session:
                    if self.user_to_session[session.user_id] == session_id:
                        del self.user_to_session[session.user_id]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


class ThreadSafeContextManager:
    """
    Thread-safe context manager for handling concurrent user requests
    Ensures each user gets isolated conversation context
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._user_locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()
    
    async def get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific user"""
        async with self._locks_lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = asyncio.Lock()
            return self._user_locks[user_id]
    
    async def process_user_request(self, user_id: str, user_message: str,
                                 processor_func, **kwargs) -> Any:
        """
        Process a user request with proper locking to ensure thread safety
        """
        user_lock = await self.get_user_lock(user_id)
        
        async with user_lock:
            # Get or create session
            session = self.session_manager.get_user_session(user_id)
            if not session:
                session_id = self.session_manager.create_session(user_id, kwargs.get('user_context'))
                session = self.session_manager.get_session(session_id)
            
            if not session:
                raise RuntimeError(f"Could not create or retrieve session for user {user_id}")
            
            # Process the request
            result = await processor_func(session, user_message, **kwargs)
            
            return result
    
    async def cleanup_user_locks(self):
        """Clean up unused user locks"""
        async with self._locks_lock:
            # Remove locks for users without active sessions
            active_users = set()
            for session in self.session_manager.sessions.values():
                if session.is_active:
                    active_users.add(session.user_id)
            
            # Keep only locks for active users
            self._user_locks = {
                user_id: lock for user_id, lock in self._user_locks.items()
                if user_id in active_users
            }