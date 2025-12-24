# Type Refinement Baseline

**Date**: 2025-12-24

## Mypy Status

| Metric | Count | Notes |
|--------|-------|-------|
| Total errors | 545 | Reduced from 548 after import fixes |
| Files with errors | 158 | Reduced from 159 |
| Checked files | 604 | Full codebase |

### Error Distribution (Top 10)

| Error Type | Count |
|------------|-------|
| `[arg-type]` | ~110 |
| `[attr-defined]` | ~72 |
| `[no-any-return]` | ~58 |
| `[type-arg]` | ~37 |
| `[misc]` | ~33 |
| `[no-untyped-def]` | ~26 |
| `[call-arg]` | ~21 |
| `[assignment]` | ~21 |
| `[import-not-found]` | ~11 (optional deps) |
| `[override]` | ~10 (intentional) |

## Type Annotation Counts

| Metric | Count | Target |
|--------|-------|--------|
| `: Any` annotations | 541 | <50 |
| `dict[str, Any]` | 768 | <100 |
| `-> Any` returns | 127 | <20 |

## Dependencies Added

- `types-jinja2>=2.11.0` ✅

## Existing Type Infrastructure

- 595 files use `from __future__ import annotations`
- 270 files use `TYPE_CHECKING` imports
- 27 existing `TypedDict` definitions
- 17 existing `Protocol` definitions

## Import Fixes (2025-12-24)

Fixed incorrect internal imports:
- `bengal.core.site.site` → `bengal.core.site`
- `bengal.config.site_loader` → `bengal.cli.helpers.site_loader`
- `bengal.orchestration.build_context` → `bengal.utils.build_context`
- `bengal.autodoc.runner` → `bengal.autodoc.orchestration.result`
- `bengal.rendering.engines.base` → `bengal.rendering.engines.protocol`
- Fixed `cache_dir` undefined variable in `sources.py`
