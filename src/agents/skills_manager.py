# -*- coding: utf-8 -*-
"""Skills manager - backward compatibility wrapper."""

from src.skills.registry import get_skill_registry
from src.skills.executor import SkillExecutor

__all__ = ["get_skill_registry", "SkillExecutor"]
