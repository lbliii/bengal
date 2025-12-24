"""
Unit tests for CSS State Machine Tabs (Document Application RFC Phase 5).

Tests the native :target-based tabs including:
- HTML structure correctness
- ARIA attributes
- URL fragment generation
- Mode switching between enhanced and css_state_machine
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bengal.directives.tabs import TabSetDirective


class TestTabSetNativeMode:
    """Tests for CSS state machine tabs rendering."""

    def _create_mock_renderer(self, tabs_mode: str = "css_state_machine"):
        """Create a mock renderer with site config."""
        renderer = MagicMock()
        renderer._site = MagicMock()
        renderer._site.config = {
            "document_application": {
                "interactivity": {
                    "tabs": tabs_mode,
                }
            }
        }
        return renderer

    def test_native_mode_uses_nav_role(self):
        """Native mode should use nav element with role='tablist'."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        # Mock tab item HTML
        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Python content</div>
<div class="tab-item" data-title="JavaScript" data-selected="false" data-icon="" data-badge="" data-disabled="false">JS content</div>"""

        html = directive.render(renderer, text, id="test-tabs", sync="", mode="css_state_machine")

        assert 'class="tabs tabs--native"' in html
        assert 'role="tablist"' in html
        assert 'role="tab"' in html
        assert 'role="tabpanel"' in html

    def test_native_mode_uses_href_fragments(self):
        """Native mode should use href fragments instead of data-tab-target."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Python content</div>"""

        html = directive.render(renderer, text, id="code", sync="", mode="css_state_machine")

        assert 'href="#code-python"' in html
        assert "data-tab-target" not in html

    def test_native_mode_generates_readable_slugs(self):
        """Native mode should generate readable URL slugs from titles."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        text = """<div class="tab-item" data-title="C Sharp Code" data-selected="false" data-icon="" data-badge="" data-disabled="false">C# content</div>"""

        html = directive.render(renderer, text, id="example", sync="", mode="css_state_machine")

        assert 'href="#example-c-sharp-code"' in html
        assert 'id="example-c-sharp-code"' in html

    def test_native_mode_includes_aria_controls(self):
        """Native mode should include aria-controls pointing to pane ID."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Content</div>"""

        html = directive.render(renderer, text, id="test", sync="", mode="css_state_machine")

        assert 'aria-controls="test-python"' in html

    def test_native_mode_pane_uses_section(self):
        """Native mode should use section element for tab panes."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Content</div>"""

        html = directive.render(renderer, text, id="test", sync="", mode="css_state_machine")

        assert '<section id="test-python"' in html
        assert 'role="tabpanel"' in html

    def test_enhanced_mode_uses_data_tab_target(self):
        """Enhanced mode should use data-tab-target (backward compatible)."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("enhanced")

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Content</div>"""

        html = directive.render(renderer, text, id="test", sync="", mode="enhanced")

        assert 'data-tab-target="test-0"' in html
        assert 'data-bengal="tabs"' in html
        assert 'href="#test-python"' not in html

    def test_mode_from_config(self):
        """Mode should be read from site config if not specified."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Content</div>"""

        # Don't pass mode - should use config
        html = directive.render(renderer, text, id="test", sync="", mode="")

        assert 'class="tabs tabs--native"' in html

    def test_explicit_mode_overrides_config(self):
        """Explicit mode attribute should override config."""
        directive = TabSetDirective()
        renderer = self._create_mock_renderer("css_state_machine")  # Config says native

        text = """<div class="tab-item" data-title="Python" data-selected="false" data-icon="" data-badge="" data-disabled="false">Content</div>"""

        # Explicitly request enhanced mode
        html = directive.render(renderer, text, id="test", sync="", mode="enhanced")

        assert 'data-bengal="tabs"' in html
        assert 'class="tabs tabs--native"' not in html


class TestTabSetSlugify:
    """Tests for slug generation."""

    def test_slugify_basic(self):
        """Basic text should be lowercased and hyphenated."""
        directive = TabSetDirective()

        assert directive._slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        """Special characters should be removed."""
        directive = TabSetDirective()

        assert directive._slugify("C++ Code") == "c-code"
        assert directive._slugify("Python (3.x)") == "python-3x"

    def test_slugify_multiple_spaces(self):
        """Multiple spaces should become single hyphen."""
        directive = TabSetDirective()

        assert directive._slugify("Tab   With   Spaces") == "tab-with-spaces"

    def test_slugify_empty(self):
        """Empty string should return 'tab'."""
        directive = TabSetDirective()

        assert directive._slugify("") == "tab"
        assert directive._slugify("   ") == "tab"
