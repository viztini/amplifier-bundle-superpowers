"""Tests for task-11: verify.md — Failure Memories @mention, When to Apply Trigger List, and Holistic Code Review.

Verifies three new sections are present in modes/verify.md:
1. '## Why This Matters' with @mention to verification-failure-memories.md
2. '## When to Apply' with ALWAYS before: and Rule applies to: subsections
3. '## Holistic Code Review' referencing superpowers:code-reviewer
All three sections must appear before '## The Bottom Line'.
"""

from pathlib import Path

MODES_DIR = Path(__file__).parent.parent / "modes"
VERIFY_FILE = MODES_DIR / "verify.md"


def read_content() -> str:
    assert VERIFY_FILE.is_file(), f"File does not exist: {VERIFY_FILE}"
    return VERIFY_FILE.read_text(encoding="utf-8")


class TestWhyThisMattersSectionWithFailureMemories:
    def test_failure_memories_mention_present(self):
        """verify.md must contain @mention to verification-failure-memories.md."""
        content = read_content()
        assert "failure-memories" in content, (
            "modes/verify.md must contain reference to 'failure-memories' "
            "(the @superpowers:context/verification-failure-memories.md @mention)"
        )

    def test_why_this_matters_section_present(self):
        """verify.md must contain a '## Why This Matters' section."""
        content = read_content()
        assert "## Why This Matters" in content, (
            "modes/verify.md must contain a '## Why This Matters' section "
            "with the failure memories @mention"
        )

    def test_failure_memories_mention_in_why_section(self):
        """The failure-memories @mention must be inside the Why This Matters section."""
        content = read_content()
        why_idx = content.find("## Why This Matters")
        assert why_idx != -1, "## Why This Matters section must exist"
        # Find the next ## heading after Why This Matters
        next_section_idx = content.find("\n## ", why_idx + 1)
        section_content = (
            content[why_idx:next_section_idx] if next_section_idx != -1 else content[why_idx:]
        )
        assert "failure-memories" in section_content, (
            "The 'failure-memories' @mention must appear inside '## Why This Matters' section"
        )


class TestWhenToApplySectionPresent:
    def test_when_to_apply_heading_present(self):
        """verify.md must contain a '## When to Apply' section."""
        content = read_content()
        assert "## When to Apply" in content, (
            "modes/verify.md must contain a '## When to Apply' section"
        )

    def test_always_before_subsection_present(self):
        """The 'ALWAYS before:' trigger list must be present."""
        content = read_content()
        assert "ALWAYS before:" in content, (
            "modes/verify.md must contain 'ALWAYS before:' subsection in When to Apply"
        )

    def test_rule_applies_to_subsection_present(self):
        """The 'Rule applies to:' list must be present."""
        content = read_content()
        assert "Rule applies to:" in content, (
            "modes/verify.md must contain 'Rule applies to:' subsection in When to Apply"
        )

    def test_always_before_covers_success_claims(self):
        """ALWAYS before: list must cover success/completion claims."""
        content = read_content()
        when_idx = content.find("## When to Apply")
        assert when_idx != -1, "## When to Apply section must exist"
        next_section_idx = content.find("\n## ", when_idx + 1)
        section_content = (
            content[when_idx:next_section_idx] if next_section_idx != -1 else content[when_idx:]
        )
        # Should mention completion/success type claims
        assert (
            "completion" in section_content.lower()
            or "success" in section_content.lower()
            or "claim" in section_content.lower()
        ), (
            "ALWAYS before: list must mention completion/success/claim triggers"
        )

    def test_always_before_covers_commit_pr_completion(self):
        """ALWAYS before: list must include committing/PR/task-completion actions."""
        content = read_content()
        when_idx = content.find("## When to Apply")
        assert when_idx != -1, "## When to Apply section must exist"
        next_section_idx = content.find("\n## ", when_idx + 1)
        section_content = (
            content[when_idx:next_section_idx] if next_section_idx != -1 else content[when_idx:]
        )
        assert (
            "commit" in section_content.lower()
            or "PR" in section_content
            or "task completion" in section_content.lower()
        ), (
            "ALWAYS before: list must mention committing/PR creation/task completion"
        )

    def test_rule_applies_to_covers_exact_phrases(self):
        """Rule applies to: must mention exact phrases like done/complete/fixed/working."""
        content = read_content()
        rule_idx = content.find("Rule applies to:")
        assert rule_idx != -1, "Rule applies to: subsection must exist"
        # Grab the text after "Rule applies to:"
        rule_section = content[rule_idx : rule_idx + 800]
        assert (
            "'done'" in rule_section.lower()
            or "done" in rule_section.lower()
            or "complete" in rule_section.lower()
        ), (
            "Rule applies to: must list exact phrases like 'done', 'complete', 'fixed', 'working'"
        )


class TestHolisticCodeReviewSection:
    def test_holistic_code_review_heading_present(self):
        """verify.md must contain a '## Holistic Code Review' section."""
        content = read_content()
        assert "## Holistic Code Review" in content, (
            "modes/verify.md must contain a '## Holistic Code Review' section"
        )

    def test_code_reviewer_reference_present(self):
        """verify.md must reference 'code-reviewer' (superpowers:code-reviewer)."""
        content = read_content()
        assert "code-reviewer" in content, (
            "modes/verify.md must contain a reference to 'code-reviewer' "
            "(superpowers:code-reviewer agent)"
        )

    def test_code_reviewer_in_holistic_section(self):
        """The code-reviewer reference must be inside Holistic Code Review section."""
        content = read_content()
        holistic_idx = content.find("## Holistic Code Review")
        assert holistic_idx != -1, "## Holistic Code Review section must exist"
        next_section_idx = content.find("\n## ", holistic_idx + 1)
        section_content = (
            content[holistic_idx:next_section_idx]
            if next_section_idx != -1
            else content[holistic_idx:]
        )
        assert "code-reviewer" in section_content, (
            "'code-reviewer' must appear inside '## Holistic Code Review' section"
        )


class TestSectionsInsertedBeforeBottomLine:
    def test_failure_memories_before_bottom_line(self):
        """failure-memories reference must appear before ## The Bottom Line."""
        content = read_content()
        bottom_line_idx = content.find("## The Bottom Line")
        assert bottom_line_idx != -1, "## The Bottom Line section must exist"
        memories_idx = content.find("failure-memories")
        assert memories_idx != -1, "failure-memories must exist in the file"
        assert memories_idx < bottom_line_idx, (
            "'failure-memories' must appear BEFORE '## The Bottom Line', "
            f"but found at {memories_idx} vs bottom line at {bottom_line_idx}"
        )

    def test_when_to_apply_before_bottom_line(self):
        """## When to Apply section must appear before ## The Bottom Line."""
        content = read_content()
        bottom_line_idx = content.find("## The Bottom Line")
        assert bottom_line_idx != -1, "## The Bottom Line section must exist"
        when_idx = content.find("## When to Apply")
        assert when_idx != -1, "## When to Apply must exist in the file"
        assert when_idx < bottom_line_idx, (
            "'## When to Apply' must appear BEFORE '## The Bottom Line', "
            f"but found at {when_idx} vs bottom line at {bottom_line_idx}"
        )

    def test_code_reviewer_before_bottom_line(self):
        """code-reviewer reference must appear before ## The Bottom Line."""
        content = read_content()
        bottom_line_idx = content.find("## The Bottom Line")
        assert bottom_line_idx != -1, "## The Bottom Line section must exist"
        cr_idx = content.find("code-reviewer")
        assert cr_idx != -1, "code-reviewer must exist in the file"
        assert cr_idx < bottom_line_idx, (
            "'code-reviewer' must appear BEFORE '## The Bottom Line', "
            f"but found at {cr_idx} vs bottom line at {bottom_line_idx}"
        )
