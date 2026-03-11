"""Tests for skill source ordering strategy.

Verifies that our bundle's skills take precedence over obra's skills
by being listed first in the tool-skills config. First-match-wins
priority means our bundle must appear before obra's.
"""

import os
from pathlib import Path

import yaml
import pytest

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
BEHAVIOR_YAML = os.path.join(REPO_ROOT, "behaviors", "superpowers-methodology.yaml")


class TestSkillSourceOrder:
    """Tests that our bundle's skills are listed before obra's."""

    @pytest.fixture(autouse=True)
    def load_config(self):
        assert os.path.isfile(BEHAVIOR_YAML), (
            f"Behavior YAML not found: {BEHAVIOR_YAML}"
        )
        with open(BEHAVIOR_YAML) as f:
            self.config = yaml.safe_load(f)

    def _get_skills_config(self) -> list:
        """Find the skills list from the tool-skills module config."""
        tools = self.config.get("tools", [])
        assert tools, "Expected a 'tools' section in behavior YAML"

        for tool in tools:
            if tool.get("module") == "tool-skills":
                skills = tool.get("config", {}).get("skills", [])
                assert skills, "Expected 'skills' list in tool-skills config"
                return skills

        pytest.fail("Could not find 'tool-skills' module in tools section")

    def test_our_skills_listed_first(self):
        """Our bundle (microsoft/amplifier-bundle-superpowers) must be listed first.

        First-match-wins priority means our skill sources take precedence over
        obra's when both bundles define a skill with the same name.
        """
        skills_config = self._get_skills_config()

        assert len(skills_config) >= 2, (
            f"Expected at least 2 skill sources, found {len(skills_config)}: {skills_config}"
        )

        assert "microsoft/amplifier-bundle-superpowers" in skills_config[0], (
            f"Expected our bundle (microsoft/amplifier-bundle-superpowers) to be listed first, "
            f"but first entry is: {skills_config[0]}"
        )

        assert "obra/superpowers" in skills_config[1], (
            f"Expected obra/superpowers to be listed second, "
            f"but second entry is: {skills_config[1]}"
        )


class TestSkillCount:
    """Tests that only the expected skill directories remain after removing obra duplicates."""

    EXPECTED_SKILLS = {"integration-testing-discipline", "superpowers-reference"}
    REMOVED_SKILLS = {
        "systematic-debugging",
        "verification-before-completion",
        "finishing-a-development-branch",
        "code-review-reception",
        "parallel-agent-dispatch",
    }

    def test_only_two_skills_remain(self):
        """Only integration-testing-discipline and superpowers-reference should exist."""
        skill_dirs = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
        assert skill_dirs == self.EXPECTED_SKILLS

    def test_removed_skills_not_present(self):
        """Each of the 5 removed skill directories must not exist."""
        for skill in self.REMOVED_SKILLS:
            assert not (SKILLS_DIR / skill).exists(), (
                f"Expected skill '{skill}' to be removed but it still exists"
            )


class TestSharedAntiRationalization:
    """Tests for the shared anti-rationalization context file."""

    SHARED_FILE = REPO_ROOT / "context" / "shared-anti-rationalization.md"

    def test_file_exists(self):
        """The shared anti-rationalization context file must exist."""
        assert self.SHARED_FILE.exists(), (
            f"Expected shared anti-rationalization file at {self.SHARED_FILE}"
        )

    def test_has_spirit_vs_letter(self):
        """File must contain 'spirit' and 'letter' keywords."""
        content = self.SHARED_FILE.read_text()
        assert "spirit" in content, (
            "Expected 'spirit' in shared-anti-rationalization.md"
        )
        assert "letter" in content, (
            "Expected 'letter' in shared-anti-rationalization.md"
        )

    def test_has_yagni(self):
        """File must contain 'YAGNI' keyword."""
        content = self.SHARED_FILE.read_text()
        assert "YAGNI" in content, "Expected 'YAGNI' in shared-anti-rationalization.md"

    def test_has_false_completion(self):
        """File must contain 'complete' (case-insensitive)."""
        content = self.SHARED_FILE.read_text()
        assert "complete" in content.lower(), (
            "Expected 'complete' (case-insensitive) in shared-anti-rationalization.md"
        )


class TestContextFileUpdates:
    """Tests that context files reflect the simplified skill strategy."""

    PHILOSOPHY_FILE = REPO_ROOT / "context" / "philosophy.md"
    INSTRUCTIONS_FILE = REPO_ROOT / "context" / "instructions.md"

    def test_philosophy_has_spirit_vs_letter(self):
        """philosophy.md must contain 'spirit' and 'letter' keywords."""
        content = self.PHILOSOPHY_FILE.read_text()
        assert "spirit" in content.lower(), "Expected 'spirit' in context/philosophy.md"
        assert "letter" in content.lower(), "Expected 'letter' in context/philosophy.md"

    def test_instructions_no_removed_skill_references(self):
        """instructions.md must not reference removed skills."""
        content = self.INSTRUCTIONS_FILE.read_text()
        assert 'skill_name="code-review-reception"' not in content, (
            'Expected skill_name="code-review-reception" to be removed from context/instructions.md'
        )
        assert 'skill_name="parallel-agent-dispatch"' not in content, (
            'Expected skill_name="parallel-agent-dispatch" to be removed from context/instructions.md'
        )


class TestSuperpowersReferenceSkill:
    """Tests for the superpowers-reference skill content."""

    SKILL_FILE = REPO_ROOT / 'skills' / 'superpowers-reference' / 'SKILL.md'
    REMOVED_SKILLS = [
        "systematic-debugging",
        "verification-before-completion",
        "finishing-a-development-branch",
        "code-review-reception",
        "dispatching-parallel-agents",
    ]

    def test_skill_exists(self):
        """The superpowers-reference SKILL.md must exist."""
        assert self.SKILL_FILE.exists(), (
            f"Expected superpowers-reference SKILL.md at {self.SKILL_FILE}"
        )

    def test_no_removed_skill_references(self):
        """No line should reference removed skills without noting they're from obra or removed."""
        content = self.SKILL_FILE.read_text()
        for skill_name in self.REMOVED_SKILLS:
            for line in content.splitlines():
                if skill_name in line:
                    line_lower = line.lower()
                    assert "obra" in line_lower or "removed" in line_lower, (
                        f"Line references removed skill '{skill_name}' without 'obra' or 'removed': {line!r}"
                    )
