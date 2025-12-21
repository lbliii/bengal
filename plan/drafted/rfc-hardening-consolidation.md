# RFC: Hardening Phase - Codebase Consolidation

**Status**: Evaluated  
**Created**: 2025-12-21  
**Author**: AI Assistant  
**Confidence**: 92% 🟢

---

## Executive Summary

Bengal has reached a feature-rich state and is entering a hardening/baking phase. This RFC proposes consolidating duplicate patterns, aligning inconsistencies, and simplifying complexity discovered during codebase audit.

**Key Findings**:
- 2 duplicate `BengalPaths` classes (24 import sites affected)
- 3 different renderer attribute access patterns in directives
- Mixed HTML escaping: 1 custom impl + 8 stdlib import aliases
- 159 scattered `site.config.get()` calls across 62 files
- 8 remaining `os.path` usages (vs 658+ `pathlib.Path`)
- 13 instance-level loggers (vs 205+ module-level standard)

**Scope**: Low-risk internal refactoring with no API changes.

---

## Problem Statement

As Bengal evolved, several patterns emerged independently across modules:

1. **Duplicate Infrastructure** - Two `BengalPaths` classes doing overlapping work
2. **Inconsistent Access Patterns** - Directives access `renderer._md` vs `renderer.md` differently
3. **Redundant Implementations** - Custom `escape_html` when stdlib works
4. **Repetitive Code** - `site.config.get("key", {})` scattered everywhere
5. **Mixed Conventions** - Some `os.path`, some `pathlib.Path`

These create maintenance burden and potential for subtle bugs.

---

## Goals

1. **Consolidate** - Merge duplicate implementations
2. **Standardize** - Align access patterns across modules
3. **Simplify** - Remove unnecessary complexity
4. **Document** - Establish patterns for future development

## Non-Goals

- API changes (all changes are internal)
- Performance optimization (focus is clarity)
- New features
- Breaking existing tests

---

## Design Options

### Option A: Big-Bang Consolidation (Not Recommended)

Consolidate everything in a single large PR.

**Pros**: Done in one commit  
**Cons**: High risk, difficult to review, hard to bisect if issues arise

### Option B: Phased Consolidation (Recommended)

Tackle each category in separate focused PRs.

**Pros**: Low risk, easy review, bisectable, can pause if needed  
**Cons**: Takes longer, multiple PRs

### Option C: Opportunistic Cleanup

Fix inconsistencies only when touching related code.

**Pros**: Zero dedicated time  
**Cons**: Inconsistencies persist indefinitely, harder to track

---

## Recommended Approach: Phased Consolidation

### Phase 1: BengalPaths Consolidation (High Priority)

**Current State**:
- `bengal/cache/paths.py` - Primary, comprehensive (237+ lines)
- `bengal/utils/paths.py` - Secondary, imports from cache/paths.py

**Action**:
1. Move `format_path_for_display()` from `utils/paths.py` to `utils/text.py`
2. Remove `BengalPaths` from `utils/paths.py` (keep as re-export if needed)
3. Update 24 import sites to use `bengal.cache.paths`
4. Delete or minimize `utils/paths.py`

**Evidence**:
- `bengal/cache/paths.py:52` - Primary definition
- `bengal/utils/paths.py:88` - Secondary imports from primary
- 24 import sites identified via grep

**Risk**: Low - mechanical refactor with grep-verifiable changes

---

### Phase 2: Renderer Access Pattern (High Priority)

**Current State**:
Three different patterns in directives:

```python
# Pattern 1: Direct private access
renderer._md

# Pattern 2: Direct public access  
renderer.md

# Pattern 3: Safeguard pattern (best)
getattr(renderer, "_md", None) or getattr(renderer, "md", None)
```

**Action**:
1. Add utility function to `directives/utils.py`:

```python
def get_markdown_instance(renderer: Any) -> Any | None:
    """Get markdown parser instance from renderer safely."""
    return getattr(renderer, "_md", None) or getattr(renderer, "md", None)
```

2. Update all directive files to use this utility:
   - `directives/glossary.py:291, 442, 457`
   - `directives/steps.py:244`
   - Any other direct accesses

**Evidence**:
- `directives/glossary.py:442` - Uses `renderer._md`
- `directives/glossary.py:457` - Uses `renderer.md`
- `directives/steps.py:244` - Uses safeguard pattern

**Risk**: Low - adds consistency without changing behavior

---

### Phase 3: HTML Escaping Consolidation (Medium Priority)

**Current State**:
- Custom `escape_html()` in `directives/utils.py:20-44`
- Standard `html.escape` imported variously as `html_module`, `html_mod`, `html_lib`

**Action**:
1. Remove custom `escape_html` from `directives/utils.py`
2. Add thin wrapper to `utils/text.py` if needed:

```python
from html import escape as _html_escape

def escape_html(text: str) -> str:
    """Escape HTML special characters for safe attribute insertion."""
    return _html_escape(text, quote=True) if text else ""
```

3. Update `directives/base.py` to import from new location
4. Standardize import name to `html` (not `html_module`, `html_lib`, etc.)

**Evidence**:
- `directives/utils.py:20-44` - Custom implementation
- 8 files importing `html` with different aliases

**Risk**: Low - stdlib function is identical behavior

---

### Phase 4: os.path to pathlib Migration (Medium Priority)

**Current State**:
8 remaining `os.path` usages amid 658 `pathlib.Path` usages.

**Action**:
Convert remaining usages:

```python
# Before
os.path.exists("/.dockerenv")
os.path.isdir(path)
os.path.join(path, index)

# After
Path("/.dockerenv").exists()
Path(path).is_dir()
Path(path) / index
```

**Affected Files**:
- `utils/rich_console.py:141,144` - Docker/Git detection
- `server/live_reload.py:305,307,308,318` - Directory/file checks
- `content_layer/sources/rest.py:90` - Environment variable expansion
- `server/request_handler.py:373` - Comment reference (minor)

**Evidence**: grep for `os\.path\.` found 8 matches across 4 files

**Risk**: Very low - mechanical transformation

---

### Phase 5: Config Accessor Properties (Lower Priority)

**Current State**:
Repeated pattern throughout codebase:
```python
site.config.get("assets", {})
site.config.get("build", {}).get("fast_mode", False)
site.config.get("i18n", {}) or {}  # Redundant
```

**Action**:
Add typed properties to `SitePropertiesMixin`:

```python
@property
def assets_config(self) -> dict[str, Any]:
    """Assets configuration section."""
    cfg = self.config.get("assets")
    return cfg if isinstance(cfg, dict) else {}

@property
def build_config(self) -> dict[str, Any]:
    """Build configuration section."""
    return self.config.get("build", {})

@property
def i18n_config(self) -> dict[str, Any]:
    """Internationalization configuration section."""
    return self.config.get("i18n", {})

@property
def menu_config(self) -> dict[str, Any]:
    """Menu configuration section."""
    return self.config.get("menu", {})
```

**Affected Sites** (159 occurrences across 62 files - migrate gradually):
- `orchestration/menu.py` (5 calls)
- `orchestration/asset.py` (8 calls)
- `discovery/content_discovery.py` (2 calls)
- `cli/commands/build.py` (2 calls)
- ...and 58 other files

**Risk**: Low - additive change, can migrate call sites gradually via deprecation warnings

---

### Phase 6: Logger Pattern Standardization (Lower Priority)

**Current State**:
- 205+ module-level loggers: `logger = get_logger(__name__)` ✅ (standard pattern)
- 13 instance-level loggers: `self.logger = get_logger(__name__)` (non-standard)

**Action**:
Convert instance-level to module-level in:
- `discovery/content_discovery.py:72`
- `orchestration/asset.py:88`
- `postprocess/sitemap.py:72`
- `postprocess/redirects.py:50`
- `postprocess/rss.py:73`
- `orchestration/build/__init__.py:82`
- `orchestration/static.py:79`
- `orchestration/content.py:41`
- `orchestration/incremental/orchestrator.py:82`
- `discovery/version_resolver.py:75`
- `config/loader.py:109`
- `cache/dependency_tracker.py:141`
- `directives/base.py:129`

**Risk**: Very low - cosmetic change, aligns with 205+ existing module-level loggers

---

## Implementation Order

| Phase | Priority | Risk | Effort | Blockers |
|-------|----------|------|--------|----------|
| 1. BengalPaths | High | Low | 2h | None |
| 2. Renderer Access | High | Low | 1h | None |
| 3. HTML Escaping | Medium | Low | 1h | None |
| 4. os.path Migration | Medium | Very Low | 30m | None |
| 5. Config Accessors | Lower | Low | 2h | None |
| 6. Logger Pattern | Lower | Very Low | 1h | None |

**Total Estimated Effort**: 8-9 hours across multiple PRs

---

## Testing Strategy

1. **Existing Tests**: All tests must pass after each phase
2. **No New Tests Needed**: Behavior is unchanged
3. **Import Verification**: `ruff check` catches broken imports
4. **Type Checking**: `mypy` verifies type consistency

---

## Migration Strategy

Each phase follows the same pattern:

1. Create branch from main
2. Make changes
3. Run `make lint` and `make test`
4. Create PR with focused scope
5. Review and merge
6. Move to next phase

No deprecation period needed - all changes are internal.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Broken imports | Low | Medium | `ruff check` catches immediately |
| Subtle behavior change | Very Low | Medium | Existing tests cover behavior |
| Merge conflicts | Low | Low | Small, focused PRs |

---

## Future Considerations

### Large File Splitting (Not In Scope)

Files exceeding 700 lines identified but not addressed in this RFC:

| File | Lines | Status |
|------|-------|--------|
| `analysis/knowledge_graph.py` | 1222 | Monitor |
| `discovery/content_discovery.py` | 1007 | Well-structured |
| `rendering/pipeline/core.py` | 999 | Consider future RFC |
| `core/section.py` | 997 | Uses mixins already |

These should be addressed in a separate RFC if they become maintenance burden.

### Typed Configuration (Not In Scope)

Full typed config (dataclass instead of dict) would be more comprehensive but is a larger undertaking. Phase 5 provides immediate value without that investment.

---

## Success Criteria

- [ ] Single `BengalPaths` class location
- [ ] Unified renderer access pattern
- [ ] No custom HTML escape implementation
- [ ] No `os.path` usage (pathlib only)
- [ ] Config accessor properties available
- [ ] Consistent logger pattern
- [ ] All existing tests pass
- [ ] No API changes

---

## Validation Summary

All claims independently verified via grep and file inspection on 2025-12-21:

| Phase | Claim | Verified |
|-------|-------|----------|
| 1. BengalPaths | 2 duplicate classes | ✅ `cache/paths.py:52`, `utils/paths.py:59` |
| 1. BengalPaths | 24 import sites | ✅ grep confirmed 24 matches across 18 files |
| 2. Renderer | 3 access patterns | ✅ `glossary.py:442,457`, `steps.py:244` |
| 3. HTML Escape | Custom impl + 8 aliases | ✅ `directives/utils.py:20-44` + 8 import variants |
| 4. os.path | 8 remaining usages | ✅ 8 matches across 4 files |
| 5. Config | Scattered access pattern | ✅ 159 occurrences across 62 files |
| 6. Logger | 13 instance-level | ✅ 13 files use `self.logger` vs 205+ module-level |

---

## Appendix: Evidence References

### BengalPaths Duplication
- Primary: `bengal/cache/paths.py:52`
- Secondary: `bengal/utils/paths.py:59`
- Cross-import: `bengal/utils/paths.py:88`

### Renderer Access Patterns
- Direct `_md`: `bengal/directives/glossary.py:442`
- Direct `md`: `bengal/directives/glossary.py:457`
- Safeguard: `bengal/directives/steps.py:244`

### HTML Escaping
- Custom: `bengal/directives/utils.py:20-44`
- Stdlib imports: 8 files with varying aliases

### os.path Usages (8 matches across 4 files)
- `bengal/utils/rich_console.py:141,144`
- `bengal/server/live_reload.py:305,307,308,318`
- `bengal/content_layer/sources/rest.py:90`
- `bengal/server/request_handler.py:373` (in comment)

---

**Confidence Breakdown**:
- Evidence Strength: 40/40 (all claims verified with file:line via grep)
- Consistency: 30/30 (no conflicting information)
- Recency: 15/15 (current codebase state)
- Tests: 7/15 (existing tests cover behavior, no new tests proposed)

**Total**: 92% 🟢

**Validation**: All claims independently verified against codebase on 2025-12-21
