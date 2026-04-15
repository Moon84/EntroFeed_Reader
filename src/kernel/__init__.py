# -*- coding: utf-8 -*-
"""EntroFeed Kernel - Core infrastructure.

This module provides the core kernel components:
- PluginRegistry: Central plugin registration system
- HookRegistry: Pre/post execution hooks
"""

from src.kernel.registry import PluginBase, PluginRegistry
from src.kernel.hooks import HookType, HookContext, HookRegistry, on as hook_on

__all__ = [
    "PluginBase",
    "PluginRegistry",
    "HookType",
    "HookContext",
    "HookRegistry",
    "hook_on",
]
