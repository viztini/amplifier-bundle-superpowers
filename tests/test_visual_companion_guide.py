"""Tests for context/visual-companion-guide.md.

Verifies that the visual companion guide:
1. Exists at the expected path
2. Contains all required sections (~15+ headings)
3. Uses Amplifier-specific patterns (bash tool, @superpowers: paths)
4. Includes all spec-required content
"""

import os
import re

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
GUIDE_PATH = os.path.join(REPO_ROOT, "context", "visual-companion-guide.md")


@pytest.fixture(scope="module")
def guide_content():
    assert os.path.isfile(GUIDE_PATH), (
        f"visual-companion-guide.md does not exist at {GUIDE_PATH}"
    )
    with open(GUIDE_PATH) as f:
        return f.read()


class TestVisualCompanionGuideExists:
    def test_file_exists(self):
        assert os.path.isfile(GUIDE_PATH), (
            "visual-companion-guide.md must exist at context/visual-companion-guide.md"
        )


class TestVisualCompanionGuideSections:
    """Tests that all required sections are present and the section count is ~15+."""

    @pytest.fixture(autouse=True)
    def load(self, guide_content):
        self.content = guide_content

    def _headings(self):
        """Return all markdown headings (## and ###)."""
        return re.findall(r"^#{1,3} .+$", self.content, re.MULTILINE)

    def test_minimum_section_count(self):
        headings = self._headings()
        assert len(headings) >= 15, (
            f"Expected ~15+ headings, got {len(headings)}: {headings}"
        )

    def test_has_when_to_use_section(self):
        assert "When to Use" in self.content

    def test_has_supplementary_visual_tools_section(self):
        assert "Supplementary Visual Tools" in self.content

    def test_has_how_it_works_section(self):
        assert "How It Works" in self.content

    def test_has_prerequisites_section(self):
        assert "Prerequisites" in self.content

    def test_has_starting_a_session_section(self):
        assert "Starting a Session" in self.content

    def test_has_the_loop_section(self):
        assert "The Loop" in self.content

    def test_has_writing_content_fragments_section(self):
        assert "Writing Content Fragments" in self.content

    def test_has_css_classes_section(self):
        assert "CSS Classes" in self.content

    def test_has_browser_events_format_section(self):
        assert "Browser Events" in self.content

    def test_has_cleaning_up_section(self):
        assert "Cleaning Up" in self.content

    def test_has_file_naming_section(self):
        assert "File Naming" in self.content

    def test_has_reference_section(self):
        assert "Reference" in self.content


class TestVisualCompanionGuideAmplifierPatterns:
    """Tests that the guide uses Amplifier-specific patterns, not platform-specific ones."""

    @pytest.fixture(autouse=True)
    def load(self, guide_content):
        self.content = guide_content

    def test_uses_bash_tool_run_in_background(self):
        """Starting a Session must use bash tool with run_in_background."""
        assert "run_in_background" in self.content, (
            "Guide must use Amplifier bash tool run_in_background=true syntax"
        )

    def test_uses_superpowers_bundle_paths(self):
        """Reference section must use @superpowers: bundle path format."""
        assert "@superpowers:" in self.content, (
            "Guide must reference files using @superpowers: bundle path format"
        )

    def test_mentions_nano_banana(self):
        """Supplementary Visual Tools section must mention nano-banana."""
        assert "nano-banana" in self.content, (
            "Guide must mention nano-banana as a supplementary visual tool"
        )

    def test_mentions_dot_graph(self):
        """Supplementary Visual Tools section must mention dot_graph."""
        assert "dot_graph" in self.content, (
            "Guide must mention dot_graph as a supplementary visual tool"
        )


class TestVisualCompanionGuideContent:
    """Tests that key content details are present."""

    @pytest.fixture(autouse=True)
    def load(self, guide_content):
        self.content = guide_content

    def test_when_to_use_mentions_browser_for_visual(self):
        """When to Use must state: visual content -> browser."""
        # Check that it mentions browser for visual content
        assert "browser" in self.content.lower()

    def test_when_to_use_mentions_terminal_for_text(self):
        """When to Use must state: text/tabular -> terminal."""
        assert "terminal" in self.content.lower()

    def test_starting_session_mentions_server_info(self):
        """Starting a Session must show how to read server-info JSON."""
        assert "server-info" in self.content

    def test_starting_session_mentions_project_dir(self):
        """Starting a Session must mention --project-dir for persistence."""
        assert "--project-dir" in self.content

    def test_starting_session_mentions_gitignore(self):
        """Starting a Session must remind about .superpowers/ gitignore."""
        assert ".superpowers/" in self.content and "gitignore" in self.content.lower()

    def test_starting_session_mentions_host_option(self):
        """Starting a Session must mention --host 0.0.0.0 for remote/containerized."""
        assert "--host 0.0.0.0" in self.content

    def test_the_loop_has_six_steps(self):
        """The Loop section must describe a 6-step cycle."""
        # Look for "6." or step 6 in numbered list near The Loop section
        loop_section_match = re.search(
            r"## The Loop(.*?)(?=^##|\Z)", self.content, re.MULTILINE | re.DOTALL
        )
        assert loop_section_match, "The Loop section not found"
        loop_content = loop_section_match.group(1)
        # Should have steps numbered 1 through 6
        assert re.search(r"^6\.", loop_content, re.MULTILINE), (
            "The Loop section must have at least 6 numbered steps"
        )

    def test_prerequisites_mentions_nodejs(self):
        """Prerequisites section must mention Node.js."""
        prereq_match = re.search(
            r"## Prerequisites(.*?)(?=^##|\Z)", self.content, re.MULTILINE | re.DOTALL
        )
        assert prereq_match, "Prerequisites section not found"
        prereq_content = prereq_match.group(1)
        assert "node" in prereq_content.lower() or "Node" in prereq_content, (
            "Prerequisites must mention Node.js"
        )

    def test_writing_fragments_has_minimal_example(self):
        """Writing Content Fragments must have a minimal HTML example."""
        assert '<div class="options">' in self.content or "options" in self.content

    def test_css_classes_mentions_options(self):
        """CSS Classes section must mention options class."""
        assert "options" in self.content

    def test_css_classes_mentions_multi_select(self):
        """CSS Classes section must mention multi-select."""
        assert (
            "multi-select" in self.content.lower()
            or "multiselect" in self.content.lower()
            or "data-multiselect" in self.content
        )

    def test_css_classes_mentions_cards(self):
        """CSS Classes section must mention cards."""
        assert "cards" in self.content

    def test_css_classes_mentions_mockup_container(self):
        """CSS Classes section must mention mockup container."""
        assert "mockup" in self.content

    def test_css_classes_mentions_split_view(self):
        """CSS Classes section must mention split view."""
        assert "split" in self.content

    def test_css_classes_mentions_pros_cons(self):
        """CSS Classes section must mention pros/cons."""
        assert "pros" in self.content.lower() and "cons" in self.content.lower()

    def test_css_classes_mentions_mock_elements(self):
        """CSS Classes section must mention mock elements."""
        assert "mock-" in self.content

    def test_css_classes_mentions_typography(self):
        """CSS Classes section must mention typography/sections."""
        assert "subtitle" in self.content or "typography" in self.content.lower()

    def test_browser_events_has_jsonl_example(self):
        """Browser Events section must show JSONL click event format."""
        assert '"type":"click"' in self.content or '"type": "click"' in self.content

    def test_reference_section_has_frame_template(self):
        """Reference section must mention frame-template."""
        assert "frame-template" in self.content

    def test_reference_section_has_helper_script(self):
        """Reference section must mention helper script."""
        assert "helper" in self.content.lower()
