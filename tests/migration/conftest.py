"""Test fixtures for directive migration parity testing.

Provides:
- HTML normalization for comparison
- Golden file support
- Parser creation for both backends
- Pytest hooks for --update-golden-files

See RFC: plan/drafted/rfc-patitas-bengal-directive-migration.md
"""

from __future__ import annotations

import html.parser
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# Directory containing golden (expected) HTML files
GOLDEN_DIR = Path(__file__).parent / "golden_files"


# =============================================================================
# Pytest Hooks
# =============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden-files option to pytest."""
    parser.addoption(
        "--update-golden-files",
        action="store_true",
        default=False,
        help="Update golden files with current Patitas output",
    )


@pytest.fixture
def update_golden_files(request: pytest.FixtureRequest) -> bool:
    """Return True if golden files should be updated."""
    return bool(request.config.getoption("--update-golden-files"))


@pytest.fixture
def golden_file_path(request: pytest.FixtureRequest) -> Path:
    """Return path for golden file based on test name."""
    test_name = request.node.name
    # Handle parametrized tests: test_html_parity[note_basic] -> note_basic
    if "[" in test_name:
        param_name = test_name.split("[")[1].rstrip("]")
        return GOLDEN_DIR / f"{param_name}.html"
    return GOLDEN_DIR / f"{test_name}.html"


# =============================================================================
# HTML Normalization
# =============================================================================


class _HtmlNormalizer(html.parser.HTMLParser):
    """HTML parser that normalizes whitespace and attribute order.
    
    Used to compare HTML output while ignoring:
    - Whitespace differences (leading/trailing/multiple spaces)
    - Attribute order differences
    - Self-closing tag variations (</br> vs <br /> vs <br>)
        
    """

    def __init__(self) -> None:
        super().__init__()
        self._output: list[str] = []
        self._in_pre = False
        self._pre_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle opening tag, normalizing attributes."""
        # Track pre/code for whitespace preservation
        if tag in ("pre", "code"):
            self._pre_depth += 1
            self._in_pre = True

        # Sort attributes alphabetically for consistent comparison
        sorted_attrs = sorted(attrs, key=lambda x: x[0])
        attr_str = ""
        for name, value in sorted_attrs:
            if value is None:
                attr_str += f" {name}"
            else:
                # Normalize attribute value quoting
                escaped_value = value.replace('"', "&quot;")
                attr_str += f' {name}="{escaped_value}"'

        self._output.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tag."""
        if tag in ("pre", "code"):
            self._pre_depth -= 1
            if self._pre_depth == 0:
                self._in_pre = False
        self._output.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle self-closing tag (e.g., <br />, <hr />)."""
        sorted_attrs = sorted(attrs, key=lambda x: x[0])
        attr_str = ""
        for name, value in sorted_attrs:
            if value is None:
                attr_str += f" {name}"
            else:
                escaped_value = value.replace('"', "&quot;")
                attr_str += f' {name}="{escaped_value}"'

        self._output.append(f"<{tag}{attr_str} />")

    def handle_data(self, data: str) -> None:
        """Handle text content."""
        if self._in_pre:
            # Preserve whitespace in pre/code blocks
            self._output.append(data)
        else:
            # Normalize whitespace outside pre/code
            normalized = " ".join(data.split())
            if normalized:
                self._output.append(normalized)

    def handle_entityref(self, name: str) -> None:
        """Handle named entity (e.g., &amp;)."""
        self._output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """Handle numeric character reference (e.g., &#x27;)."""
        self._output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        """Handle HTML comments."""
        self._output.append(f"<!--{data}-->")

    def get_normalized(self) -> str:
        """Get normalized HTML output."""
        return "".join(self._output)


def normalize_html(html_content: str) -> str:
    """Normalize HTML for comparison.
    
    Normalizes:
    - Whitespace (leading/trailing, multiple spaces collapsed)
    - Attribute order (sorted alphabetically)
    - Self-closing tags (standardized to <tag />)
    - Blank lines removed
    
    Preserves:
    - Whitespace inside pre/code blocks
    - HTML entities
    - Semantic structure
    
    Args:
        html_content: Raw HTML string
    
    Returns:
        Normalized HTML string for comparison
        
    """
    if not html_content:
        return ""

    # First pass: Remove blank lines and strip line-level whitespace
    lines = []
    for line in html_content.split("\n"):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    html_content = "\n".join(lines)

    # Second pass: Parse and normalize using HTML parser
    try:
        normalizer = _HtmlNormalizer()
        normalizer.feed(html_content)
        return normalizer.get_normalized()
    except Exception:
        # Fallback: simple regex-based normalization
        # Collapse multiple whitespace
        normalized = re.sub(r"\s+", " ", html_content)
        # Normalize self-closing tags
        normalized = re.sub(r"<(\w+)([^>]*)\s*/>", r"<\1\2 />", normalized)
        return normalized.strip()


# =============================================================================
# Parser Fixtures
# =============================================================================


@pytest.fixture
def render_with_mistune() -> Callable[[str], str]:
    """Create a function to render markdown using the mistune backend.
    
    Returns:
        Function that takes markdown source and returns HTML
        
    """
    from bengal.rendering.parsers.mistune import MistuneParser

    parser = MistuneParser(enable_highlighting=False)

    def _render(source: str) -> str:
        return parser.parse(source, {})

    return _render


@pytest.fixture
def render_with_patitas() -> Callable[[str], str]:
    """Create a function to render markdown using the Patitas backend.
    
    Returns:
        Function that takes markdown source and returns HTML
        
    """
    from bengal.rendering.parsers.patitas import create_markdown
    from bengal.rendering.parsers.patitas.directives.registry import create_default_registry

    # Get registry with all Phase A directives
    registry = create_default_registry()

    # Create markdown instance with directives enabled
    md = create_markdown(
        plugins=["table", "strikethrough", "task_lists", "math"],
        highlight=False,
    )

    def _render(source: str) -> str:
        # Parse to AST
        ast = md.parse_to_ast(source)

        # Render with directive registry (via ContextVar config)
        from bengal.rendering.parsers.patitas import (
            RenderConfig,
            render_config_context,
        )
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

        with render_config_context(RenderConfig(highlight=False, directive_registry=registry)):
            renderer = HtmlRenderer(source)
            return renderer.render(ast)

    return _render


# =============================================================================
# Comparison Fixtures
# =============================================================================


@pytest.fixture
def assert_html_equal() -> Callable[[str, str, str], None]:
    """Create assertion function for HTML equality.
    
    Returns:
        Function that asserts two HTML strings are semantically equal
        
    """

    def _assert(actual: str, expected: str, context: str = "") -> None:
        actual_normalized = normalize_html(actual)
        expected_normalized = normalize_html(expected)

        if actual_normalized != expected_normalized:
            # Provide detailed diff on failure
            msg = f"HTML mismatch{f' ({context})' if context else ''}\n"
            msg += f"\n--- Expected (normalized) ---\n{expected_normalized}\n"
            msg += f"\n--- Actual (normalized) ---\n{actual_normalized}\n"
            msg += f"\n--- Expected (raw) ---\n{expected}\n"
            msg += f"\n--- Actual (raw) ---\n{actual}\n"
            pytest.fail(msg)

    return _assert


@pytest.fixture
def compare_backends(
    render_with_mistune: Callable[[str], str],
    render_with_patitas: Callable[[str], str],
    assert_html_equal: Callable[[str, str, str], None],
) -> Callable[[str, str], None]:
    """Create function to compare output from both backends.
    
    Returns:
        Function that takes test name and source, compares backends
        
    """

    def _compare(name: str, source: str) -> None:
        mistune_html = render_with_mistune(source)
        patitas_html = render_with_patitas(source)
        assert_html_equal(patitas_html, mistune_html, f"test: {name}")

    return _compare


# =============================================================================
# Golden File Fixtures
# =============================================================================


@pytest.fixture
def save_golden_file() -> Callable[[Path, str], None]:
    """Create function to save golden file.
    
    Returns:
        Function that saves HTML content to golden file path
        
    """

    def _save(path: Path, html_content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_content)

    return _save


@pytest.fixture
def load_golden_file() -> Callable[[Path], str | None]:
    """Create function to load golden file.
    
    Returns:
        Function that loads HTML from golden file path, or None if not found
        
    """

    def _load(path: Path) -> str | None:
        if path.exists():
            return path.read_text()
        return None

    return _load
