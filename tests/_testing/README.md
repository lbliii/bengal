# Bengal Testing Utilities

Shared fixtures, markers, and utilities for the Bengal test suite.

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

## Test Roots

See `tests/roots/README.md` for available test roots.

Common roots:
- `test-basic` - Minimal 1-page site
- `test-baseurl` - Tests baseurl handling
- `test-taxonomy` - 3 pages with tags
- `test-templates` - Template example documentation
- `test-assets` - Custom + theme assets

## Adding to conftest.py

To enable these utilities in your tests:

```python
# tests/conftest.py

# Register testing plugins
pytest_plugins = ["tests._testing.fixtures", "tests._testing.markers"]
```

## Design Principles

1. **Ergonomic**: Tests should be easy to write and read
2. **Minimal**: Test roots are tiny and focused
3. **Reusable**: Share setup across many tests
4. **Deterministic**: Normalize volatile output
5. **Fast**: Avoid repeated expensive setup
