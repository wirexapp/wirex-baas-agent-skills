"""Validate skill structure and agentskills.io spec compliance."""

import json
import re

import pytest
from skills_ref import read_properties, validate

from conftest import SKILLS_DIR, SKILL_NAMES, file_content


class TestSkillsRefValidation:
    """Run skills-ref validate() on every skill directory."""

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_validates(self, skill_name):
        problems = validate(SKILLS_DIR / skill_name)
        assert problems == [], f"{skill_name} validation errors: {problems}"


class TestSkillProperties:
    """Verify skill properties beyond spec minimums."""

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_properties(self, skill_name):
        """Combined check: description length, license, metadata."""
        props = read_properties(SKILLS_DIR / skill_name)
        assert len(props.description) >= 100, (
            f"description too short ({len(props.description)} chars, need >= 100)"
        )
        assert props.license == "Apache-2.0", f"license is {props.license!r}"
        assert props.metadata.get("author") == "wirex", "metadata.author != 'wirex'"
        assert "version" in props.metadata, "metadata.version missing"

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_name_matches_directory(self, skill_name):
        """Frontmatter name must equal directory name."""
        props = read_properties(SKILLS_DIR / skill_name)
        assert props.name == skill_name


class TestDirectoryStructure:
    """Verify file/directory conventions."""

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_md_exists(self, skill_name):
        assert (SKILLS_DIR / skill_name / "SKILL.md").is_file()

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_references_dir_exists(self, skill_name):
        assert (SKILLS_DIR / skill_name / "references").is_dir()

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_references_has_at_least_one_file(self, skill_name):
        refs = list((SKILLS_DIR / skill_name / "references").glob("*.md"))
        assert len(refs) >= 1, f"{skill_name}/references/ has no .md files"

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_md_under_500_lines(self, skill_name):
        content = file_content(SKILLS_DIR / skill_name / "SKILL.md")
        lines = content.splitlines()
        assert len(lines) <= 500, f"SKILL.md is {len(lines)} lines (max 500)"

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_no_unexpected_files(self, skill_name):
        """Skill dirs should only contain SKILL.md and references/."""
        skill_dir = SKILLS_DIR / skill_name
        entries = {e.name for e in skill_dir.iterdir() if not e.name.startswith(".")}
        allowed = {"SKILL.md", "references"}
        unexpected = entries - allowed
        assert not unexpected, f"Unexpected entries: {unexpected}"

    def test_all_skills_present(self):
        actual = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
        assert actual == sorted(SKILL_NAMES)

    def test_marketplace_json_lists_plugin(self):
        marketplace = json.loads(
            (SKILLS_DIR.parent / ".claude-plugin" / "marketplace.json").read_text()
        )
        plugin_names = [p["name"] for p in marketplace["plugins"]]
        assert "wirex-baas" in plugin_names


class TestInternalLinks:
    """Verify markdown links to reference files resolve to actual files."""

    LINK_RE = re.compile(r"\[.*?\]\((references/[^)]+\.md)\)")

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_reference_links_resolve(self, skill_name):
        skill_dir = SKILLS_DIR / skill_name
        content = file_content(skill_dir / "SKILL.md")
        broken = []
        for match in self.LINK_RE.finditer(content):
            target = skill_dir / match.group(1)
            if not target.is_file():
                broken.append(match.group(1))
        assert not broken, f"Broken links in {skill_name}/SKILL.md: {broken}"


class TestJsonCodeBlocks:
    """Validate that JSON code blocks in skills are syntactically correct."""

    JSON_BLOCK_RE = re.compile(r"```json\n(.*?)```", re.DOTALL)

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_json_blocks_parse(self, skill_name):
        from conftest import skill_all_content

        content = skill_all_content(skill_name)
        errors = []
        for i, match in enumerate(self.JSON_BLOCK_RE.finditer(content)):
            block = match.group(1).strip()
            # Skip blocks with placeholder patterns that aren't valid JSON
            if any(p in block for p in ["<", "...", "// ", "{token}", "{card"]):
                continue
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                # Show first 80 chars of the block for context
                preview = block[:80].replace("\n", " ")
                errors.append(f"  block {i + 1}: {e.msg} — {preview}...")
        assert not errors, (
            f"Invalid JSON in {skill_name}:\n" + "\n".join(errors)
        )
