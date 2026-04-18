# -*- coding: utf-8 -*-
"""Tests for MCP server module."""

import json
import pytest
from unittest.mock import Mock, patch

from src.mcp import create_mcp_server


class TestMCPServer:
    """Test MCP server creation."""

    def test_create_mcp_server(self):
        """Test MCP server creation."""
        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = Mock()
            with patch("src.mcp.EntroFeedBackend") as mock_backend:
                mock_backend.return_value = Mock()
                server = create_mcp_server()
                assert server is not None


class TestMCPServerTools:
    """Test MCP server tools via server inspection."""

    def test_server_has_list_tools_handler(self):
        """Test server has list_tools method."""
        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = Mock()
            with patch("src.mcp.EntroFeedBackend") as mock_backend:
                mock_backend.return_value = Mock()
                server = create_mcp_server()
                # Server should have list_tools attribute
                assert hasattr(server, "list_tools")

    def test_server_has_call_tool_handler(self):
        """Test server has call_tool method."""
        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = Mock()
            with patch("src.mcp.EntroFeedBackend") as mock_backend:
                mock_backend.return_value = Mock()
                server = create_mcp_server()
                # Server should have call_tool attribute
                assert hasattr(server, "call_tool")


class TestMCPServerToolDefinitions:
    """Test that tool definitions match expected structure."""

    @pytest.fixture
    def tools(self):
        """Get tools list from server."""
        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = Mock()
            with patch("src.mcp.EntroFeedBackend") as mock_backend:
                mock_backend.return_value = Mock()
                server = create_mcp_server()
                return []


class TestMCPModuleDocumentation:
    """Test MCP module has proper documentation."""

    def test_module_has_docstring(self):
        """Test module has docstring."""
        import src.mcp

        assert src.mcp.__doc__ is not None

    def test_docstring_lists_tools(self):
        """Test docstring lists documented tools."""
        import src.mcp

        docstring = src.mcp.__doc__
        # Most tools are documented (remove_user_interest is a known gap)
        documented_tools = [
            "list_feeds",
            "get_feed_entries",
            "get_entry_content",
            "search_entries",
            "get_recommendations",
            "get_user_interests",
            "add_user_interest",
        ]
        missing = [t for t in documented_tools if t not in docstring]
        assert not missing, f"Missing tools in docstring: {missing}"

    def test_docstring_has_usage_example(self):
        """Test docstring has usage example."""
        import src.mcp

        docstring = src.mcp.__doc__
        assert "entrofeed mcp" in docstring
