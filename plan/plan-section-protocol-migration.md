# Plan: Section → SectionLike Protocol Migration

**Status**: Ready  
**Effort**: 4-6 hours  
**Risk**: Low  
**Impact**: High (2% → 80%+ protocol adoption)

---

## Overview

Migrate 176 usages of concrete `Section` type annotations to `SectionLike` protocol.
This is the single highest-impact change from the v2 architecture RFC.

---

## Pre-Work: Protocol Extensions

The current `SectionLike` protocol is missing commonly-used attributes.

### Current Protocol (bengal/protocols/core.py:122-182)

```python
class SectionLike(Protocol):
    name: str
    title: str
    path: Path | None
    href: str
    pages: list[PageLike]
    subsections: list[SectionLike]
    parent: SectionLike | None
    index_page: PageLike | None
```

### Required Additions

```python
# Add to SectionLike protocol
@property
def root(self) -> SectionLike:
    """Root section of the tree."""
    ...

@property
def is_virtual(self) -> bool:
    """True if section has no disk directory."""
    ...

@property
def icon(self) -> str | None:
    """Icon name from _index.md frontmatter."""
    ...

@property
def regular_pages(self) -> list[PageLike]:
    """Pages excluding index page."""
    ...

def get_all_pages(self, *, recursive: bool = False) -> list[PageLike]:
    """Get pages, optionally including subsection pages."""
    ...
```

---

## Migration Tasks

### Task 1: Extend SectionLike Protocol (30 min)

**File**: `bengal/protocols/core.py`

Add the 5 missing members to `SectionLike`:

```python
@runtime_checkable
class SectionLike(Protocol):
    # ... existing properties ...
    
    @property
    def root(self) -> SectionLike:
        """Root section of the tree."""
        ...

    @property
    def is_virtual(self) -> bool:
        """True if section has no disk directory."""
        ...

    @property
    def icon(self) -> str | None:
        """Icon name from _index.md frontmatter."""
        ...

    @property
    def regular_pages(self) -> list[PageLike]:
        """Pages excluding index page."""
        ...

    def get_all_pages(self, *, recursive: bool = False) -> list[PageLike]:
        """Get pages, optionally including subsection pages."""
        ...
```

**Commit**: `protocols: extend SectionLike with root, is_virtual, icon, regular_pages, get_all_pages`

---

### Task 2: Migrate Core Module (45 min)

**Files** (10 files, highest impact):

| File | Usages | Notes |
|------|--------|-------|
| `bengal/core/section/__init__.py` | 4 | Self-referential, keep concrete |
| `bengal/core/section/hierarchy.py` | 5 | Internal mixin, keep concrete |
| `bengal/core/section/queries.py` | 6 | Internal mixin, keep concrete |
| `bengal/core/section/navigation.py` | 3 | Internal mixin, keep concrete |
| `bengal/core/nav_tree.py` | 3 | **Migrate** |
| `bengal/core/cascade_engine.py` | 3 | **Migrate** |
| `bengal/core/registry.py` | 5 | **Migrate** |
| `bengal/core/site/section_registry.py` | 3 | **Migrate** |
| `bengal/core/page/relationships.py` | 3 | **Migrate** |

**Strategy**: Keep concrete types in Section's own mixins (they need `self` typing). Migrate all external usages.

**Commit**: `core: migrate Section → SectionLike in core modules`

---

### Task 3: Migrate Rendering/Navigation (60 min)

**Files** (12 files, user-facing impact):

| File | Usages | Priority |
|------|--------|----------|
| `bengal/rendering/template_context.py` | 3 | High |
| `bengal/rendering/template_functions/navigation/scaffold.py` | 4 | High |
| `bengal/rendering/template_functions/navigation/section.py` | 2 | High |
| `bengal/rendering/template_functions/navigation/auto_nav.py` | 1 | High |
| `bengal/rendering/template_functions/navigation/tree.py` | 2 | High |
| `bengal/rendering/template_functions/navigation/__init__.py` | 1 | Medium |
| `bengal/rendering/template_functions/openapi.py` | 4 | Medium |
| `bengal/rendering/pipeline/autodoc_renderer.py` | 1 | Medium |
| `bengal/rendering/context/section_context.py` | 1 | Low |

**Commit**: `rendering: migrate Section → SectionLike in template functions`

---

### Task 4: Migrate Content Discovery (45 min)

**Files** (8 files):

| File | Usages |
|------|--------|
| `bengal/content/discovery/section_builder.py` | 6 |
| `bengal/content/discovery/content_discovery.py` | 9 |
| `bengal/content/discovery/page_factory.py` | 2 |
| `bengal/content/discovery/__init__.py` | 1 |
| `bengal/content/discovery/directory_walker.py` | 1 |
| `bengal/content_types/strategies.py` | 7 |
| `bengal/content_types/registry.py` | 2 |
| `bengal/content_types/base.py` | 2 |

**Commit**: `content: migrate Section → SectionLike in discovery`

---

### Task 5: Migrate Orchestration (45 min)

**Files** (8 files):

| File | Usages |
|------|--------|
| `bengal/orchestration/section.py` | 19 |
| `bengal/orchestration/menu.py` | 1 |
| `bengal/orchestration/taxonomy.py` | 2 |
| `bengal/orchestration/build/__init__.py` | 3 |
| `bengal/orchestration/build/content.py` | 1 |
| `bengal/orchestration/incremental/cascade_tracker.py` | 2 |
| `bengal/orchestration/incremental/rebuild_filter.py` | 1 |

**Note**: `orchestration/section.py` has 19 usages - review carefully for factory methods that need concrete return types.

**Commit**: `orchestration: migrate Section → SectionLike`

---

### Task 6: Migrate Remaining Modules (30 min)

**Files** (remaining):

| File | Usages |
|------|--------|
| `bengal/health/validators/navigation.py` | 1 |
| `bengal/health/validators/connectivity.py` | 1 |
| `bengal/cache/indexes/section_index.py` | 1 |
| `bengal/autodoc/orchestration/page_builders.py` | 1 |
| `bengal/autodoc/orchestration/result.py` | 1 |
| `bengal/autodoc/orchestration/index_pages.py` | 1 |
| `bengal/utils/paths/url_strategy.py` | 2 |
| `bengal/directives/navigation.py` | 3 |
| `bengal/errors/exceptions.py` | 2 |
| `bengal/analysis/links/types.py` | 2 |

**Commit**: `chore: migrate remaining Section → SectionLike usages`

---

### Task 7: Validation (30 min)

1. **Type Check**: `uv run ty check bengal/`
2. **Tests**: `uv run pytest tests/ -x`
3. **Grep Audit**: `grep -r ": Section\b" bengal/ --include="*.py" | wc -l`
   - Target: < 30 remaining (only in Section's own implementation)

**Commit**: `tests: verify Section protocol migration`

---

## Files to NOT Migrate

Keep concrete `Section` in these locations:

1. **Section's own implementation** (`bengal/core/section/*.py`)
   - Mixins need concrete self-types
   
2. **Factory functions** that must return concrete instances
   - `section_builder.py:build_section()` return type
   - `Section.create_virtual()` return type

3. **Internal caches** typed with concrete Section
   - Performance optimization, not public API

---

## Execution Order

```
1. [ ] Extend SectionLike protocol (Task 1)
2. [ ] Run ty check - should have NEW errors (protocol not satisfied)
3. [ ] Migrate core/ (Task 2)  
4. [ ] Migrate rendering/ (Task 3)
5. [ ] Migrate content/ (Task 4)
6. [ ] Migrate orchestration/ (Task 5)
7. [ ] Migrate remaining (Task 6)
8. [ ] Full validation (Task 7)
9. [ ] Squash into single commit or keep atomic
```

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `SectionLike` usages | 4 | ~150 |
| `Section` (concrete) usages | 176 | ~30 |
| Protocol adoption | 2% | **85%+** |

---

## Rollback

If issues discovered:
1. Protocol extensions are additive (backward compatible)
2. Each task is one commit - can revert individually
3. No runtime behavior changes - purely type annotations

---

## Next Steps After Completion

1. Add CI check: "No new concrete Section annotations"
2. Consider same migration for Page (11% → 80%)
3. Document protocol-first patterns in CONTRIBUTING.md
