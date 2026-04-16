# -*- coding: utf-8 -*-
"""Plugin registry for EntroFeed.

Provides a centralized registry for all plugin types:
- llm: LLM providers (OpenAI, Ollama, DashScope, etc.)
- notification: Notification channels (Slack, Matrix, etc.)
- content: Content retrieval (Requests, Playwright, RSSHub)
- storage: Storage backends (TinyDB, SQLite, LMDB)

Features:
- Auto-registration via module import
- Lifecycle hooks (startup/shutdown) with priority
- Tool availability checking with env validation
- Metrics integration for observability
"""

from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from os import environ
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel

from src.metrics import (
    PluginCheckResult,
    record_plugin_check,
    record_plugin_error,
    record_plugin_init,
    record_plugin_shutdown,
)

_logger = getLogger("uvicorn.error")


class PluginBase(BaseModel):
    """Base class for all plugins."""

    id: ClassVar[str] = "base_plugin"

    # Optional: list of required environment variables
    required_env: ClassVar[List[str]] = []

    # Optional: check function to verify plugin availability
    _check_fn: ClassVar[Optional[Callable[[], bool]]] = None

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        raise NotImplementedError

    @classmethod
    def get_plugin_id(cls) -> str:
        """Return the unique plugin identifier."""
        return cls.id

    @classmethod
    def get_check_fn(cls) -> Optional[Callable[[], bool]]:
        """Get the availability check function."""
        return getattr(cls, '_check_fn', None)

    @classmethod
    def check_availability(cls) -> PluginCheckResult:
        """Check if this plugin is available with current environment.

        Returns PluginCheckResult with:
        - available: bool
        - reason: str (why not available)
        - missing_env: List[str] (missing env vars)
        """
        from src.metrics import PluginCheckResult as MetricsCheckResult

        # Check required environment variables
        missing = []
        for env_var in cls.required_env:
            if not environ.get(env_var):
                missing.append(env_var)

        if missing:
            result = MetricsCheckResult(
                available=False,
                reason=f"Missing required environment variables: {', '.join(missing)}",
                missing_env=missing
            )
            record_plugin_check(cls.get_plugin_type(), cls.id, False, result.reason)
            return result

        # Run custom check function if defined
        check_fn = cls.get_check_fn()
        if check_fn:
            try:
                if not check_fn():
                    result = MetricsCheckResult(
                        available=False,
                        reason="Check function returned False"
                    )
                    record_plugin_check(cls.get_plugin_type(), cls.id, False, result.reason)
                    return result
            except Exception as e:
                result = MetricsCheckResult(
                    available=False,
                    reason=f"Check function raised: {type(e).__name__}: {e}"
                )
                record_plugin_check(cls.get_plugin_type(), cls.id, False, result.reason)
                return result

        result = MetricsCheckResult(available=True)
        record_plugin_check(cls.get_plugin_type(), cls.id, True)
        return result


@dataclass
class LifecycleHook:
    """A lifecycle hook for plugin startup/shutdown."""
    plugin_id: str
    plugin_type: str
    callback: Callable
    priority: int = 100  # Lower = earlier execution

    def __post_init__(self):
        # Sort by priority (lower = earlier)
        self.priority = int(self.priority)


@dataclass
class PluginRegistration:
    """Registration record for a plugin."""
    plugin_type: str
    plugin_id: str
    plugin_cls: Type[PluginBase]
    factory: Optional[Callable] = None
    init_hooks: List[LifecycleHook] = field(default_factory=list)
    shutdown_hooks: List[LifecycleHook] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PluginRegistry:
    """Singleton registry for all plugins.

    Provides centralized plugin registration and instantiation.
    Plugins self-register on import via their module's __init__.py.

    Features:
    - Lifecycle hooks with priority ordering
    - Tool availability checking
    - Metrics integration
    """

    _plugins: ClassVar[Dict[str, Dict[str, Type[PluginBase]]]] = {
        "llm": {},
        "notification": {},
        "content": {},
        "storage": {},
    }

    _factories: ClassVar[Dict[str, Callable]] = {}

    # Lifecycle hooks storage
    _startup_hooks: List[LifecycleHook] = []
    _shutdown_hooks: List[LifecycleHook] = []

    # Plugin registrations with metadata
    _registrations: Dict[str, PluginRegistration] = {}

    @classmethod
    def register(
        cls,
        plugin_type: str,
        plugin_cls: Type[PluginBase],
        *,
        factory: Optional[Callable] = None,
        priority: int = 100
    ) -> None:
        """Register a plugin class.

        Args:
            plugin_type: Category (llm, notification, content, storage)
            plugin_cls: Plugin class inheriting from PluginBase
            factory: Optional factory function for instantiation
            priority: Initialization priority (lower = earlier)
        """
        if plugin_type not in cls._plugins:
            cls._plugins[plugin_type] = {}

        # Get plugin ID
        plugin_id = getattr(plugin_cls, 'id', None)
        if plugin_id is None:
            plugin_id = plugin_cls.__name__.lower().replace('handler', '').replace('storage', '')

        cls._plugins[plugin_type][plugin_id] = plugin_cls

        if factory:
            cls._factories[f"{plugin_type}:{plugin_id}"] = factory

        # Store registration metadata
        cls._registrations[f"{plugin_type}:{plugin_id}"] = PluginRegistration(
            plugin_type=plugin_type,
            plugin_id=plugin_id,
            plugin_cls=plugin_cls,
            factory=factory
        )

        _logger.debug(f"Registered plugin: {plugin_type}:{plugin_id}")

    @classmethod
    def register_startup_hook(
        cls,
        plugin_type: str,
        plugin_id: str,
        callback: Callable,
        priority: int = 100
    ) -> None:
        """Register a startup hook for a plugin.

        Args:
            plugin_type: Plugin type
            plugin_id: Plugin ID
            callback: Async callable to run at startup
            priority: Execution order (lower = earlier)
        """
        hook = LifecycleHook(
            plugin_id=plugin_id,
            plugin_type=plugin_type,
            callback=callback,
            priority=priority
        )
        cls._startup_hooks.append(hook)
        cls._startup_hooks.sort(key=lambda h: h.priority)
        _logger.debug(f"Registered startup hook for {plugin_type}:{plugin_id} (priority={priority})")

    @classmethod
    def register_shutdown_hook(
        cls,
        plugin_type: str,
        plugin_id: str,
        callback: Callable,
        priority: int = 100
    ) -> None:
        """Register a shutdown hook for a plugin.

        Args:
            plugin_type: Plugin type
            plugin_id: Plugin ID
            callback: Sync callable to run at shutdown
            priority: Execution order (lower = earlier)
        """
        hook = LifecycleHook(
            plugin_id=plugin_id,
            plugin_type=plugin_type,
            callback=callback,
            priority=priority
        )
        cls._shutdown_hooks.append(hook)
        # Shutdown hooks run in reverse priority order
        cls._shutdown_hooks.sort(key=lambda h: -h.priority)
        _logger.debug(f"Registered shutdown hook for {plugin_type}:{plugin_id} (priority={priority})")

    @classmethod
    async def run_startup_hooks(cls) -> Dict[str, bool]:
        """Run all registered startup hooks in priority order.

        Returns:
            Dict mapping plugin_id to success status
        """
        results = {}
        for hook in cls._startup_hooks:
            try:
                _logger.info(f"Running startup hook: {hook.plugin_type}:{hook.plugin_id}")
                await hook.callback()
                record_plugin_init(hook.plugin_type, hook.plugin_id, 0.0, True)
                results[hook.plugin_id] = True
            except Exception as e:
                _logger.error(f"Startup hook failed for {hook.plugin_type}:{hook.plugin_id}: {e}")
                record_plugin_error(hook.plugin_type, hook.plugin_id)
                results[hook.plugin_id] = False
        return results

    @classmethod
    async def run_shutdown_hooks(cls) -> Dict[str, bool]:
        """Run all registered shutdown hooks in reverse priority order.

        Returns:
            Dict mapping plugin_id to success status
        """
        results = {}
        for hook in cls._shutdown_hooks:
            try:
                _logger.info(f"Running shutdown hook: {hook.plugin_type}:{hook.plugin_id}")
                hook.callback()
                record_plugin_shutdown(hook.plugin_type, hook.plugin_id)
                results[hook.plugin_id] = True
            except Exception as e:
                _logger.error(f"Shutdown hook failed for {hook.plugin_type}:{hook.plugin_id}: {e}")
                results[hook.plugin_id] = False
        return results

    @classmethod
    def get_plugin_cls(cls, plugin_type: str, plugin_id: str) -> Optional[Type[PluginBase]]:
        """Get a plugin class by type and ID."""
        return cls._plugins.get(plugin_type, {}).get(plugin_id)

    @classmethod
    def list_plugins(cls, plugin_type: str) -> Dict[str, Type[PluginBase]]:
        """List all plugins of a given type."""
        return cls._plugins.get(plugin_type, {}).copy()

    @classmethod
    def list_plugin_types(cls) -> list:
        """List all available plugin types."""
        return list(cls._plugins.keys())

    @classmethod
    def list_all_plugins(cls) -> Dict[str, Dict[str, Type[PluginBase]]]:
        """List all plugins by type."""
        return cls._plugins.copy()

    @classmethod
    def create(cls, plugin_type: str, plugin_id: str, **config) -> PluginBase:
        """Create a plugin instance by type and ID."""
        plugin_cls = cls.get_plugin_cls(plugin_type, plugin_id)
        if not plugin_cls:
            raise ValueError(f"Unknown plugin: {plugin_type}:{plugin_id}")

        factory_key = f"{plugin_type}:{plugin_id}"
        if factory_key in cls._factories:
            return cls._factories[factory_key](**config)

        return plugin_cls(**config)

    @classmethod
    def has_plugin(cls, plugin_type: str, plugin_id: str) -> bool:
        """Check if a plugin is registered."""
        return cls.get_plugin_cls(plugin_type, plugin_id) is not None

    @classmethod
    def check_plugin(cls, plugin_type: str, plugin_id: str) -> PluginCheckResult:
        """Check availability of a specific plugin."""
        plugin_cls = cls.get_plugin_cls(plugin_type, plugin_id)
        if not plugin_cls:
            from src.metrics import PluginCheckResult as MetricsCheckResult
            return MetricsCheckResult(
                available=False,
                reason=f"Plugin not found: {plugin_type}:{plugin_id}"
            )
        return plugin_cls.check_availability()

    @classmethod
    def check_all_plugins(cls) -> Dict[str, Dict[str, PluginCheckResult]]:
        """Check availability of all registered plugins.

        Returns:
            {plugin_type: {plugin_id: PluginCheckResult}}
        """
        from src.metrics import PluginCheckResult as MetricsCheckResult

        results = {}
        for plugin_type, plugins in cls._plugins.items():
            results[plugin_type] = {}
            for plugin_id, plugin_cls in plugins.items():
                # Skip plugins that don't have check_availability method
                if not hasattr(plugin_cls, 'check_availability'):
                    results[plugin_type][plugin_id] = MetricsCheckResult(
                        available=True,
                        reason="No availability check defined"
                    )
                    continue
                results[plugin_type][plugin_id] = plugin_cls.check_availability()
        return results

    @classmethod
    def get_registration_info(cls, plugin_type: str, plugin_id: str) -> Optional[PluginRegistration]:
        """Get registration info for a plugin."""
        return cls._registrations.get(f"{plugin_type}:{plugin_id}")

    @classmethod
    def get_startup_hooks(cls) -> List[LifecycleHook]:
        """Get all startup hooks in priority order."""
        return cls._startup_hooks.copy()

    @classmethod
    def get_shutdown_hooks(cls) -> List[LifecycleHook]:
        """Get all shutdown hooks in reverse priority order."""
        return cls._shutdown_hooks.copy()


# Convenience accessors for each plugin type
def get_llm_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("llm")


def get_notification_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("notification")


def get_content_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("content")


def get_storage_plugins() -> Dict[str, Type[PluginBase]]:
    return PluginRegistry.list_plugins("storage")


def load_storage_config():
    """Load and configure the storage handler based on environment config."""
    # Trigger storage plugin auto-registration
    from src.plugins.storage import SQLiteStorageHandler  # noqa: F401
    # Trigger LLM plugin auto-registration
    from src.plugins.llm import openai, ollama, dashscope, dummy, null  # noqa: F401
    # Trigger notification plugin auto-registration
    from src.plugins.notification import (  # noqa: F401
        slack, ntfy, null as notification_null,
    )
    # Trigger content plugin auto-registration
    from src.plugins.content import requests, playwright, rsshub  # noqa: F401
    config_type = environ.get("ENTROFEED_STORAGE_HANDLER", "sqlite")
    storage_handler = PluginRegistry.create("storage", config_type)
    _logger.info(f"Loading storage handler of type {config_type}")
    return storage_handler
