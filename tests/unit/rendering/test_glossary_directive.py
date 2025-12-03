"""Tests for glossary directive."""

from __future__ import annotations

from pathlib import Path
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
        """Test parsing glossary with tag filter."""
        directive = GlossaryDirective()

        # Mock the match object
        match = MagicMock()
        match.group.return_value = ""

        # Override parse_options to return tags
        directive.parse_options = MagicMock(return_value=[("tags", "admonitions")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        assert len(result["attrs"]["terms"]) == 1
        assert result["attrs"]["terms"][0]["term"] == "Admonition"

    def test_parse_with_multiple_tags(self, glossary_file, mock_state):
        """Test filtering with multiple tags (OR logic)."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        # Filter by both admonitions and layout tags
        directive.parse_options = MagicMock(return_value=[("tags", "admonitions, layout")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        # Should match Admonition (admonitions) and Card Grid (layout)
        assert len(result["attrs"]["terms"]) == 2
        term_names = [t["term"] for t in result["attrs"]["terms"]]
        assert "Admonition" in term_names
        assert "Card Grid" in term_names

    def test_parse_with_core_tag_matches_multiple(self, glossary_file, mock_state):
        """Test that 'core' tag matches the Directive term."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "core")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" not in result["attrs"]
        assert len(result["attrs"]["terms"]) == 1
        assert result["attrs"]["terms"][0]["term"] == "Directive"

    def test_parse_sorted_option(self, glossary_file, mock_state):
        """Test sorted option orders terms alphabetically."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        # Get all directives terms, sorted
        directive.parse_options = MagicMock(
            return_value=[("tags", "directives"), ("sorted", "true")]
        )

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        terms = result["attrs"]["terms"]
        term_names = [t["term"] for t in terms]

        # Should be alphabetically sorted
        assert term_names == sorted(term_names, key=str.lower)

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
        """Test error when no terms match tags."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "nonexistent")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" in result["attrs"]
        assert "No terms found" in result["attrs"]["error"]

    def test_parse_missing_file(self, mock_state):
        """Test error when glossary file not found."""
        directive = GlossaryDirective()

        match = MagicMock()
        match.group.return_value = ""

        directive.parse_options = MagicMock(return_value=[("tags", "test")])

        result = directive.parse(MagicMock(), match, mock_state)

        assert result["type"] == "glossary"
        assert "error" in result["attrs"]
        assert "not found" in result["attrs"]["error"]


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
            "terms": [
                {"term": "Test", "definition": "A test term.", "tags": ["foo", "bar"]}
            ],
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

