# -*- coding: utf-8 -*-
"""Skill loader - Parses SKILL.md manifest files."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.constants import DATA_DIR


class SkillLoader:
    """Loads skills from SKILL.md manifest files.

    SKILL.md format:
    ---
    name: skill_name
    description: "Description of the skill"
    version: 1.0.0
    category: content_analysis
    tools:
      - tool_name
    ---
    # Workflow content
    """

    SKILL_DIR = DATA_DIR / "skills"

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or self.SKILL_DIR

    def load_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Load a skill by name."""
        skill_path = self.skills_dir / skill_name / "SKILL.md"
        if not skill_path.exists():
            return None
        return self._parse_skill_md(skill_path.read_text(), skill_name)

    def _parse_skill_md(self, content: str, name: str) -> Dict[str, Any]:
        """Parse SKILL.md content into manifest dict."""
        # Split frontmatter from markdown
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not match:
            return {"name": name, "description": "", "workflow": content}

        frontmatter, workflow = match.groups()
        manifest = yaml.safe_load(frontmatter) or {}
        manifest["name"] = name
        manifest["workflow"] = workflow.strip()
        return manifest

    def list_skills(self) -> list:
        """List all available skills."""
        if not self.skills_dir.exists():
            return []
        return [d.name for d in self.skills_dir.iterdir() if d.is_dir()]
