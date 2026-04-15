# -*- coding: utf-8 -*-
"""Skills Manager - Skill loading and management for EntroFeed."""

import json
import logging
import os
import re
import yaml
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SkillsManager:
    """Manage skills loading and configuration."""

    def __init__(self, skills_dir: Path = None):
        """Initialize skills manager.

        Args:
            skills_dir: Directory containing skills
        """
        self.skills_dir = skills_dir or Path("./data/skills")
        self._skills_cache: Dict[str, Dict] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize skills from directory."""
        if self._initialized:
            return

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_skills()
            self._initialized = True
            return

        # Load all skills
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                self._load_skill(skill_path.name)

        self._initialized = True

    def _load_skill(self, skill_name: str) -> Optional[Dict]:
        """Load a skill from directory.

        Args:
            skill_name: Name of skill to load

        Returns:
            Skill data dict or None
        """
        skill_dir = self.skills_dir / skill_name
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            return None

        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse frontmatter
            skill_data = self._parse_skill_md(content)
            skill_data["name"] = skill_name
            skill_data["path"] = str(skill_dir)

            self._skills_cache[skill_name] = skill_data
            return skill_data
        except Exception as e:
            print(f"Failed to load skill '{skill_name}': {e}")
            return None

    def _parse_skill_md(self, content: str) -> Dict:
        """Parse SKILL.md content.

        Args:
            content: File content

        Returns:
            Parsed skill data
        """
        # Check for YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    markdown_content = parts[2].strip()
                    return {
                        "metadata": frontmatter or {},
                        "description": frontmatter.get("description", ""),
                        "content": markdown_content,
                    }
                except yaml.YAMLError:
                    pass

        # Fallback: treat entire content as description
        return {
            "metadata": {},
            "description": content[:200],
            "content": content,
        }

    def _create_default_skills(self) -> None:
        """Create default skills directory with examples."""
        default_skills = {
            "article_analyzer": {
                "description": "深度分析文章内容、提取关键信息",
                "content": """# Article Analyzer

## When to Use
用户请求分析文章、提取要点时使用。

## How to Use
使用 get_entry_content 获取文章内容，然后分析提取：
- 主要论点
- 关键发现
- 支持证据
- 局限性

## Tools
- get_entry_content
- search_entries
"""
            },
            "daily_digest": {
                "description": "汇总多个条目形成每日简报",
                "content": """# Daily Digest

## When to Use
用户请求获取每日要点汇总时使用。

## How to Use
1. 使用 get_daily_digest 获取当日高优先级内容
2. 按优先级排序
3. 生成简洁摘要

## Tools
- get_daily_digest
- get_high_priority_content
"""
            },
            "translator": {
                "description": "多语言翻译",
                "content": """# Translator

## When to Use
用户请求翻译内容时使用。

## How to Use
使用 translate_text 工具进行翻译。

## Tools
- translate_text
"""
            },
        }

        for skill_name, skill_data in default_skills.items():
            skill_dir = self.skills_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            # Create SKILL.md with frontmatter
            content = f"""---
name: {skill_name}
description: "{skill_data['description']}"
---

{skill_data['content']}
"""

            with open(skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
                f.write(content)

    def get_skill(self, name: str) -> Optional[Dict]:
        """Get skill by name.

        Args:
            name: Skill name

        Returns:
            Skill data or None
        """
        if not self._initialized:
            self.initialize()

        if name not in self._skills_cache:
            self._load_skill(name)

        return self._skills_cache.get(name)

    def list_skills(self) -> List[Dict]:
        """List all available skills.

        Returns:
            List of skill metadata
        """
        if not self._initialized:
            self.initialize()

        return [
            {
                "name": name,
                "description": data.get("description", ""),
                "metadata": data.get("metadata", {}),
            }
            for name, data in self._skills_cache.items()
        ]

    def get_skill_tools(self, name: str) -> List[str]:
        """Get tools required by a skill.

        Args:
            name: Skill name

        Returns:
            List of tool names
        """
        skill = self.get_skill(name)
        if not skill:
            return []

        # Extract from metadata or content
        metadata = skill.get("metadata", {})
        return metadata.get("tools", [])

    def execute_skill(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a skill based on its workflow.

        Args:
            skill_name: Name of skill to execute
            context: Execution context (user_input, entry_id, etc.)

        Returns:
            Execution result dict
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}",
                "available_skills": list(self._skills_cache.keys()),
            }

        try:
            result = self._execute_workflow(skill, context)
            return {
                "success": True,
                "skill": skill_name,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Skill execution failed for {skill_name}: {e}")
            return {
                "success": False,
                "skill": skill_name,
                "error": str(e),
            }

    def _execute_workflow(
        self,
        skill: Dict,
        context: Dict[str, Any]
    ) -> str:
        """
        Execute a skill's workflow.

        Args:
            skill: Skill data dict
            context: Execution context

        Returns:
            Execution result as string
        """
        from src.agents.tools import TOOL_FUNCTIONS

        workflow = skill.get("content", "")
        user_input = context.get("user_input", "")

        if not workflow:
            return "[No workflow defined in skill]"

        # Replace {{...}} placeholders with tool results
        def replace_tool_call(match):
            tool_expr = match.group(1).strip()
            parts = tool_expr.split(":", 1)
            tool_name = parts[0].strip()

            if tool_name not in TOOL_FUNCTIONS:
                return f"[Tool not found: {tool_name}]"

            tool_func = TOOL_FUNCTIONS[tool_name]

            try:
                if len(parts) > 1:
                    # Has arguments
                    args_str = parts[1].strip()
                    args = self._parse_tool_args(args_str, context)
                    result = tool_func(**args)
                else:
                    result = tool_func()

                if isinstance(result, dict):
                    return json.dumps(result, indent=2, ensure_ascii=False)
                return str(result)
            except Exception as e:
                return f"[Error calling {tool_name}: {e}]"

        # Process workflow
        result = re.sub(r"\{\{(.*?)\}\}", replace_tool_call, workflow)

        # Replace context variables
        def replace_context(match):
            key = match.group(1).strip()
            if key == "user_input":
                return user_input
            return context.get(key, f"[Missing: {key}]")

        result = re.sub(r"\{\{(\w+)\}\}", replace_context, result)

        return result

    def _parse_tool_args(
        self,
        args_str: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse tool arguments from string.

        Args:
            args_str: Arguments string (e.g., "query='AI', limit=10")
            context: Execution context

        Returns:
            Parsed arguments dict
        """
        args = {}

        # Match key='value' or key="value" or key=number
        pattern = r"(\w+)=['\"]([^'\"]*)['\"]|(\w+)=(\d+)"
        matches = re.findall(pattern, args_str)

        for match in matches:
            key = match[0] or match[2]
            value = match[1] or match[3]

            # Try to substitute context variables
            if value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()
                value = context.get(var_name, "")
            elif value in context:
                value = context[value]

            # Convert numeric values
            if match[2]:  # Numeric argument
                value = int(value)

            args[key] = value

        return args


# Singleton instance
_manager: Optional[SkillsManager] = None


def get_skills_manager(skills_dir: Path = None) -> SkillsManager:
    """Get or create singleton skills manager."""
    global _manager
    if _manager is None:
        _manager = SkillsManager(skills_dir=skills_dir)
    return _manager


__all__ = [
    "SkillsManager",
    "get_skills_manager",
]
