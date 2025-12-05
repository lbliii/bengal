"""Tests for glossary directive."""


from unittest.mock import MagicMock

import pytest
import yaml

from bengal.rendering.plugins.directives.glossary import (
    GlossaryDirective,
    render_glossary,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directory for test data files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def glossary_file(temp_data_dir):
    """Create a sample glossary YAML file."""
    data = {
        "terms": [
            {
                "term": "Directive",
                "definition": "Extended markdown syntax that creates rich components.",
                "tags": ["directives", "core"],
            },
            {
                "term": "Admonition",
                "definition": "A styled callout box for important information.",
                "tags": ["directives", "admonitions"],
            },
            {
                "term": "Card Grid",
                "definition": "A container for responsive card layouts.",
                "tags": ["directives", "layout"],
            },
            {
                "term": "Badge",
                "definition": "A small styled label for tags or status.",
                "tags": ["directives", "formatting"],
            },
            {
                "term": "Object Tree",
                "definition": "Bengal's hierarchical site structure.",
                "tags": ["directives", "navigation", "architecture"],
            },
        ]
    }

    file_path = temp_data_dir / "glossary.yaml"
    with open(file_path, "w") as f:
        yaml.dump(data, f)

    return file_path


@pytest.fixture
def mock_state(temp_data_dir):
    """Create a mock state object with root_path."""

    class State:
        pass

    state = State()
    state.root_path = temp_data_dir.parent
    return state


class TestGlossaryDirective:
    """Test GlossaryDirective class."""

    def test_initialization(self):
        """Test creating directive instance."""
        directive = GlossaryDirective()
        assert directive is not None

    def test_parse_with_tags_filter(self, glossary_file, mock_state):
        """Test parsing glossary stores tags for deferred loading."""
        directive = GlossaryDirective()

        # Mock the match object
        match = MagicMock()
        match.group.return_value = ""

        # Override parse_options to return tags
        directive.parse_options = MagicMock(return_value=[("tags", "admonitions")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        # Parse phase now defers data loading - verify options are stored
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["tags"] == ["admonitions"]

    def test_parse_with_multiple_tags(self, glossary_file, mock_state):
        """Test parsing with multiple tags stores them for deferred loading."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        # Filter by both admonitions and layout tags
        directive.parse_options = MagicMock(return_value=[("tags", "admonitions, layout")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        # Parse phase now defers data loading - verify tags are stored
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["tags"] == ["admonitions", "layout"]

    def test_parse_with_core_tag_matches_multiple(self, glossary_file, mock_state):
        """Test that 'core' tag is stored for deferred loading."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "core")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        # Parse phase now defers data loading - verify tag is stored
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["tags"] == ["core"]

    def test_parse_sorted_option(self, glossary_file, mock_state):
        """Test sorted option is stored for deferred sorting."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        # Get all directives terms, sorted
        directive.parse_options = MagicMock(
            return_value=[("tags", "directives"), ("sorted", "true")]
        )

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        # Parse phase now defers data loading - verify sorted flag is stored
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["sorted"] is True
        assert result["attrs"]["tags"] == ["directives"]

    def test_parse_no_tags_error(self, glossary_file, mock_state):
        """Test error when no tags specified."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" in result["attrs"]
        assert "No tags specified" in result["attrs"]["error"]

    def test_parse_no_matching_terms(self, glossary_file, mock_state):
        """Test parse stores nonexistent tags (error surfaces in render phase)."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "nonexistent")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        # Parse phase doesn't validate tags - it defers to render
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["tags"] == ["nonexistent"]

    def test_parse_missing_file(self, mock_state):
        """Test parse stores options (file errors surface in render phase)."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "test")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        # Parse phase doesn't validate files - it defers to render
        assert result["attrs"]["_deferred"] is True
        assert result["attrs"]["tags"] == ["test"]

    def test_parse_collapsed_option(self, glossary_file, mock_state):
        """Test parsing collapsed option."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "core"), ("collapsed", "true")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert result["attrs"]["collapsed"] is True

    def test_parse_limit_option(self, glossary_file, mock_state):
        """Test parsing limit option."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "directives"), ("limit", "3")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert result["attrs"]["limit"] == 3

    def test_parse_limit_invalid_returns_zero(self, glossary_file, mock_state):
        """Test that invalid limit value defaults to 0 (show all)."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "core"), ("limit", "invalid")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert result["attrs"]["limit"] == 0  # Default to show all


class TestGlossaryRenderer:
    """Test glossary HTML rendering."""

    def test_render_basic(self):
        """Test basic glossary rendering."""
        attrs = {
            "terms": [
                {
                    "term": "Directive",
                    "definition": "Extended markdown syntax.",
                    "tags": ["core"],
                }
            ],
            "tags": ["core"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        assert '<dl class="bengal-glossary">' in html
        assert "<dt>Directive</dt>" in html
        assert "<dd>Extended markdown syntax.</dd>" in html
        assert "</dl>" in html

    def test_render_multiple_terms(self):
        """Test rendering multiple terms."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["a"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["b"]},
            ],
            "tags": ["a", "b"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        assert "<dt>Term A</dt>" in html
        assert "<dt>Term B</dt>" in html
        assert "<dd>Definition A</dd>" in html
        assert "<dd>Definition B</dd>" in html

    def test_render_with_tags_shown(self):
        """Test rendering with tag badges."""
        attrs = {
            "terms": [{"term": "Test", "definition": "A test term.", "tags": ["foo", "bar"]}],
            "tags": ["foo"],
            "show_tags": True,
        }

        html = render_glossary(None, "", **attrs)

        assert "bengal-glossary-tag" in html
        assert ">foo<" in html
        assert ">bar<" in html

    def test_render_error(self):
        """Test error rendering."""
        attrs = {
            "error": "Test error message",
            "path": "data/glossary.yaml",
        }

        html = render_glossary(None, "", **attrs)

        assert "bengal-glossary-error" in html
        assert "Test error message" in html
        assert "data/glossary.yaml" in html

    def test_render_escapes_html(self):
        """Test that HTML in definitions is escaped."""
        attrs = {
            "terms": [
                {
                    "term": "<script>",
                    "definition": "<b>Bold</b> & special",
                    "tags": ["test"],
                }
            ],
            "tags": ["test"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        # HTML should be escaped
        assert "&lt;script&gt;" in html
        assert "&lt;b&gt;Bold&lt;/b&gt;" in html
        assert "&amp; special" in html

    def test_render_collapsed_option(self):
        """Test rendering with collapsed option wraps in details element."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["a"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["b"]},
            ],
            "tags": ["a", "b"],
            "show_tags": False,
            "collapsed": True,
        }

        html = render_glossary(None, "", **attrs)

        # Should be wrapped in details/summary
        assert '<details class="bengal-glossary-collapsed">' in html
        assert "<summary>Key Terms (2)</summary>" in html
        assert "</details>" in html
        # Content should still be inside
        assert "<dt>Term A</dt>" in html
        assert "<dt>Term B</dt>" in html

    def test_render_limit_option(self):
        """Test rendering with limit shows only first N terms."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["test"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["test"]},
                {"term": "Term C", "definition": "Definition C", "tags": ["test"]},
                {"term": "Term D", "definition": "Definition D", "tags": ["test"]},
                {"term": "Term E", "definition": "Definition E", "tags": ["test"]},
            ],
            "tags": ["test"],
            "show_tags": False,
            "limit": 2,
        }

        html = render_glossary(None, "", **attrs)

        # First 2 terms should be visible
        assert "<dt>Term A</dt>" in html
        assert "<dt>Term B</dt>" in html

        # Remaining 3 should be in expandable section
        assert '<details class="bengal-glossary-more">' in html
        assert "<summary>Show 3 more terms</summary>" in html
        assert "<dt>Term C</dt>" in html
        assert "<dt>Term D</dt>" in html
        assert "<dt>Term E</dt>" in html

    def test_render_limit_singular_term(self):
        """Test limit with exactly 1 remaining term uses singular."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["test"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["test"]},
            ],
            "tags": ["test"],
            "show_tags": False,
            "limit": 1,
        }

        html = render_glossary(None, "", **attrs)

        # Should use singular "term" not "terms"
        assert "<summary>Show 1 more term</summary>" in html

    def test_render_limit_greater_than_count_shows_all(self):
        """Test limit greater than term count shows all terms."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["test"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["test"]},
            ],
            "tags": ["test"],
            "show_tags": False,
            "limit": 10,  # Greater than actual count
        }

        html = render_glossary(None, "", **attrs)

        # Should show all terms, no expandable section
        assert "<dt>Term A</dt>" in html
        assert "<dt>Term B</dt>" in html
        assert "bengal-glossary-more" not in html
        assert "Show" not in html

    def test_render_collapsed_and_limit_combined(self):
        """Test both collapsed and limit options together."""
        attrs = {
            "terms": [
                {"term": "Term A", "definition": "Definition A", "tags": ["test"]},
                {"term": "Term B", "definition": "Definition B", "tags": ["test"]},
                {"term": "Term C", "definition": "Definition C", "tags": ["test"]},
            ],
            "tags": ["test"],
            "show_tags": False,
            "collapsed": True,
            "limit": 1,
        }

        html = render_glossary(None, "", **attrs)

        # Outer wrapper should be collapsed
        assert '<details class="bengal-glossary-collapsed">' in html
        assert "<summary>Key Terms (3)</summary>" in html

        # Inner limit expansion should also exist
        assert '<details class="bengal-glossary-more">' in html
        assert "<summary>Show 2 more terms</summary>" in html

    def test_render_inline_markdown_backticks(self):
        """Test that backticks in definitions render as code."""
        attrs = {
            "terms": [
                {
                    "term": "Directive",
                    "definition": "Use `{note}` syntax for admonitions.",
                    "tags": ["test"],
                }
            ],
            "tags": ["test"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        # Backticks should become <code> tags
        assert "<code>{note}</code>" in html

    def test_render_inline_markdown_bold(self):
        """Test that **bold** in definitions renders as strong."""
        attrs = {
            "terms": [
                {
                    "term": "Test",
                    "definition": "This is **important** text.",
                    "tags": ["test"],
                }
            ],
            "tags": ["test"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        # Bold should become <strong> tags
        assert "<strong>important</strong>" in html

    def test_render_inline_markdown_italic(self):
        """Test that *italic* in definitions renders as em."""
        attrs = {
            "terms": [
                {
                    "term": "Test",
                    "definition": "This is *emphasized* text.",
                    "tags": ["test"],
                }
            ],
            "tags": ["test"],
            "show_tags": False,
        }

        html = render_glossary(None, "", **attrs)

        # Italic should become <em> tags
        assert "<em>emphasized</em>" in html

    def test_render_deferred_no_matching_terms(self, temp_data_dir, glossary_file):
        """Test deferred render error when no terms match tags."""
        # Create mock renderer with _site attribute
        mock_renderer = MagicMock()
        mock_site = MagicMock()
        mock_site.root_path = temp_data_dir.parent
        mock_site.data = None  # Force file-based loading
        mock_renderer._site = mock_site

        attrs = {
            "_deferred": True,
            "tags": ["nonexistent"],
            "sorted": False,
            "show_tags": False,
            "collapsed": False,
            "limit": 0,
            "source": "data/glossary.yaml",
        }

        html = render_glossary(mock_renderer, "", **attrs)

        assert "bengal-glossary-error" in html
        assert "No terms found" in html

    def test_render_deferred_missing_file(self, temp_data_dir):
        """Test deferred render error when glossary file not found."""
        # Create mock renderer with _site attribute
        mock_renderer = MagicMock()
        mock_site = MagicMock()
        mock_site.root_path = temp_data_dir.parent
        mock_site.data = None  # Force file-based loading
        mock_renderer._site = mock_site

        attrs = {
            "_deferred": True,
            "tags": ["test"],
            "sorted": False,
            "show_tags": False,
            "collapsed": False,
            "limit": 0,
            "source": "data/nonexistent.yaml",
        }

        html = render_glossary(mock_renderer, "", **attrs)

        assert "bengal-glossary-error" in html
        assert "not found" in html

    def test_render_deferred_with_filtering(self, temp_data_dir, glossary_file):
        """Test deferred render correctly filters terms by tags."""
        # Create mock renderer with _site attribute
        mock_renderer = MagicMock()
        mock_site = MagicMock()
        mock_site.root_path = temp_data_dir.parent
        mock_site.data = None  # Force file-based loading
        mock_renderer._site = mock_site

        attrs = {
            "_deferred": True,
            "tags": ["admonitions"],
            "sorted": False,
            "show_tags": False,
            "collapsed": False,
            "limit": 0,
            "source": "data/glossary.yaml",
        }

        html = render_glossary(mock_renderer, "", **attrs)

        # Should only include Admonition term (the only one with 'admonitions' tag)
        assert "<dt>Admonition</dt>" in html
        assert "<dd>" in html
        # Should NOT include other terms
        assert "<dt>Card Grid</dt>" not in html

    def test_render_deferred_sorted(self, temp_data_dir, glossary_file):
        """Test deferred render correctly sorts terms alphabetically."""
        # Create mock renderer with _site attribute
        mock_renderer = MagicMock()
        mock_site = MagicMock()
        mock_site.root_path = temp_data_dir.parent
        mock_site.data = None  # Force file-based loading
        mock_renderer._site = mock_site

        attrs = {
            "_deferred": True,
            "tags": ["directives"],  # All terms have this tag
            "sorted": True,
            "show_tags": False,
            "collapsed": False,
            "limit": 0,
            "source": "data/glossary.yaml",
        }

        html = render_glossary(mock_renderer, "", **attrs)

        # All 5 terms should be present and alphabetically sorted
        # Find the order of dt tags in the HTML
        import re

        dt_matches = re.findall(r"<dt>([^<]+)</dt>", html)
        assert dt_matches == sorted(dt_matches, key=str.lower)
