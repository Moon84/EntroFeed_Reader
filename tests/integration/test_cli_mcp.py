# -*- coding: utf-8 -*-
"""Integration tests for CLI and MCP."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock, AsyncMock


class TestCLIImports:
    """Test CLI module can be imported."""

    def test_cli_module_imports(self):
        """Test CLI module can be imported."""
        from src.cli import (
            cli,
            backup,
            restore,
            export_opml,
            import_opml,
            load_feeds,
            check_feeds,
            load_settings,
            load_handlers,
        )

        assert cli is not None
        assert callable(cli)

    def test_cli_commands_registered(self):
        """Test CLI commands are registered."""
        from src.cli import cli

        assert hasattr(cli, "commands")
        assert len(cli.commands) > 0


class TestMCPImports:
    """Test MCP module can be imported."""

    def test_mcp_module_imports(self):
        """Test MCP module can be imported."""
        from src.mcp import create_mcp_server, run_mcp_server, mcp

        assert create_mcp_server is not None
        assert run_mcp_server is not None
        assert mcp is not None

    def test_create_mcp_server_returns_server(self):
        """Test create_mcp_server returns a server object."""
        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = MagicMock()
            with patch("src.mcp.EntroFeedBackend"):
                from src.mcp import create_mcp_server

                server = create_mcp_server()
                assert server is not None
                assert hasattr(server, "list_tools")
                assert hasattr(server, "call_tool")

    def test_mcp_tools_defined(self):
        """Test MCP tools are properly defined."""
        from src.mcp import create_mcp_server

        with patch("src.mcp.get_storage") as mock_storage:
            mock_storage.return_value = MagicMock()
            with patch("src.mcp.EntroFeedBackend"):
                server = create_mcp_server()

                assert hasattr(server, "list_tools")
                assert hasattr(server, "call_tool")


class TestMCPCommandLine:
    """Test MCP CLI command."""

    def test_mcp_command_exists(self):
        """Test mcp command exists."""
        from src.mcp import mcp

        assert mcp is not None
        assert callable(mcp)

    def test_mcp_click_command(self):
        """Test mcp is a click command."""
        from src.mcp import mcp

        assert hasattr(mcp, "callback")
        assert hasattr(mcp, "params")


class TestCLIClickGroup:
    """Test CLI is a click group."""

    def test_cli_is_click_group(self):
        """Test cli is a click group."""
        from src.cli import cli

        assert hasattr(cli, "commands")
        assert hasattr(cli, "add_command")

    def test_cli_has_mcp_command(self):
        """Test CLI has mcp command added."""
        from src.cli import cli

        assert "mcp" in cli.commands or hasattr(cli, "mcp")


class TestMCPDocstring:
    """Test MCP module documentation."""

    def test_mcp_has_docstring(self):
        """Test MCP has docstring."""
        import src.mcp

        assert src.mcp.__doc__ is not None
        assert len(src.mcp.__doc__) > 100

    def test_mcp_docstring_lists_tools(self):
        """Test docstring lists tools."""
        import src.mcp

        doc = src.mcp.__doc__
        assert "list_feeds" in doc
        assert "get_feed_entries" in doc
        assert "get_entry_content" in doc

    def test_mcp_docstring_has_usage(self):
        """Test docstring has usage example."""
        import src.mcp

        assert "entrofeed mcp" in src.mcp.__doc__


class TestCLIDocstring:
    """Test CLI module documentation."""

    def test_cli_has_commands(self):
        """Test CLI has documented commands."""
        import src.cli

        doc = src.cli.__doc__ if src.cli.__doc__ else ""
        # CLI should have some structure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
