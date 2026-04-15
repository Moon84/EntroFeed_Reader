# -*- coding: utf-8 -*-
"""Skills module for EntroFeed - Manifest-driven skill system.

Provides infrastructure for loading and executing skills defined as SKILL.md manifests.
"""

from src.skills.loader import SkillLoader
from src.skills.registry import SkillRegistry
from src.skills.executor import SkillExecutor

__all__ = [
    "SkillLoader",
    "SkillRegistry",
    "SkillExecutor",
]
