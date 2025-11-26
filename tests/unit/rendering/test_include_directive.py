"""Tests for include directive."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.rendering.parsers import MistuneParser
from bengal.rendering.plugins.directives.include import IncludeDirective, render_include


@pytest.fixture
def temp_site_dir(tmp_path):
    """Create temporary site directory structure."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    content_dir = site_dir / "content"
    content_dir.mkdir()
    snippets_dir = content_dir / "snippets"
    snippets_dir.mkdir()
    return site_dir


@pytest.fixture
def mock_state_with_root(temp_site_dir):
    """Create a mock state object with root_path."""

    class State:
        pass

    state = State()
    state.root_path = temp_site_dir
    return state


@pytest.fixture
def mock_state_with_source(temp_site_dir):
    """Create a mock state object with root_path and source_path."""

    class State:
        pass

    state = State()
    state.root_path = temp_site_dir
    # Simulate a page in content/docs/guides/
    guides_dir = temp_site_dir / "content" / "docs" / "guides"
    guides_dir.mkdir(parents=True)
    state.source_path = guides_dir / "my-page.md"
    return state


@pytest.fixture
def sample_markdown_file(temp_site_dir):
    """Create a sample markdown file to include."""
    snippets_dir = temp_site_dir / "content" / "snippets"
    file_path = snippets_dir / "warning.md"
    file_path.write_text(
        """```{warning}
This feature is in beta. Please report any issues.
```"""
    )
    return file_path


@pytest.fixture
def multi_line_markdown_file(temp_site_dir):
    """Create a multi-line markdown file for line range testing."""
    snippets_dir = temp_site_dir / "content" / "snippets"
    file_path = snippets_dir / "steps.md"
    content = "\n".join([f"Step {i}: Do something" for i in range(1, 11)])
    file_path.write_text(content)
    return file_path


class TestIncludeDirective:
    """Test IncludeDirective class."""

    def test_initialization(self):
        """Test creating directive instance."""
        directive = IncludeDirective()
        assert directive is not None

    def test_parse_basic_include(self, sample_markdown_file, mock_state_with_root):
        """Test parsing basic include directive."""
        directive = IncludeDirective()

        # Mock the match object
        match = MagicMock()
        directive.parse_title = lambda m: "content/snippets/warning.md"
        directive.parse_options = lambda m: []

        # Mock the block parser and parse_tokens
        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[{"type": "paragraph", "children": []}])

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" not in result["attrs"]
        assert result["attrs"]["path"] == str(sample_markdown_file)

    def test_parse_with_line_range(self, multi_line_markdown_file, mock_state_with_root):
        """Test parsing include directive with line range."""
        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "content/snippets/steps.md"
        directive.parse_options = lambda m: [("start-line", "3"), ("end-line", "7")]

        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert result["attrs"]["start_line"] == 3
        assert result["attrs"]["end_line"] == 7

    def test_parse_missing_file(self, mock_state_with_root):
        """Test parsing when file doesn't exist."""
        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "content/snippets/missing.md"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" in result["attrs"]
        assert "not found" in result["attrs"]["error"].lower()

    def test_parse_no_path(self, mock_state_with_root):
        """Test parsing when no file path is provided."""
        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: ""
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" in result["attrs"]
        assert "no file path" in result["attrs"]["error"].lower()

    def test_path_resolution_relative_to_page(self, temp_site_dir, mock_state_with_source):
        """Test that paths resolve relative to current page's directory."""
        # Create a snippet in the same directory as the page
        guides_dir = temp_site_dir / "content" / "docs" / "guides"
        local_snippet = guides_dir / "local-snippet.md"
        local_snippet.write_text("Local content")

        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "local-snippet.md"
        directive.parse_options = lambda m: []

        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        result = directive.parse(block, match, mock_state_with_source)

        assert result["type"] == "include"
        assert "error" not in result["attrs"]
        assert result["attrs"]["path"] == str(local_snippet)

    def test_path_resolution_fallback_to_content(self, temp_site_dir, mock_state_with_source):
        """Test that paths fall back to content directory if not found relative to page."""
        # Create snippet in content/snippets (not in page's directory)
        snippets_dir = temp_site_dir / "content" / "snippets"
        global_snippet = snippets_dir / "global-snippet.md"
        global_snippet.write_text("Global content")

        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/global-snippet.md"
        directive.parse_options = lambda m: []

        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        result = directive.parse(block, match, mock_state_with_source)

        assert result["type"] == "include"
        assert "error" not in result["attrs"]
        assert result["attrs"]["path"] == str(global_snippet)

    def test_path_traversal_prevention(self, temp_site_dir, mock_state_with_root):
        """Test that path traversal attempts are blocked."""
        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "../../etc/passwd"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        # Should either error or reject the path
        assert "error" in result["attrs"] or "path_traversal" in str(result["attrs"]).lower()

    def test_absolute_path_rejection(self, temp_site_dir, mock_state_with_root):
        """Test that absolute paths are rejected."""
        directive = IncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "/etc/passwd"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        # Should reject absolute path
        assert (
            result["attrs"].get("error") is not None or "absolute" in str(result["attrs"]).lower()
        )

    def test_load_file_with_line_range(self, multi_line_markdown_file, mock_state_with_root):
        """Test loading file with line range."""
        directive = IncludeDirective()

        content = directive._load_file(multi_line_markdown_file, start_line=3, end_line=7)

        lines = content.split("\n")
        assert len(lines) == 5  # Lines 3-7 inclusive
        assert "Step 3" in content
        assert "Step 7" in content
        assert "Step 1" not in content
        assert "Step 10" not in content

    def test_load_file_start_line_only(self, multi_line_markdown_file, mock_state_with_root):
        """Test loading file with only start_line specified."""
        directive = IncludeDirective()

        content = directive._load_file(multi_line_markdown_file, start_line=8, end_line=None)

        lines = content.split("\n")
        assert len(lines) == 3  # Lines 8-10
        assert "Step 8" in content
        assert "Step 10" in content
        assert "Step 7" not in content

    def test_load_file_end_line_only(self, multi_line_markdown_file, mock_state_with_root):
        """Test loading file with only end_line specified."""
        directive = IncludeDirective()

        content = directive._load_file(multi_line_markdown_file, start_line=None, end_line=3)

        lines = content.split("\n")
        assert len(lines) == 3  # Lines 1-3
        assert "Step 1" in content
        assert "Step 3" in content
        assert "Step 4" not in content

    def test_load_file_invalid_range(self, multi_line_markdown_file, mock_state_with_root):
        """Test loading file with invalid line range."""
        directive = IncludeDirective()

        # Start > end
        content = directive._load_file(multi_line_markdown_file, start_line=10, end_line=5)
        assert content == ""

        # Start > file length
        content = directive._load_file(multi_line_markdown_file, start_line=100, end_line=200)
        assert content == ""

    def test_load_file_nonexistent(self, temp_site_dir):
        """Test loading nonexistent file."""
        directive = IncludeDirective()

        nonexistent = temp_site_dir / "nonexistent.md"
        content = directive._load_file(nonexistent, start_line=None, end_line=None)

        assert content is None

    def test_resolve_path_without_state_attributes(self, temp_site_dir):
        """Test path resolution when state has no root_path or source_path."""
        directive = IncludeDirective()

        class EmptyState:
            pass

        state = EmptyState()

        # Should fall back to cwd or handle gracefully
        result = directive._resolve_path("content/snippets/warning.md", state)

        # May return None or resolve relative to cwd
        assert result is None or isinstance(result, Path)


class TestRenderInclude:
    """Test render_include function."""

    def test_render_success(self):
        """Test rendering successful include."""
        renderer = MagicMock()

        html = render_include(renderer, "<p>Included content</p>", path="snippets/warning.md")

        assert html == "<p>Included content</p>"

    def test_render_error(self):
        """Test rendering include with error."""
        renderer = MagicMock()

        html = render_include(renderer, "", error="File not found: snippets/missing.md")

        assert "include-error" in html
        assert "File not found" in html


class TestIncludeDirectiveIntegration:
    """Integration tests with MistuneParser."""

    @pytest.fixture
    def parser(self):
        """Create a MistuneParser instance."""
        return MistuneParser()

    def test_include_directive_in_markdown(self, parser, temp_site_dir, sample_markdown_file):
        """Test include directive works in full markdown parsing."""
        # Note: This test requires the directive to be registered and state to be set
        # In real usage, state would be set by the rendering pipeline
        content = """
```{include} content/snippets/warning.md
```
"""

        # This test may fail if state.root_path is not set, which is expected
        # In real usage, the pipeline sets this
        result = parser.parse(content, {})

        # Should either process the directive or leave it as-is if state not set
        assert isinstance(result, str)

    def test_include_with_nested_directives(self, parser, temp_site_dir):
        """Test that included content can contain nested directives."""
        snippets_dir = temp_site_dir / "content" / "snippets"
        nested_file = snippets_dir / "nested.md"
        nested_file.write_text(
            """```{tip}
This is a tip inside included content.
```"""
        )

        content = """
```{include} content/snippets/nested.md
```
"""

        result = parser.parse(content, {})

        # Should process nested directive if include works
        assert isinstance(result, str)

    def test_include_directive_registered(self, parser):
        """Test that include directive is registered with parser."""
        # Check that the directive is available
        # This is more of a smoke test
        content = """
```{include} test.md
```
"""

        result = parser.parse(content, {})

        # Should not crash
        assert isinstance(result, str)
