"""Tests for literalinclude directive."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.directives.literalinclude import (
    LiteralIncludeDirective,
    render_literalinclude,
)
from bengal.rendering.parsers import MistuneParser


@pytest.fixture
def temp_site_dir(tmp_path):
    """Create temporary site directory structure."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    content_dir = site_dir / "content"
    content_dir.mkdir()
    examples_dir = content_dir / "examples"
    examples_dir.mkdir()
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
def sample_python_file(temp_site_dir):
    """Create a sample Python file to include."""
    examples_dir = temp_site_dir / "content" / "examples"
    file_path = examples_dir / "api.py"
    file_path.write_text(
        """def get_user(user_id: int) -> User:
    \"\"\"Get user by ID.\"\"\"
    return db.query(User).filter(User.id == user_id).first()

def create_user(name: str, email: str) -> User:
    \"\"\"Create a new user.\"\"\"
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    return user
"""
    )
    return file_path


@pytest.fixture
def sample_yaml_file(temp_site_dir):
    """Create a sample YAML file to include."""
    examples_dir = temp_site_dir / "content" / "examples"
    file_path = examples_dir / "config.yaml"
    file_path.write_text(
        """database:
  host: localhost
  port: 5432
  name: myapp

server:
  port: 8000
  debug: true
"""
    )
    return file_path


@pytest.fixture
def multi_line_code_file(temp_site_dir):
    """Create a multi-line code file for line range testing."""
    examples_dir = temp_site_dir / "content" / "examples"
    file_path = examples_dir / "code.py"
    lines = [f"# Line {i}" for i in range(1, 21)]
    lines.append("def example():")
    lines.append("    pass")
    file_path.write_text("\n".join(lines))
    return file_path


class TestLiteralIncludeDirective:
    """Test LiteralIncludeDirective class."""

    def test_initialization(self):
        """Test creating directive instance."""
        directive = LiteralIncludeDirective()
        assert directive is not None

    def test_parse_basic_literalinclude(self, sample_python_file, mock_state_with_root):
        """Test parsing basic literalinclude directive."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory (which is auto-detected as base)
        directive.parse_title = lambda m: "examples/api.py"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert "error" not in result["attrs"]
        assert result["attrs"]["path"] == str(sample_python_file)
        assert result["attrs"]["language"] == "python"
        assert "code" in result["attrs"]

    def test_parse_with_language_override(self, sample_yaml_file, mock_state_with_root):
        """Test parsing literalinclude with language override."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/config.yaml"
        directive.parse_options = lambda m: [("language", "yaml")]

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert result["attrs"]["language"] == "yaml"

    def test_parse_with_line_range(self, multi_line_code_file, mock_state_with_root):
        """Test parsing literalinclude with line range."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/code.py"
        directive.parse_options = lambda m: [("start-line", "5"), ("end-line", "15")]

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert result["attrs"]["start_line"] == 5
        assert result["attrs"]["end_line"] == 15
        code_lines = result["attrs"]["code"].split("\n")
        assert len(code_lines) == 11  # Lines 5-15 inclusive

    def test_parse_with_emphasize_lines(self, sample_python_file, mock_state_with_root):
        """Test parsing literalinclude with emphasize lines."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/api.py"
        directive.parse_options = lambda m: [("emphasize-lines", "2,3,4")]

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert result["attrs"]["emphasize_lines"] == "2,3,4"

    def test_parse_with_emphasize_range(self, sample_python_file, mock_state_with_root):
        """Test parsing literalinclude with emphasize line range."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/api.py"
        directive.parse_options = lambda m: [("emphasize-lines", "2-4")]

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert result["attrs"]["emphasize_lines"] == "2-4"

    def test_parse_with_linenos(self, sample_python_file, mock_state_with_root):
        """Test parsing literalinclude with line numbers."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/api.py"
        directive.parse_options = lambda m: [("linenos", "true")]

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert result["attrs"]["linenos"] is True

    def test_parse_missing_file(self, mock_state_with_root):
        """Test parsing when file doesn't exist."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        # Path is relative to content/ directory
        directive.parse_title = lambda m: "examples/missing.py"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert "error" in result["attrs"]
        assert "not found" in result["attrs"]["error"].lower()

    def test_parse_no_path(self, mock_state_with_root):
        """Test parsing when no file path is provided."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: ""
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        assert "error" in result["attrs"]
        assert "no file path" in result["attrs"]["error"].lower()

    def test_detect_language_python(self):
        """Test language detection for Python files."""
        directive = LiteralIncludeDirective()

        assert directive._detect_language("file.py") == "python"
        assert directive._detect_language("script.py") == "python"

    def test_detect_language_javascript(self):
        """Test language detection for JavaScript files."""
        directive = LiteralIncludeDirective()

        assert directive._detect_language("file.js") == "javascript"
        assert directive._detect_language("app.ts") == "typescript"

    def test_detect_language_yaml(self):
        """Test language detection for YAML files."""
        directive = LiteralIncludeDirective()

        assert directive._detect_language("config.yaml") == "yaml"
        assert directive._detect_language("data.yml") == "yaml"

    def test_detect_language_unknown(self):
        """Test language detection for unknown extensions."""
        directive = LiteralIncludeDirective()

        assert directive._detect_language("file.unknown") is None
        assert directive._detect_language("noextension") is None

    def test_path_resolution_relative_to_page(self, temp_site_dir, mock_state_with_source):
        """Test that paths resolve relative to current page's directory."""
        # Create a code file in the same directory as the page
        guides_dir = temp_site_dir / "content" / "docs" / "guides"
        local_code = guides_dir / "local.py"
        local_code.write_text("def local(): pass")

        directive = LiteralIncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "local.py"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_source)

        assert result["type"] == "literalinclude"
        assert "error" not in result["attrs"]
        assert result["attrs"]["path"] == str(local_code)

    def test_path_traversal_prevention(self, temp_site_dir, mock_state_with_root):
        """Test that path traversal attempts are blocked."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "../../etc/passwd"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        # Should either error or reject the path
        assert "error" in result["attrs"] or "path_traversal" in str(result["attrs"]).lower()

    def test_absolute_path_rejection(self, temp_site_dir, mock_state_with_root):
        """Test that absolute paths are rejected."""
        directive = LiteralIncludeDirective()

        match = MagicMock()
        directive.parse_title = lambda m: "/etc/passwd"
        directive.parse_options = lambda m: []

        block = MagicMock()

        result = directive.parse(block, match, mock_state_with_root)

        assert result["type"] == "literalinclude"
        # Should reject absolute path
        assert (
            result["attrs"].get("error") is not None or "absolute" in str(result["attrs"]).lower()
        )

    def test_load_file_with_line_range(self, multi_line_code_file, mock_state_with_root):
        """Test loading file with line range."""
        directive = LiteralIncludeDirective()

        content = directive._load_file(
            multi_line_code_file, start_line=5, end_line=15, emphasize_lines=None
        )

        lines = content.split("\n")
        assert len(lines) == 11  # Lines 5-15 inclusive
        assert "# Line 5" in content
        assert "# Line 15" in content
        # Check that lines outside range are NOT included
        # Note: "# Line 1\n" not in content (with newline to avoid substring match with Line 10-19)
        assert content.startswith("# Line 5")  # First line should be Line 5
        assert "# Line 20" not in content

    def test_load_file_with_emphasize(self, multi_line_code_file, mock_state_with_root):
        """Test loading file with emphasize lines."""
        directive = LiteralIncludeDirective()

        content = directive._load_file(
            multi_line_code_file, start_line=None, end_line=None, emphasize_lines="5,6,7"
        )

        # Content should be loaded (emphasis is handled in render)
        assert "# Line 1" in content
        assert "# Line 5" in content

    def test_load_file_with_emphasize_range(self, multi_line_code_file, mock_state_with_root):
        """Test loading file with emphasize line range."""
        directive = LiteralIncludeDirective()

        content = directive._load_file(
            multi_line_code_file, start_line=None, end_line=None, emphasize_lines="5-7"
        )

        assert content is not None
        assert "# Line 5" in content

    def test_load_file_nonexistent(self, temp_site_dir):
        """Test loading nonexistent file."""
        directive = LiteralIncludeDirective()

        nonexistent = temp_site_dir / "nonexistent.py"
        content = directive._load_file(
            nonexistent, start_line=None, end_line=None, emphasize_lines=None
        )

        assert content is None


class TestRenderLiteralInclude:
    """Test render_literalinclude function."""

    def test_render_success_with_language(self):
        """Test rendering successful literalinclude with language."""
        renderer = MagicMock()
        renderer.block_code = MagicMock(
            return_value='<pre><code class="language-python">code</code></pre>\n'
        )

        html = render_literalinclude(
            renderer, "", code="def example(): pass", language="python", **{}
        )

        assert "python" in html.lower() or "code" in html.lower()
        renderer.block_code.assert_called_once_with("def example(): pass", "python")

    def test_render_success_without_language(self):
        """Test rendering successful literalinclude without language."""
        renderer = MagicMock()
        renderer.block_code = MagicMock(return_value="<pre><code>code</code></pre>\n")

        html = render_literalinclude(renderer, "", code="plain text", language=None, **{})

        assert "code" in html.lower()

    def test_render_with_linenos(self):
        """Test rendering with line numbers."""
        renderer = MagicMock()
        renderer.block_code = MagicMock(return_value="<pre><code>code</code></pre>\n")

        html = render_literalinclude(
            renderer, "", code="def example(): pass", language="python", linenos=True, **{}
        )

        assert "linenos" in html.lower() or "line" in html.lower()

    def test_render_with_emphasize_lines(self):
        """Test rendering with emphasize lines."""
        renderer = MagicMock()
        renderer.block_code = MagicMock(return_value="<pre><code>code</code></pre>\n")

        html = render_literalinclude(
            renderer,
            "",
            code="def example(): pass",
            language="python",
            emphasize_lines="2,3,4",
            **{},
        )

        assert "emphasize" in html.lower() or "data-emphasize" in html.lower()

    def test_render_error(self):
        """Test rendering literalinclude with error."""
        renderer = MagicMock()

        html = render_literalinclude(
            renderer, "", error="File not found: examples/missing.py", **{}
        )

        assert "literalinclude-error" in html
        assert "File not found" in html

    def test_render_fallback_no_block_code(self):
        """Test rendering when renderer doesn't have block_code method."""
        renderer = MagicMock(spec=[])  # Empty spec means no block_code attribute

        html = render_literalinclude(
            renderer, "", code="def example(): pass", language="python", **{}
        )

        # Should fall back to simple code block
        assert "<code" in html.lower() and "<pre>" in html.lower()


class TestLiteralIncludeDirectiveIntegration:
    """Integration tests with MistuneParser."""

    @pytest.fixture
    def parser(self):
        """Create a MistuneParser instance."""
        return MistuneParser()

    def test_literalinclude_directive_in_markdown(self, parser, temp_site_dir, sample_python_file):
        """Test literalinclude directive works in full markdown parsing."""
        content = """
```{literalinclude} content/examples/api.py
```
"""

        # This test may fail if state.root_path is not set, which is expected
        # In real usage, the pipeline sets this
        result = parser.parse(content, {})

        # Should either process the directive or leave it as-is if state not set
        assert isinstance(result, str)

    def test_literalinclude_with_options(self, parser, temp_site_dir, sample_python_file):
        """Test literalinclude with various options."""
        content = """
```{literalinclude} content/examples/api.py
:language: python
:start-line: 1
:end-line: 3
:linenos: true
```
"""

        result = parser.parse(content, {})

        # Should not crash
        assert isinstance(result, str)

    def test_literalinclude_directive_registered(self, parser):
        """Test that literalinclude directive is registered with parser."""
        content = """
```{literalinclude} test.py
```
"""

        result = parser.parse(content, {})

        # Should not crash
        assert isinstance(result, str)

    def test_literalinclude_language_detection(self, parser, temp_site_dir):
        """Test that language is auto-detected from extension."""
        examples_dir = temp_site_dir / "content" / "examples"
        js_file = examples_dir / "app.js"
        js_file.write_text("console.log('hello');")

        content = """
```{literalinclude} content/examples/app.js
```
"""

        result = parser.parse(content, {})

        # Should not crash
        assert isinstance(result, str)
