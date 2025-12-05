# Bengal Testing Utilities

Shared fixtures, markers, mocks, and utilities for the Bengal test suite.

## Quick Start

### Using Test Roots with @pytest.mark.bengal

```python
@pytest.mark.bengal(testroot="test-basic")
def test_simple_site(site, build_site):
    """Test using the test-basic root."""
    build_site()
    assert len(site.pages) == 1
    assert (site.output_dir / "index.html").exists()
```

### Using site_factory Directly

```python
def test_custom_setup(site_factory):
    """Test with custom site creation."""
    site = site_factory("test-baseurl", confoverrides={"site.baseurl": "/custom"})
    assert site.config["site"]["baseurl"] == "/custom"
```

### Using Mock Objects

```python
from tests._testing.mocks import MockPage, MockSection, MockSite, create_mock_xref_index

def test_with_mocks():
    """Test using canonical mock objects."""
    page = MockPage(title="Test Page", url="/test/")
    section = MockSection(name="docs", title="Documentation")
    site = MockSite(pages=[page])
    xref_index = create_mock_xref_index([page])
```

### Using Module-Scoped Parser (Rendering Tests)

```python
# In tests/unit/rendering/
def test_markdown_parsing(parser):
    """Parser fixture is module-scoped for efficiency."""
    result = parser.parse("# Hello World", {})
    assert "<h1>Hello World</h1>" in result
```

### Testing CLI Commands

```python
from tests._testing.cli import run_cli

def test_build_command(tmp_path):
    """Test CLI build command."""
    result = run_cli(["site", "build"], cwd=tmp_path)
    result.assert_ok()
    result.assert_stdout_contains("Build complete")
```

## Modules

### `mocks.py`

Canonical mock objects for testing. **Use these instead of defining inline mocks**:

- `MockPage` - Mock page with common attributes (title, url, metadata, tags, etc.)
- `MockSection` - Mock section for navigation tests
- `MockSite` - Mock site for validator tests
- `create_mock_xref_index(pages)` - Build xref_index from mock pages
- `create_mock_page_hierarchy(structure)` - Generate hierarchies from dict spec

```python
from tests._testing.mocks import MockPage, MockSection, MockSite

# Simple page
page = MockPage(title="API Reference", url="/api/")

# Page with metadata
page = MockPage(
    title="Getting Started",
    url="/docs/quickstart/",
    metadata={"description": "Quick start guide"},
    tags=["tutorial", "beginner"]
)

# Section with pages
section = MockSection(name="docs", title="Documentation", pages=[page])

# Site with pages
site = MockSite(pages=[page])

# Build xref_index for cross-reference tests
from tests._testing.mocks import create_mock_xref_index
xref_index = create_mock_xref_index([page1, page2, page3])
```

### `fixtures.py`

Provides core fixtures:

- `rootdir` - Path to `tests/roots/` directory
- `site_factory(testroot, confoverrides)` - Factory to create Site from roots
- `build_site()` - Helper to build a site

### `markers.py`

Implements `@pytest.mark.bengal` marker and provides the `site` fixture:

- `@pytest.mark.bengal` - Marker for declarative test site setup
- `site` - Auto-injected fixture when using `@pytest.mark.bengal`

```python
@pytest.mark.bengal(testroot="test-basic")
@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.title": "Custom"})
```

### `cli.py`

CLI testing utilities:

- `run_cli(args, ...)` - Run bengal CLI command
- `CLIResult` - Result with `.assert_ok()`, `.assert_fail_with()`, etc.

### `normalize.py`

Output normalization for deterministic assertions:

- `normalize_html(html_str)` - Strip timestamps, hashes, paths
- `normalize_json(data)` - Normalize JSON (sort keys, strip volatile)
- `json_dumps_normalized(data)` - Dump normalized JSON

## Rendering Test Fixtures

The `tests/unit/rendering/conftest.py` provides module-scoped fixtures for efficient parsing tests:

- `parser` - Module-scoped MistuneParser (reused across tests in same module)
- `parser_with_site` - Parser with xref_index from test-directives root
- `mock_xref_index` - Empty xref_index for manual setup
- `reset_parser_state` (autouse) - Resets parser state between tests

```python
# Efficient: parser created once per module
def test_heading_parsing(parser):
    result = parser.parse("# Title", {})
    assert "<h1>Title</h1>" in result

# With pre-populated xref_index
def test_cross_references(parser_with_site):
    result = parser_with_site.parse("See [[cards]]", {})
    assert "/cards/" in result
```

## Test Roots

See `tests/roots/README.md` for available test roots.

Common roots:
- `test-basic` - Minimal 1-page site
- `test-baseurl` - Tests baseurl handling
- `test-taxonomy` - 3 pages with tags
- `test-templates` - Template example documentation
- `test-assets` - Custom + theme assets
- `test-directives` - Card, admonition, glossary directives
- `test-navigation` - Multi-level menu/nav hierarchy
- `test-large` - 100+ pages for performance testing

## Adding to conftest.py

To enable these utilities in your tests:

```python
# tests/conftest.py

# Register testing plugins
pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]
```

## Migration Guide

### Migrating from Inline MockPage Classes

**Before** (duplicated in each test file):
```python
class MockPage:
    def __init__(self, title, url, description="", icon="", tags=None):
        self.title = title
        self.url = url
        self.metadata = {"description": description, "icon": icon}
        self.tags = tags or []
        self.date = None
```

**After** (use canonical mock):
```python
from tests._testing.mocks import MockPage

page = MockPage(
    title="Test Page",
    url="/test/",
    metadata={"description": "desc", "icon": "home"},
    tags=["tag1", "tag2"]
)
```

### Migrating Parser Tests

**Before** (parser created in each test):
```python
def test_parsing(self):
    parser = MistuneParser()  # Created 100+ times!
    result = parser.parse(content, {})
```

**After** (use module-scoped fixture):
```python
def test_parsing(self, parser):  # Injected, reused
    result = parser.parse(content, {})
```

## Design Principles

1. **Ergonomic**: Tests should be easy to write and read
2. **Minimal**: Test roots are tiny and focused
3. **Reusable**: Share setup across many tests via mocks and fixtures
4. **Deterministic**: Normalize volatile output
5. **Fast**: Module-scoped fixtures avoid repeated expensive setup
6. **Canonical**: Use `_testing/mocks.py` instead of inline class definitions
