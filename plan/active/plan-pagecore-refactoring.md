# Implementation Plan: PageCore Refactoring

**Based on**: RFC: Cache-Proxy Contract Enforcement  
**Created**: 2025-10-26  
**Status**: Ready to implement  
**Estimated Time**: 3-4 days (26 hours)  
**Complexity**: Moderate (composition refactoring + property delegation)

---

## Executive Summary

Refactor Page/PageMetadata/PageProxy to use shared `PageCore` base class, eliminating manual 3-way field synchronization. This prevents cache bugs by making it impossible to have mismatched field definitions. Page uses composition, PageMetadata becomes a type alias, PageProxy wraps PageCore.

### Plan Details
- **Total Tasks**: 21 tasks across 4 phases
- **Estimated Time**: 26 hours (3-4 days)
- **Complexity**: Moderate (~400 lines across 15+ files)
- **Confidence Gates**: RFC ≥85% ✅, Implementation ≥90%

### Key Benefits
- ✅ Type-safe field contract (compiler enforces)
- ✅ Single source of truth (add field once, works everywhere)
- ✅ Zero runtime overhead (direct field access)
- ✅ Prevents cache bugs (impossible to have mismatched Page/PageMetadata/PageProxy)

---

## Phase 1: Foundation (Day 1, 6 tasks, 8 hours)

### Core: PageCore Creation

#### Task 1.1: Create PageCore dataclass
- **ID**: `core-pagecore-create`
- **Files**: `bengal/core/page_core.py` (NEW FILE)
- **Action**:
  - Create `PageCore` dataclass with all cacheable fields:
    - `source_path: Path`
    - `title: str`
    - `date: datetime | None`
    - `tags: list[str]`
    - `slug: str | None`
    - `weight: int | None`
    - `lang: str | None`
    - `type: str | None` (cascaded)
    - `section: str | None` (path-based)
    - `file_hash: str | None`
  - Add comprehensive docstring explaining cacheable vs non-cacheable
  - Add type hints and field defaults
- **Dependencies**: None
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add bengal/core/page_core.py && git commit -m "core: add PageCore dataclass with cacheable fields

Introduce PageCore as single source of truth for cacheable page metadata.

Fields included:
- Frontmatter: title, date, tags, slug, weight, lang
- Cascaded: type (from section _index.md)
- References: section (path-based, not object)
- Validation: file_hash

What goes in PageCore:
✅ Metadata from frontmatter (no disk I/O needed)
✅ Computed fields that don't require full content
✅ Section references (path-based for stability)

What does NOT go in PageCore:
❌ Full content (content, rendered_html) - requires parsing
❌ Generated data (toc, toc_items) - requires content processing
❌ Build artifacts (output_path, links) - ephemeral per build

This is step 1 of PageCore refactoring to prevent cache bugs.
See: plan/active/rfc-cache-proxy-contract.md"
```

---

#### Task 1.2: Add unit tests for PageCore
- **ID**: `test-pagecore-unit`
- **Files**: `tests/unit/test_page_core.py` (NEW FILE)
- **Action**:
  - `test_page_core_creation()` - All fields initialized correctly
  - `test_page_core_serialization()` - `asdict()` works for JSON
  - `test_page_core_deserialization()` - Can reconstruct from dict
  - `test_page_core_field_defaults()` - Optional fields have correct defaults
  - `test_page_core_immutability()` - Dataclass fields can be updated (not frozen)
  - `test_page_core_with_all_fields()` - All fields populated
  - `test_page_core_with_minimal_fields()` - Only required fields
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~120
- **Commit**:
```bash
git add tests/unit/test_page_core.py && git commit -m "tests(core): add unit tests for PageCore dataclass

Comprehensive test coverage:
- Field initialization and defaults
- JSON serialization/deserialization
- All fields accessible
- Minimal vs full field population

Validates PageCore as reliable cache data structure."
```

---

### Cache: Update PageMetadata

#### Task 1.3: Convert PageMetadata to PageCore alias
- **ID**: `cache-pagemetadata-alias`
- **Files**: `bengal/cache/page_discovery_cache.py`
- **Action**:
  - Remove old `PageMetadata` dataclass definition (lines 35-47)
  - Add import: `from bengal.core.page_core import PageCore`
  - Add type alias: `PageMetadata = PageCore`
  - Add comment explaining why it's an alias
  - **DO NOT change** `PageDiscoveryCacheEntry` (still uses `.metadata`)
  - **DO NOT change** JSON serialization (works via `asdict()`)
- **Dependencies**: Task 1.1
- **Status**: pending
- **Lines**: ~10 (net reduction of ~40 lines!)
- **Commit**:
```bash
git add bengal/cache/page_discovery_cache.py && git commit -m "cache: convert PageMetadata to PageCore type alias

Replace manual PageMetadata dataclass with PageCore alias.

Before:
@dataclass
class PageMetadata:
    source_path: str
    title: str
    # ... 10 duplicated fields

After:
from bengal.core.page_core import PageCore
PageMetadata = PageCore  # Single source of truth!

This eliminates field duplication between Page and PageMetadata.
JSON serialization unchanged (asdict() works identically).

Lines removed: 40 (duplicate field definitions)"
```

---

#### Task 1.4: Update cache tests for PageCore
- **ID**: `test-cache-pagecore`
- **Files**: `tests/unit/test_page_discovery_cache.py`
- **Action**:
  - Update imports to use `PageCore` if needed
  - Verify all existing tests still pass (PageMetadata = PageCore)
  - Add test: `test_pagemetadata_is_pagecore()` - Verify alias works
  - Update any assertions that depend on field order
- **Dependencies**: Task 1.3
- **Status**: pending
- **Lines**: ~20
- **Commit**:
```bash
git add tests/unit/test_page_discovery_cache.py && git commit -m "tests(cache): update tests for PageMetadata = PageCore alias

Verify PageMetadata alias works correctly:
- All existing tests pass unchanged
- PageMetadata IS PageCore (isinstance checks work)
- JSON serialization/deserialization unchanged

No functional changes, just validating refactoring correctness."
```

---

#### Task 1.5: Run Phase 1 validation
- **ID**: `validate-phase-1`
- **Files**: N/A (validation task)
- **Action**:
  - Run: `pytest tests/unit/test_page_core.py -v`
  - Run: `pytest tests/unit/test_page_discovery_cache.py -v`
  - Run linter: `ruff check bengal/core/page_core.py bengal/cache/page_discovery_cache.py`
  - Run type checker: `mypy bengal/core/page_core.py`
  - Verify no regressions in other tests: `pytest tests/unit/ -k "not test_page"`
- **Dependencies**: Tasks 1.1-1.4
- **Status**: pending
- **Gate**: All tests pass, linter clean, type checker passes
- **Command**:
```bash
pytest tests/unit/test_page_core.py tests/unit/test_page_discovery_cache.py -v
ruff check bengal/core/ bengal/cache/
mypy bengal/core/page_core.py
```

---

#### Task 1.6: Phase 1 checkpoint commit
- **ID**: `checkpoint-phase-1`
- **Files**: All Phase 1 files
- **Action**:
  - Verify all Phase 1 tasks complete
  - Ensure tests pass
  - Tag commit for rollback: `git tag phase-1-pagecore-foundation`
- **Dependencies**: Task 1.5
- **Status**: pending
- **Commit**:
```bash
git tag -a phase-1-pagecore-foundation -m "Phase 1 complete: PageCore foundation and PageMetadata alias"
```

---

## Phase 2: Core Refactoring (Day 2, 7 tasks, 10 hours)

### Core: Page Class Refactoring

#### Task 2.1: Add PageCore composition to Page class
- **ID**: `core-page-composition`
- **Files**: `bengal/core/page/__init__.py`
- **Action**:
  - Import: `from bengal.core.page_core import PageCore`
  - Add `core: PageCore` field to Page dataclass (first field)
  - **DO NOT remove** existing fields yet (will be replaced by properties)
  - Add temporary comment: `# TODO: Replace with @property delegates`
  - Ensure Page still instantiates correctly
- **Dependencies**: Task 1.6
- **Status**: pending
- **Lines**: ~5
- **Commit**:
```bash
git add bengal/core/page/__init__.py && git commit -m "core(page): add PageCore composition field

Add core: PageCore field to Page dataclass as first step of refactoring.

Existing fields remain (will become property delegates in next task).
This allows incremental migration without breaking existing code.

Next: Add @property delegates for backward compatibility."
```

---

#### Task 2.2: Add property delegates for all core fields
- **ID**: `core-page-properties`
- **Files**: `bengal/core/page/__init__.py`
- **Action**:
  - Remove direct dataclass fields that exist in PageCore:
    - Remove: `title: str`, `date: datetime | None`, `tags: list[str]`, etc.
  - Add `@property` getters for each PageCore field:
    ```python
    @property
    def title(self) -> str:
        return self.core.title

    @title.setter
    def title(self, value: str):
        self.core.title = value
    ```
  - Repeat for: `date`, `tags`, `slug`, `weight`, `lang`, `type`, `section`
  - Add docstrings to properties explaining they delegate to core
  - **Keep** non-core fields: `content`, `rendered_html`, `output_path`, `toc`, etc.
- **Dependencies**: Task 2.1
- **Status**: pending
- **Lines**: ~80 (properties) - ~40 (removed fields) = ~40 net
- **Commit**:
```bash
git add bengal/core/page/__init__.py && git commit -m "core(page): add property delegates for PageCore fields

Replace direct fields with @property delegates to page.core.

Before:
@dataclass
class Page:
    title: str
    date: datetime | None
    content: str

After:
@dataclass
class Page:
    core: PageCore
    content: str  # Not in core

    @property
    def title(self) -> str:
        return self.core.title

Benefits:
✅ Backward compatible (page.title still works)
✅ Single source of truth (PageCore)
✅ Clear separation (core = cacheable, Page adds non-cacheable)

Fields delegated: title, date, tags, slug, weight, lang, type, section"
```

---

#### Task 2.3: Update Page instantiation in page initializer
- **ID**: `core-page-instantiation`
- **Files**: `bengal/utils/page_initializer.py`
- **Action**:
  - Update `PageInitializer.initialize()` to create PageCore first:
    ```python
    core = PageCore(
        source_path=source_path,
        title=metadata.get("title", "Untitled"),
        date=metadata.get("date"),
        tags=metadata.get("tags", []),
        slug=metadata.get("slug"),
        weight=metadata.get("weight"),
        lang=metadata.get("lang"),
        type=metadata.get("type"),
        section=metadata.get("section"),
    )
    page = Page(
        core=core,
        content=content,
        rendered_html="",
        # ... other non-core fields
    )
    ```
  - Update any other places that create Page objects
- **Dependencies**: Task 2.2
- **Status**: pending
- **Lines**: ~30
- **Commit**:
```bash
git add bengal/utils/page_initializer.py && git commit -m "core(utils): update PageInitializer to use PageCore composition

Modify page creation flow:
1. Extract metadata from frontmatter
2. Create PageCore with cacheable fields
3. Create Page with core + non-cacheable fields

This ensures Page.core is always populated correctly during initialization."
```

---

#### Task 2.4: Update Page instantiation across codebase
- **ID**: `core-page-instantiation-global`
- **Files**: Multiple (grep for `Page(` calls)
- **Action**:
  - Grep for all `Page(` instantiation sites: `git grep "Page("`
  - Update each site to create PageCore first, then Page
  - Focus on:
    - `tests/unit/test_page*.py`
    - `tests/integration/`
    - Any factories or test fixtures
  - Add helper function if many sites need updating:
    ```python
    def create_page_with_core(title: str, content: str = "", **kwargs) -> Page:
        core = PageCore(
            source_path=kwargs.get("source_path", Path("test.md")),
            title=title,
            date=kwargs.get("date"),
            tags=kwargs.get("tags", []),
            # ... other core fields
        )
        return Page(core=core, content=content, **non_core_kwargs)
    ```
- **Dependencies**: Task 2.3
- **Status**: pending
- **Lines**: ~100 (across multiple files)
- **Commit**:
```bash
git add tests/ && git commit -m "tests: update Page instantiation to use PageCore composition

Update all test fixtures and factories to create PageCore first:
- Unit test fixtures
- Integration test helpers
- Mock page creation

Add helper: create_page_with_core() for common test patterns.

This ensures tests exercise the new composition-based architecture."
```

---

#### Task 2.5: Update Page tests for property access
- **ID**: `test-page-properties`
- **Files**: `tests/unit/test_page*.py`
- **Action**:
  - Add tests for property delegates:
    - `test_page_title_property()` - Get/set via property
    - `test_page_date_property()` - Get/set via property
    - `test_page_core_field_access()` - Direct core access works
    - `test_page_property_delegates_to_core()` - Property points to core
  - Update any assertions that fail due to property access
  - Ensure `page.title = "New"` works (setter)
- **Dependencies**: Task 2.4
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add tests/unit/test_page*.py && git commit -m "tests(core): add tests for Page property delegates

Validate property delegation works correctly:
- Getters return core field values
- Setters update core field values
- Direct core access works (page.core.title)
- Backward compatibility maintained (page.title works)

Ensures refactoring doesn't break existing behavior."
```

---

#### Task 2.6: Run Phase 2 validation
- **ID**: `validate-phase-2`
- **Files**: N/A (validation task)
- **Action**:
  - Run: `pytest tests/unit/test_page*.py -v`
  - Run: `pytest tests/unit/ -k "page" -v`
  - Run linter: `ruff check bengal/core/`
  - Run type checker: `mypy bengal/core/page/`
  - Verify no regressions: `pytest tests/unit/`
- **Dependencies**: Tasks 2.1-2.5
- **Status**: pending
- **Gate**: All unit tests pass, no type errors, linter clean
- **Command**:
```bash
pytest tests/unit/ -v
ruff check bengal/core/
mypy bengal/core/page/
```

---

#### Task 2.7: Phase 2 checkpoint commit
- **ID**: `checkpoint-phase-2`
- **Files**: All Phase 2 files
- **Action**:
  - Verify all Phase 2 tasks complete
  - Tag commit: `git tag phase-2-page-refactoring`
- **Dependencies**: Task 2.6
- **Status**: pending
- **Commit**:
```bash
git tag -a phase-2-page-refactoring -m "Phase 2 complete: Page class refactored with PageCore composition"
```

---

## Phase 3: Proxy & Orchestration (Day 3, 5 tasks, 6 hours)

### Core: PageProxy Refactoring

#### Task 3.1: Refactor PageProxy to wrap PageCore
- **ID**: `core-proxy-pagecore`
- **Files**: `bengal/core/page/proxy.py`
- **Action**:
  - Update `__init__` to accept `core: PageCore` instead of `metadata: Any`:
    ```python
    def __init__(self, core: PageCore, loader: callable):
        self._core = core
        self._loader = loader
        self._lazy_loaded = False
        self._full_page: Page | None = None
    ```
  - Replace field population with property delegates:
    ```python
    @property
    def title(self) -> str:
        return self._core.title

    @property
    def date(self) -> datetime | None:
        return self._core.date
    ```
  - Remove manual field assignments (lines 118-126)
  - Update `_ensure_loaded()` to transfer `core` instead of individual fields
- **Dependencies**: Task 2.7
- **Status**: pending
- **Lines**: ~60
- **Commit**:
```bash
git add bengal/core/page/proxy.py && git commit -m "core(proxy): refactor PageProxy to wrap PageCore

Replace manual field population with PageCore composition.

Before:
def __init__(self, metadata: Any, ...):
    self.title = metadata.title
    self.date = metadata.date
    # ... 10 manual copies

After:
def __init__(self, core: PageCore, ...):
    self._core = core

@property
def title(self) -> str:
    return self._core.title

Benefits:
✅ No manual field copying (single core object)
✅ Automatic sync with Page and PageMetadata
✅ Type-safe (PageCore defines contract)

This completes the Page/PageMetadata/PageProxy unification."
```

---

#### Task 3.2: Update PageProxy creation in content discovery
- **ID**: `disc-proxy-creation`
- **Files**: `bengal/discovery/content_discovery.py`
- **Action**:
  - Update `discover_with_cache()` to pass PageCore to PageProxy:
    ```python
    # Get cached metadata (already PageCore/PageMetadata)
    cached_core = cache.get_metadata(source_path)

    # Create proxy with core
    proxy = PageProxy(
        core=cached_core,
        loader=make_loader(source_path, lang, section_path),
    )
    ```
  - Remove manual field extraction from metadata dict
- **Dependencies**: Task 3.1
- **Status**: pending
- **Lines**: ~20
- **Commit**:
```bash
git add bengal/discovery/content_discovery.py && git commit -m "discovery: update PageProxy creation to use PageCore

Pass PageCore directly to PageProxy instead of individual fields.

Simplified from:
metadata = cache.get_metadata(path)
proxy = PageProxy(metadata=metadata, ...)  # Manual field extraction inside

To:
core = cache.get_metadata(path)  # Already PageCore!
proxy = PageProxy(core=core, ...)  # Direct use

Cache metadata is PageCore, so no conversion needed."
```

---

### Orchestration: Cache Save/Load

#### Task 3.3: Update cache save to use Page.core
- **ID**: `orch-cache-save-core`
- **Files**: `bengal/orchestration/build.py`
- **Action**:
  - Update Phase 1.25 cache saving (around line 350-370):
    ```python
    # Before: Manual field copying
    metadata = PageMetadata(
        source_path=...,
        title=page.title,
        date=page.date.isoformat() if page.date else None,
        # ... 10 more manual copies
    )

    # After: Direct use
    metadata = page.core  # Already PageCore/PageMetadata!
    cache.add_metadata(metadata)
    ```
  - Remove ~15 lines of manual field copying
  - Verify relative path handling for `source_path` still works
- **Dependencies**: Task 3.2
- **Status**: pending
- **Lines**: ~5 (net reduction of ~10 lines)
- **Commit**:
```bash
git add bengal/orchestration/build.py && git commit -m "orchestration(build): simplify cache save using Page.core

Replace manual field copying with direct PageCore use.

Before (15+ lines):
metadata = PageMetadata(
    source_path=str(page.source_path.relative_to(site.root_path)),
    title=page.title,
    date=page.date.isoformat() if page.date else None,
    tags=page.tags,
    # ... 10 more manual copies
)

After (1 line):
metadata = page.core  # Already PageCore/PageMetadata!

Lines saved: 14
Bug risk eliminated: Can't forget to add new fields to cache

This is the main payoff of PageCore refactoring."
```

---

#### Task 3.4: Add integration test for cache-proxy consistency
- **ID**: `test-cache-proxy-consistency`
- **Files**: `tests/integration/test_pagecore_consistency.py` (NEW FILE)
- **Action**:
  - `test_full_to_incremental_build_cycle()` - Full build → cache → incremental with PageProxy
  - `test_page_core_survives_cache_roundtrip()` - Serialize → deserialize → same fields
  - `test_proxy_has_all_core_fields()` - PageProxy can access all PageCore fields
  - `test_cache_proxy_field_consistency()` - For each field in PageCore, verify accessible in PageProxy
  - `test_dev_server_with_pagecore()` - Dev server works with PageCore-based proxies
  - Use property testing to verify all fields:
    ```python
    for field in PageCore.__dataclass_fields__:
        assert hasattr(proxy, field), f"PageProxy missing {field}"
        assert getattr(proxy, field) == getattr(page.core, field)
    ```
- **Dependencies**: Task 3.3
- **Status**: pending
- **Lines**: ~150
- **Commit**:
```bash
git add tests/integration/test_pagecore_consistency.py && git commit -m "tests(integration): add PageCore cache-proxy consistency tests

Comprehensive validation of PageCore refactoring:

1. Full → incremental build cycle with PageProxy
2. Cache roundtrip (serialize → deserialize → identical)
3. PageProxy has ALL PageCore fields (property test)
4. Field values match between Page.core and PageProxy._core
5. Dev server works with PageCore-based system

This test would have caught the original cache bugs:
- Missing parent/ancestors (blank breadcrumbs)
- Missing type field (wrong layouts)
- Field mismatch between Page/Proxy

Success criteria: All PageCore fields accessible in PageProxy without full load."
```

---

#### Task 3.5: Run Phase 3 validation
- **ID**: `validate-phase-3`
- **Files**: N/A (validation task)
- **Action**:
  - Run: `pytest tests/integration/test_pagecore_consistency.py -v`
  - Run: `pytest tests/integration/ -v`
  - Run full test suite: `pytest tests/ -v`
  - Run linter: `ruff check bengal/`
  - Run type checker: `mypy bengal/core/ bengal/cache/ bengal/orchestration/ bengal/discovery/`
  - Manual test: Start dev server, edit page, verify no breakage
- **Dependencies**: Tasks 3.1-3.4
- **Status**: pending
- **Gate**: All tests pass, no regressions, dev server works
- **Command**:
```bash
pytest tests/ -v
ruff check bengal/
mypy bengal/
cd site && bengal site serve  # Manual test
```

---

## Phase 4: Documentation & Polish (Day 4, 3 tasks, 4 hours)

### Documentation

#### Task 4.1: Add comprehensive docstrings to PageCore
- **ID**: `docs-pagecore-docstrings`
- **Files**: `bengal/core/page_core.py`
- **Action**:
  - Add detailed module docstring explaining PageCore purpose
  - Add docstrings to each field explaining:
    - What it stores
    - When it's populated
    - Why it's cacheable
  - Add examples in docstrings:
    ```python
    """
    Cacheable page metadata shared between Page, PageMetadata, and PageProxy.

    This is the single source of truth for all cacheable page data. Any field
    added here automatically becomes available in:
    - Page: via page.core.field or @property delegate
    - PageMetadata: IS PageCore (type alias)
    - PageProxy: via proxy.field property

    Example:
        # Creating a PageCore
        core = PageCore(
            source_path=Path("content/post.md"),
            title="My Post",
            date=datetime(2025, 10, 26),
            tags=["python", "web"],
        )

        # Using in Page
        page = Page(core=core, content="# Hello")
        assert page.title == "My Post"  # Property delegate

        # Caching
        metadata = page.core  # Already PageCore!
        json_str = json.dumps(asdict(metadata), default=str)
    """
    ```
- **Dependencies**: Task 3.5
- **Status**: pending
- **Lines**: ~100 (docstrings)
- **Commit**:
```bash
git add bengal/core/page_core.py && git commit -m "docs(core): add comprehensive docstrings to PageCore

Add detailed documentation:
- Module-level docstring explaining PageCore purpose
- Field-level docstrings with examples
- Usage examples for Page/PageMetadata/PageProxy
- Guidelines on what belongs in PageCore vs Page

Makes it clear to contributors how to use and extend PageCore."
```

---

#### Task 4.2: Update CONTRIBUTING.md with PageCore guidelines
- **ID**: `docs-contributing-pagecore`
- **Files**: `CONTRIBUTING.md`
- **Action**:
  - Add section: "Working with PageCore"
  - Document the contract:
    ```markdown
    ## Working with PageCore

    **What is PageCore?**

    PageCore is the single source of truth for cacheable page metadata. It's
    shared between Page, PageMetadata, and PageProxy.

    **When to add a field to PageCore:**

    ✅ DO add if:
    - Field comes from frontmatter (title, date, tags, etc.)
    - Field is computed without full content (slug, url path)
    - Field needs to be accessible in templates without lazy loading

    ❌ DON'T add if:
    - Field requires full content parsing (toc, excerpt)
    - Field is a build artifact (output_path, links)
    - Field changes every build (timestamp, render time)

    **How to add a new field:**

    1. Add to PageCore (bengal/core/page_core.py)
    2. Add @property delegate to Page (bengal/core/page/__init__.py)
    3. Add @property delegate to PageProxy (bengal/core/page/proxy.py)
    4. Done! Field is now in Page, PageMetadata, and PageProxy

    **Example:**

    ```python
    # 1. Add to PageCore
    @dataclass
    class PageCore:
        # ... existing fields
        author: str | None = None  # NEW field

    # 2. Add to Page
    @property
    def author(self) -> str | None:
        return self.core.author

    # 3. Add to PageProxy
    @property
    def author(self) -> str | None:
        return self._core.author
    ```
    ```
- **Dependencies**: Task 4.1
- **Status**: pending
- **Lines**: ~80
- **Commit**:
```bash
git add CONTRIBUTING.md && git commit -m "docs(contrib): add PageCore contract guidelines

Document how to work with PageCore for contributors:
- When to add fields to PageCore vs Page
- How to add a new field (3-step process)
- Examples of good and bad candidates for PageCore
- Explanation of cacheable vs non-cacheable

Prevents future cache bugs by making contract explicit."
```

---

#### Task 4.3: Update CHANGELOG.md with PageCore entry
- **ID**: `docs-changelog-pagecore`
- **Files**: `CHANGELOG.md`
- **Action**:
  - Add entry under `## Unreleased` or `## [0.2.0]`:
    ```markdown
    ## [0.2.0] - 2025-XX-XX

    ### Changed (Internal)
    - **Core**: Refactored Page/PageMetadata/PageProxy to use shared PageCore base class
      - Page now uses composition with `page.core` containing cacheable fields
      - PageMetadata is now a type alias to PageCore (eliminates duplication)
      - PageProxy wraps PageCore directly (automatic field sync)
      - **Impact**: Internal refactoring, no user-facing changes
      - **Benefit**: Prevents cache bugs from field mismatches
      - **Breaking**: Plugins accessing internal fields may need updates (unlikely)

    ### Fixed
    - **Cache**: Fixed cache-proxy consistency bugs (blank breadcrumbs, wrong types)
    - **Cache**: Fixed duplicate cache entries from inconsistent path formats
    - **Dev Server**: Fixed infinite rebuild loop from log file watching

    ### Added
    - **Core**: PageCore dataclass as single source of truth for cacheable metadata
    - **Tests**: Added comprehensive cache-proxy consistency integration tests
    ```
- **Dependencies**: Task 4.2
- **Status**: pending
- **Lines**: ~20
- **Commit**:
```bash
git add CHANGELOG.md && git commit -m "docs(changelog): add v0.2.0 entry for PageCore refactoring

Document PageCore refactoring in changelog:
- Internal changes (Page/PageMetadata/PageProxy unification)
- Bugs fixed (cache consistency, dev server)
- New features (PageCore as single source of truth)

User impact: None (internal refactoring)
Developer impact: Easier to add new fields, prevents cache bugs"
```

---

## Phase 5: Final Validation (Day 4, 1 task, 2 hours)

### Validation

#### Task 5.1: Complete pre-merge checklist
- **ID**: `validate-final`
- **Files**: N/A (validation task)
- **Action**:
  - [ ] All unit tests pass: `pytest tests/unit/ -v`
  - [ ] All integration tests pass: `pytest tests/integration/ -v`
  - [ ] All performance tests pass: `pytest tests/performance/ -v`
  - [ ] Performance < 1% regression: Benchmark 1000-page site
  - [ ] Linter passes: `ruff check bengal/`
  - [ ] Type checker passes: `mypy bengal/`
  - [ ] Manual dev server test:
    - `cd site && bengal site serve`
    - Edit `content/getting-started/_index.md`
    - Verify breadcrumbs appear correctly
    - Verify sidebar appears correctly
    - Create new file, verify it appears
    - Delete file, verify it disappears
  - [ ] Documentation complete:
    - PageCore docstrings
    - CONTRIBUTING.md updated
    - CHANGELOG.md updated
    - architecture/object-model.md (already done)
  - [ ] All commits atomic and descriptive
  - [ ] Confidence ≥ 90%
- **Dependencies**: All previous tasks
- **Status**: pending
- **Gate**: All checks pass
- **Command**:
```bash
# Full validation suite
pytest tests/ -v --tb=short
ruff check bengal/
mypy bengal/

# Performance benchmark
cd benchmarks
pytest benchmark_full_build.py -v

# Manual dev server test
cd ../site
rm -rf .bengal/page_metadata.json public
bengal site serve --watch
# Then test file operations manually
```

---

## 📊 Task Summary

| Phase | Area | Tasks | Time | Status |
|-------|------|-------|------|--------|
| 1. Foundation | Core/Cache | 6 | 8h | pending |
| 2. Core Refactoring | Core/Tests | 7 | 10h | pending |
| 3. Proxy & Orchestration | Core/Orchestration | 5 | 6h | pending |
| 4. Documentation | Docs | 3 | 4h | pending |
| 5. Final Validation | Validation | 1 | 2h | pending |
| **Total** | | **21** | **26h** | **0% complete** |

---

## 🎯 Critical Path

**Must complete in order**:
1. Phase 1: PageCore foundation (Tasks 1.1-1.6)
2. Phase 2: Page refactoring (Tasks 2.1-2.7)
3. Phase 3: Proxy & orchestration (Tasks 3.1-3.5)
4. Phase 4: Documentation (Tasks 4.1-4.3)
5. Phase 5: Final validation (Task 5.1)

**Can parallelize** (after dependencies met):
- Tasks 1.2 + 1.3 (PageCore tests + PageMetadata alias)
- Tasks 2.4 + 2.5 (Page instantiation + tests)
- Tasks 4.1 + 4.2 (Docstrings + CONTRIBUTING)

---

## 📋 Quality Gates

### Phase 1 Gate (Foundation Complete)
- ✅ PageCore dataclass created with all cacheable fields
- ✅ PageMetadata is type alias to PageCore
- ✅ Unit tests pass for PageCore and cache
- ✅ Linter and type checker pass

### Phase 2 Gate (Core Refactoring Complete)
- ✅ Page uses composition with PageCore
- ✅ Property delegates work correctly
- ✅ All Page instantiation updated
- ✅ Unit tests pass for Page

### Phase 3 Gate (Integration Complete)
- ✅ PageProxy wraps PageCore
- ✅ Cache save/load uses PageCore
- ✅ Integration tests pass
- ✅ Dev server works manually

### Phase 4 Gate (Documentation Complete)
- ✅ PageCore docstrings comprehensive
- ✅ CONTRIBUTING.md updated
- ✅ CHANGELOG.md updated

### Phase 5 Gate (Ready to Merge)
- ✅ All tests pass
- ✅ Performance < 1% regression
- ✅ Manual validation successful
- ✅ All documentation complete
- ✅ Confidence ≥ 90%

---

## 🚀 Next Steps

**To begin implementation**:
```bash
# Start with Task 1.1
::implement Task 1.1

# Or start entire Phase 1
::implement Phase 1
```

**To track progress**:
- Update task statuses in this document as you complete them
- Run validation gates at end of each phase
- Document any issues or deviations in this file

**Alternative workflows**:
- Prototype Task 1.1-1.3 first to validate approach
- Run `::validate` on implementation at end of each phase
- Use `git tag` at each phase checkpoint for easy rollback

---

## 📌 Notes

### Implementation Tips

1. **Start with tests**: Write PageCore tests first (TDD approach)
2. **Incremental commits**: Commit after each task (atomic commits)
3. **Verify as you go**: Run tests after each task
4. **Use checkpoints**: Tag commits at end of each phase for rollback
5. **Property testing**: Use hypothesis for PageCore roundtrip tests

### Risk Mitigation

- **Breaking changes**: Property delegates maintain backward compatibility
- **Test failures**: Update incrementally, fix as they arise
- **Performance**: Benchmark at Phase 3 to catch regressions early
- **Dev server**: Manual test at Phase 3 to verify UX

### Success Criteria

- ✅ Dev server works flawlessly with file changes
- ✅ All PageCore fields accessible in PageProxy without lazy load
- ✅ Cache save/load is 1 line instead of 15
- ✅ Adding new field requires 3 changes (PageCore + 2 properties) instead of 10+
- ✅ No user-facing changes (templates work unchanged)
- ✅ Performance within 1% of baseline

---

## 🔄 Progress Tracking

**Phase 1**: ⏸️ Not started  
**Phase 2**: ⏸️ Not started  
**Phase 3**: ⏸️ Not started  
**Phase 4**: ⏸️ Not started  
**Phase 5**: ⏸️ Not started  

**Overall**: 0% complete (0/21 tasks)

---

**Status**: Ready to implement  
**Recommended Next Command**: `::implement Task 1.1` (create PageCore dataclass)
