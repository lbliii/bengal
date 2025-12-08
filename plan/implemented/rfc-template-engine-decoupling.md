# RFC: TemplateEngine Package Decoupling

## Metadata

```yaml
Title: Decouple TemplateEngine into Focused Package Structure
Author: AI + Human reviewer
Date: 2025-12-08
Updated: 2025-12-08 (added codebase analysis findings)
Implemented: 2025-12-08
Status: Implemented
Confidence: 95%
```

---

## Discovery Summary (2025-12-08 Update)

Analysis of the codebase revealed that partial decoupling has already been attempted but not completed:

| Module | Status | Issue |
|--------|--------|-------|
| `template_engine/environment.py` | ✅ Exists | Has `create_jinja_environment()` and `resolve_theme_chain()` but **TemplateEngine doesn't use them** |
| `template_engine/asset_url.py` | ✅ Exists | Has `AssetURLMixin` but **TemplateEngine re-implements inline** |
| `template_engine/url_helpers.py` | ✅ Exists | Has `url_for()`, `with_baseurl()` but **TemplateEngine wraps with pass-through methods** |
| `template_engine/menu.py` | ❌ Missing | Menu caching still inline in TemplateEngine |
| `template_engine/manifest.py` | ❌ Missing | Manifest loading still inline in TemplateEngine |

**Key Finding**: The refactoring is ~50% complete but abandoned. The main `TemplateEngine` class still contains duplicate implementations instead of using the extracted modules.

**Priority Matrix**:

| Action | Impact | Effort | Priority |
|--------|--------|--------|----------|
| Wire TemplateEngine to use existing `environment.py` | High | Low | 🔴 P0 |
| Wire TemplateEngine to use existing `asset_url.py` | High | Low | 🔴 P0 |
| Consolidate 6× `file://` path code | Medium | Low | 🟡 P1 |
| Extract MenuProvider to `menu.py` | Medium | Low | 🟡 P1 |
| Extract ManifestLoader to `manifest.py` | Low | Low | 🟢 P2 |

---

## 1. Problem Statement

### Current State

The `TemplateEngine` class in `bengal/rendering/template_engine.py` is **861 lines**, significantly exceeding Bengal's 400-line threshold for single-file modules.

**Evidence**:
- File: `bengal/rendering/template_engine.py:1-861`
- Import count: 8 internal bengal imports + numerous stdlib/third-party
- Method count: 15+ public/private methods
- The `_asset_url()` method alone spans ~200 lines (lines 515-730)

### Pain Points

1. **Violates Architecture Rules**: Exceeds 400-line threshold documented in `architecture-patterns.mdc`
2. **Multiple Responsibilities** (SRP violation):
   - Jinja2 environment creation and configuration
   - Theme chain resolution
   - Asset manifest loading and caching
   - Menu retrieval and caching
   - URL generation with baseurl handling
   - File:// protocol relative path computation
   - Template profiling integration
   - Bytecode cache management
3. **Testing Difficulty**: Hard to unit test individual concerns in isolation
4. **Maintenance Burden**: Changes to asset URLs risk breaking menu caching logic
5. **Extensive Code Duplication** (verified by codebase analysis):
   - Theme resolution duplicated between `template_engine.py:291-371` and `template_engine/environment.py:28-122`
   - Asset URL helper duplicated between `template_engine.py:515-729` and `template_engine/asset_url.py:87-220`
   - The `file://` relative path calculation repeated **6 times** within `_asset_url()` (lines 564-576, 599-617, 635-656, 675-698, 706-727)
   - `url_helpers.py` provides functions that `TemplateEngine` wraps with pass-through methods adding no value

### User Impact

- **Theme developers**: Difficult to understand template system structure
- **Contributors**: High cognitive load when modifying rendering layer
- **Maintainers**: Risk of regression when touching large monolithic class

---

## 2. Goals & Non-Goals

### Goals

1. **G1**: Reduce `TemplateEngine` to <400 lines by extracting focused modules
2. **G2**: Single Responsibility Principle - each module handles one concern
3. **G3**: Improve testability with isolated, mockable components
4. **G4**: Eliminate code duplication between `template_engine.py` and `template_engine/` submodules
5. **G5**: Maintain backward compatibility - no public API changes

### Non-Goals

- **NG1**: Not changing template function registration architecture (separate concern)
- **NG2**: Not refactoring the Jinja2 usage patterns (internal to each module)
- **NG3**: Not addressing VirtualAutodocOrchestrator duplication (follow-up RFC - see Section 10 for findings)
- **NG4**: Not consolidating all URL logic codebase-wide (separate RFC)

---

## 3. Architecture Impact

### Affected Subsystems

- **Rendering** (`bengal/rendering/`): Primary impact
  - `template_engine.py` → converted to package
  - `template_engine/` submodules expanded
  - `pipeline/` imports updated

- **Orchestration** (`bengal/orchestration/`): Minor import updates
  - `render.py` creates TemplateEngine instances

- **Server** (`bengal/server/`): Minor import updates
  - Dev server may reference TemplateEngine

- **Autodoc** (`bengal/autodoc/`): No changes (future RFC)
  - VirtualAutodocOrchestrator creates own environment

### Integration Points

```
RenderingPipeline
    └── TemplateEngine (facade)
            ├── EnvironmentFactory (creates Jinja2 env)
            ├── AssetURLResolver (asset_url logic)
            ├── MenuProvider (menu caching)
            ├── ManifestLoader (asset manifest)
            └── URLHelpers (baseurl, url_for)
```

---

## 4. Design Options

### Option A: Package with Composition (Recommended)

**Description**: Convert `template_engine.py` to a package. Main `TemplateEngine` class becomes a thin facade that composes focused helper classes.

```
bengal/rendering/template_engine/
├── __init__.py           # Re-exports TemplateEngine
├── core.py               # TemplateEngine facade (~150 lines)
├── environment.py        # Jinja2 Environment factory (~200 lines)
├── asset_url.py          # AssetURLResolver class (~250 lines)
├── menu.py               # MenuProvider class (~80 lines)
├── manifest.py           # ManifestLoader class (~100 lines)
└── url_helpers.py        # Existing file, expanded (~80 lines)
```

**Pros**:
- Clear separation of concerns
- Each module independently testable
- Follows existing Page package pattern (`bengal/core/page/`)
- Backward compatible (same public API)

**Cons**:
- More files to navigate
- Slightly more complex initialization

**Complexity**: Moderate
**Evidence**: Pattern proven in `bengal/core/page/` (9 files, well-organized)

---

### Option B: Mixin-Based Decomposition

**Description**: Keep single file but extract concerns into mixins that TemplateEngine inherits.

```python
class TemplateEngine(
    AssetURLMixin,
    MenuProviderMixin,
    ManifestMixin,
    EnvironmentMixin,
):
    """Thin coordinator combining all mixins."""
```

**Pros**:
- Single file (easier navigation)
- Familiar mixin pattern (used in Page, Site)

**Cons**:
- File still >400 lines (just reorganized)
- Harder to test mixins in isolation
- Mixin order dependencies possible

**Complexity**: Simple
**Evidence**: Pattern used in `bengal/core/site/` but site still has coupling issues

---

### Option C: Functional Decomposition

**Description**: Extract pure functions into utility modules, keep TemplateEngine minimal.

```python
# bengal/rendering/template_engine.py (~200 lines)
from bengal.rendering.asset_resolution import resolve_asset_url
from bengal.rendering.menu_cache import get_cached_menu

class TemplateEngine:
    def _asset_url(self, path):
        return resolve_asset_url(path, self.site, self._manifest_cache)
```

**Pros**:
- Maximum testability (pure functions)
- Clear dependency injection points

**Cons**:
- State management becomes awkward
- Doesn't match existing codebase patterns
- More parameter passing

**Complexity**: Moderate
**Evidence**: Less consistent with existing patterns

---

### Recommended: Option A (Package with Composition)

**Reasoning**:
1. **Consistency**: Matches `bengal/core/page/` package pattern
2. **Testability**: Each class can be instantiated and tested independently
3. **Maintainability**: Clear ownership of each concern
4. **Future-proof**: Easy to add new concerns (e.g., i18n URL handling)

---

## 5. Detailed Design (Option A)

### New Module Structure

```
bengal/rendering/template_engine/
├── __init__.py           # Public API exports
├── core.py               # TemplateEngine facade class
├── environment.py        # EnvironmentFactory class
├── asset_url.py          # AssetURLResolver class  
├── menu.py               # MenuProvider class
├── manifest.py           # ManifestLoader class
└── url_helpers.py        # url_for, with_baseurl (existing, expanded)
```

### API Changes

**Public API (unchanged)**:
```python
# Before and after - same usage
from bengal.rendering.template_engine import TemplateEngine

engine = TemplateEngine(site, profile_templates=False)
html = engine.render("page.html", context)
```

**Internal changes**:
```python
# bengal/rendering/template_engine/core.py
class TemplateEngine:
    """Facade coordinating template rendering components."""

    def __init__(self, site: Any, profile_templates: bool = False):
        self.site = site
        self._profile_templates = profile_templates

        # Compose helpers
        self._env_factory = EnvironmentFactory(site)
        self._asset_resolver = AssetURLResolver(site)
        self._menu_provider = MenuProvider(site)
        self._manifest_loader = ManifestLoader(site.output_dir)

        # Create environment
        self.env = self._env_factory.create()
        self.template_dirs = self._env_factory.template_dirs

        # Register globals
        self._register_globals()

    def render(self, template_name: str, context: dict) -> str:
        """Render template (unchanged signature)."""
        # ... delegation to env.get_template().render()
```

### Module Responsibilities

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `core.py` | ~150 | Facade, render(), render_string(), profiling |
| `environment.py` | ~200 | Jinja2 Environment creation, theme chain, bytecode cache |
| `asset_url.py` | ~250 | Asset URL resolution, file:// handling, fingerprinting |
| `menu.py` | ~80 | Menu dict caching, i18n-aware menu retrieval |
| `manifest.py` | ~100 | Asset manifest loading, mtime-based caching |
| `url_helpers.py` | ~80 | url_for(), with_baseurl() |

**Total**: ~860 lines → 6 files averaging ~143 lines each

### Data Flow

```
render(template_name, context)
    │
    ├── env.get_template(template_name)  [environment.py]
    │
    ├── context["site"] = self.site
    │
    ├── template.render(**context)
    │       │
    │       ├── {{ asset_url("css/style.css") }}
    │       │       └── AssetURLResolver.resolve()  [asset_url.py]
    │       │               └── ManifestLoader.get_entry()  [manifest.py]
    │       │
    │       └── {{ get_menu("main") }}
    │               └── MenuProvider.get_menu()  [menu.py]
    │
    └── return html
```

### Error Handling

No new exceptions. Existing error handling preserved:
- `TemplateNotFound` from Jinja2 (unchanged)
- Logging via `bengal.utils.logger` (unchanged)
- Graceful fallbacks for missing manifest entries (unchanged)

### Configuration

No new configuration options. Existing config paths:
- `site.config["cache_templates"]` → used in `environment.py`
- `site.config["dev_server"]` → used in `environment.py`, `asset_url.py`
- `site.config["strict_mode"]` → used in `environment.py`

### Testing Strategy

```python
# tests/unit/rendering/template_engine/test_asset_url.py
class TestAssetURLResolver:
    def test_asset_url_with_manifest(self):
        """Test asset URL resolution when manifest exists."""
        resolver = AssetURLResolver(mock_site)
        resolver._manifest_loader = MockManifestLoader({"css/style.css": ...})

        url = resolver.resolve("css/style.css")
        assert url == "/assets/css/style.abc123.css"

    def test_file_protocol_relative_paths(self):
        """Test relative path computation for file:// baseurl."""
        ...

# tests/unit/rendering/template_engine/test_menu.py
class TestMenuProvider:
    def test_menu_caching(self):
        """Test menu dicts are cached."""
        ...
```

---

## 6. Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Clear module responsibilities | Single-file simplicity |
| Independent testability | Slightly more files to navigate |
| Follows 400-line rule | One-time refactoring cost |
| Easier onboarding | Minor import changes in dependents |

### Risks

**Risk 1**: Subtle behavioral changes during extraction
- **Likelihood**: Low
- **Impact**: Medium (could break template rendering)
- **Mitigation**: Comprehensive test coverage before refactoring, run full site test suite

**Risk 2**: Performance regression from additional object creation
- **Likelihood**: Very Low
- **Impact**: Low (initialization only, not per-render)
- **Mitigation**: Profile before/after, lazy initialization if needed

**Risk 3**: Breaking internal consumers (Autodoc, Pipeline)
- **Likelihood**: Low
- **Impact**: Low (internal APIs, easy to update)
- **Mitigation**: Search for all `from bengal.rendering.template_engine import` usages

---

## 7. Performance & Compatibility

### Performance Impact

- **Build time**: Negligible (object creation overhead ~0.1ms once per build)
- **Memory**: Negligible (same data, different organization)
- **Cache implications**: None (template bytecode cache unchanged)

### Compatibility

- **Breaking changes**: None (public API preserved)
- **Migration path**: Drop-in replacement
- **Deprecation timeline**: N/A

---

## 8. Migration & Rollout

### Implementation Phases

**Phase 1: Audit Existing Modules** (30 min)
- Verify `template_engine/environment.py` has complete theme chain logic
- Verify `template_engine/asset_url.py` has complete asset URL logic
- Verify `template_engine/url_helpers.py` has url_for/with_baseurl
- Document any gaps between existing modules and inline implementations

**Phase 2: Consolidate Duplicates** (1-2 hours)
- Delete duplicate `_resolve_theme_chain()` from `template_engine.py`
- Delete duplicate `_read_theme_extends()` from `template_engine.py`
- Wire TemplateEngine to use `environment.create_jinja_environment()`
- Wire TemplateEngine to inherit or compose `AssetURLMixin` from `asset_url.py`
- Remove pass-through wrappers for url_for/with_baseurl

**Phase 3: Extract Remaining Concerns** (1-2 hours)
- Extract `MenuProvider` to `menu.py` (new file)
- Extract `ManifestLoader` to `manifest.py` (new file)
- Extract file:// path calculation to helper function
- Consolidate 6× inline `file://` handling into single helper

**Phase 4: Facade Refactoring** (1-2 hours)
- Move remaining `TemplateEngine` logic to `core.py`
- Convert to facade pattern with composition
- Update internal imports across `bengal/`
- Delete old `template_engine.py`

**Phase 5: Verification** (1 hour)
- Run full test suite (`pytest tests/`)
- Build example sites (`bengal build` on `site/`)
- Profile for performance regression
- Verify no changes to public API

### Rollout Strategy

- **Feature flag**: No (internal refactoring)
- **Beta period**: N/A
- **Documentation updates**:
  - Update architecture docs if they reference template_engine.py
  - No user-facing documentation changes needed

---

## 9. Open Questions

- [x] **Q1**: Should `AssetURLResolver` be usable standalone (for Autodoc)?
  - **Answer**: Yes, design for reuse. Future RFC will have Autodoc use it.

- [ ] **Q2**: Should we also extract template function registration?
  - **Context**: `register_all()` in `template_functions.py` is called from environment creation
  - **Recommendation**: Keep as-is for this RFC, consider in future

- [ ] **Q3**: Should `url_for` and `with_baseurl` move to a shared `bengal/utils/url_resolution.py`?
  - **Context**: URL logic exists in multiple places (RenderOrchestrator, template_engine, etc.)
  - **Recommendation**: Separate RFC for URL consolidation

- [ ] **Q4**: Should existing `template_engine/environment.py` and `template_engine/asset_url.py` be adopted rather than creating new files?
  - **Context**: These modules already exist but `TemplateEngine` doesn't use them. The class re-implements their logic inline.
  - **Analysis**: `environment.py` has `create_jinja_environment()` and `resolve_theme_chain()` - identical to private methods in TemplateEngine
  - **Analysis**: `asset_url.py` has `AssetURLMixin` - cleaner version of `_asset_url()` but not inherited
  - **Recommendation**: Yes, delete duplicates in `template_engine.py`, use extracted modules. This RFC should document migrating to existing modules, not creating new ones.

- [ ] **Q5**: How should `file://` protocol handling be consolidated?
  - **Context**: Same relative path calculation appears 6× in `_asset_url()`
  - **Pattern detected**:
    ```python
    # Repeated at lines 564-576, 599-617, 635-656, 675-698, 706-727
    if depth > 0:
        relative_prefix = "/".join([".."] * depth)
        return f"{relative_prefix}/{path}"
    else:
        return f"./{path}"
    ```
  - **Recommendation**: Extract to `compute_relative_path(depth: int, path: str) -> str` helper

- [ ] **Q6**: Should VirtualAutodocOrchestrator share the template environment?
  - **Context**: `autodoc/virtual_orchestrator.py:68-139` creates separate Environment
  - **Impact**: Misses bytecode cache, strict_mode, shared filters/functions
  - **Recommendation**: Follow-up RFC after this refactoring stabilizes

---

## 10. Evidence Summary

### Code Evidence

| Claim | Evidence | Confidence |
|-------|----------|------------|
| TemplateEngine exceeds 400 lines | `bengal/rendering/template_engine.py:1-861` (861 lines) | 100% |
| _asset_url is ~200 lines | `bengal/rendering/template_engine.py:515-730` | 100% |
| Page package pattern exists | `bengal/core/page/` (9 files, well-organized) | 100% |
| Site uses mixin pattern | `bengal/core/site/core.py:60-68` (7 mixins) | 100% |
| URL helpers already exist | `bengal/rendering/template_engine/url_helpers.py` exists | 100% |

### Duplication Evidence (Discovered 2025-12-08)

| Duplication | Location A | Location B | Status |
|-------------|-----------|------------|--------|
| Theme chain resolution | `template_engine.py:291-313` (`_resolve_theme_chain`) | `template_engine/environment.py:28-57` (`resolve_theme_chain`) | **Identical logic** |
| Theme extends reading | `template_engine.py:314-371` (`_read_theme_extends`) | `template_engine/environment.py:60-122` (`read_theme_extends`) | **Identical logic** |
| Asset URL resolution | `template_engine.py:515-729` (`_asset_url`) | `template_engine/asset_url.py:87-220` (`AssetURLMixin._asset_url`) | **Mixin exists but unused** |
| file:// path calculation | `template_engine.py:564-576, 599-617, 635-656, 675-698, 706-727` | (repeated 6× inline) | **Internal duplication** |
| URL helpers | `template_engine.py:483-513` (`_url_for`, `_with_baseurl`) | `template_engine/url_helpers.py:20-95` | **Wrapper adds no value** |

### Related Subsystem Coupling (Future Work)

| Subsystem | Issue | Recommendation |
|-----------|-------|----------------|
| VirtualAutodocOrchestrator | Creates own Jinja2 Environment at `autodoc/virtual_orchestrator.py:68-139` | Accept TemplateEngine instance or use shared factory |
| VirtualAutodocOrchestrator | Duplicates template directory discovery | Reuse `EnvironmentFactory` after extraction |
| VirtualAutodocOrchestrator | Misses bytecode cache, shared filters | Integrate with main template system |

**Evidence for VirtualAutodocOrchestrator duplication**:
```python
# autodoc/virtual_orchestrator.py:68-107
def _create_template_environment(self) -> Environment:
    """Create Jinja2 environment for HTML templates."""
    # ... creates entirely separate environment
    env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=select_autoescape(["html", "htm", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # No bytecode cache
    # No shared template functions from register_all()
    # No strict_mode support
```

### Test Evidence

- Existing tests in `tests/unit/rendering/` validate current behavior
- No changes to public API means existing tests remain valid

### Architecture Rule Evidence

- 400-line threshold: `architecture-patterns.mdc` Section 5
- Package conversion pattern: Documented for Page model

---

## Appendix: File Mapping

### Current State (Partially Refactored - Inconsistent)

```
bengal/rendering/template_engine.py (861 lines) ← Main file, still monolithic
├── TemplateEngine.__init__() - lines 98-133
├── TemplateEngine._create_environment() - lines 134-289    ← DUPLICATE of environment.py
├── TemplateEngine._resolve_theme_chain() - lines 291-313   ← DUPLICATE of environment.py
├── TemplateEngine._read_theme_extends() - lines 315-371    ← DUPLICATE of environment.py
├── TemplateEngine.render() - lines 373-427
├── TemplateEngine.render_string() - lines 447-462
├── TemplateEngine._url_for() - lines 483-497              ← WRAPPER for url_helpers.py
├── TemplateEngine._with_baseurl() - lines 499-513         ← WRAPPER for url_helpers.py
├── TemplateEngine._asset_url() - lines 515-729            ← DUPLICATE of asset_url.py (+ file:// 6×)
├── TemplateEngine._get_menu() - lines 739-770             ← TO EXTRACT
├── TemplateEngine._get_menu_lang() - lines 772-789        ← TO EXTRACT
├── TemplateEngine._get_manifest_entry() - lines 812-817   ← TO EXTRACT
├── TemplateEngine._load_asset_manifest() - lines 819-840  ← TO EXTRACT
└── ... (filters, helpers)

bengal/rendering/template_engine/                          ← Package exists but UNUSED
├── __init__.py (empty or minimal)
├── environment.py (280 lines)                             ← EXISTS - has create_jinja_environment()
│   ├── resolve_theme_chain()                              ← EXISTS - duplicated in main file
│   ├── read_theme_extends()                               ← EXISTS - duplicated in main file
│   └── create_jinja_environment()                         ← EXISTS - not used by TemplateEngine
├── asset_url.py (220 lines)                               ← EXISTS - has AssetURLMixin
│   ├── normalize_and_validate_asset_path()                ← EXISTS - duplicated in main file
│   ├── compute_relative_asset_path()                      ← EXISTS - duplicated 6× in main file
│   └── class AssetURLMixin                                ← EXISTS - not inherited by TemplateEngine
└── url_helpers.py (95 lines)                              ← EXISTS - has url_for, with_baseurl
    ├── url_for()                                          ← EXISTS - wrapped by _url_for()
    └── with_baseurl()                                     ← EXISTS - wrapped by _with_baseurl()
```

### Target State (Package - Fully Composed)

```
bengal/rendering/template_engine/
├── __init__.py (20 lines)
│   └── from .core import TemplateEngine
│
├── core.py (150 lines)                                    ← NEW - thin facade
│   └── class TemplateEngine
│       ├── __init__() - creates composed helpers
│       ├── render() - delegates to env
│       ├── render_string() - delegates to env
│       ├── get_template_profile()
│       └── invalidate_menu_cache()
│
├── environment.py (200 lines)                             ← EXISTS - adopt as-is
│   └── Functions (already extracted):
│       ├── resolve_theme_chain()
│       ├── read_theme_extends()
│       └── create_jinja_environment()
│
├── asset_url.py (180 lines)                               ← EXISTS - consolidate file:// handling
│   └── class AssetURLResolver (refactored from mixin)
│       ├── resolve(path, page_context) → str
│       ├── _compute_relative_path(depth, path) → str      ← NEW - consolidate 6× duplication
│       └── ... (existing methods)
│
├── menu.py (80 lines)                                     ← NEW - extract from main
│   └── class MenuProvider
│       ├── get_menu(name) → list[dict]
│       ├── get_menu_lang(name, lang) → list[dict]
│       └── invalidate_cache()
│
├── manifest.py (100 lines)                                ← NEW - extract from main
│   └── class ManifestLoader
│       ├── get_entry(logical_path) → AssetManifestEntry | None
│       ├── _load_manifest()
│       └── _is_stale()
│
└── url_helpers.py (80 lines)                              ← EXISTS - use directly (no wrappers)
    ├── url_for(page, site) → str
    ├── with_baseurl(path, site) → str
    └── filter_dateformat()                                ← EXISTS - already here
```

### Summary of Changes

| File | Current | Target | Action |
|------|---------|--------|--------|
| `template_engine.py` | 861 lines (monolithic) | DELETE | Remove after migration |
| `template_engine/__init__.py` | Minimal | 20 lines | Re-export TemplateEngine |
| `template_engine/core.py` | N/A | 150 lines | NEW - facade class |
| `template_engine/environment.py` | 280 lines (unused) | 200 lines | ADOPT - wire to facade |
| `template_engine/asset_url.py` | 220 lines (unused mixin) | 180 lines | ADOPT - consolidate file:// |
| `template_engine/menu.py` | N/A | 80 lines | NEW - extract from main |
| `template_engine/manifest.py` | N/A | 100 lines | NEW - extract from main |
| `template_engine/url_helpers.py` | 95 lines | 80 lines | KEEP - remove wrappers in main |
