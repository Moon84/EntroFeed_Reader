# -*- coding: utf-8 -*-
"""Tests for Skills module."""

import tempfile
from pathlib import Path

from src.skills.loader import SkillLoader
from src.skills.registry import SkillRegistry
from src.skills.executor import SkillExecutor


class TestSkillLoader:
    """Test SkillLoader functionality."""

    def test_parse_skill_md_with_frontmatter(self):
        """Test parsing SKILL.md with YAML frontmatter."""
        content = """---
name: test_skill
description: "A test skill"
version: 1.0.0
category: testing
---
# Workflow
This is the workflow content.
"""
        loader = SkillLoader()
        result = loader._parse_skill_md(content, "test_skill")

        assert result["name"] == "test_skill"
        assert result["description"] == "A test skill"
        assert result["version"] == "1.0.0"
        assert result["category"] == "testing"
        assert "This is the workflow content." in result["workflow"]

    def test_parse_skill_md_without_frontmatter(self):
        """Test parsing SKILL.md without frontmatter."""
        content = "Just plain workflow content."
        loader = SkillLoader()
        result = loader._parse_skill_md(content, "plain_skill")

        assert result["name"] == "plain_skill"
        assert result["description"] == ""
        assert "Just plain workflow content." in result["workflow"]

    def test_load_skill_from_directory(self):
        """Test loading a skill from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: test_skill
description: "Test"
---
Workflow content here.
""")
            loader = SkillLoader(skills_dir=Path(tmpdir))
            skill = loader.load_skill("test_skill")

            assert skill is not None
            assert skill["name"] == "test_skill"
            assert "Workflow content here." in skill["workflow"]

    def test_load_skill_not_found(self):
        """Test loading non-existent skill returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(skills_dir=Path(tmpdir))
            skill = loader.load_skill("nonexistent")
            assert skill is None

    def test_list_skills(self):
        """Test listing skills in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "skill1").mkdir()
            (Path(tmpdir) / "skill2").mkdir()
            (Path(tmpdir) / "not_a_skill.txt").write_text("not a skill")

            loader = SkillLoader(skills_dir=Path(tmpdir))
            skills = loader.list_skills()

            assert "skill1" in skills
            assert "skill2" in skills
            assert len(skills) == 2


class TestSkillRegistry:
    """Test SkillRegistry functionality."""

    def test_singleton_access(self):
        """Test getting singleton instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reg1 = SkillRegistry.get_instance(Path(tmpdir))
            reg2 = SkillRegistry.get_instance(Path(tmpdir))
            assert reg1 is reg2

    def test_load_skills_from_directory(self):
        """Test loading skills into registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "my_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: my_skill
description: "My skill"
---
Workflow.
""")
            registry = SkillRegistry(Path(tmpdir))

            assert "my_skill" in registry.list_all()
            skill = registry.get("my_skill")
            assert skill["name"] == "my_skill"

    def test_get_nonexistent_skill(self):
        """Test getting non-existent skill returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(Path(tmpdir))
            assert registry.get("nonexistent") is None

    def test_add_skill(self):
        """Test manually adding a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(Path(tmpdir))
            manifest = {
                "name": "added_skill",
                "description": "Manually added",
                "workflow": "Test workflow",
            }
            registry.add_skill("added_skill", manifest)

            assert "added_skill" in registry.list_all()
            assert registry.get("added_skill")["description"] == "Manually added"


class TestSkillExecutor:
    """Test SkillExecutor functionality."""

    def test_execute_nonexistent_skill(self):
        """Test executing non-existent skill returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(Path(tmpdir))
            executor = SkillExecutor()

            # Manually set registry
            executor.registry = registry

            result = executor.execute("nonexistent", {"input": "test"})
            assert result["success"] is False
            assert "not found" in result["error"]

    def test_execute_skill_without_tools(self):
        """Test executing skill with plain workflow (no tool calls)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "plain_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("""---
name: plain_skill
description: "Plain workflow"
---
This is just text content.
""")
            registry = SkillRegistry(Path(tmpdir))
            executor = SkillExecutor()
            executor.registry = registry

            result = executor.execute("plain_skill", {"input": "test"})
            assert result["success"] is True
            assert "This is just text content." in result["output"]

    def test_parse_args_simple(self):
        """Test argument parsing."""
        executor = SkillExecutor()

        args = executor._parse_args("arg1='value1',arg2='value2'", {})
        assert args["arg1"] == "value1"
        assert args["arg2"] == "value2"

    def test_parse_args_with_context(self):
        """Test argument parsing with context variables."""
        executor = SkillExecutor()
        context = {"my_var": "context_value"}

        args = executor._parse_args("arg='${my_var}'", context)
        assert args["arg"] == "context_value"

    def test_parse_args_empty(self):
        """Test parsing empty argument string."""
        executor = SkillExecutor()
        args = executor._parse_args("", {})
        assert args == {}
