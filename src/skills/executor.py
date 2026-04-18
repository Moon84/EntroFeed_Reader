# -*- coding: utf-8 -*-
"""Skill executor - Runs skill workflows."""

import re
from typing import Any, Dict

from src.skills.registry import get_skill_registry


class SkillExecutor:
    """Executes skills based on their manifest workflow.

    Workflow syntax uses {{tool_name:arg='value'}} placeholders.
    """

    def __init__(self):
        self.registry = get_skill_registry()

    def execute(self, skill_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a skill workflow.

        Args:
            skill_name: Name of the skill to execute
            context: Context dict with 'input' and any other variables

        Returns:
            Dict with 'success', 'output', and optional 'error'
        """
        skill = self.registry.get(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill not found: {skill_name}"}

        try:
            workflow = skill.get("workflow", "")
            result = self._execute_workflow(workflow, context)
            return {"success": True, "output": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_workflow(self, workflow: str, context: Dict[str, Any]) -> str:
        """Execute workflow by replacing tool placeholders."""
        # Pattern: {{tool_name:arg1='val1',arg2='val2'}}
        pattern = r"\{\{(\w+)(?::(.+?))?\}\}"

        def replace_tool(match):
            tool_name = match.group(1)
            args_str = match.group(2) or ""

            # Parse args
            args = self._parse_args(args_str, context)

            # Get tool function from TOOL_FUNCTIONS
            from src.agents.tools import TOOL_FUNCTIONS
            tool_func = TOOL_FUNCTIONS.get(tool_name)
            if not tool_func:
                return f"[Tool not found: {tool_name}]"

            try:
                result = tool_func(**args)
                return str(result) if result else ""
            except Exception as e:
                return f"[Error: {e}]"

        return re.sub(pattern, replace_tool, workflow)

    def _parse_args(self, args_str: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse tool arguments from string."""
        if not args_str.strip():
            return {}

        args = {}
        # Simple key='value' parsing
        pattern = r"(\w+)='([^']*)'"
        for match in re.finditer(pattern, args_str):
            key, value = match.groups()
            # Substitute context variables
            if value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                value = context.get(var_name, value)
            args[key] = value
        return args
