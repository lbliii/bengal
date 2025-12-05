# RFC: Test Suite Scaling Refactor

**Status**: Draft (Updated)  
**Created**: 2025-12-03  
**Last Revised**: 2025-12-05  
**Author**: AI-assisted  
**Priority**: Medium  
**Estimated Effort**: 2-3 PRs  

---

## Summary

Bengal's test suite has doubled from ~2,000 to 4,150+ tests since October 2025 without corresponding infrastructure updates. This RFC proposes refactoring the testing strategy to improve maintainability, reduce execution time, and establish patterns that scale with continued growth.

---

## Problem Statement

### Current State (Verified Dec 5, 2025)

| Metric | Value | Issue |
|--------|-------|-------|
| Total test functions | ~4,065 | ✅ Good coverage |
| Test roots | 7 | ❌ Underutilized |
| `@pytest.mark.bengal` usage | 32 (9 files) | ❌ Great pattern, rarely used |
| Ad-hoc fixture creation | ~2,313 occurrences | ❌ Massive duplication |
| `MistuneParser()` instantiations | 106 in rendering | ❌ Repeated expensive setup |
| `Site.from_config/Site(` in unit | 242 | ❌ Repeated expensive setup |
| Unit test files in rendering/ | 56 | ⚠️ Largest test mass |
| MockPage class duplications | 6+ files | ❌ Repeated mock patterns |

### Key Pain Points

1. **Test roots are underutilized** - Only 7 roots for ~4,065 test functions; most tests create fixtures from scratch

2. **Rendering tests repeat parser setup** - 106 `MistuneParser()` instantiations; each test creates its own

3. **Mock patterns duplicated** - Same mock page/section creation code found in 6+ files (test_menu.py, test_taxonomies.py, test_directive_validator.py, test_template_links_baseurl.py, test_xref_bug.py, etc.)

4. **Site creation is expensive** - 242 site creations in unit tests; `shared_site_class` fixture exists but underused

5. **`@pytest.mark.bengal` underadopted** - Only 32 usages across 9 files despite being an excellent declarative pattern

---

## Evidence

### Test Root Usage Analysis (Verified Dec 5)

```
tests/roots/
├── test-basic/        # 1 page - smoke tests
├── test-baseurl/      # 2 pages - URL handling
├── test-taxonomy/     # 3 pages with tags
├── test-cascade/      # Nested sections (4 pages)
├── test-assets/       # Custom assets (image + content)
├── test-templates/    # Template escaping
└── autodoc-grouping/  # OpenAPI grouping (Python package)
```

**Missing scenarios**:
- Directive testing (cards, glossary, tabs, admonitions)
- Navigation testing (multi-level menus, breadcrumbs)
- Large site (100+ pages for perf tests)
- Incremental builds (pre-built cache state)

### Fixture Pattern Distribution (Verified Dec 5)

```bash
# Ad-hoc fixture creation (~2,313 occurrences)
grep -r "tmp_path\|site_factory\|shared_site" tests/unit --include="*.py" | wc -l
# → 2313

# Declarative root usage (32 occurrences)
grep -r "@pytest\.mark\.bengal" tests --include="*.py" | wc -l
# → 32 (across 9 files)
```

### Rendering Test Structure

From `tests/unit/rendering/test_cards_directive.py` (1,063 lines):

```python
# This pattern repeats ~40 times in just this file:
def test_simple_card_grid(self):
    parser = MistuneParser()
    content = """..."""
    result = parser.parse(content, {})
    assert "card-grid" in result
```

From multiple test files (verified Dec 5):

```python
# MockPage class defined in 6+ separate files:
# - tests/unit/core/test_menu.py (2 definitions)
# - tests/unit/template_functions/test_taxonomies.py
# - tests/unit/health/test_directive_validator_fences.py
# - tests/unit/health/test_directive_validator.py
# - tests/unit/rendering/test_template_links_baseurl.py (3 definitions)
# - tests/unit/rendering/test_template_tests.py
# - tests/unit/rendering/test_xref_bug.py

class MockPage:
    def __init__(self, title, url, description, icon, tags):
        self.title = title
        self.url = url
        self.metadata = {"description": description, "icon": icon}
        self.tags = tags or []
        self.date = None
```

---

## Existing Infrastructure to Leverage

Before adding new infrastructure, we should maximize use of existing patterns:

### Already Available ✅

| Component | Location | Current Usage |
|-----------|----------|---------------|
| `site_factory` fixture | `tests/_testing/fixtures.py:32-90` | Widely used; copies roots to tmp_path |
| `shared_site_class` fixture | `tests/conftest.py:312-376` | Class-scoped; creates 10-page site |
| `@pytest.mark.bengal` marker | `tests/_testing/markers.py` | Only 32 usages (underadopted) |
| `reset_bengal_state` autouse | `tests/conftest.py:266-309` | Resets console, logger, theme cache |
| Test progress reporter | `tests/conftest.py:53-96` | Available for long tests |

### Patterns from Production Code

| Pattern | Production Location | Test Opportunity |
|---------|---------------------|------------------|
| Thread-local parser caching | `bengal/rendering/pipeline.py:43-91` | Model for module-scoped parser fixture |
| Parallel executor with workers | `bengal/health/health_check.py` | Reference for test parallelism |

---

## Proposed Solution

### Phase 1: New Test Roots (Low Risk)

Add purpose-built test roots for common scenarios:

#### 1.1 `test-directives` Root

```
tests/roots/test-directives/
├── bengal.toml
├── content/
│   ├── _index.md           # Index with child-cards
│   ├── cards.md            # Card examples
│   ├── admonitions.md      # Admonition examples
│   └── sections/
│       ├── _index.md       # Section index
│       └── page.md         # Regular page
└── data/
    └── glossary.yaml       # Glossary data
```

**Eliminates**: Mock page/section creation in directive tests

#### 1.2 `test-navigation` Root

```
tests/roots/test-navigation/
├── bengal.toml
└── content/
    ├── _index.md
    ├── docs/
    │   ├── _index.md
    │   ├── getting-started/
    │   │   ├── _index.md
    │   │   └── quickstart.md
    │   └── reference/
    │       ├── _index.md
    │       └── api.md
    └── blog/
        └── _index.md
```

**Eliminates**: Ad-hoc hierarchy creation for menu/nav tests

#### 1.3 `test-large` Root

```
tests/roots/test-large/
├── bengal.toml
└── content/
    └── [100+ generated pages]  # Script-generated
```

**Eliminates**: Inline large site creation in perf tests

### Phase 2: Scoped Fixtures (Medium Risk)

#### 2.1 Module-Scoped Parser Fixture

In `tests/unit/rendering/conftest.py`:

```python
import pytest
from bengal.rendering.parsers import MistuneParser

@pytest.fixture(scope="module")
def parser():
    """Module-scoped parser for rendering tests.

    Reused across all tests in a module to avoid repeated instantiation.

    Safety: Parser instances are stateless for parsing operations, but some
    tests modify parser.md.renderer._xref_index. The autouse fixture below
    resets this state between tests to prevent pollution.
    """
    return MistuneParser()


@pytest.fixture(autouse=True, scope="function")
def reset_parser_state(request):
    """Reset parser state between tests to prevent pollution.

    Some tests modify parser.md.renderer._xref_index. This fixture ensures
    each test starts with a clean parser state, even when using a
    module-scoped parser fixture.

    Only runs when parser fixture is used (checks if parser is in request.fixturenames).
    """
    # Only reset if parser fixture is used in this test
    if "parser" not in request.fixturenames:
        yield
        return

    parser = request.getfixturevalue("parser")

    # Save original state (if any)
    original_xref_index = getattr(parser.md.renderer, "_xref_index", None)

    yield

    # Reset after test completes
    parser.md.renderer._xref_index = original_xref_index


@pytest.fixture(scope="module")
def parser_with_site(site_factory):
    """Parser with xref_index from test-directives root.

    Note: Tests using this fixture should NOT modify _xref_index directly.
    Use the base parser fixture if you need to modify xref_index per test.
    """
    site = site_factory("test-directives")
    site.discover_content()

    parser = MistuneParser()
    parser.md.renderer._xref_index = site.build_xref_index()
    return parser
```

**Impact**: 106 parser instantiations → ~20 (one per module)

**Safety Note**: The `reset_parser_state` autouse fixture ensures test isolation
even when sharing a module-scoped parser. Tests that need to modify `_xref_index`
should use the base `parser` fixture (which gets reset) rather than `parser_with_site`.

#### 2.2 Shared Site Fixture Pattern

Update `tests/_testing/fixtures.py`:

```python
@pytest.fixture(scope="module")
def directive_site(site_factory):
    """Pre-built site for directive tests."""
    site = site_factory("test-directives")
    site.discover_content()
    site.discover_assets()
    return site


@pytest.fixture(scope="module")  
def directive_pages(directive_site):
    """Dictionary of pages by filename for easy access."""
    return {p.source_path.stem: p for p in directive_site.pages}
```

### Phase 3: Consolidate Mock Patterns (Medium Risk)

#### 3.1 Extract Common Mocks

Create `tests/_testing/mocks.py`:

```python
"""Shared mock objects for testing."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import Mock


@dataclass
class MockPage:
    """Mock page for directive testing."""
    title: str
    url: str = "/"
    source_path: Path = field(default_factory=lambda: Path("test.md"))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    date: Any = None
    _section: Any = None


@dataclass
class MockSection:
    """Mock section for directive testing."""
    name: str
    title: str
    path: Path = field(default_factory=lambda: Path("section"))
    metadata: dict[str, Any] = field(default_factory=dict)
    subsections: list = field(default_factory=list)
    pages: list = field(default_factory=list)
    index_page: Any = None

    def __post_init__(self):
        if self.index_page is None:
            self.index_page = Mock()
            self.index_page.url = f"/{self.name}/"


def create_mock_xref_index(pages: list[MockPage]) -> dict:
    """Build xref_index from mock pages."""
    return {
        "by_id": {},
        "by_path": {str(p.source_path.with_suffix("")): p for p in pages},
        "by_slug": {p.source_path.stem: [p] for p in pages},
    }
```

#### 3.2 Update Directive Tests

Before:
```python
def _create_mock_page(self, title, url, description="", icon="", tags=None):
    class MockPage:
        def __init__(self, title, url, description, icon, tags):
            # ... 10 lines of setup
    return MockPage(...)
```

After:
```python
from tests._testing.mocks import MockPage

def test_with_mock_page(self, parser):
    page = MockPage(title="Test", url="/test/")
    # ...
```

### Phase 4: Documentation Update

#### 4.1 Update `tests/README.md`

- Current test count (4,150+)
- Fixture usage guidelines
- When to use `@pytest.mark.bengal` vs `site_factory`
- Link to test roots documentation

#### 4.2 Update `tests/_testing/README.md`

- Document new mock utilities
- Scoped fixture patterns
- Migration guide for existing tests

#### 4.3 Update `tests/TEST_COVERAGE.md`

- Current coverage numbers
- Module-by-module breakdown
- Coverage goals and non-goals

---

## Implementation Plan

### PR 1: Test Roots (Low Risk)

1. Create `test-directives` root with sample content
2. Create `test-navigation` root with hierarchy
3. Add script to generate `test-large` root
4. Update `tests/roots/README.md`

**Files Changed**: ~15  
**Estimated Time**: 2-3 hours

### PR 2: Scoped Fixtures + Mocks (Medium Risk)

1. Add `tests/_testing/mocks.py`
2. Add `tests/unit/rendering/conftest.py` with parser fixtures and `reset_parser_state` autouse fixture
3. Migrate 2-3 directive test files as proof of concept (verify no test pollution)
4. Update `tests/_testing/README.md`

**Files Changed**: ~8  
**Estimated Time**: 3-4 hours

**Validation**: After migrating 2-3 files, run full test suite to verify:
- No test pollution (tests pass consistently)
- Parser state resets correctly between tests
- Performance improvement measurable

### PR 3: Full Migration (Medium Risk)

1. Migrate remaining rendering tests to use scoped parser
2. Replace inline mock classes with `MockPage`/`MockSection`
3. Update integration tests to use new roots where applicable

**Files Changed**: ~30-40  
**Estimated Time**: 4-6 hours

### PR 4: Documentation

1. Update `tests/README.md` with:
   - Current test count (~4,065 test functions)
   - Fixture usage guidelines (when to use `site_factory` vs `shared_site_class` vs test roots)
   - `@pytest.mark.bengal` adoption guide
2. Update `tests/_testing/README.md` with:
   - New mock utilities documentation
   - Migration guide for existing tests
   - Scoped fixture best practices
3. Update `tests/roots/README.md` with new root documentation

**Files Changed**: ~3  
**Estimated Time**: 1-2 hours

---

## Quick Wins (Can Implement Immediately)

These changes require no new infrastructure and can be done now:

1. **Consolidate MockPage** - Create `tests/_testing/mocks.py` and replace 10+ duplicate class definitions
2. **Add rendering conftest** - Create `tests/unit/rendering/conftest.py` with module-scoped parser
3. **Document existing patterns** - Update READMEs to promote `shared_site_class` and `@pytest.mark.bengal`

### Immediate Action: MockPage Consolidation

```python
# tests/_testing/mocks.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class MockPage:
    """Canonical mock page for testing."""
    title: str
    url: str = "/"
    source_path: Path = field(default_factory=lambda: Path("test.md"))
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    date: Any = None
    _section: Any = None
```

Then update imports in:
- `tests/unit/core/test_menu.py`
- `tests/unit/template_functions/test_taxonomies.py`
- `tests/unit/health/test_directive_validator*.py`
- `tests/unit/rendering/test_template_links_baseurl.py`
- `tests/unit/rendering/test_template_tests.py`
- `tests/unit/rendering/test_xref_bug.py`

---

## Expected Outcomes

### Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Test execution time | ~60-90s | ~40-60s | ~30% faster |
| Parser instantiations | 106 | ~20 | 5x reduction |
| Site creations (unit) | 242 | ~50 | 4-5x reduction |

### Maintainability

| Metric | Before | After |
|--------|--------|-------|
| MockPage class definitions | 10+ duplicated | 1 canonical |
| Ad-hoc fixture setup | ~2,313 occurrences | Mostly reused via roots |
| New test creation | Slow (copy/paste setup) | Fast (use fixtures + roots) |
| `@pytest.mark.bengal` usage | 32 | 100+ |

### Scalability

- Test roots provide foundation for future tests
- Scoped fixtures prevent linear slowdown as tests grow
- Centralized mocks reduce maintenance burden

---

## Alternatives Considered

### 1. pytest-bdd for Declarative Tests

**Rejected**: Too much migration effort; current patterns work well with better fixtures.

### 2. Snapshot Testing for Rendering

**Deferred**: Could complement this work but doesn't address fixture issues.

### 3. Parallel Test Execution Improvements

**Complementary**: xdist already used; this RFC focuses on setup overhead.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scoped fixtures cause test pollution | Medium | Medium | **Parser state mutability**: Some tests modify `parser.md.renderer._xref_index`. Mitigated via `reset_parser_state` autouse fixture that resets state between tests. Sites are read-only in most tests (function-scoped `site_factory`). |
| Migration introduces regressions | Medium | Low | Incremental migration; run full suite after each PR; start with 2-3 files as proof of concept |
| New patterns not adopted | Medium | Medium | Clear documentation; PR review enforcement; migration guide in `tests/_testing/README.md` |
| Parser state reset overhead | Low | Low | Reset operation is O(1) assignment; negligible compared to parser instantiation savings |

---

## Success Criteria

- [ ] All 4 new test roots created and documented
- [ ] Module-scoped parser fixture used in 80%+ of rendering tests
- [ ] Mock page/section classes consolidated to `_testing/mocks.py`
- [ ] Test execution time reduced by 20%+
- [ ] `tests/README.md` accurate and comprehensive
- [ ] No test regressions (all ~4,065 test functions pass)
- [ ] `@pytest.mark.bengal` adoption increased from 32 to 100+ usages

---

## References

- `tests/roots/README.md` - Current test root documentation
- `tests/_testing/README.md` - Testing utilities documentation
- `tests/conftest.py` - Current fixture definitions
- `tests/TEST_COVERAGE.md` - Coverage report (updated 2025-12-03)

---

## Validation Notes

**Validated**: 2025-12-05 (Refreshed)  
**Confidence**: 88% 🟢 (High)

### Verified Claims ✅ (Dec 5, 2025)

- **Test metrics**: All metrics re-verified against codebase
  - `@pytest.mark.bengal`: 32 occurrences across 9 files ✅ (decreased from 48/11 - likely test consolidation)
  - `MistuneParser()` instantiations: 106 in rendering tests ✅ (unchanged)
  - `Site.from_config/Site(`: 242 in unit tests ✅ (unchanged)
  - Test roots: 7 existing roots confirmed ✅ (unchanged)
  - Ad-hoc fixture usage: ~2,313 occurrences ✅ (slight improvement from 2,395)
  - MockPage duplication: Found in 6+ files with 10+ class definitions ✅
  - Unit test files in rendering/: 56 files ✅

### Recent Changes Since Initial Draft (Dec 3-5)

- Added build-integrated validation tests (`test_phase2b_cache_integration.py`)
- Fixed Python 3.14 compatibility issues in tests
- Added observability module tests
- Added compression (Zstandard) tests
- Added parallel health validator tests
- No new test roots created
- No `_testing/mocks.py` created yet (still needed)
- No `tests/unit/rendering/conftest.py` created yet (still needed)

### Safety Concerns Addressed ⚠️

- **Parser state mutability**: RFC originally claimed "Parser is stateless so sharing is safe"
  - **Reality**: Some tests modify `parser.md.renderer._xref_index` (see `test_cards_directive.py:810`)
  - **Mitigation**: Added `reset_parser_state` autouse fixture to Phase 2.1
  - **Risk level**: Medium → Low (with mitigation)

- **Fixture infrastructure**: `shared_site_class` exists in `conftest.py:312-376` and is proven safe
  - Creates 10-page site once per class
  - Properly handles modifiable copies via `request.param`

### Architecture Alignment ✅

- **Parser reuse pattern**: Production code uses thread-local parser caching (`bengal/rendering/pipeline.py:43-91`)
- **Test root pattern**: Proposed roots follow existing conventions
- **Fixture patterns**: `site_factory` in `tests/_testing/fixtures.py` already copies roots to tmp_path

### Evidence Trail (Updated Dec 5)

```bash
# Parser instantiations
grep -r "MistuneParser()" tests/unit/rendering | wc -l  # → 106

# MockPage class definitions  
grep -r "class MockPage" tests --include="*.py" | wc -l  # → 10

# Ad-hoc fixture usage
grep -r "tmp_path\|site_factory\|shared_site" tests/unit | wc -l  # → 2313

# @pytest.mark.bengal usage
grep -r "@pytest\.mark\.bengal" tests | wc -l  # → 32

# Test function count
grep -r "def test_" tests --include="*.py" | wc -l  # → ~4065
```

---

## Appendix: Files to Modify

### Phase 1 (New Test Roots)
```
tests/roots/test-directives/bengal.toml
tests/roots/test-directives/content/_index.md
tests/roots/test-directives/content/cards.md
tests/roots/test-directives/content/sections/_index.md
tests/roots/test-directives/data/glossary.yaml
tests/roots/test-navigation/bengal.toml
tests/roots/test-navigation/content/...
tests/roots/test-large/bengal.toml
tests/roots/README.md
```

### Phase 2 (Scoped Fixtures)
```
tests/_testing/mocks.py (new)
tests/unit/rendering/conftest.py (new)
tests/_testing/fixtures.py (update)
```

### Phase 3 (Migration)
```
tests/unit/rendering/test_cards_directive.py
tests/unit/rendering/test_glossary_directive.py
tests/unit/rendering/test_tabs_directive.py
tests/unit/rendering/test_button_directive.py
tests/unit/rendering/test_navigation_directives.py
... (15+ more rendering test files)
```

### Phase 4 (Documentation)
```
tests/README.md
tests/_testing/README.md
tests/TEST_COVERAGE.md (already updated)
```
