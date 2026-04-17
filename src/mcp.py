# -*- coding: utf-8 -*-
"""MCP Server for EntroFeed.

This module provides a Model Context Protocol (MCP) server that exposes
EntroFeed tools to external AI systems and CLI clients.

Usage:
    entrofeed mcp --port 8765

The MCP server exposes the following tools:
- list_feeds: List all configured RSS feeds
- get_feed_entries: Get entries from a specific feed
- get_entry_content: Get full content of a feed entry
- search_entries: Search entries by query
- get_recommendations: Get content recommendations
- get_user_interests: Get user interests
- add_user_interest: Add a new user interest
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.storage.singleton import get_storage
from src.backend import EntroFeedBackend

logger = logging.getLogger("mcp")


def create_mcp_server():
    """Create and configure the MCP server."""
    server = Server("entrofeed")

    storage_handler = get_storage()
    backend = EntroFeedBackend(db=storage_handler)

    # Define available tools
    TOOLS = [
        Tool(
            name="list_feeds",
            description="List all configured RSS feeds",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_feed_entries",
            description="Get entries from a specific feed or recent entries",
            inputSchema={
                "type": "object",
                "properties": {
                    "feed_id": {
                        "type": "string",
                        "description": "Feed ID (optional, if None gets recent entries)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="get_entry_content",
            description="Get full content of a feed entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {
                        "type": "string",
                        "description": "Entry ID",
                    },
                },
                "required": ["entry_id"],
            },
        ),
        Tool(
            name="search_entries",
            description="Search entries by query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_recommendations",
            description="Get content recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["interest", "trending", "similar"],
                        "description": "Recommendation type",
                        "default": "interest",
                    },
                    "entry_id": {
                        "type": "string",
                        "description": "Entry ID for similar recommendations",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="get_user_interests",
            description="Get user interests",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                    },
                },
            },
        ),
        Tool(
            name="add_user_interest",
            description="Add a new user interest",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Interest name",
                    },
                    "category": {
                        "type": "string",
                        "description": "Interest category",
                        "default": "other",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (1-5)",
                        "default": 3,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="remove_user_interest",
            description="Remove a user interest",
            inputSchema={
                "type": "object",
                "properties": {
                    "interest_id": {
                        "type": "string",
                        "description": "Interest ID to remove",
                    },
                },
                "required": ["interest_id"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools():
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            if name == "list_feeds":
                feeds = backend.list_feeds()
                return [TextContent(type="text", text=json.dumps(feeds, indent=2))]

            elif name == "get_feed_entries":
                feed_id = arguments.get("feed_id")
                limit = arguments.get("limit", 20)
                entries = list(backend.list_entries(feed_id=feed_id, recent=True))
                return [TextContent(type="text", text=json.dumps(entries[:limit], indent=2))]

            elif name == "get_entry_content":
                entry_id = arguments.get("entry_id")
                content = await backend.get_entry_content(feed_entry_id=entry_id)
                return [TextContent(type="text", text=json.dumps(content, indent=2))]

            elif name == "search_entries":
                from src.agents.tools import search_entries
                query = arguments.get("query", "")
                limit = arguments.get("limit", 10)
                result = search_entries(query, limit=limit)
                return [TextContent(type="text", text=result)]

            elif name == "get_recommendations":
                rec_type = arguments.get("type", "interest")
                entry_id = arguments.get("entry_id")
                limit = arguments.get("limit", 10)

                if rec_type == "similar" and entry_id:
                    from src.recommender import get_similar_recommendations
                    recs = get_similar_recommendations(entry_id=entry_id, limit=limit)
                elif rec_type == "trending":
                    from src.recommender import get_trending_recommendations
                    recs = get_trending_recommendations(limit=limit)
                else:
                    from src.recommender import get_interest_recommendations
                    recs = get_interest_recommendations(limit=limit)

                return [TextContent(type="text", text=json.dumps(recs, indent=2))]

            elif name == "get_user_interests":
                from src.services.ontology import get_ontology_registry
                registry = get_ontology_registry()
                category = arguments.get("category")
                interests = registry.get_user_interests(category=category)
                return [TextContent(type="text", text=json.dumps([i.to_dict() for i in interests], indent=2))]

            elif name == "add_user_interest":
                from src.services.ontology import get_ontology_registry
                from src.services.ontology.types import InterestTag, InterestCategory, TagSource

                registry = get_ontology_registry()
                name = arguments.get("name", "").lower()
                category = arguments.get("category", "other")
                priority = arguments.get("priority", 3)

                try:
                    cat = InterestCategory(category.lower())
                except ValueError:
                    cat = InterestCategory.OTHER

                tag = InterestTag(
                    name=name,
                    category=cat,
                    source=TagSource.EXPLICIT,
                    confidence=1.0
                )

                interest = registry.add_interest(tag, priority)
                return [TextContent(type="text", text=json.dumps(interest.to_dict(), indent=2))]

            elif name == "remove_user_interest":
                from src.services.ontology import get_ontology_registry
                registry = get_ontology_registry()
                interest_id = arguments.get("interest_id")
                success = registry.remove_interest(interest_id)
                return [TextContent(type="text", text=json.dumps({"success": success, "interest_id": interest_id}))]

            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


async def run_mcp_server(port: int = 8765, host: str = "127.0.0.1"):
    """Run the MCP server."""
    server = create_mcp_server()

    # Note: MCP stdio mode is typically used for subprocess communication
    # For TCP mode, we use the server's run method
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


@click.command()
@click.option("--port", default=8765, help="Port to listen on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--stdio", is_flag=True, help="Use stdio mode instead of TCP")
def mcp(port: int, host: str, stdio: bool):
    """
    Start the EntroFeed MCP server.

    The MCP server exposes EntroFeed tools to external AI systems
    via the Model Context Protocol.

    Examples:
        entrofeed mcp --port 8765
        entrofeed mcp --stdio
    """
    if stdio:
        # Run in stdio mode (for subprocess communication)
        asyncio.run(run_mcp_server(port, host))
    else:
        # Run TCP server
        from mcp.server import Server
        from mcp.server.tcp import create_tcp_server

        server = create_mcp_server()
        asyncio.run(create_tcp_server(server, host, port))
        print(f"EntroFeed MCP server running on {host}:{port}")
        asyncio.run(asyncio.Event().wait())  # Keep running


if __name__ == "__main__":
    mcp()
