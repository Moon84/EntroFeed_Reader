# -*- coding: utf-8 -*-
"""Tests for Content Retrieval Plugins."""


from src.plugins.content import (
    ContentPluginRegistry,
    RequestsContentRetriever,
    PlaywrightContentRetriever,
    RSSHubContentRetriever,
)


class TestContentPluginRegistry:
    """Test ContentPluginRegistry."""

    def test_register_works(self):
        """Test that plugins are registered."""
        handlers = ContentPluginRegistry.list_handlers()
        assert "requests" in handlers
        assert "playwright" in handlers
        assert "rsshub" in handlers

    def test_get_handler(self):
        """Test getting handler by ID."""
        handler = ContentPluginRegistry.get_handler("requests")
        assert handler is not None
        assert handler.id == "requests"

    def test_get_handler_not_found(self):
        """Test getting non-existent handler returns None."""
        handler = ContentPluginRegistry.get_handler("nonexistent")
        assert handler is None


class TestRequestsContentRetriever:
    """Test RequestsContentRetriever."""

    def test_id(self):
        """Test handler ID."""
        assert RequestsContentRetriever.id == "requests"

    def test_headers_class_var(self):
        """Test headers are defined."""
        assert hasattr(RequestsContentRetriever, "headers")
        assert "User-Agent" in RequestsContentRetriever.headers


class TestPlaywrightContentRetriever:
    """Test PlaywrightContentRetriever."""

    def test_id(self):
        """Test handler ID."""
        assert PlaywrightContentRetriever.id == "playwright"


class TestRSSHubContentRetriever:
    """Test RSSHubContentRetriever."""

    def test_id(self):
        """Test handler ID."""
        assert RSSHubContentRetriever.id == "rsshub"

    def test_base_url_default(self):
        """Test default RSShub base URL."""
        handler = RSSHubContentRetriever()
        assert handler.base_url == "http://localhost:1200"
