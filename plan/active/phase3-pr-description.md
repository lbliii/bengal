# Phase 3: Testing Infrastructure - Selective Migration & Supporting Utilities

This PR completes Phase 3 of the testing strategy enhancements, adding critical infrastructure and documenting test patterns.

## Overview

Phase 3 focused on **selective migration** of integration tests and completing the testing infrastructure with HTTP server utilities and comprehensive cache cleanup.

## What Changed

### 1. HTTP Server Utilities (`tests/_testing/http.py`)

New `http_server` fixture for ephemeral test servers:

```python
def test_external_links(site, build_site, http_server, tmp_path):
    """Test link checking with ephemeral server."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "test.html").write_text("<h1>Test</h1>")

    # Start server on ephemeral port
    base_url = http_server.start(fixtures)

    # Use in tests...
```

**Features:**
- Automatic port allocation
- Graceful shutdown
- `wait_for_port()` helper for connection verification

### 2. Enhanced Cache Hygiene (`tests/conftest.py`)

Expanded `reset_bengal_state` fixture to reset all stateful components:

```python
@pytest.fixture(autouse=True)
def reset_bengal_state():
    """Reset all stateful singletons/caches between tests."""
    yield

    # 1. Reset Rich console
    from bengal.utils.rich_console import reset_console
    reset_console()

    # 2. Reset logger state (close file handles, clear registry)
    from bengal.utils.logger import reset_loggers
    reset_loggers()

    # 3. Clear theme cache (forces fresh discovery)
    from bengal.utils.theme_registry import clear_theme_cache
    clear_theme_cache()
```

**Impact:**
- Prevents test contamination
- Closes file handles properly
- Ensures fresh state for each test

### 3. Comprehensive Test Documentation (`CONTRIBUTING.md`)

Added extensive "Writing Tests" section with:

- **Test Organization**: Unit vs integration, test roots
- **Quick Start Examples**: `@pytest.mark.bengal` patterns
- **CLI Testing**: `run_cli()` usage
- **Output Normalization**: `normalize_html()`, `normalize_json()`
- **HTTP Server**: Ephemeral server patterns
- **Test Markers**: Fast dev loop with `-m "not slow"`

### 4. Test Root Created: `test-cascade`

New test root for cascading frontmatter tests:

```
tests/roots/test-cascade/
├── bengal.toml
└── content/
    └── products/
        ├── _index.md (cascade: type, show_price, product_line)
        └── widgets/
            ├── _index.md (cascade: category, warranty)
            ├── super-widget.md (inherits all)
            └── custom-widget.md (inherits + overrides)
```

**Usage:**
```python
@pytest.mark.bengal(testroot="test-cascade")
def test_cascade_inheritance(site):
    widget = next(p for p in site.pages if "super-widget" in str(p.source_path))
    assert widget.metadata["type"] == "product"  # from products/
    assert widget.metadata["category"] == "widget"  # from widgets/
```

### 5. Selective Test Migration

**Migrated in Phase 3:**
- 1 cascade integration test (`test_cascade_integration.py`)
- 3 CLI tests (`test_cli_help.py`, `test_cli_output_integration.py`)

**Strategic Decision:**
Stopped selective migration at 17 integration tests (across all phases). Many remaining tests are infrastructure-specific and not suitable for generic test roots. Creating roots for every edge case would defeat the "minimal, reusable" principle.

## Cumulative Impact (All Phases)

### Tests Using New Infrastructure

| File | Tests |
|------|-------|
| `test_baseurl_builds.py` | 2 |
| `test_cascade_integration.py` | 1 |
| `test_cli_help.py` | 1 |
| `test_cli_output_integration.py` | 11 |
| `test_documentation_builds.py` | 2 |
| `test_infrastructure_prototype.py` | 10 (validation) |
| **Total** | **27 tests** |

### Infrastructure Created

**Modules:**
- `tests/_testing/__init__.py`
- `tests/_testing/fixtures.py` (rootdir, site_factory, build_site)
- `tests/_testing/markers.py` (@pytest.mark.bengal, site fixture)
- `tests/_testing/cli.py` (run_cli, CLIResult, strip_ansi)
- `tests/_testing/normalize.py` (normalize_html, normalize_json)
- `tests/_testing/http.py` (http_server fixture) **NEW**
- `tests/_testing/README.md`

**Test Roots:**
- `test-basic` (1-page site)
- `test-baseurl` (baseurl testing)
- `test-taxonomy` (tags testing)
- `test-templates` (template examples)
- `test-assets` (asset handling)
- `test-cascade` (cascade frontmatter) **NEW**

**Configuration:**
- `conftest.py`: pytest_plugins registration
- `conftest.py`: `reset_bengal_state` fixture (expanded)
- `CONTRIBUTING.md`: Comprehensive test guide **NEW**

### Performance Impact (from Phase 0)

✅ **test_output_quality.py**: 11 builds → 1 build (class-scoped fixture)  
✅ **Hypothesis tests**: 100 examples → 20 in dev, 100 in CI  
✅ **Marked slow tests**: Opt-out with `pytest -m "not slow"`  
✅ **Developer feedback loop**: ~3-5 min → ~20s

### Ergonomic Impact

✅ **Eliminated 300+ lines** of duplicate site setup code  
✅ **Declarative test configuration** with `@pytest.mark.bengal`  
✅ **Standardized CLI testing** with `run_cli()`  
✅ **Deterministic assertions** with normalization utilities  
✅ **Comprehensive patterns** in CONTRIBUTING.md

## Testing

All migrated tests pass:

```bash
# Run migrated integration tests
pytest tests/integration/test_baseurl_builds.py -v
pytest tests/integration/test_cascade_integration.py -v
pytest tests/integration/test_cli_help.py -v
pytest tests/integration/test_cli_output_integration.py -v
pytest tests/integration/test_documentation_builds.py -v

# Run infrastructure validation
pytest tests/test_infrastructure_prototype.py -v

# Fast dev loop
pytest -m "not slow" -n auto  # ~20s
```

## Strategic Outcomes

1. ✅ **Selective Migration**: Demonstrated principle with 17 integration tests
2. ✅ **Reusable Patterns**: 6 test roots for common scenarios
3. ✅ **Test Isolation**: Comprehensive cache cleanup
4. ✅ **Fast Dev Loop**: Marker-based test selection
5. ✅ **Documentation**: Clear patterns for future contributors

## Next Steps (Future Phases)

- Create additional test roots as patterns emerge
- Migrate more tests opportunistically (not exhaustively)
- Consider pytest-regressions for snapshots (Phase 5+)
- Monitor test suite performance over time

## Related

- RFC: `plan/active/testing-strategy-enhancements-v2.md`
- Phase 0 PR: #31 (Performance fixes)
- Phase 1 PR: #33 (Infrastructure)
- Phase 2 PR: #34 (Initial migration)
- Phase 3 PR: This PR
