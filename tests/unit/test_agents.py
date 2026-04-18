# -*- coding: utf-8 -*-
"""Tests for Agents module."""


from src.agents.session import Message, ChatSession


class TestMessage:
    """Test Message dataclass."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.metadata == {}

    def test_message_to_dict(self):
        """Test converting message to dict."""
        msg = Message(role="assistant", content="Hi there")
        data = msg.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "Hi there"
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test creating message from dict."""
        data = {
            "role": "user",
            "content": "Test",
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {"key": "value"},
        }
        msg = Message.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test"
        assert msg.timestamp == "2024-01-01T00:00:00"
        assert msg.metadata == {"key": "value"}


class TestChatSession:
    """Test ChatSession dataclass."""

    def test_create_session(self):
        """Test creating a chat session."""
        session = ChatSession(id="test-123")
        assert session.id == "test-123"
        assert session.title == "New Chat"
        assert session.messages == []

    def test_add_message(self):
        """Test adding messages to session."""
        session = ChatSession(id="test-123")
        session.add_message(role="user", content="Hello")

        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"
        assert session.updated_at != session.created_at

    def test_add_message_with_metadata(self):
        """Test adding message with metadata."""
        session = ChatSession(id="test-123")
        metadata = {"entry_id": "entry-1"}
        msg = session.add_message(role="user", content="Hello", metadata=metadata)

        assert msg.metadata == metadata

    def test_to_dict(self):
        """Test converting session to dict."""
        session = ChatSession(id="test-123")
        session.add_message(role="user", content="Hello")

        data = session.to_dict()

        assert data["id"] == "test-123"
        assert data["title"] == "New Chat"
        assert len(data["messages"]) == 1

    def test_from_dict(self):
        """Test creating session from dict."""
        data = {
            "id": "test-456",
            "title": "Custom Title",
            "messages": [{"role": "user", "content": "Hi"}],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:01",
            "metadata": {},
        }
        session = ChatSession.from_dict(data)

        assert session.id == "test-456"
        assert session.title == "Custom Title"
        assert len(session.messages) == 1

    def test_get_context_messages(self):
        """Test getting context messages."""
        session = ChatSession(id="test-123")
        for i in range(25):
            session.add_message(role="user", content=f"Message {i}")

        # Should return last 20 by default
        context = session.get_context_messages()
        assert len(context) == 20
        assert context[0]["content"] == "Message 5"

    def test_get_context_messages_all(self):
        """Test getting all context messages."""
        session = ChatSession(id="test-123")
        session.add_message(role="user", content="Hello")
        session.add_message(role="assistant", content="Hi")

        context = session.get_context_messages(max_messages=0)
        assert len(context) == 2

    def test_generate_title(self):
        """Test generating title from first user message."""
        session = ChatSession(id="test-123")
        session.add_message(role="user", content="What is AI?")
        session.add_message(role="assistant", content="AI is...")

        title = session.generate_title()
        assert "What is AI" in title
        assert len(title) <= 50

    def test_generate_title_empty(self):
        """Test generating title with no messages."""
        session = ChatSession(id="test-123")
        title = session.generate_title()
        assert title == "New Chat"

    def test_messages_can_be_cleared(self):
        """Test that session messages can be cleared directly."""
        session = ChatSession(id="test-123")
        session.add_message(role="user", content="Hello")
        session.add_message(role="assistant", content="Hi")

        # Direct message clearing
        session.messages = []
        assert len(session.messages) == 0
