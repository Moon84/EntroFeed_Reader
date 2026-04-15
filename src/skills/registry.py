# -*- coding: utf-8 -*-
"""Skill registry - Manages available skills."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.skills.loader import SkillLoader


class SkillRegistry:
    """Registry for skills with singleton access."""

    _instance: Optional["SkillRegistry"] = None
    _loader: SkillLoader
    _skills: Dict[str, Dict[str, Any]] = {}

    def __init__(self, skills_dir: Optional[Path] = None):
        self._loader = SkillLoader(skills_dir)
        self._load_all_skills()

    @classmethod
    def get_instance(cls, skills_dir: Optional[Path] = None) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls(skills_dir)
        return cls._instance

    def _load_all_skills(self) -> None:
        """Load all skills from the skills directory."""
        for name in self._loader.list_skills():
            skill = self._loader.load_skill(name)
            if skill:
                self._skills[name] = skill

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._skills.get(name)

    def list_all(self) -> List[str]:
        return list(self._skills.keys())

    def add_skill(self, name: str, manifest: Dict[str, Any]) -> None:
        self._skills[name] = manifest


def get_skill_registry() -> SkillRegistry:
    return SkillRegistry.get_instance()
