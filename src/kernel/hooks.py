# -*- coding: utf-8 -*-
"""Hook system for EntroFeed plugins.

Provides pre/post execution hooks for extensibility.
Plugins can register hooks to be called at specific lifecycle points.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from logging import getLogger

logger = getLogger("hooks")


class HookType(str, Enum):
    """Available hook types."""

    # Feed lifecycle
    PRE_FEED_POLL = "pre_feed_poll"
    POST_FEED_POLL = "post_feed_poll"
    PRE_FEED_REFRESH = "pre_feed_refresh"
    POST_FEED_REFRESH = "post_feed_refresh"

    # Content lifecycle
    PRE_CONTENT_RETRIEVAL = "pre_content_retrieval"
    POST_CONTENT_RETRIEVAL = "post_content_retrieval"

    # Summarization
    PRE_SUMMARIZATION = "pre_summarization"
    POST_SUMMARIZATION = "post_summarization"

    # Notification
    PRE_NOTIFICATION = "pre_notification"
    POST_NOTIFICATION = "post_notification"

    # Entry state
    ON_ENTRY_READ = "on_entry_read"
    ON_ENTRY_LIKED = "on_entry_liked"
    ON_ENTRY_FAVORITED = "on_entry_favorited"

    # Interest/Ontology
    ON_INTEREST_UPDATED = "on_interest_updated"
    ON_CONTENT_TAGGED = "on_content_tagged"

    # Agent
    PRE_AGENT_TOOL_CALL = "pre_agent_tool_call"
    POST_AGENT_TOOL_CALL = "post_agent_tool_call"

    # Scheduler
    ON_SCHEDULER_START = "on_scheduler_start"
    ON_SCHEDULER_SHUTDOWN = "on_scheduler_shutdown"


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    hook_type: HookType
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get data value with optional default."""
        return self.data.get(key, default)


class HookRegistry:
    """Registry for pre/post execution hooks.

    Plugins register hooks to be called at specific lifecycle points.
    Hooks are executed in registration order.
    """

    _hooks: Dict[HookType, List[Callable[[HookContext], Any]]] = {
        ht: [] for ht in HookType
    }

    _enabled: bool = True

    @classmethod
    def register(cls, hook_type: HookType, handler: Callable[[HookContext], Any]) -> None:
        """Register a hook handler."""
        if handler not in cls._hooks[hook_type]:
            cls._hooks[hook_type].append(handler)
            logger.debug(f"Registered hook: {hook_type}")

    @classmethod
    def unregister(cls, hook_type: HookType, handler: Callable[[HookContext], Any]) -> None:
        """Unregister a hook handler."""
        if handler in cls._hooks[hook_type]:
            cls._hooks[hook_type].remove(handler)
            logger.debug(f"Unregistered hook: {hook_type}")

    @classmethod
    def execute(cls, hook_type: HookType, data: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Execute all handlers for a hook type."""
        if not cls._enabled:
            return []

        ctx = HookContext(hook_type=hook_type, data=data or {}, metadata={})
        results = []

        for handler in cls._hooks[hook_type]:
            try:
                result = handler(ctx)
                results.append(result)
                logger.debug(f"Hook {hook_type} executed: {handler.__name__}")
            except Exception as e:
                logger.error(f"Hook {hook_type} handler {handler.__name__} failed: {e}")

        return results

    @classmethod
    def execute_first(
        cls, hook_type: HookType, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Execute hooks and return first non-None result."""
        results = cls.execute(hook_type, data)
        return next((r for r in results if r is not None), None)

    @classmethod
    def enable(cls) -> None:
        """Enable hook execution."""
        cls._enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable hook execution."""
        cls._enabled = False

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if hooks are enabled."""
        return cls._enabled

    @classmethod
    def clear(cls, hook_type: Optional[HookType] = None) -> None:
        """Clear hooks for a type, or all if not specified."""
        if hook_type:
            cls._hooks[hook_type] = []
        else:
            cls._hooks = {ht: [] for ht in HookType}


def on(hook_type: HookType) -> Callable:
    """Decorator to register a hook handler."""

    def decorator(func: Callable[[HookContext], Any]) -> Callable:
        HookRegistry.register(hook_type, func)
        return func

    return decorator
