"""Tests for the standalone code-reviewer agent.

Verifies that agents/code-reviewer.md meets spec requirements:
- Valid YAML frontmatter with meta.name: code-reviewer
- model_role: [critique, reasoning, general]
- 3 tool modules: tool-filesystem, tool-bash, tool-search
- Body has 6 review dimensions
- Output format section present
- Review philosophy section present
- @mentions at bottom
"""

from pathlib import Path

import yaml

AGENTS_DIR = Path(__file__).parent.parent / "agents"
CODE_REVIEWER = AGENTS_DIR / "code-reviewer.md"


def _parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from a markdown file."""
    content = filepath.read_text()
    parts = content.split("---")
    if len(parts) < 3:
        return {}, content
    frontmatter = yaml.safe_load(parts[1])
    body = "---".join(parts[2:])
    return frontmatter or {}, body


class TestCodeReviewerExists:
    def test_file_exists(self):
        """agents/code-reviewer.md must exist."""
        assert CODE_REVIEWER.exists(), "agents/code-reviewer.md does not exist"


class TestCodeReviewerFrontmatter:
    def test_has_valid_yaml_frontmatter(self):
        """agents/code-reviewer.md must have valid YAML frontmatter."""
        content = CODE_REVIEWER.read_text()
        parts = content.split("---")
        assert len(parts) >= 3, "No YAML frontmatter found (missing --- delimiters)"
        # Should parse without error
        parsed = yaml.safe_load(parts[1])
        assert parsed is not None, "Frontmatter YAML is empty or invalid"

    def test_meta_name_is_code_reviewer(self):
        """meta.name must be 'code-reviewer'."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        assert "meta" in fm, "No 'meta' key in frontmatter"
        assert fm["meta"].get("name") == "code-reviewer", (
            f"meta.name must be 'code-reviewer', got: {fm['meta'].get('name')}"
        )

    def test_meta_description_has_two_examples(self):
        """meta.description must contain at least 2 <example> blocks."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        assert "meta" in fm, "No 'meta' key in frontmatter"
        description = fm["meta"].get("description", "")
        example_count = description.count("<example>")
        assert example_count >= 2, (
            f"meta.description must have at least 2 <example> blocks, found {example_count}"
        )

    def test_model_role_contains_critique(self):
        """model_role must include 'critique'."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        model_role = fm.get("model_role", [])
        assert "critique" in model_role, (
            f"model_role must include 'critique', got: {model_role}"
        )

    def test_model_role_contains_reasoning(self):
        """model_role must include 'reasoning'."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        model_role = fm.get("model_role", [])
        assert "reasoning" in model_role, (
            f"model_role must include 'reasoning', got: {model_role}"
        )

    def test_model_role_contains_general(self):
        """model_role must include 'general'."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        model_role = fm.get("model_role", [])
        assert "general" in model_role, (
            f"model_role must include 'general', got: {model_role}"
        )

    def test_has_tool_filesystem(self):
        """tools must include tool-filesystem."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        tools = fm.get("tools", [])
        tool_modules = [t.get("module", "") for t in tools]
        assert "tool-filesystem" in tool_modules, (
            f"tool-filesystem not found in tools: {tool_modules}"
        )

    def test_has_tool_bash(self):
        """tools must include tool-bash."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        tools = fm.get("tools", [])
        tool_modules = [t.get("module", "") for t in tools]
        assert "tool-bash" in tool_modules, (
            f"tool-bash not found in tools: {tool_modules}"
        )

    def test_has_tool_search(self):
        """tools must include tool-search."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        tools = fm.get("tools", [])
        tool_modules = [t.get("module", "") for t in tools]
        assert "tool-search" in tool_modules, (
            f"tool-search not found in tools: {tool_modules}"
        )

    def test_tool_sources_use_amplifier_module_pattern(self):
        """All tool sources must use git+https://github.com/microsoft/amplifier-module-*@main pattern."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        tools = fm.get("tools", [])
        for tool in tools:
            source = tool.get("source", "")
            assert "github.com/microsoft/amplifier-module-" in source, (
                f"Tool source '{source}' does not match expected amplifier-module-* pattern"
            )

    def test_exactly_three_tools(self):
        """tools list must contain exactly 3 entries (filesystem, bash, search)."""
        fm, _ = _parse_frontmatter(CODE_REVIEWER)
        tools = fm.get("tools", [])
        assert len(tools) == 3, (
            f"Expected exactly 3 tools, got {len(tools)}: {[t.get('module') for t in tools]}"
        )


class TestCodeReviewerBody:
    def test_has_six_review_dimensions(self):
        """Body must mention all 6 review dimensions."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        # Check for the presence of key dimension concepts
        dimensions = [
            "Plan",  # Dimension 1: Plan/Spec Alignment
            "Code Quality",  # Dimension 2: Code Quality
            "Architecture",  # Dimension 3: Architecture
            "Test",  # Dimension 4: Test Quality
            "Documentation",  # Dimension 5: Documentation
            "Production",  # Dimension 6: Production Readiness
        ]
        for dimension in dimensions:
            assert dimension in body, (
                f"Review dimension '{dimension}' not found in agent body"
            )

    def test_has_output_format_section(self):
        """Body must have an Output Format section."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Output Format" in body, "Output Format section not found in agent body"

    def test_has_summary_in_output_format(self):
        """Output format must include Summary."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Summary" in body, "Summary not found in output format"

    def test_has_strengths_in_output_format(self):
        """Output format must include Strengths."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Strengths" in body, "Strengths not found in output format"

    def test_has_verdict_in_output_format(self):
        """Output format must include Verdict with APPROVED/NEEDS CHANGES."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Verdict" in body, "Verdict not found in output format"
        assert "APPROVED" in body, "APPROVED not found in output format"
        assert "NEEDS CHANGES" in body, "NEEDS CHANGES not found in output format"

    def test_has_review_philosophy_section(self):
        """Body must have a Review Philosophy section."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Review Philosophy" in body or "Philosophy" in body, (
            "Review Philosophy section not found in agent body"
        )

    def test_philosophy_mentions_constructive(self):
        """Review philosophy must mention being constructive."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "constructive" in body.lower(), (
            "Review philosophy must mention 'constructive'"
        )

    def test_philosophy_mentions_specific(self):
        """Review philosophy must mention being specific."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "specific" in body.lower(), "Review philosophy must mention 'specific'"

    def test_philosophy_only_critical_blocks(self):
        """Review philosophy must state only Critical issues block merge."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Critical" in body, "Critical severity level not found in agent body"

    def test_has_receiving_code_review_skill_reference(self):
        """Body must reference load_skill('receiving-code-review')."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "receiving-code-review" in body, (
            "Reference to load_skill('receiving-code-review') not found in body"
        )

    def test_has_required_actions_in_output(self):
        """Output format must include Required Actions."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Required Actions" in body, "Required Actions not found in output format"

    def test_has_critical_issues_in_output(self):
        """Output format must include Critical Issues."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Critical" in body, "Critical Issues not found in output format"

    def test_has_suggestions_in_output(self):
        """Output format must include Suggestions."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "Suggestions" in body or "suggestion" in body.lower(), (
            "Suggestions not found in output format"
        )


class TestCodeReviewerMentions:
    def test_has_language_philosophy_mention(self):
        """Must have @foundation:context/LANGUAGE_PHILOSOPHY.md mention."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "@foundation:context/LANGUAGE_PHILOSOPHY.md" in body, (
            "@foundation:context/LANGUAGE_PHILOSOPHY.md not found in body"
        )

    def test_has_common_agent_base_mention(self):
        """Must have @foundation:context/shared/common-agent-base.md mention."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "@foundation:context/shared/common-agent-base.md" in body, (
            "@foundation:context/shared/common-agent-base.md not found in body"
        )

    def test_has_superpowers_philosophy_mention(self):
        """Must have @superpowers:context/philosophy.md mention."""
        _, body = _parse_frontmatter(CODE_REVIEWER)
        assert "@superpowers:context/philosophy.md" in body, (
            "@superpowers:context/philosophy.md not found in body"
        )

    def test_mentions_at_bottom(self):
        """@mentions should appear at the bottom of the file."""
        content = CODE_REVIEWER.read_text()
        last_300_chars = content[-300:]
        assert (
            "@foundation:context/LANGUAGE_PHILOSOPHY.md" in last_300_chars
            or "@foundation:context/shared/common-agent-base.md" in last_300_chars
            or "@superpowers:context/philosophy.md" in last_300_chars
        ), "@mentions not found in last 300 characters of file"
