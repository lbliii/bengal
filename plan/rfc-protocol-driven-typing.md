# RFC: Protocol-Driven Typing for ty Compliance

**Status**: Ready (Planned 2026-01-17)  
**Created**: 2026-01-17  
**Updated**: 2026-02-14  
**Author**: AI Assistant  
**Related**: `rfc-ty-type-hardening.md`, `rfc-protocol-consolidation.md`

> **Path note (2026-02-14)**: References to `bengal/build/detectors/` updated; that package was never created.

---

## Executive Summary

Bengal has **339 ty errors** (277 errors + 62 warnings). The **root cause is clear**: we built a comprehensive protocol system in `bengal/protocols/` but almost nobody uses it.

### The Core Problem: Protocols Exist But Aren't Used

```
Type Annotation          | Usage Count
-------------------------|------------
site: Site (concrete)    | 169 functions
site: SiteLike (protocol)| 1 function   ← UNUSED!

page: Page (concrete)    | 130 functions
page: PageLike (protocol)| 2 functions  ← UNUSED!

section: Section         | 30 functions
section: SectionLike     | 2 functions  ← UNUSED!
```

**We have the protocols. We're just not using them.**

When functions demand concrete `Site` but receive `SiteLike`-compatible objects, ty errors. The solution isn't to build more protocols—it's to **migrate existing signatures to use the protocols we already have**.

### Error Distribution

| Error Type | Count | Root Cause |
|------------|-------|------------|
| `invalid-argument-type` | 105 | Concrete type expected, protocol passed |
| `unresolved-attribute` | 55 | Missing attributes after `hasattr` checks |
| `unused-ignore-comment` | 42 | Stale `# type: ignore` directives |
| `invalid-assignment` | 24 | Type annotation mismatches |
| `call-non-callable` | 22 | `hasattr` doesn't narrow to callable |
| `possibly-missing-attribute` | 20 | Optional attribute access |

---

## The Real Problem: Protocol Adoption

### What We Have

`bengal/protocols/` exports 21 protocols:

```python
# bengal/protocols/__init__.py
__all__ = [
    # Core (UNDERUSED)
    "PageLike", "SectionLike", "SiteLike", "NavigableSection", "QueryableSection",
    # Rendering (moderately used)
    "TemplateEnvironment", "TemplateRenderer", "TemplateEngine", "HighlightService",
    # Infrastructure (well used)
    "ProgressReporter", "Cacheable", "OutputCollector", "ContentSourceProtocol",
    # Build (well used)
    "BuildPhase", "RenderContext", "RenderResult",
    ...
]
```

### What We're Not Using

The core protocols (`PageLike`, `SectionLike`, `SiteLike`) are barely adopted:

```python
# Current: 169 functions demand concrete Site
def register_functions(env: TemplateEnvironment, site: Site) -> None: ...

# Should be: Accept anything Site-like
def register_functions(env: TemplateEnvironment, site: SiteLike) -> None: ...
```

### Why This Matters

When code passes a `Self@indexes` or `AssetSiteLike` to a function expecting `Site`:

```
error[invalid-argument-type]: Expected `Site`, found `AssetSiteLike`
```

But `AssetSiteLike` satisfies `SiteLike`! The function doesn't need the full `Site`—it just needs the subset that `SiteLike` defines.

---

## Protocol Gaps: Missing Attributes

The existing protocols need extension to cover common use cases:

### PageLike Missing Attributes

| Attribute | Used By | Purpose |
|-----------|---------|---------|
| `metadata: dict[str, Any]` | `template_tests.py`, `openapi.py` | Raw frontmatter access |
| `tags: list[str] \| None` | `template_tests.py` | Taxonomy filtering |

### SiteLike Missing Attributes

| Attribute | Used By | Purpose |
|-----------|---------|---------|
| `output_dir: Path` | `assets.py` | Build output location |
| `dev_mode: bool` | `assets.py` | Development vs production |

### Protocol Extension (Phase 2)

```python
# bengal/protocols/core.py - additions
@runtime_checkable
class PageLike(Protocol):
    # ... existing ...
    @property
    def metadata(self) -> dict[str, Any]: ...
    @property
    def tags(self) -> list[str] | None: ...

@runtime_checkable  
class SiteLike(Protocol):
    # ... existing ...
    @property
    def output_dir(self) -> Path: ...
    @property
    def dev_mode(self) -> bool: ...
```

---

## Problem Categories

### Category 1: Config | dict Union (6+ instances)

**Pattern**: Functions expect `dict[str, Any]` but receive `Config | dict[str, Any]`

```python
# bengal/autodoc/orchestration/orchestrator.py:93
self.normalized_config = normalize_autodoc_config(site.config)
# Error: Expected `dict[str, Any]`, found `Config | dict[str, Any]`
```

**Root cause**: `Site.config` is typed as `Config | dict[str, Any]` but functions only accept `dict`.

**Solution**: Update function signatures to accept `Config | dict[str, Any]` or use a protocol.

### Category 2: hasattr Doesn't Narrow (22 instances)

**Pattern**: After `hasattr(obj, "method")`, calling `obj.method()` fails.

```python
# (Path updated 2026-02-14: bengal/build/ does not exist; template detection in orchestration/incremental/ or effects/)
if hasattr(engine, "clear_template_cache"):
    engine.clear_template_cache(template_names)  # Error: Object of type `object` is not callable
```

**Root cause**: ty can't narrow `object` to `HasClearTemplateCache` after `hasattr`.

**Solution**: Use `isinstance` with protocols or explicit casts.

### Category 3: __file__ May Be None (14 instances)

**Pattern**: `Path(module.__file__)` fails because `__file__` can be `str | None`.

```python
# bengal/cli/commands/theme.py:182
pkg_dir = Path(bengal.__file__).parent / "themes"
# Error: Expected `str | PathLike[str]`, found `str | None`
```

**Solution**: Guard with assertion or check:
```python
assert bengal.__file__ is not None
pkg_dir = Path(bengal.__file__).parent / "themes"
```

### Category 4: Stale type: ignore Comments (42 instances)

**Pattern**: Old `# type: ignore` directives that are no longer needed.

```python
# bengal/assets/js_bundler.py:89
from jsmin import jsmin  # type: ignore[import-untyped]  # UNUSED
```

**Solution**: Remove or update these comments.

### Category 5: Protocol Self-Type Mismatches (8+ instances)

**Pattern**: Method signatures use `Self` but implementation passes `HtmlRendererProtocol`.

```python
# bengal/parsing/backends/patitas/renderers/html.py
def _render_block(self: HtmlRendererProtocol, node: Block, sb: StringBuilder) -> None:
# Error: Expected `HtmlRendererProtocol`, found `Self@render`
```

**Solution**: Use proper `Self` typing or fix protocol definitions.

### Category 6: Async/Sync Override Mismatch (5 instances)

**Pattern**: Sync method overrides async method from parent class.

```python
# bengal/cli/dashboard/base.py:123
def action_quit(self) -> None:  # Should be async
# Error: Invalid override - App.action_quit is async
```

**Solution**: Make override async or use different pattern.

---

## Proposed Solutions

### Phase 0: Protocol Migration (HIGH IMPACT - 3-4 hours)

**This is the real fix.** Migrate from concrete types to existing protocols.

#### 0.1 Site → SiteLike Migration

169 functions use `site: Site`. Many only need `SiteLike`:

```python
# Before (169 instances)
def register_functions(env: TemplateEnvironment, site: Site) -> None:
    baseurl = site.baseurl  # Only uses .baseurl, .config, .pages
    ...

# After
from bengal.protocols import SiteLike

def register_functions(env: TemplateEnvironment, site: SiteLike) -> None:
    baseurl = site.baseurl  # Works! SiteLike has .baseurl
    ...
```

**Impact**: Many `invalid-argument-type` errors where `AssetSiteLike` or `Self@...` is passed.

#### 0.2 Page → PageLike Migration  

130 functions use `page: Page`. Many only need `PageLike`:

```python
# Before (130 instances)
def render_page_card(page: Page) -> str:
    return f"<h1>{page.title}</h1>"  # Only uses .title, .href

# After
from bengal.protocols import PageLike

def render_page_card(page: PageLike) -> str:
    return f"<h1>{page.title}</h1>"  # Works!
```

#### 0.3 Section → SectionLike Migration

30 functions use `section: Section`:

```python
# Before
def build_nav(section: Section) -> list[dict]: ...

# After  
from bengal.protocols import SectionLike

def build_nav(section: SectionLike) -> list[dict]: ...
```

### Phase 1: Quick Wins (1 hour)

#### 1.1 Remove Stale Ignore Comments

42 instances of `unused-ignore-comment`. Simple find-and-remove:

```bash
# Files with stale ignores (sample)
bengal/assets/js_bundler.py:89
bengal/cli/base.py:242, 343
bengal/cli/commands/collections.py:292
```

#### 1.2 Guard __file__ Access

Add assertions before `Path(module.__file__)`:

```python
# Before
pkg_dir = Path(bengal.__file__).parent

# After
if bengal.__file__ is None:
    raise RuntimeError("Bengal package __file__ is None (frozen/namespace package?)")
pkg_dir = Path(bengal.__file__).parent
```

**Files**: `cli/commands/theme.py` (5), `build/detectors/template.py` (2), `assets/pipeline.py` (2)

### Phase 2: Config Protocol (1-2 hours)

#### Problem

`Site.config` is `Config | dict[str, Any]`, but many functions only accept `dict[str, Any]`.

#### Solution: ConfigLike Protocol

Add to `bengal/protocols/core.py`:

```python
class ConfigLike(Protocol):
    """Protocol for objects that provide dict-like config access."""
    
    def get(self, key: str, default: Any = None) -> Any: ...
    def __getitem__(self, key: str) -> Any: ...
    def __contains__(self, key: str) -> bool: ...
    
    @property
    def raw(self) -> dict[str, Any]:
        """Return underlying dict for functions requiring raw dict."""
        ...
```

#### Migration

```python
# Before
def normalize_autodoc_config(site_config: dict[str, Any]) -> dict[str, Any]:

# After (Option A: Accept both)
def normalize_autodoc_config(site_config: ConfigLike | dict[str, Any]) -> dict[str, Any]:
    config_dict = site_config.raw if hasattr(site_config, "raw") else site_config

# After (Option B: Always use .raw at call site)
self.normalized_config = normalize_autodoc_config(site.config.raw if hasattr(site.config, "raw") else site.config)
```

### Phase 3: hasattr Narrowing (2-3 hours)

#### Problem

ty doesn't narrow types after `hasattr()` checks. There are 30+ instances.

#### Solution A: TypeGuard Functions

```python
from typing import TypeGuard

class HasClearTemplateCache(Protocol):
    def clear_template_cache(self, names: list[str]) -> None: ...

def has_clear_template_cache(obj: object) -> TypeGuard[HasClearTemplateCache]:
    return hasattr(obj, "clear_template_cache") and callable(getattr(obj, "clear_template_cache"))

# Usage
if has_clear_template_cache(engine):
    engine.clear_template_cache(template_names)  # ty knows it's callable
```

#### Solution B: Protocol + isinstance

```python
from typing import runtime_checkable

@runtime_checkable
class HasClearTemplateCache(Protocol):
    def clear_template_cache(self, names: list[str]) -> None: ...

# Usage (runtime_checkable allows isinstance)
if isinstance(engine, HasClearTemplateCache):
    engine.clear_template_cache(template_names)
```

#### Files to Update

| File | Pattern | Solution |
|------|---------|----------|
| `build/detectors/template.py:142` | `hasattr(engine, "clear_template_cache")` | TypeGuard |
| `cli/dashboard/app.py:232` | `hasattr(self.screen, "action_rebuild")` | Protocol |
| `cli/dashboard/screens.py:48` | `hasattr(self.app, "config_changed_signal")` | Protocol |
| `collections/validator.py:289` | `hasattr(e, "errors")` | TypeGuard |
| `core/page/relationships.py:107` | `hasattr(self, "walk")` | Self-type fix |

### Phase 4: Async Override Fixes (30 min)

#### Problem

```python
# bengal/cli/dashboard/base.py
def action_quit(self) -> None:  # Sync
    self.exit()

# Parent class (textual App)
async def action_quit(self) -> None:  # Async
```

#### Solution

```python
async def action_quit(self) -> None:
    """Quit the dashboard."""
    self.exit()
```

**Files**: `cli/dashboard/base.py:123`, `cli/dashboard/serve.py:501`

### Phase 5: Protocol Self-Type Fixes (1 hour)

#### Problem

Renderers use `self: HtmlRendererProtocol` annotation but this conflicts with `Self`.

```python
def _render_block(self: HtmlRendererProtocol, node: Block, sb: StringBuilder) -> None:
```

#### Solution

Remove explicit self-type annotation and let Protocol inheritance handle it:

```python
# The class already implements HtmlRendererProtocol through inheritance
def _render_block(self, node: Block, sb: StringBuilder) -> None:
```

---

## Implementation Plan

### Priority Order (by error reduction)

| Phase | What | Errors Fixed | Time | Complexity |
|-------|------|--------------|------|------------|
| **0. Protocol migration** | **Use PageLike/SiteLike/SectionLike** | **~60-80** | **3-4 hours** | **Medium** |
| 1. Stale ignores | Remove `# type: ignore` | 42 | 30 min | Low |
| 2. __file__ guards | Assert `__file__` not None | 14 | 30 min | Low |
| 3. Config protocol | Add `ConfigLike` | 6 | 1 hour | Medium |
| 4. Async overrides | Fix `action_quit` | 5 | 30 min | Low |
| 5. hasattr narrowing | TypeGuard functions | 22 | 2 hours | Medium |
| 6. Protocol self-types | Fix `Self` annotations | 8 | 1 hour | Medium |

**Total**: ~160-180 errors (47-53% of total), ~8-10 hours

### The Big Win: Phase 0

Phase 0 is the highest-impact change. By migrating ~330 function signatures from concrete types to protocols:

- `site: Site` → `site: SiteLike` (169 functions)
- `page: Page` → `page: PageLike` (130 functions)  
- `section: Section` → `section: SectionLike` (30 functions)

This eliminates errors like:
- `Expected Site, found AssetSiteLike`
- `Expected Page, found Self@render`
- `Expected Section, found (<Protocol with members 'href'> & ...)`

### Remaining Errors (Phase 2 RFC)

After all phases, ~160 errors may remain. These require deeper analysis:

- Complex generic type mismatches
- Third-party library type issues
- Fundamental architecture decisions

---

## Success Criteria

| Metric | Current | After Phase 0 | After All Phases | Target |
|--------|---------|---------------|------------------|--------|
| Total ty errors | 339 | ~260 | ~160 | <100 |
| `site: Site` (should be SiteLike) | 169 | ~50 | ~20 | <20 |
| `page: Page` (should be PageLike) | 130 | ~40 | ~15 | <15 |
| `unused-ignore-comment` | 42 | 42 | 0 | 0 |
| `call-non-callable` from hasattr | 22 | 22 | <5 | 0 |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| TypeGuard functions add overhead | Only use where needed; prefer `isinstance` with `runtime_checkable` |
| Breaking async changes | Run full test suite after each change |
| Protocol proliferation | Add protocols to existing `bengal/protocols/` only when reused |

---

## Files to Change (by Phase)

### Phase 0: Protocol Migration (HIGHEST PRIORITY)

**Top files using `site: Site` that should use `SiteLike`:**
- `bengal/rendering/template_functions/*.py` (40+ files)
- `bengal/health/validators/*.py` (15 files)
- `bengal/orchestration/*.py` (12 files)
- `bengal/postprocess/*.py` (8 files)

**Top files using `page: Page` that should use `PageLike`:**
- `bengal/rendering/pipeline/core.py` (12 instances!)
- `bengal/rendering/renderer.py` (7 instances)
- `bengal/debug/explainer.py` (8 instances)
- `bengal/analysis/graph/knowledge_graph.py` (7 instances)
- `bengal/postprocess/social_cards.py` (5 instances)

**Files using `section: Section` that should use `SectionLike`:**
- `bengal/orchestration/section.py` (9 instances)
- `bengal/content_types/strategies.py` (7 instances)

### Phase 1: Stale Ignores
- `bengal/assets/js_bundler.py`
- `bengal/cli/base.py`
- `bengal/cli/commands/collections.py`
- (37 more files - run `ty check` with `--fix` if available)

### Phase 2: __file__ Guards
- `bengal/cli/commands/theme.py` (lines 182, 272, 508, 538)
- *(bengal/build/ not created; verify template detector location)*
- `bengal/assets/pipeline.py` (line 455)

### Phase 3: Config Protocol
- `bengal/protocols/core.py` (add ConfigLike)
- `bengal/autodoc/orchestration/orchestrator.py`
- `bengal/autodoc/orchestration/utils.py`
- `bengal/cli/commands/health.py`
- `bengal/rendering/template_context.py`
- `bengal/version_config.py`

### Phase 4: Async Overrides
- `bengal/cli/dashboard/base.py:123`
- `bengal/cli/dashboard/serve.py:501`

### Phase 5: hasattr Narrowing
- *(bengal/build/detectors/ not created; verify template detector location)*
- `bengal/cli/dashboard/app.py:232`
- `bengal/cli/dashboard/screens.py:48,612`
- `bengal/collections/validator.py:289`
- `bengal/core/page/relationships.py:107`

---

## Appendix: Full ty Error Breakdown

```
105 [invalid-argument-type]     - Type mismatches in function calls
 55 [unresolved-attribute]      - Accessing missing attributes
 42 [unused-ignore-comment]     - Stale type: ignore comments
 24 [invalid-assignment]        - Wrong types in assignments
 22 [call-non-callable]         - hasattr doesn't prove callable
 20 [possibly-missing-attribute] - Optional attribute access
 17 [invalid-return-type]       - Return type mismatches
 14 [unknown-argument]          - Unknown keyword arguments
 11 [invalid-type-arguments]    - Wrong generic type parameters
  5 [invalid-method-override]   - Async/sync override conflicts
  4 [unsupported-operator]      - Operator type mismatches
  4 [unresolved-import]         - Missing imports
  4 [not-subscriptable]         - Subscripting non-subscriptable
  4 [not-iterable]              - Iterating non-iterable
  3 [missing-argument]          - Missing required arguments
  2 [unresolved-reference]      - Undefined names
  2 [too-many-positional-arguments] - Too many args
  1 [no-matching-overload]      - No overload matches
---
339 TOTAL
```

---

## References

- [PEP 544 - Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [PEP 647 - User-Defined Type Guards](https://peps.python.org/pep-0647/)
- [ty documentation](https://docs.astral.sh/ty/)
- Bengal `bengal/protocols/` - Existing protocol infrastructure
- Bengal `bengal/config/accessor.py` - Existing Config accessor
