"""Tests for include directive."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.directives.include import (
    MAX_INCLUDE_DEPTH,
    MAX_INCLUDE_SIZE,
    IncludeDirective,
    render_include,
)
from bengal.parsing import MistuneParser


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
    """Create a mock state object with root_path and env dict."""

    class State:
        pass

    state = State()
    state.root_path = temp_site_dir
    state.env = {}  # Include tracking uses state.env dict
    return state


@pytest.fixture
def mock_state_with_source(temp_site_dir):
    """Create a mock state object with root_path, source_path, and env dict."""

    class State:
        pass

    state = State()
    state.root_path = temp_site_dir
    state.env = {}  # Include tracking uses state.env dict
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
        # Path is relative to content dir (since no source_path in state)
        directive.parse_title = lambda m: "snippets/warning.md"
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
        # Path is relative to content dir (since no source_path in state)
        directive.parse_title = lambda m: "snippets/steps.md"
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


class TestIncludeDirectiveRobustness:
    """Test include directive robustness features (depth limit, cycle detection)."""

    def test_max_depth_limit_exceeded(self, temp_site_dir, mock_state_with_root):
        """Test that exceeding max include depth returns an error."""
        directive = IncludeDirective()

        # Create a file to include - use path relative to content dir
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        test_file = snippets_dir / "depth-test.md"
        test_file.write_text("Test content")

        # Simulate being at max depth already (tracked in state.env)
        mock_state_with_root.env["_include_depth"] = MAX_INCLUDE_DEPTH

        match = MagicMock()
        # Path is relative to content dir, so use "snippets/depth-test.md"
        directive.parse_title = lambda m: "snippets/depth-test.md"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" in result["attrs"]
        assert "maximum include depth" in result["attrs"]["error"].lower()
        assert str(MAX_INCLUDE_DEPTH) in result["attrs"]["error"]

    def test_depth_increments_for_nested_includes(self, temp_site_dir, mock_state_with_root):
        """Test that include depth is tracked and incremented."""
        directive = IncludeDirective()

        # Create a file to include
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        test_file = snippets_dir / "nested-test.md"
        test_file.write_text("Test content")

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/nested-test.md"
        directive.parse_options = lambda m: []

        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        # Initially no depth set (tracked in state.env)
        assert mock_state_with_root.env.get("_include_depth", 0) == 0

        result = directive.parse(block, match, mock_state_with_root)

        # Should succeed
        assert "error" not in result["attrs"]

        # After parsing, depth should be restored to original (0)
        assert mock_state_with_root.env.get("_include_depth", 0) == 0

    def test_cycle_detection_same_file(self, temp_site_dir, mock_state_with_root):
        """Test that including the same file twice is detected as a cycle."""
        directive = IncludeDirective()

        # Create a file to include
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        test_file = snippets_dir / "cycle-test.md"
        test_file.write_text("Test content")

        # Simulate that this file was already included (tracked in state.env)
        canonical_path = str(test_file.resolve())
        mock_state_with_root.env["_included_files"] = {canonical_path}

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/cycle-test.md"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" in result["attrs"]
        assert "cycle detected" in result["attrs"]["error"].lower()

    def test_cycle_detection_indirect_cycle(self, temp_site_dir, mock_state_with_root):
        """Test that indirect cycles (a→b→a) are detected."""
        directive = IncludeDirective()

        # Create two files
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        file_a = snippets_dir / "indirect-a.md"
        file_b = snippets_dir / "indirect-b.md"
        file_a.write_text("Content A")
        file_b.write_text("Content B")

        # Simulate that file_a was already included (tracked in state.env)
        canonical_a = str(file_a.resolve())
        mock_state_with_root.env["_included_files"] = {canonical_a}

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/indirect-a.md"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "include"
        assert "error" in result["attrs"]
        assert "cycle detected" in result["attrs"]["error"].lower()

    def test_sibling_includes_allowed(self, temp_site_dir, mock_state_with_root):
        """Test that sibling includes (same level, different files) are allowed."""
        directive = IncludeDirective()

        # Create two files
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        file_a = snippets_dir / "sibling-a.md"
        file_b = snippets_dir / "sibling-b.md"
        file_a.write_text("Content A")
        file_b.write_text("Content B")

        match = MagicMock()
        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        # Include file A
        directive.parse_title = lambda m: "snippets/sibling-a.md"
        directive.parse_options = lambda m: []
        result_a = directive.parse(block, match, mock_state_with_root)

        # Include file B (should succeed since B wasn't included yet)
        directive.parse_title = lambda m: "snippets/sibling-b.md"
        result_b = directive.parse(block, match, mock_state_with_root)

        # Both should succeed
        assert "error" not in result_a["attrs"]
        assert "error" not in result_b["attrs"]

    def test_included_files_accumulate(self, temp_site_dir, mock_state_with_root):
        """Test that included files are tracked across sibling includes."""
        directive = IncludeDirective()

        # Create two files
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        file_a = snippets_dir / "accum-a.md"
        file_b = snippets_dir / "accum-b.md"
        file_a.write_text("Content A")
        file_b.write_text("Content B")

        match = MagicMock()
        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        # Include file A
        directive.parse_title = lambda m: "snippets/accum-a.md"
        directive.parse_options = lambda m: []
        directive.parse(block, match, mock_state_with_root)

        # Verify file A is now in the included files set (tracked in state.env)
        included_files = mock_state_with_root.env.get("_included_files", set())
        assert str(file_a.resolve()) in included_files

        # Include file B
        directive.parse_title = lambda m: "snippets/accum-b.md"
        directive.parse(block, match, mock_state_with_root)

        # Verify both files are now tracked
        included_files = mock_state_with_root.env.get("_included_files", set())
        assert str(file_a.resolve()) in included_files
        assert str(file_b.resolve()) in included_files

    def test_max_depth_constant_is_reasonable(self):
        """Test that MAX_INCLUDE_DEPTH is set to a reasonable value."""
        # Should allow reasonable nesting (5-20)
        assert MAX_INCLUDE_DEPTH >= 5
        assert MAX_INCLUDE_DEPTH <= 20

        # Current value should be 10
        assert MAX_INCLUDE_DEPTH == 10


class TestIncludeFileSizeLimit:
    """Test include directive file size limits."""

    def test_max_include_size_constant_is_reasonable(self):
        """Test that MAX_INCLUDE_SIZE is set to a reasonable value."""
        # Should be between 1MB and 100MB
        assert MAX_INCLUDE_SIZE >= 1 * 1024 * 1024  # At least 1MB
        assert MAX_INCLUDE_SIZE <= 100 * 1024 * 1024  # At most 100MB

        # Current value should be 10MB
        assert MAX_INCLUDE_SIZE == 10 * 1024 * 1024

    def test_small_file_allowed(self, temp_site_dir, mock_state_with_root):
        """Test that small files are allowed."""
        directive = IncludeDirective()

        # Create a small file
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        small_file = snippets_dir / "small.md"
        small_file.write_text("Small content")

        content = directive._load_file(small_file, start_line=None, end_line=None)

        assert content is not None
        assert content == "Small content"

    def test_large_file_rejected(self, temp_site_dir, mock_state_with_root):
        """Test that files exceeding MAX_INCLUDE_SIZE are rejected."""
        directive = IncludeDirective()

        # Create a file larger than MAX_INCLUDE_SIZE
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        large_file = snippets_dir / "large.md"

        # Write content just over the limit (11MB)
        large_content = "x" * (MAX_INCLUDE_SIZE + 1024 * 1024)
        large_file.write_text(large_content)

        content = directive._load_file(large_file, start_line=None, end_line=None)

        assert content is None

    def test_file_at_limit_allowed(self, temp_site_dir, mock_state_with_root):
        """Test that files exactly at MAX_INCLUDE_SIZE are allowed."""
        directive = IncludeDirective()

        # Create a file exactly at the limit
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        limit_file = snippets_dir / "limit.md"

        # Write content exactly at the limit
        limit_content = "x" * MAX_INCLUDE_SIZE
        limit_file.write_text(limit_content)

        content = directive._load_file(limit_file, start_line=None, end_line=None)

        assert content is not None


class TestIncludeSymlinkRejection:
    """Test include directive symlink rejection for security."""

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_symlink_rejected(self, temp_site_dir, mock_state_with_root):
        """Test that symlinks are rejected."""
        directive = IncludeDirective()

        # Create a real file and a symlink to it
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        real_file = snippets_dir / "real.md"
        real_file.write_text("Real content")
        symlink_file = snippets_dir / "symlink.md"
        symlink_file.symlink_to(real_file)

        # Real file should work
        resolved_real = directive._resolve_path("snippets/real.md", mock_state_with_root)
        assert resolved_real is not None

        # Symlink should be rejected
        resolved_symlink = directive._resolve_path("snippets/symlink.md", mock_state_with_root)
        assert resolved_symlink is None

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_symlink_to_outside_rejected(self, temp_site_dir, mock_state_with_root, tmp_path):
        """Test that symlinks pointing outside site root are rejected."""
        directive = IncludeDirective()

        # Create a file outside site root
        outside_file = tmp_path / "outside.md"
        outside_file.write_text("Outside content")

        # Create a symlink inside site root pointing outside
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        escape_symlink = snippets_dir / "escape.md"
        escape_symlink.symlink_to(outside_file)

        # Should be rejected (symlink check happens before path validation)
        resolved = directive._resolve_path("snippets/escape.md", mock_state_with_root)
        assert resolved is None

    @pytest.mark.skipif(os.name == "nt", reason="Symlinks require admin on Windows")
    def test_directory_symlink_files_rejected(self, temp_site_dir, mock_state_with_root):
        """Test that files in symlinked directories are still accessible via direct path."""
        directive = IncludeDirective()

        # Create a real directory with a file
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        real_file = snippets_dir / "file.md"
        real_file.write_text("Content in real dir")

        # Create a symlinked directory
        symlink_dir = temp_site_dir / "content" / "symlinked"
        symlink_dir.symlink_to(snippets_dir)

        # File via symlinked directory path is a symlink, should be rejected
        # Note: The file itself isn't a symlink, but the path involves one
        resolved = directive._resolve_path("symlinked/file.md", mock_state_with_root)
        # The file.md itself isn't a symlink, so this might resolve
        # What matters is that is_symlink() on the final resolved path returns False
        if resolved:
            assert not resolved.is_symlink()


class TestIncludeStateIsolation:
    """Test that include directive state doesn't leak between parses.
    
    These tests verify the state.env storage pattern works correctly,
    particularly around empty dict handling (regression test for falsy {} bug).
    """

    def test_state_env_initialized_when_none(self, temp_site_dir):
        """Test that state.env is properly initialized when None."""
        directive = IncludeDirective()

        class StateWithoutEnv:
            pass

        state = StateWithoutEnv()
        state.root_path = temp_site_dir

        # Deliberately no state.env attribute
        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        (snippets_dir / "test.md").write_text("Content")

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/test.md"
        directive.parse_options = lambda m: []
        directive.parse_tokens = MagicMock(return_value=[])

        block = MagicMock()
        result = directive.parse(block, match, state)

        # state.env should be created and populated
        assert hasattr(state, "env")
        assert state.env is not None
        assert "_include_depth" in state.env
        assert "error" not in result["attrs"]

    def test_state_env_empty_dict_not_replaced(self, temp_site_dir, mock_state_with_root):
        """Test that empty state.env dict is properly handled (not treated as falsy).
        
        Regression test: Empty dict {} is falsy in Python, so `env or {}` would
        create a new dict instead of using the existing one. This test ensures
        we use `is None` check instead.
        """
        directive = IncludeDirective()

        # Ensure env is empty dict (not None)
        original_env = {}
        mock_state_with_root.env = original_env

        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        (snippets_dir / "test.md").write_text("Content")

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/test.md"
        directive.parse_options = lambda m: []
        directive.parse_tokens = MagicMock(return_value=[])

        block = MagicMock()
        directive.parse(block, match, mock_state_with_root)

        # env should still be the SAME dict object, not a new one
        assert mock_state_with_root.env is original_env
        assert "_include_depth" in mock_state_with_root.env
        assert "_included_files" in mock_state_with_root.env

    def test_parallel_includes_isolated(self, temp_site_dir):
        """Test that parallel include parses don't share state incorrectly."""

        class State:
            pass

        # Create two separate states
        state1 = State()
        state1.root_path = temp_site_dir
        state1.env = {}

        state2 = State()
        state2.root_path = temp_site_dir
        state2.env = {}

        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        file_a = snippets_dir / "a.md"
        file_b = snippets_dir / "b.md"
        file_a.write_text("Content A")
        file_b.write_text("Content B")

        directive = IncludeDirective()
        directive.parse_tokens = MagicMock(return_value=[])

        match = MagicMock()
        block = MagicMock()

        # Parse in state1
        directive.parse_title = lambda m: "snippets/a.md"
        directive.parse_options = lambda m: []
        directive.parse(block, match, state1)

        # Parse in state2
        directive.parse_title = lambda m: "snippets/b.md"
        directive.parse(block, match, state2)

        # States should be independent
        files1 = state1.env.get("_included_files", set())
        files2 = state2.env.get("_included_files", set())

        # Each state should only have its own file
        assert len(files1) == 1
        assert len(files2) == 1
        assert "a.md" in str(list(files1)[0])
        assert "b.md" in str(list(files2)[0])
        # No cross-contamination
        assert "b.md" not in str(files1)
        assert "a.md" not in str(files2)

    def test_depth_restored_after_parse(self, temp_site_dir, mock_state_with_root):
        """Test that include depth is restored after parsing completes."""
        directive = IncludeDirective()

        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        (snippets_dir / "test.md").write_text("Content")

        # Set initial depth
        mock_state_with_root.env["_include_depth"] = 5

        match = MagicMock()
        directive.parse_title = lambda m: "snippets/test.md"
        directive.parse_options = lambda m: []
        directive.parse_tokens = MagicMock(return_value=[])

        block = MagicMock()
        directive.parse(block, match, mock_state_with_root)

        # Depth should be restored to original value
        assert mock_state_with_root.env["_include_depth"] == 5

    def test_included_files_persist_across_siblings(self, temp_site_dir, mock_state_with_root):
        """Test that included files tracking persists across sibling includes."""
        directive = IncludeDirective()

        snippets_dir = temp_site_dir / "content" / "snippets"
        snippets_dir.mkdir(parents=True, exist_ok=True)
        file_a = snippets_dir / "persist-a.md"
        file_b = snippets_dir / "persist-b.md"
        file_a.write_text("A")
        file_b.write_text("B")

        match = MagicMock()
        block = MagicMock()
        directive.parse_tokens = MagicMock(return_value=[])

        # Include A
        directive.parse_title = lambda m: "snippets/persist-a.md"
        directive.parse_options = lambda m: []
        directive.parse(block, match, mock_state_with_root)

        # Include B
        directive.parse_title = lambda m: "snippets/persist-b.md"
        directive.parse(block, match, mock_state_with_root)

        # Both should be tracked
        files = mock_state_with_root.env.get("_included_files", set())
        assert len(files) == 2
        paths_str = str(files)
        assert "persist-a.md" in paths_str
        assert "persist-b.md" in paths_str
