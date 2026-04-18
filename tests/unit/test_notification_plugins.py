# -*- coding: utf-8 -*-
"""Tests for Notification Plugins."""


from src.plugins.notification import (
    NotificationPluginBase,
    NotificationPluginRegistry,
    SlackNotificationHandler,
    NtfyNotificationHandler,
    NullNotificationHandler,
)


class TestNotificationPluginRegistry:
    """Test NotificationPluginRegistry."""

    def test_register_works(self):
        """Test that plugins are registered."""
        handlers = NotificationPluginRegistry.list_handlers()
        assert "slack" in handlers
        assert "ntfy" in handlers
        assert "null_notification" in handlers

    def test_get_handler(self):
        """Test getting handler by ID."""
        handler = NotificationPluginRegistry.get_handler("slack")
        assert handler is not None
        assert handler.id == "slack"

    def test_get_handler_not_found(self):
        """Test getting non-existent handler returns None."""
        handler = NotificationPluginRegistry.get_handler("nonexistent")
        assert handler is None


class TestNullNotificationHandler:
    """Test NullNotificationHandler."""

    def test_id(self):
        """Test handler ID."""
        assert NullNotificationHandler.id == "null_notification"

    def test_send_notification_does_not_raise(self):
        """Test send_notification doesn't raise."""
        import asyncio
        from src.models.feed import Feed, FeedEntry

        handler = NullNotificationHandler()
        feed = Feed(name="Test", url="http://test.com")
        entry = FeedEntry(
            feed_id=feed.id,
            title="Test Entry",
            url="http://test.com/entry",
            published_at=0,
            updated_at=0,
        )

        # Should not raise
        asyncio.run(handler.send_notification(feed=feed, entry=entry))


class TestSlackNotificationHandler:
    """Test SlackNotificationHandler."""

    def test_id(self):
        """Test handler ID."""
        assert SlackNotificationHandler.id == "slack"

    def test_required_env(self):
        """Test required environment variables."""
        assert "SLACK_API_TOKEN" in SlackNotificationHandler.required_env

    def test_token_field_exists(self):
        """Test token field exists and is required."""
        fields = SlackNotificationHandler.model_fields
        assert "token" in fields
        assert fields["token"].is_required()


class TestNtfyNotificationHandler:
    """Test NtfyNotificationHandler."""

    def test_id(self):
        """Test handler ID."""
        assert NtfyNotificationHandler.id == "ntfy"

    def test_required_env(self):
        """Test required environment variables."""
        assert "NTFY_TOPIC" in NtfyNotificationHandler.required_env

    def test_topic_field_exists(self):
        """Test topic field exists and is required."""
        fields = NtfyNotificationHandler.model_fields
        assert "topic" in fields
        assert fields["topic"].is_required()


class TestNotificationPluginBase:
    """Test NotificationPluginBase."""

    def test_get_plugin_type(self):
        """Test get_plugin_type returns correct value."""
        assert NotificationPluginBase.get_plugin_type() == "notification"

    def test_destinations_returns_list(self):
        """Test destinations returns list."""
        handler = NullNotificationHandler()
        assert isinstance(handler.destinations, list)
