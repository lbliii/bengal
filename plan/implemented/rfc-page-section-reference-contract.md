# RFC: Page-Section Reference Contract Hardening

**Status**: Approved
**Created**: 2024-12-08
**Author**: Auto-generated from debugging session
**Reviewer**: AI Assistant (2024-12-08)
**Priority**: High (Navigation broken for virtual pages)

---

## Executive Summary

During debugging of the virtual autodoc navigation issue, I discovered a **critical bug** and several **systemic architectural issues** in how Bengal establishes and maintains page-section relationships. The immediate bug causes all virtual API documentation pages to have flat navigation instead of hierarchical. The systemic issues represent technical debt that increases debugging difficulty and risks similar bugs in the future.

**Root Cause**: Virtual sections have `path=None`, but the `_section` property setter stores `section.path` as the lookup key. The getter then returns `None` for any page where `_section_path is None`.

**Impact**: 408 virtual API documentation pages render with completely flat navigation instead of showing the hierarchical package/module structure.

## Verification Findings (2024-12-08)

### 1. Root Cause Confirmation
- **Confirmed** in `bengal/core/page/__init__.py`: The `_section` property getter strictly relies on `self._section_path`.
- **Confirmed** in `bengal/core/section.py`: `create_virtual` explicitly sets `path=None`.
- **Conclusion**: The combination guarantees `_section` returns `None` for all virtual pages, breaking navigation.

### 2. Systemic Issue Confirmation
- **Duplicate Code Identified**:
  - `bengal/core/site.py`: `_setup_page_references`
  - `bengal/orchestration/content.py`: `_setup_page_references` (almost identical logic)
- **Recommendation**: As part of the fix, `ContentOrchestrator` should delegate to `Site` to enforce a single source of truth for graph construction.

### 3. Architecture Alignment
- The proposed fix (storing `_section_url` for virtual lookup) aligns with Bengal's "Passive Models" pattern by avoiding direct object references in the core model, preserving cacheability potential.
- Adding `Site.get_section_by_url()` is necessary because `get_section_by_path()` performs filesystem normalization (resolving symlinks/absolute paths) which is incorrect for virtual URLs.

---

## Background

### What Was Observed

1. Virtual autodoc pages rendered correctly (content, URLs worked)
2. Sidebar navigation showed ALL API modules at the same level (flat)
3. Expected: Hierarchical navigation (api > core > cascade_engine)
4. Actual: Flat list (bengal, __main__, theme, core, cascade_engine, ...)

### Debugging Journey

The debugging session went through several false leads before finding the root cause:

1. **Initial hypothesis**: Virtual orchestrator returning flat sections
   - Fixed by returning only root `api` section
   - **Result**: Hierarchy built correctly, but nav still flat

2. **Second hypothesis**: Config not loading (`virtual_pages: False`)
   - Fixed by using `Site.from_config()` correctly
   - **Result**: Config loads correctly, but nav still flat

3. **Third hypothesis**: `_setup_page_references()` not being called
   - Verified it IS called after autodoc integration
   - **Result**: Method runs, but `_section` still None

4. **Root cause found**: `_section` property setter/getter incompatible with virtual sections

---

## Root Cause Analysis

### The Bug

Located in `bengal/core/page/__init__.py`:

```python
@_section.setter
def _section(self, value: Any) -> None:
    """Set the section this page belongs to (stores path, not object)."""
    if value is None:
        self._section_path = None
    else:
        # BUG: Virtual sections have path=None!
        self._section_path = value.path  # ← Stores None for virtual sections
```

And the getter:

```python
@property
def _section(self) -> Any | None:
    """Get the section this page belongs to (lazy lookup via path)."""
    if self._section_path is None:  # ← Always true for virtual pages!
        return None  # ← Returns None, navigation breaks

    # ... lookup logic never reached for virtual pages
```

### Why Virtual Sections Have `path=None`

From `bengal/core/section.py`:

```python
@classmethod
def create_virtual(cls, name: str, relative_url: str, ...) -> Section:
    """Create a virtual section (no disk directory)."""
    return cls(
        path=None,  # ← Virtual sections have no disk path
        metadata=section_metadata,
        _virtual=True,
        _relative_url_override=relative_url,
    )
```

Virtual sections don't correspond to disk directories, so `path=None` is intentional. But the `_section` property assumed ALL sections would have a `path`.

---

## Systemic Issues Discovered

### Issue 1: Silent State Failures

**Problem**: When `page._section` is `None`, templates silently fall back to flat navigation. No error, no warning, no log entry.

**Evidence**: `docs-nav.html` line 41-42:
```jinja2
{% set root_section = page._section.root if (page._section) else none %}
{% if root_section %}
    {# hierarchical nav #}
{% else %}
    {# SILENT FALLBACK to flat nav #}
{% endif %}
```

**Impact**: User sees broken navigation but has no way to diagnose why.

**Recommendation**: Add post-discovery validation that warns about pages with missing `_section` when they should have one.

### Issue 2: Duplicate `_setup_page_references` Implementations

**Problem**: Two different implementations exist:
- `Site._setup_page_references()` in `bengal/core/site.py:639`
- `ContentOrchestrator._setup_page_references()` in `bengal/orchestration/content.py:247`

**Evidence**:
```bash
$ grep -l "def _setup_page_references" bengal/
bengal/core/site.py
bengal/orchestration/content.py
```

**Impact**: Confusing which to use, potential for divergence, violates DRY.

**Recommendation**: Consolidate into ONE canonical implementation on `Site` class.

### Issue 3: Path-Based Lookup Assumes Disk Paths

**Problem**: The `_section` property uses `section.path` as a lookup key in the site registry. This was designed for cache stability across rebuilds (avoiding object reference issues). But it assumes all sections have disk paths.

**Evidence**: The page `_section` setter stores `value.path`, but virtual sections have `path=None`.

**Impact**: Virtual sections can't participate in the path-based lookup system.

**Recommendation**: Support alternative identifiers for virtual sections (e.g., `relative_url` or `name`).

### Issue 4: Hidden Timing Dependencies

**Problem**: Page-section relationships require specific ordering:
1. Create pages and sections
2. Add pages to sections via `add_page()`
3. Add sections to `site.sections`
4. Call `register_sections()` to build registry
5. Call `_setup_page_references()` to set `_section`

If any step is wrong, pages silently have `_section=None`.

**Evidence**: The `ContentOrchestrator.discover_content()` method has extensive comments about ordering:
```python
# Build section registry for path-based lookups (MUST come before _setup_page_references)
# This enables O(1) section lookups via page._section property
self.site.register_sections()

# Set up page references for navigation
self._setup_page_references()
```

**Impact**: Easy to add pages/sections in wrong order and get silent failures.

**Recommendation**: Either document the contract clearly OR make reference setup automatic (e.g., in `add_page()`).

### Issue 5: Virtual vs Regular Code Path Divergence

**Problem**: Virtual pages follow a different discovery path than regular pages:
- Regular: `ContentDiscovery._create_page()` → sets `page._site` and `page._section` immediately
- Virtual: `VirtualAutodocOrchestrator.generate()` → relies on later `_setup_page_references()`

**Evidence**:
```python
# ContentDiscovery._create_page() - IMMEDIATE setup
if self.site is not None:
    page._site = self.site
if section is not None:
    page._section = section

# VirtualAutodocOrchestrator - DEFERRED setup
page = Page.create_virtual(...)
parent_section.add_page(page)
# _section set later by _setup_page_references()
```

**Impact**: Different code paths can have different failure modes that are hard to debug.

**Recommendation**: Unify the patterns OR add comprehensive integration tests covering both paths.

### Issue 6: No Contract Validation

**Problem**: No assertions or validation that pages have proper references after discovery.

**Evidence**: Searched for `assert.*_section` - found NO assertions validating that pages in sections have correct `_section` references.

**Impact**: Bugs like this one can go unnoticed until users report broken navigation.

**Recommendation**: Add validation in `NavigationValidator` or as part of `_setup_page_references()`:
```python
def _validate_page_references(self) -> None:
    """Validate all pages have correct section references."""
    for section in self.sections:
        for page in section.pages:
            if page._section != section:
                logger.warning(
                    "page_section_mismatch",
                    page=str(page.source_path),
                    expected=section.name,
                    actual=page._section.name if page._section else "None"
                )
```

---

## Proposed Fix

### Immediate Fix (P0)

Modify the `_section` setter/getter to handle virtual sections:

```python
@_section.setter
def _section(self, value: Any) -> None:
    """Set the section this page belongs to."""
    if value is None:
        self._section_path = None
        self._section_url = None  # NEW: For virtual sections
    else:
        if value.path is not None:
            # Regular section: use path for lookup
            self._section_path = value.path
            self._section_url = None
        else:
            # Virtual section: use relative_url for lookup
            self._section_path = None
            self._section_url = value.relative_url  # NEW

@property
def _section(self) -> Any | None:
    """Get the section this page belongs to."""
    if self._section_path is None and self._section_url is None:
        return None

    if self._site is None:
        # ... warning logic
        return None

    if self._section_path is not None:
        # Regular section: path-based lookup
        return self._site.get_section_by_path(self._section_path)
    else:
        # Virtual section: URL-based lookup
        return self._site.get_section_by_url(self._section_url)  # NEW
```

Also requires adding `get_section_by_url()` to `Site`.

### Alternative: Direct Reference for Virtual Pages

Store the section object directly for virtual pages (simpler, less elegant):

```python
@_section.setter
def _section(self, value: Any) -> None:
    if value is None:
        self._section_path = None
        self._virtual_section_ref = None
    elif value._virtual:
        # Virtual section: store direct reference
        self._section_path = None
        self._virtual_section_ref = value
    else:
        # Regular section: store path
        self._section_path = value.path
        self._virtual_section_ref = None
```

### Systemic Fixes (P1-P3)

| Priority | Fix | Effort |
|----------|-----|--------|
| P1 | Consolidate `_setup_page_references` into Site | 1 day |
| P1 | Add integration test for virtual page navigation | 2 hours |
| P1 | Add post-discovery validation for `_section` | 2 hours |
| P2 | Add `NavigationValidator` check for missing `_section` | 2 hours |
| P2 | Document page-section contract in architecture docs | 1 hour |
| P3 | Consider making reference setup automatic in `add_page()` | Research |

---

## Testing Plan

### Unit Tests

1. **Test virtual section `_section` property**:
   ```python
   def test_virtual_page_section_reference():
       """Virtual pages should have correct _section reference."""
       section = Section.create_virtual(name="api", relative_url="/api/")
       page = Page.create_virtual(source_id="api/index.md", ...)
       page._section = section
       assert page._section == section  # Currently FAILS
   ```

2. **Test mixed regular/virtual sections**:
   ```python
   def test_mixed_section_navigation():
       """Both regular and virtual pages should have correct navigation."""
       # Create site with both regular and virtual sections
       # Verify all pages have correct _section
   ```

### Integration Tests

1. **Test virtual autodoc navigation hierarchy**:
   ```python
   def test_autodoc_virtual_pages_have_hierarchical_navigation():
       """Autodoc pages should have hierarchical navigation, not flat."""
       site = Site.from_config(Path("site"))
       ContentOrchestrator(site).discover()

       # Find a deeply nested autodoc page
       cascade_page = next(p for p in site.pages if "cascade_engine" in p.title)

       # Verify it has a section
       assert cascade_page._section is not None
       assert cascade_page._section.name == "core"

       # Verify hierarchical root
       assert cascade_page._section.root.name == "api"
   ```

---

## Success Criteria

- [ ] Virtual autodoc pages have correct `_section` references
- [ ] Navigation renders hierarchically for virtual pages
- [ ] `NavigationValidator` catches missing `_section` issues
- [ ] Single canonical `_setup_page_references` implementation
- [ ] Integration test prevents regression

---

## Lessons Learned

1. **Path-based lookups need fallback strategies** for entities without disk paths
2. **Silent fallbacks in templates hide bugs** - add logging/warnings
3. **Duplicate implementations create confusion** - consolidate early
4. **Virtual/synthetic content needs the same contracts as regular content**
5. **Validation catches bugs earlier** than user reports

---

## Appendix: Debugging Commands Used

```python
# Check if pages have _section set
from bengal.core.site import Site
site = Site.from_config(Path('site'))
ContentOrchestrator(site).discover()
api_pages = [p for p in site.pages if p._virtual]
for p in api_pages[:5]:
    print(f"{p.title}: _section={p._section}")

# Check virtual section paths
api_section = next(s for s in site.sections if s.name == 'api')
print(f"api.path={api_section.path}")  # None for virtual!
print(f"api._virtual={api_section._virtual}")  # True
```

---

## Related Files

- `bengal/core/page/__init__.py` - `_section` property (lines 380-482)
- `bengal/core/section.py` - `create_virtual()` factory
- `bengal/orchestration/content.py` - `_setup_page_references()`
- `bengal/core/site.py` - `_setup_page_references()` (duplicate)
- `bengal/themes/default/templates/partials/docs-nav.html` - Navigation template
- `bengal/autodoc/virtual_orchestrator.py` - Virtual page generation

---

## References

- [architecture/object-model.md](../architecture/object-model.md) - Page/Section relationships
- [bengal/core/page/page_core.py](../../bengal/core/page/page_core.py) - Cache contract (why path-based lookup exists)
- [tests/unit/core/test_page_section_references.py](../../tests/unit/core/test_page_section_references.py) - Existing tests
