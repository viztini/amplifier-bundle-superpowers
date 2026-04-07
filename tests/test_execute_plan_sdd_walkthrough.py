"""Tests for SDD walkthrough reference in execute-plan mode.

Verifies that modes/execute-plan.md contains a reference to the SDD
walkthrough skill, placed after the Model Selection Guidance section.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
EXECUTE_PLAN_MD = REPO_ROOT / "modes" / "execute-plan.md"


def _read_content() -> str:
    assert EXECUTE_PLAN_MD.exists(), f"File not found: {EXECUTE_PLAN_MD}"
    return EXECUTE_PLAN_MD.read_text()


class TestSddWalkthroughReference:
    """Tests that execute-plan.md contains SDD walkthrough references."""

    def test_sdd_walkthrough_skill_name_present(self):
        """grep match for 'sdd-walkthrough' in modes/execute-plan.md."""
        content = _read_content()
        assert "sdd-walkthrough" in content, (
            "Expected 'sdd-walkthrough' in modes/execute-plan.md "
            "(load_skill call referencing the walkthrough skill)"
        )

    def test_sdd_worked_example_section_present(self):
        """grep match for 'SDD Worked Example' in modes/execute-plan.md."""
        content = _read_content()
        assert "SDD Worked Example" in content, (
            "Expected '## SDD Worked Example' section in modes/execute-plan.md"
        )

    def test_sdd_section_after_model_selection_guidance(self):
        """SDD Worked Example section appears after Model Selection Guidance."""
        content = _read_content()
        model_guidance_pos = content.find("## Model Selection Guidance")
        sdd_section_pos = content.find("## SDD Worked Example")
        assert model_guidance_pos != -1, (
            "Expected '## Model Selection Guidance' section in modes/execute-plan.md"
        )
        assert sdd_section_pos != -1, (
            "Expected '## SDD Worked Example' section in modes/execute-plan.md"
        )
        assert sdd_section_pos > model_guidance_pos, (
            "Expected '## SDD Worked Example' to appear AFTER '## Model Selection Guidance'"
        )

    def test_sdd_section_after_default_to_coding_line(self):
        """SDD section is inserted after 'Default to `coding` when uncertain.'"""
        content = _read_content()
        default_coding_pos = content.find("Default to `coding` when uncertain.")
        sdd_section_pos = content.find("## SDD Worked Example")
        assert default_coding_pos != -1, (
            "Expected 'Default to `coding` when uncertain.' in modes/execute-plan.md"
        )
        assert sdd_section_pos != -1, (
            "Expected '## SDD Worked Example' section in modes/execute-plan.md"
        )
        assert sdd_section_pos > default_coding_pos, (
            "Expected '## SDD Worked Example' to appear AFTER 'Default to `coding` when uncertain.'"
        )

    def test_load_skill_call_present(self):
        """Section includes a load_skill call for sdd-walkthrough."""
        content = _read_content()
        assert "load_skill(skill_name='sdd-walkthrough')" in content, (
            "Expected load_skill(skill_name='sdd-walkthrough') call in modes/execute-plan.md"
        )

    def test_three_agent_pipeline_description(self):
        """Section describes the three-agent pipeline walkthrough."""
        content = _read_content()
        assert "three-agent pipeline" in content, (
            "Expected description mentioning 'three-agent pipeline' in SDD Worked Example section"
        )

    def test_spec_review_failures_mentioned(self):
        """Section mentions spec review failures as part of the walkthrough."""
        content = _read_content()
        assert "spec review failure" in content.lower() or "spec-review failure" in content.lower(), (
            "Expected mention of spec review failures in modes/execute-plan.md"
        )

    def test_done_with_concerns_mentioned(self):
        """Section mentions DONE_WITH_CONCERNS."""
        content = _read_content()
        assert "DONE_WITH_CONCERNS" in content, (
            "Expected mention of DONE_WITH_CONCERNS in the SDD Worked Example section"
        )

    def test_five_tasks_mentioned(self):
        """Section notes 5 realistic tasks."""
        content = _read_content()
        # Check for variations: "5 realistic tasks", "five realistic tasks", etc.
        assert ("5 realistic" in content or "five realistic" in content
                or "5 tasks" in content or "five tasks" in content), (
            "Expected mention of 5 realistic tasks in modes/execute-plan.md"
        )

    def test_delegate_calls_mentioned(self):
        """Section notes Amplifier delegate() calls."""
        content = _read_content()
        assert "delegate()" in content, (
            "Expected mention of delegate() calls in modes/execute-plan.md"
        )

    def test_model_role_parameters_mentioned(self):
        """Section notes model_role parameters."""
        content = _read_content()
        assert "model_role" in content, (
            "Expected mention of model_role parameters in modes/execute-plan.md "
            "(should already exist from Model Selection Guidance, confirmed in SDD section too)"
        )
