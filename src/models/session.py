"""Session management models"""
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class SessionData:
    """Data stored within a session"""
    product_name: Optional[str] = None
    price: Optional[str] = None
    specifications: Dict[str, str] = field(default_factory=dict)
    spec_questions: Dict[str, str] = field(default_factory=dict)
    current_spec_index: int = 0
    cloud_image_url: Optional[str] = None

@dataclass
class Session:
    """User session model"""
    chat_id: int
    stage: str = "await_initial_choice"
    data: SessionData = field(default_factory=SessionData)
    llm_history: List[Any] = field(default_factory=list)
    last_interaction_time: float = field(default_factory=time.time)
    last_processed_message_id: Optional[int] = None
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_interaction_time) > timeout_seconds
    
    def update_interaction_time(self) -> None:
        """Update last interaction time"""
        self.last_interaction_time = time.time()
    
    def reset(self) -> None:
        """Reset session to initial state"""
        self.stage = "await_initial_choice"
        self.data = SessionData()
        self.llm_history = []
        self.update_interaction_time()

class SessionManager:
    """Manages user sessions"""
    
    def __init__(self, timeout_seconds: int = 900):
        self.sessions: Dict[int, Session] = {}
        self.timeout_seconds = timeout_seconds
    
    def get_session(self, chat_id: int) -> Session:
        """Get or create session for chat_id"""
        current_time = time.time()
        
        if chat_id in self.sessions:
            session = self.sessions[chat_id]
            if session.is_expired(self.timeout_seconds):
                print(f"Chat {chat_id} session timed out. Resetting context.")
                session.reset()
            else:
                session.update_interaction_time()
        else:
            session = Session(chat_id=chat_id)
            self.sessions[chat_id] = session
        
        return session
    
    def remove_session(self, chat_id: int) -> None:
        """Remove session"""
        if chat_id in self.sessions:
            del self.sessions[chat_id]
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count removed"""
        expired_chat_ids = [
            chat_id for chat_id, session in self.sessions.items()
            if session.is_expired(self.timeout_seconds)
        ]
        
        for chat_id in expired_chat_ids:
            del self.sessions[chat_id]
        
        return len(expired_chat_ids)
