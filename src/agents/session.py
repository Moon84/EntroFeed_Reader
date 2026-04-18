# -*- coding: utf-8 -*-
"""Chat Session Management - Handles conversation history and session persistence."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """A single message in a conversation."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            metadata=data.get('metadata', {}),
        )


@dataclass
class ChatSession:
    """A chat session containing conversation history."""

    id: str
    title: str = "New Chat"
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> Message:
        """Add a message to the session."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.updated_at = datetime.now().isoformat()
        return msg

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'messages': [m.to_dict() for m in self.messages],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        return cls(
            id=data['id'],
            title=data.get('title', 'New Chat'),
            messages=[Message.from_dict(m) for m in data.get('messages', [])],
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            metadata=data.get('metadata', {}),
        )

    def get_context_messages(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get recent messages as dict list for API calls."""
        recent = self.messages[-max_messages:] if max_messages > 0 else self.messages
        return [{"role": m.role, "content": m.content} for m in recent]

    def generate_title(self) -> str:
        """Generate a title from the first user message."""
        if self.messages:
            for msg in self.messages:
                if msg.role == 'user':
                    # Take first 30 chars of first user message
                    title = msg.content[:30]
                    if len(msg.content) > 30:
                        title += "..."
                    return title
        return "New Chat"


class ChatSessionManager:
    """Manages multiple chat sessions with persistence."""

    def __init__(self, storage_path: str = None):
        """Initialize session manager.

        Args:
            storage_path: Path to JSON file for session persistence
        """
        from pathlib import Path
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(os.getenv("DATA_DIR", "./data")) / "chat_sessions.json"

        self._sessions: Dict[str, ChatSession] = {}
        self._load_sessions()

    def _load_sessions(self):
        """Load sessions from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for session_data in data.get('sessions', []):
                        session = ChatSession.from_dict(session_data)
                        self._sessions[session.id] = session
            except Exception as e:
                print(f"Failed to load sessions: {e}")
                self._sessions = {}
        else:
            self._sessions = {}

    def _save_sessions(self):
        """Save sessions to disk."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'sessions': [s.to_dict() for s in self._sessions.values()]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save sessions: {e}")

    def create_session(self, title: str = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=str(uuid.uuid4())[:8],
            title=title or "New Chat",
        )
        self._sessions[session.id] = session
        self._save_sessions()
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save_sessions()
            return True
        return False

    def list_sessions(self) -> List[ChatSession]:
        """List all sessions, sorted by updated_at descending."""
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[Message]:
        """Add a message to a session."""
        session = self.get_session(session_id)
        if session:
            msg = session.add_message(role, content, metadata)
            # Auto-generate title from first message
            if session.title == "New Chat" and role == "user":
                session.title = session.generate_title()
            self._save_sessions()
            return msg
        return None

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages from a session."""
        session = self.get_session(session_id)
        if session:
            session.messages = []
            session.updated_at = datetime.now().isoformat()
            session.title = "New Chat"
            self._save_sessions()
            return True
        return False


# Singleton instance
_manager: Optional[ChatSessionManager] = None


def get_session_manager() -> ChatSessionManager:
    """Get or create singleton session manager."""
    global _manager
    if _manager is None:
        _manager = ChatSessionManager()
    return _manager


__all__ = [
    "Message",
    "ChatSession",
    "ChatSessionManager",
    "get_session_manager",
]
