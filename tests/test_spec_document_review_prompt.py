"""Tests for context/spec-document-review-prompt.md.

Verifies that the spec document review prompt exists with all required content:
- Dispatch pattern using delegate()
- 5-category review table (Completeness, Consistency, Clarity, Scope, YAGNI)
- Calibration guidance
- Output format (Approved/Issues Found)
- 3-cycle max rule
- Roughly 60-70 lines
"""

from pathlib import Path

CONTEXT_DIR = Path(__file__).parent.parent / "context"
REVIEW_PROMPT = CONTEXT_DIR / "spec-document-review-prompt.md"


def read_prompt() -> str:
    assert REVIEW_PROMPT.is_file(), f"File does not exist: {REVIEW_PROMPT}"
    return REVIEW_PROMPT.read_text()


class TestSpecDocumentReviewPromptExists:
    def test_file_exists(self):
        assert REVIEW_PROMPT.is_file(), (
            "context/spec-document-review-prompt.md must exist"
        )


class TestDispatchPattern:
    def test_has_delegate_call(self):
        content = read_prompt()
        assert "delegate(" in content, "Must include delegate() dispatch pattern"

    def test_has_context_depth_none(self):
        content = read_prompt()
        assert "context_depth" in content and "none" in content, (
            "Must specify context_depth='none' in dispatch pattern"
        )

    def test_has_model_role_critique(self):
        content = read_prompt()
        assert "critique" in content, (
            "Must specify model_role='critique' in dispatch pattern"
        )


class TestReviewTable:
    def test_has_completeness_category(self):
        content = read_prompt()
        assert "Completeness" in content, "Review table must include Completeness"

    def test_has_consistency_category(self):
        content = read_prompt()
        assert "Consistency" in content, "Review table must include Consistency"

    def test_has_clarity_category(self):
        content = read_prompt()
        assert "Clarity" in content, "Review table must include Clarity"

    def test_has_scope_category(self):
        content = read_prompt()
        assert "Scope" in content, "Review table must include Scope"

    def test_has_yagni_category(self):
        content = read_prompt()
        assert "YAGNI" in content, "Review table must include YAGNI"


class TestCalibrationGuidance:
    def test_has_calibration_section(self):
        content = read_prompt()
        assert "Calibration" in content or "calibration" in content.lower(), (
            "Must include calibration guidance"
        )

    def test_calibration_mentions_real_problems(self):
        content = read_prompt()
        assert "real" in content.lower() and (
            "problem" in content.lower() or "issue" in content.lower()
        ), "Calibration must reference flagging real implementation problems only"


class TestOutputFormat:
    def test_has_approved_status(self):
        content = read_prompt()
        assert "Approved" in content, "Output format must include Approved status"

    def test_has_issues_found_status(self):
        content = read_prompt()
        assert "Issues Found" in content, (
            "Output format must include 'Issues Found' status"
        )

    def test_has_recommendations(self):
        content = read_prompt()
        assert "Recommendation" in content, "Output format must include Recommendations"


class TestProcessingResult:
    def test_has_max_cycle_rule(self):
        content = read_prompt()
        assert "3" in content and (
            "cycle" in content.lower() or "review" in content.lower()
        ), "Must include maximum 3 review cycles rule"

    def test_mentions_brainstormer(self):
        content = read_prompt()
        assert "brainstormer" in content.lower(), (
            "Processing section must mention delegating back to brainstormer"
        )

    def test_mentions_user_escalation(self):
        content = read_prompt()
        assert "escalat" in content.lower() or "user" in content.lower(), (
            "Must mention user escalation after max cycles"
        )


class TestApproximateLength:
    def test_is_approximately_60_to_70_lines(self):
        content = read_prompt()
        lines = content.splitlines()
        # Allow some flexibility: 50-85 lines is reasonable
        assert 50 <= len(lines) <= 85, f"File should be ~60-70 lines, got {len(lines)}"
