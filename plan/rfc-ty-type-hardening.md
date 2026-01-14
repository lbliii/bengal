# RFC: ty Type Checker Hardening

**Status**: Draft  
**Created**: 2026-01-14  
**Author**: AI Assistant  
**Related**: `pyproject.toml` `[tool.ty]` configuration

---

## Executive Summary

Bengal has ~540 `ty` type errors remaining after initial cleanup. This RFC categorizes the errors, proposes fixes by priority, and establishes patterns for gradual hardening without breaking runtime behavior.

**Current State**:
- 150 `invalid-argument-type`
- 99 `unresolved-attribute`
- 59 `unused-ignore-comment` (kept for mypy compat)
- 47 `unknown-argument`
- 25 `possibly-missing-attribute`
- 23 `invalid-return-type`
- 22 `invalid-assignment`
- 22 `call-non-callable`
- 18 `not-subscriptable`
- 15 `unresolved-import` (optional deps)

---

## Error Categories & Proposed Fixes

### Category 1: Type Narrowing (ty doesn't understand truthiness)

**Pattern**: ty reports `~AlwaysFalsy` when code checks truthiness before use.

**Example** (`bengal/analysis/graph_builder.py:479`):
```python
if hasattr(item, "page") and item.page and item.page in analysis_pages_set:
    self.incoming_refs[item.page] += 10  # ty: key type is ~AlwaysFalsy
```

**Root Cause**: ty doesn't narrow types after `and item.page` truthiness check.

**Fix Options**:

| Option | Approach | Effort | Runtime Impact |
|--------|----------|--------|----------------|
| A | Add explicit `assert item.page is not None` | Low | Minimal |
| B | Use `cast()` after truthiness check | Low | None |
| C | Refactor to early return pattern | Medium | None |
| D | Add `# type: ignore[invalid-argument-type]` | Low | None |

**Recommended**: Option A for critical paths, Option D for edge cases.

**Affected Files** (sample):
- `bengal/analysis/graph_builder.py` (2 errors)
- `bengal/analysis/link_suggestions.py` (1 error)
- `bengal/cli/dashboard/screens.py` (multiple)

---

### Category 2: Unresolved Attributes on Protocols/Types

**Pattern**: ty can't find attributes that exist at runtime.

**Subcategory 2a: Dynamic Attributes**

**Example** (`bengal/autodoc/orchestration/page_builders.py:123`):
```python
element.display_source_file = display_source_file  # ty: unresolved attribute
```

**Root Cause**: `DocElement` doesn't declare `display_source_file` in type definition.

**Fix**: Add attribute to `DocElement` dataclass/class definition:
```python
@dataclass
class DocElement:
    # ... existing fields ...
    display_source_file: str | None = None  # For display in templates
```

**Subcategory 2b: Protocol Method Gaps**

**Example** (`bengal/cli/commands/theme.py:405`):
```python
path = engine._find_template_path(name)  # ty: unresolved on TemplateEngine
```

**Root Cause**: `_find_template_path` is implementation detail not in protocol.

**Fix Options**:
1. Add to `TemplateEngineProtocol` (if truly needed by callers)
2. Use `cast()` to concrete type
3. Access via different API

**Affected Files**:
- `bengal/autodoc/orchestration/page_builders.py` (1 error)
- `bengal/cache/build_cache/parsed_content_cache.py` (1 error)
- `bengal/cli/commands/graph/report.py` (2 errors)
- `bengal/cli/commands/theme.py` (2 errors)

---

### Category 3: Dictionary Key Type Mismatches

**Pattern**: Using `str` keys when `Path` is declared.

**Example** (`bengal/cache/dependency_tracker.py:402`):
```python
# Declaration: reverse_dependencies: dict[Path, set[Path]]
self.reverse_dependencies[term_key].add(source)  # term_key is str
```

**Root Cause**: Inconsistent Path vs str handling.

**Fix Options**:

| Option | Approach | Effort |
|--------|----------|--------|
| A | Normalize all keys to `Path` | Medium |
| B | Change type to `dict[str \| Path, ...]` | Low |
| C | Change type to `dict[str, ...]` with Path conversion | Medium |

**Recommended**: Option A - normalize to `Path` for consistency.

**Pattern Fix**:
```python
# Before
self.reverse_dependencies[term_key].add(source)

# After
self.reverse_dependencies[Path(term_key)].add(Path(source))
```

**Affected Files**:
- `bengal/cache/dependency_tracker.py` (4 errors)
- `bengal/cache/asset_dependency_map.py` (potential)

---

### Category 4: Build API Signature Mismatch

**Pattern**: `build()` method called with kwargs not in signature.

**Example** (`bengal/cli/dashboard/build.py:292-295`):
```python
orchestrator.build(
    parallel=self.options.parallel,      # ty: unknown-argument
    incremental=self.options.incremental,
    quiet=True,
    profile=False,
)
```

**Root Cause**: `build()` likely takes `BuildOptions` object, not kwargs.

**Fix**: Check actual signature and update call sites.

```python
# If build() takes BuildOptions:
from bengal.orchestration.build.options import BuildOptions

orchestrator.build(BuildOptions(
    parallel=self.options.parallel,
    incremental=self.options.incremental,
    quiet=True,
    profile=False,
))
```

**Affected Files**:
- `bengal/cli/dashboard/build.py` (4 errors)
- `bengal/cli/dashboard/screens.py` (4+ errors)

---

### Category 5: Callable Type Issues

**Pattern**: Objects used as callables but not typed as `Callable`.

**Example** (`bengal/cli/dashboard/app.py:233`):
```python
self.screen.action_rebuild()  # ty: object is not callable
```

**Root Cause**: `screen` typed as base class without `action_rebuild` method.

**Fix Options**:
1. Add method to protocol/base class
2. Use `cast()` to specific screen type
3. Add `hasattr` check with appropriate typing

**Affected Files**:
- `bengal/cli/dashboard/app.py` (1 error)
- `bengal/cli/dashboard/screens.py` (1 error)
- `bengal/collections/validator.py` (1 error)
- `bengal/core/page/relationships.py` (1 error)

---

### Category 6: Optional Dependency Imports

**Pattern**: Imports fail for optional packages.

**Example**:
```python
import typer  # ty: Cannot resolve imported module `typer`
```

**Root Cause**: ty doesn't know these are optional/conditional imports.

**Fix Options**:

| Option | Approach | Effort |
|--------|----------|--------|
| A | Add to `[tool.ty]` exclude patterns | Low |
| B | Create stub files for optional deps | Medium |
| C | Use `TYPE_CHECKING` with protocol stubs | High |

**Recommended**: Option A for now - configure ty to ignore these modules.

**pyproject.toml addition**:
```toml
[tool.ty]
# Ignore optional dependency imports
ignore-modules = ["typer", "mako", "marimo", "smartcrop", "cachetools"]
```

**Affected Modules**:
- `typer` (2 errors) - CLI framework alternative
- `mako` (1 error) - Template engine
- `marimo` (4 errors) - Notebook integration
- `smartcrop` (1 error) - Image processing
- `cachetools` (1 error) - Caching utilities

---

### Category 7: Method Override Signature Mismatches

**Pattern**: Override methods with different signatures.

**Example** (`bengal/cli/dashboard/base.py:123`):
```python
def action_quit(self) -> None:  # ty: invalid override
    # Base class may have different signature
```

**Root Cause**: Covariant/contravariant parameter issues.

**Fix**: Ensure override signatures match base class exactly, or use `@override` decorator with proper typing.

**Affected Files**:
- `bengal/cli/dashboard/base.py` (1 error)
- `bengal/cli/dashboard/serve.py` (1 error)
- `bengal/cli/dashboard/widgets/throbber.py` (3 errors)
- `bengal/server/request_handler.py` (1 error)

---

## Implementation Plan

### Phase 1: Configuration & Quick Wins (1-2 hours)

1. **Configure ty to ignore optional deps**:
   ```toml
   [tool.ty]
   ignore-modules = ["typer", "mako", "marimo", "smartcrop", "cachetools"]
   ```

2. **Add assertions for type narrowing** in critical paths:
   - `bengal/analysis/graph_builder.py`
   - `bengal/analysis/link_suggestions.py`

3. **Fix Build API calls** - verify signature and update callers

**Expected Reduction**: ~70 errors

### Phase 2: Protocol & Attribute Fixes (2-3 hours)

1. **Add missing attributes to dataclasses**:
   - `DocElement.display_source_file`
   - Other dynamic attributes

2. **Expand protocols** where needed:
   - `TemplateEngineProtocol` methods
   - `KnowledgeGraph` methods

3. **Normalize Path/str handling** in dependency tracker

**Expected Reduction**: ~50 errors

### Phase 3: Complex Fixes (4-6 hours)

1. **Method override signature alignment**
2. **Callable type fixes** in dashboard
3. **Return type corrections**

**Expected Reduction**: ~40 errors

### Phase 4: Assessment & Documentation (1 hour)

1. **Document remaining intentional gaps** (mypy compat ignores)
2. **Update type checking CI configuration**
3. **Create patterns guide** for future development

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Total ty errors | ~540 | <100 |
| Critical errors (blocking) | ~150 | 0 |
| Warnings (acceptable) | ~85 | <85 |
| Runtime regressions | 0 | 0 |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Runtime behavior changes | Run full test suite after each phase |
| mypy compatibility breaks | Keep `# type: ignore[override]` comments |
| Over-engineering | Focus on errors, not warnings first |
| Circular import issues | Use `TYPE_CHECKING` blocks |

---

## Files by Error Count

High-impact files (>5 errors):
1. `bengal/cli/dashboard/screens.py` (~15 errors)
2. `bengal/cli/dashboard/build.py` (~8 errors)
3. `bengal/cache/dependency_tracker.py` (~6 errors)
4. `bengal/cli/commands/theme.py` (~5 errors)

---

## Appendix: ty vs mypy Error Code Mapping

| ty Error | mypy Equivalent | Notes |
|----------|-----------------|-------|
| `invalid-argument-type` | `arg-type` | Parameter type mismatch |
| `unresolved-attribute` | `attr-defined` | Missing attribute |
| `invalid-return-type` | `return-value` | Return type mismatch |
| `call-non-callable` | `misc` | Non-callable called |
| `unknown-argument` | `call-arg` | Unknown kwarg |

---

## References

- [ty Documentation](https://docs.astral.sh/ty/)
- Bengal `pyproject.toml` `[tool.ty]` section
- Related RFC: `rfc-protocol-consolidation.md`
