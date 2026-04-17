# -*- coding: utf-8 -*-
"""EntroFeed Agent - Main agent implementation based on AgentScope."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentscope.agents import ReActAgent
from agentscope.memory import TemporaryMemory
from agentscope.message import Msg

logger = logging.getLogger(__name__)


class EntroFeedAgent(ReActAgent):
    """EntroFeed Agent with RSS/Feed and Ontology capabilities.

    This agent extends ReActAgent with:
    - Built-in tools for RSS/Feed operations
    - Ontology integration for user interests
    - Skill loading from workspace

    Args:
        name: Agent name
        model_config: Model configuration dict
        sys_prompt: System prompt
        max_iters: Maximum iterations
    """

    def __init__(
        self,
        name: str = "EntroFeed",
        model_config: Optional[Dict[str, Any]] = None,
        sys_prompt: Optional[str] = None,
        max_iters: int = 10,
        workspace_dir: Optional[Path] = None,
    ):
        """Initialize EntroFeedAgent.

        Args:
            name: Agent name
            model_config: Configuration for the LLM model
            sys_prompt: System prompt
            max_iters: Maximum number of iterations
            workspace_dir: Directory for skills and configs
        """
        self.name = name
        self._workspace_dir = workspace_dir or Path(os.getenv("DATA_DIR", "./data"))
        self._tool_functions = {}

        # Build system prompt
        if sys_prompt is None:
            sys_prompt = self._build_default_sys_prompt()

        # Initialize model
        model = self._create_model(model_config)

        # Initialize parent
        super().__init__(
            name=name,
            model=model,
            sys_prompt=sys_prompt,
            memory=TemporaryMemory(),
            max_iters=max_iters,
        )

        # Load tools
        self._load_tools()

        logger.info(f"EntroFeedAgent '{name}' initialized")

    def _create_model(self, config: Optional[Dict[str, Any]]) -> Any:
        """Create LLM model.

        Args:
            config: Model configuration

        Returns:
            Configured model instance
        """
        from src.plugins.llm import create_llm_handler
        handler = create_llm_handler()
        return handler

    def _load_tools(self) -> None:
        """Load tool functions."""
        from src.agents.tools import TOOL_FUNCTIONS
        self._tool_functions = TOOL_FUNCTIONS

    def _build_default_sys_prompt(self) -> str:
        """Build default system prompt.

        Returns:
            System prompt string
        """
        return """You are EntroFeed, an intelligent RSS reader assistant.

Your capabilities:
1. Browse and summarize RSS feeds
2. Track user interests and content preferences
3. Generate daily digests of important content
4. Help users find relevant information
5. Translate content when needed

Available tools:
- list_feeds: List all RSS feeds
- get_feed_entries: Get entries from a feed
- get_entry_content: Get full content of an entry
- search_entries: Search entries by query
- get_user_interests: Get user interests
- add_user_interest: Add a user interest
- get_high_priority_content: Get high priority content
- get_daily_digest: Get daily digest
- translate_text: Translate text

Be helpful, concise, and focused on delivering value to the user.
"""

    # ============ Tool Execution ============

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a registered tool by name.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool

        Returns:
            Tool result
        """
        if tool_name not in self._tool_functions:
            return {"error": f"Tool not found: {tool_name}"}

        try:
            tool_func = self._tool_functions[tool_name]
            return tool_func(**kwargs)
        except Exception as e:
            return {"error": str(e)}

    # ============ Convenience Methods ============

    def process_entry(self, entry_id: str) -> Dict[str, Any]:
        """Process a feed entry and update user interests.

        Args:
            entry_id: Entry ID to process

        Returns:
            Processing result
        """
        from src.agents.tools import process_content_for_user
        import json

        try:
            result = process_content_for_user(entry_id)
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_daily_digest(self, date: str = None) -> Dict[str, Any]:
        """Get daily digest.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Digest data
        """
        from src.agents.tools import get_daily_digest
        import json

        try:
            result = get_daily_digest(date)
            return json.loads(result)
        except Exception as e:
            return {"error": str(e)}

    def update_interests(self, entry_id: str, priority: int = 3) -> bool:
        """Update user interests based on read content.

        Args:
            entry_id: Entry ID
            priority: Content priority

        Returns:
            True if successful
        """
        from src.services.ontology import get_ontology_registry

        try:
            registry = get_ontology_registry()
            registry.on_content_read(entry_id, priority)
            return True
        except Exception as e:
            logger.error(f"Failed to update interests: {e}")
            return False

    # ============ Skill Execution ============

    def execute_skill(self, skill_name: str, user_input: str = "") -> Dict[str, Any]:
        """Execute a skill.

        Args:
            skill_name: Name of skill to execute
            user_input: User input to pass to skill

        Returns:
            Execution result dict
        """
        from src.skills.executor import SkillExecutor

        try:
            executor = SkillExecutor()
            return executor.execute(skill_name, {"user_input": user_input})
        except Exception as e:
            logger.error(f"Failed to execute skill {skill_name}: {e}")
            return {"success": False, "error": str(e)}

    def list_available_skills(self) -> List[Dict[str, Any]]:
        """List all available skills.

        Returns:
            List of skill info
        """
        from src.skills.registry import get_skill_registry

        try:
            registry = get_skill_registry()
            return registry.list_all()
        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return []


# ============ Model Factory ============

def create_model_and_formatter(agent_id: str = None):
    """Create model and formatter for agent.

    Args:
        agent_id: Agent identifier

    Returns:
        Tuple of (model, formatter)
    """
    from src.plugins.llm import create_llm_handler
    handler = create_llm_handler()
    return handler, None


class TokenTracker:
    """Track LLM token usage across sessions with persistent storage."""

    _usage: list = []
    _daily_limit: int = 1000000  # 1M tokens daily limit (configurable)
    _initialized: bool = False

    @classmethod
    def _ensure_init(cls):
        """Ensure usage data is loaded from storage."""
        if cls._initialized:
            return
        cls._initialized = True
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()
            # Load last 7 days of usage from storage
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=7)).date().isoformat()
            records = storage.get_token_usage(since=cutoff)
            cls._usage = records if records else []
        except Exception as e:
            print(f"Failed to load token usage from storage: {e}")
            cls._usage = []

    @classmethod
    def add_usage(cls, model: str, input_tokens: int, output_tokens: int):
        """Add token usage record."""
        from datetime import datetime
        record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
        cls._usage.append(record)

        # Record Prometheus metrics
        try:
            from src.metrics import record_token_usage
            record_token_usage(model, input_tokens, output_tokens)
        except Exception:
            pass  # Metrics are best-effort

        # Persist to storage
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()
            storage.save_token_usage(record)
        except Exception as e:
            print(f"Failed to persist token usage: {e}")

    @classmethod
    def get_today_usage(cls) -> dict:
        """Get today's token usage."""
        cls._ensure_init()
        from datetime import datetime
        today = datetime.now().date().isoformat()
        today_usage = [
            u for u in cls._usage
            if u["timestamp"].startswith(today)
        ]
        total_input = sum(u["input_tokens"] for u in today_usage)
        total_output = sum(u["output_tokens"] for u in today_usage)
        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "requests": len(today_usage),
            "limit": cls._daily_limit,
        }

    @classmethod
    def get_usage_history(cls, days: int = 7) -> list:
        """Get usage history for last N days."""
        cls._ensure_init()
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
        return [u for u in cls._usage if u["timestamp"] >= cutoff]

    @classmethod
    def reset(cls):
        """Reset usage tracking."""
        cls._usage = []
        try:
            from src.storage.singleton import get_storage
            storage = get_storage()
            storage.clear_token_usage()
        except Exception as e:
            print(f"Failed to clear token usage from storage: {e}")


__all__ = [
    "EntroFeedAgent",
    "create_model_and_formatter",
    "TokenTracker",
]
