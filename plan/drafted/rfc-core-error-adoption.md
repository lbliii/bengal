# RFC: Core Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Last Verified**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/core/`  
**Confidence**: 90% 🟢 (all claims verified against source code)  
**Priority**: P3 (Low) — Core models are passive data structures; current error handling is intentional  
**Estimated Effort**: 0.5 hours (single dev, optional enhancements only)

---

## Executive Summary

The `bengal/core/` package has **appropriate error handling adoption** for its architectural role as passive data models. The package correctly uses the Bengal error framework in 4 locations for URL collisions, circular references, and config validation. The extensive exception suppression (39 `except Exception` blocks) is **intentional** for graceful degradation and Jinja2 template safety.

**Current state**:
- **4 uses** of Bengal error framework (URL collision, menu cycle, config validation)
- **3 error codes used**: `D005` (duplicate path), `C007` (circular reference), `C003` (invalid value)
- **1 custom exception**: `URLCollisionError` extending `BengalContentError`
- **2 locations** with raw `RuntimeError` (frozen registry mutation)
- **39 locations** with `except Exception` (intentional graceful degradation)
- **0 `record_error()` calls**: By design (core models don't participate in sessions)

**Adoption Score**: 6/10 (Good for passive data models)

**Recommendation**: Optional enhancement to migrate `RuntimeError` in `registry.py` to `BengalError`. No urgent changes needed—current error handling aligns with the passive data model architecture.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis](#gap-analysis)
4. [Proposed Changes](#proposed-changes)
5. [Implementation Phases](#implementation-phases)
6. [Success Criteria](#success-criteria)
7. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Architectural Context

The `bengal/core/` package provides foundational data models:

> "Core models are passive data structures with computed properties. They do not perform I/O, logging, or side effects."
> — `bengal/core/__init__.py:30-32`

This architectural constraint means:
- **Error handling should be minimal** — models don't perform operations that fail
- **Exception suppression is appropriate** — for template safety and graceful degradation
- **Bengal error framework is for boundary cases** — URL collisions, config validation

### Why This RFC

To document the **intentional** error handling patterns in the core package and identify the small number of locations where enhancement could improve debugging.

### Impact Assessment

| Aspect | Current Impact | After Enhancement |
|--------|----------------|-------------------|
| URL collisions | ✅ Full Bengal framework | No change needed |
| Menu cycles | ✅ Full Bengal framework | No change needed |
| Config validation | ✅ Full Bengal framework | No change needed |
| Frozen registry | ⚠️ Raw RuntimeError | Optional: BengalError |
| Theme resolution | ✅ Graceful degradation | No change needed |
| Template access | ✅ Dict compatibility | No change needed |

---

## Current State Evidence

### Package Structure

| Subpackage | Files | Purpose |
|------------|-------|---------|
| `asset/` | 3 | Static file representation |
| `page/` | 11 | Page data model and components |
| `section/` | 8 | Section hierarchy |
| `site/` | 9 | Site container and factories |
| `theme/` | 4 | Theme configuration and resolution |
| `output/` | 3 | Output collection types |
| Root | 12 | Menu, nav_tree, registry, version, etc. |
| **Total** | **50** | |

### Bengal Error Framework Usage (✅ Good)

**1. URL Collision Detection** (`site/core.py:795-799`):

```python
from bengal.errors import BengalContentError, ErrorCode

raise BengalContentError(
    "URL collisions detected (strict mode):\n\n" + "\n\n".join(collisions),
    code=ErrorCode.D005,
    suggestion="Check for duplicate slugs, conflicting autodoc output, or use different URLs for conflicting pages",
)
```

**2. Circular Menu Reference** (`menu.py:562-565`):

```python
raise BengalContentError(
    f"Menu has circular reference involving '{root.name}'",
    code=ErrorCode.C007,
    suggestion="Check menu configuration for circular parent-child relationships",
)
```

**3. Invalid Theme Config** (`theme/config.py:90-94`):

```python
raise BengalConfigError(
    f"Invalid default_appearance '{self.default_appearance}'. "
    f"Must be one of: {', '.join(valid_appearances)}",
    code=ErrorCode.C003,
    suggestion=f"Set default_appearance to one of: {', '.join(valid_appearances)}",
)
```

**4. URL Collision Error Class** (`url_ownership.py:89-158`):

```python
class URLCollisionError(BengalContentError):
    """
    Exception raised when URL collision detected at claim time.

    Provides detailed diagnostics including both claims, priority comparison,
    and suggested fixes.

    Extends BengalContentError for consistent error handling.
    """
```

### Raw Exception Usage (⚠️ Review Needed)

**1. Frozen Registry RuntimeError** (`registry.py:168-170, 190-192`):

```python
def register_page(self, page: Page) -> None:
    if self._frozen:
        raise RuntimeError("Cannot modify frozen registry")
    # ...

def register_section(self, section: Section) -> None:
    if self._frozen:
        raise RuntimeError("Cannot modify frozen registry")
```

**Assessment**: `RuntimeError` is acceptable for internal programming errors (violating the freeze contract). However, migrating to `BengalError` would provide:
- Consistent error handling
- Investigation helpers
- Error session tracking (if desired)

**2. Dict Compatibility KeyError** (`nav_tree.py:114-115`, `page/frontmatter.py:64-65`):

```python
# nav_tree.py
def __getitem__(self, key: str) -> Any:
    try:
        return getattr(self, key)
    except AttributeError as e:
        raise KeyError(key) from e

# frontmatter.py
def __getitem__(self, key: str) -> Any:
    # ...
    raise KeyError(key)
```

**Assessment**: These are **correct** for Jinja2 template compatibility. Templates expect `KeyError` for missing dict keys. **No change needed.**

**3. Abstract Method NotImplementedError** (`site/discovery.py:56-57`):

```python
def _theme_asset_paths(self) -> list[Path]:
    """Get theme assets paths in inheritance order (from ThemeIntegrationMixin)."""
    raise NotImplementedError("Implemented by ThemeIntegrationMixin")
```

**Assessment**: Standard Python convention for abstract methods. **No change needed.**

### Intentional Exception Suppression (✅ By Design)

The core package has **39** `except Exception` blocks that are **intentional** for:

#### 1. Graceful Degradation in Theme/Asset Processing

| File | Count | Purpose |
|------|-------|---------|
| `theme/registry.py` | 13 | Package discovery, resource access |
| `theme/resolution.py` | 7 | Theme chain resolution |
| `asset/asset_core.py` | 7 | CSS/JS minification, image optimization |

Example (`theme/registry.py:58-67`):

```python
except Exception as e:
    emit(
        None,
        "debug",
        "theme_templates_dir_check_failed",
        package=self.package,
        method="importlib_import",
        error=str(e),
        error_type=type(e).__name__,
    )
```

**Rationale**: Theme resolution should never crash the build. Missing themes, broken packages, or resource access failures should fall back gracefully.

#### 2. Template Safety and Dict-like Access

| File | Count | Purpose |
|------|-------|---------|
| `nav_tree.py` | 2 | Config/baseurl access fallback |
| `page/proxy.py` | 1 | Lazy loading fallback |
| `page/metadata.py` | 1 | Baseurl lookup fallback |
| `section/utils.py` | 2 | Section lookup fallback |
| `section/navigation.py` | 1 | Baseurl access fallback |

Example (`nav_tree.py:547-551`):

```python
try:
    baseurl = (site.config.get("baseurl", "") or "").rstrip("/")
except Exception:
    self._href_cached = site_path
    return site_path
```

**Rationale**: Templates must never crash. Missing config or malformed data should produce reasonable fallbacks.

#### 3. Diagnostics System Isolation

`section/__init__.py:137-141`:

```python
try:
    sink.emit(event)
except Exception:
    # Diagnostics must never break core behavior.
    return
```

**Rationale**: Diagnostics are observability features that must not affect core functionality.

#### 4. Best-Effort Cleanup Operations

| File | Count | Purpose |
|------|-------|---------|
| `asset/asset_core.py` | 3 | Fingerprint cleanup, manifest lookup |
| `site/discovery.py` | 1 | Registry error during URL claiming |

Example (`asset/asset_core.py:672-679`):

```python
except Exception as exc:  # pragma: no cover - best-effort cleanup
    emit_diagnostic(
        self,
        "debug",
        "asset_fingerprint_cleanup_failed",
        asset=str(self.source_path),
        error=str(exc),
    )
```

**Rationale**: Cleanup operations should not fail the build if they encounter unexpected errors.

---

## Gap Analysis

### What's Good ✅

1. **URL ownership system** — `URLCollisionError` is well-designed with diagnostic context
2. **Error codes** — Appropriate use of `D005`, `C007`, `C003` for boundary cases
3. **Graceful degradation** — Theme/asset processing fails soft with diagnostics
4. **Template safety** — Dict-like access patterns with fallbacks
5. **Diagnostics isolation** — Core behavior never broken by observability

### What Could Be Enhanced 🟡

1. **Frozen registry RuntimeError** — Could be `BengalError` for consistency
2. **Error session tracking** — Not used (acceptable for passive models)

### What's Not Applicable ❌

1. **Build phase tracking** — Core models don't participate in build phases
2. **Investigation helpers** — Not needed for passive data models
3. **Actionable suggestions** — Only relevant at boundaries (already implemented)

---

## Proposed Changes

### Phase 1: Optional Enhancement (0.5 hours)

**Migrate `RuntimeError` to `BengalError` in `registry.py`**

This is **optional** since `RuntimeError` is acceptable for internal programming errors. Enhancement provides:
- Consistent error handling across codebase
- Error session tracking (if registry errors become common)
- Investigation helpers

#### Before (`registry.py:168-170`):

```python
def register_page(self, page: Page) -> None:
    if self._frozen:
        raise RuntimeError("Cannot modify frozen registry")
```

#### After:

```python
from bengal.errors import BengalError

def register_page(self, page: Page) -> None:
    if self._frozen:
        raise BengalError(
            "Cannot modify frozen registry after freeze()",
            suggestion="Ensure registration happens during discovery phase, before freeze() is called",
        )
```

**Files to modify**:
- `bengal/core/registry.py` (2 locations)

---

## Implementation Phases

### Phase 1: Optional Enhancement (P3)

| Task | File | Effort |
|------|------|--------|
| Replace `RuntimeError` with `BengalError` | `registry.py:168-170` | 5 min |
| Replace `RuntimeError` with `BengalError` | `registry.py:190-192` | 5 min |
| Update tests | `tests/unit/core/test_registry.py` | 10 min |
| Verify exception handling | Manual test | 10 min |

**Total**: 30 minutes

### No Other Phases Needed

The current error handling in the core package is **appropriate** for its architectural role.

---

## Success Criteria

### Adoption Metrics

| Metric | Before | After |
|--------|--------|-------|
| Bengal error framework uses | 4 | 6 (if Phase 1 done) |
| Raw `RuntimeError` | 2 | 0 (if Phase 1 done) |
| Exception suppression (intentional) | 39 | 39 (no change) |
| Dict compatibility exceptions | 2 | 2 (no change) |

### Functional Criteria

- [ ] Frozen registry violations raise `BengalError` (if Phase 1)
- [ ] All existing tests pass
- [ ] Theme resolution still fails gracefully
- [ ] Template access still provides dict compatibility
- [ ] No performance regression

---

## Risks and Mitigations

### Risk 1: Over-Engineering

**Risk**: Converting all exception handling to Bengal errors

**Mitigation**: This RFC explicitly documents which patterns are **intentional**:
- Exception suppression for graceful degradation
- `KeyError` for dict compatibility
- `NotImplementedError` for abstract methods

### Risk 2: Breaking Template Safety

**Risk**: Changing exception types breaks Jinja2 templates

**Mitigation**:
- `KeyError` patterns are **not modified**
- `except Exception` blocks are **not modified**
- Only `RuntimeError` (programming error) is optionally enhanced

### Risk 3: Performance Impact

**Risk**: Additional error context creation slows down hot paths

**Mitigation**:
- `RuntimeError` → `BengalError` only affects error paths
- Error creation is rare (only on contract violations)
- No impact on success paths

---

## Appendix: Error Code Reference

### Codes Used in Core Package

| Code | Value | Location | Context |
|------|-------|----------|---------|
| `D005` | `duplicate_page_path` | `site/core.py:799` | URL collision in strict mode |
| `C007` | `config_circular_reference` | `menu.py:564` | Circular menu reference |
| `C003` | `config_invalid_value` | `theme/config.py:93` | Invalid `default_appearance` |

### Potentially Relevant Codes (Not Currently Used)

| Code | Value | Could Apply To |
|------|-------|----------------|
| `N009` | `content_weight_invalid` | Page weight validation |
| `N010` | `content_slug_invalid` | Slug validation |
| `D004` | `circular_section_reference` | Section hierarchy cycles |

**Assessment**: Current error code coverage is sufficient. Core models validate at boundaries (URL registration, menu building, config loading) where errors have user-facing impact.

---

## Appendix: Exception Suppression Inventory

### Full List of `except Exception` Blocks

| File | Line | Purpose | Fallback |
|------|------|---------|----------|
| `nav_tree.py` | 549 | Baseurl config access | Use site_path |
| `section/utils.py` | 46 | Section attribute access | Return None |
| `section/utils.py` | 56 | Section path access | Return str |
| `section/navigation.py` | 104 | Baseurl config access | Empty string |
| `theme/config.py` | 217 | Theme YAML parse | Fall back to config |
| `theme/registry.py` | 58 | Templates dir (importlib) | Return False |
| `theme/registry.py` | 74 | Templates dir (resources) | Return False |
| `theme/registry.py` | 99 | Assets dir (importlib) | Return False |
| `theme/registry.py` | 115 | Assets dir (resources) | Return False |
| `theme/registry.py` | 140 | Manifest (importlib) | Return False |
| `theme/registry.py` | 156 | Manifest (resources) | Return False |
| `theme/registry.py` | 184 | Resource path (importlib) | Continue to next method |
| `theme/registry.py` | 206 | Resource path (fspath) | Try as_file |
| `theme/registry.py` | 222 | Resource path (as_file) | Log and continue |
| `theme/registry.py` | 232 | Resource path (files) | Log and return None |
| `theme/registry.py` | 258 | Entry point discovery | Return empty dict |
| `theme/registry.py` | 280 | Version lookup | Set version=None |
| `theme/registry.py` | 290 | Distribution lookup | Log and continue |
| `theme/resolution.py` | 47 | Installed theme extends | Return None |
| `theme/resolution.py` | 69 | theme.toml parse | Log and continue |
| `theme/resolution.py` | 79 | theme.toml read | Log and return None |
| `theme/resolution.py` | 97 | theme.yaml parse | Log and return None |
| `theme/resolution.py` | 179 | Asset dir resolution | Log and continue |
| `theme/resolution.py` | 220 | Package asset discovery | Log and continue |
| `theme/resolution.py` | 234 | Bundled theme discovery | Log and continue |
| `site/discovery.py` | 140 | Registry claim error | Continue (graceful) |
| `page/proxy.py` | 259 | Lazy page loading | Log and set _load_error |
| `page/metadata.py` | 210 | Baseurl lookup | Use empty string |
| `section/__init__.py` | 139 | Diagnostics emit | Return (never break) |
| `asset/asset_core.py` | 250 | CSS import unexpected | Keep @import |
| `asset/asset_core.py` | 412 | CSS minification | Use original content |
| `asset/asset_core.py` | 514 | Image optimization | Log warning |
| `asset/asset_core.py` | 591 | Atomic image save | Cleanup and re-raise |
| `asset/asset_core.py` | 653 | Manifest cleanup | Best-effort only |
| `asset/asset_core.py` | 672 | Fingerprint cleanup | Log and continue |
| `asset/asset_core.py` | 708 | Asset URL lookup | Fallback to simple URL |
| `site/theme.py` | 96 | Theme chain resolution | Log and use empty |
| `site/data.py` | 98 | Data file parse | Log and continue |
| `page/content.py` | 178 | Markdown rendering | Return empty string |

**All 39 blocks are intentional** for the reasons documented in this RFC.

---

## Decision

**Recommendation**: Accept as P3 (Low Priority)

The core package has **appropriate** error handling for passive data models. The optional Phase 1 enhancement (migrating `RuntimeError` → `BengalError`) can be done opportunistically but is not urgent.

**No immediate action required.**
