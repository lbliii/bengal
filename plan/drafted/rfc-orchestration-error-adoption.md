# RFC: Orchestration Package Error System Adoption

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/orchestration/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Orchestration is critical build infrastructure with mixed adoption  
**Estimated Effort**: 2.5 hours (single dev)

---

## Executive Summary

The `bengal/orchestration/` package has **partial adoption** (~50%) of the Bengal error system. Some orchestrators (render, asset, incremental) demonstrate good error handling patterns, while others (menu, taxonomy, content, postprocess) rely primarily on logging without structured exceptions.

**Current state**:
- **2/39 files** use `ErrorAggregator` pattern (`render.py`, `asset.py`)
- **4/39 files** use `BengalError` or subclasses
- **2 error codes** used: R002 (`initialization.py:153`), D003 (`content.py:65`)
- **47 logger.error/warning calls** across 20 files — none with error codes
- **0 session tracking** via `record_error()`
- **0 orchestration-specific** (B-series) error codes defined

**Good Patterns Found**:

| File | Pattern | Evidence |
|------|---------|----------|
| `render.py` | `ErrorAggregator`, `extract_error_context` | Full aggregation for parallel rendering |
| `asset.py` | `BengalError`, `ErrorContext`, `enrich_error` | Rich context in parallel/sequential processing |
| `incremental/orchestrator.py` | `BengalError` with suggestions | Structured errors for initialization failures |

**Adoption Score**: 5/10 → Target: 8/10

**Recommendation**: Add orchestration error codes (B001-B099), extend patterns from render.py and asset.py to other orchestrators, add session tracking to BuildOrchestrator.

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

### Why This Matters

The Bengal error system provides:
- **Error codes** for searchability and documentation linking
- **Build phase tracking** for investigation
- **Related test file mapping** for debugging
- **Investigation helpers** (grep commands, related files)
- **Session tracking** for error aggregation across builds
- **Actionable suggestions** for user recovery

The orchestration package coordinates the entire build pipeline—21 phases from content discovery through post-processing. Build failures in orchestration affect every Bengal user. When orchestration fails, users need:
- Clear error messages with error codes
- Actionable suggestions for recovery
- Session tracking for pattern detection
- Consistent error handling across all orchestrators

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No orchestration error codes | Build failures hard to diagnose | Can't grep for specific orchestration errors |
| Inconsistent patterns | Different error formats per orchestrator | No unified debugging approach |
| No session tracking | Build summaries miss orchestration errors | No recurring pattern detection |
| Missing suggestions | Cryptic error messages | Manual investigation required |

---

## Current State Evidence

### Error Code Usage by File

**Grep Result**: `grep -rn "ErrorCode" bengal/orchestration/`

```
bengal/orchestration/build/initialization.py:153:code=ErrorCode.R002
bengal/orchestration/build/content.py:65:code=ErrorCode.D003
```

Only **2 error codes** used in orchestration package.

### BengalError Usage

**File**: `bengal/orchestration/incremental/orchestrator.py:163-256`

```python
# Line 165
from bengal.errors import BengalError

raise BengalError(
    "Cache not initialized - call initialize() first",
    suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
)
```

**Gap**: Uses base `BengalError` without an error code.

**File**: `bengal/orchestration/build/initialization.py:148-153`

```python
from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    f"Template validation failed: {e}",
    code=ErrorCode.R002,
    suggestion="Fix template syntax errors before building",
)
```

**Good**: Uses `BengalRenderingError` with error code and suggestion.

### Error Aggregation Pattern

**File**: `bengal/orchestration/render.py:34-35, 435-459`

```python
from bengal.errors import ErrorAggregator, extract_error_context

# In parallel processing loop
aggregator = ErrorAggregator(total_items=len(pages))
threshold = 5

for future in concurrent.futures.as_completed(future_to_page):
    try:
        future.result()
    except Exception as e:
        context = extract_error_context(e, page)
        if aggregator.should_log_individual(e, context, threshold=threshold, max_samples=3):
            logger.error("page_rendering_error", **context)
        aggregator.add_error(e, context=context)

aggregator.log_summary(logger, threshold=threshold, error_type="rendering")
```

**Excellent pattern** that should be replicated in other orchestrators.

### Error Context Enrichment

**File**: `bengal/orchestration/asset.py:726-738`

```python
from bengal.errors import BengalError, ErrorContext, enrich_error

try:
    # ... process CSS
except Exception as e:
    context = ErrorContext(
        file_path=css_entry.source_path,
        operation="processing CSS entry",
        suggestion="Check CSS syntax, file encoding, and dependencies",
        original_error=e,
    )
    enriched = enrich_error(e, context, BengalError)
    raise enriched from e
```

**Excellent pattern** for enriching exceptions with context.

### Logger.error/warning Calls (47 total)

| File | Count | Has error_code | Has suggestion |
|------|-------|----------------|----------------|
| `taxonomy.py` | 2 | ❌ | ❌ |
| `streaming.py` | 1 | ❌ | ❌ |
| `render.py` | 4 | ❌ | ❌ |
| `related_posts.py` | 1 | ❌ | ❌ |
| `postprocess.py` | 2 | ❌ | ❌ |
| `content.py` | 5 | ❌ | ❌ |
| `static.py` | 5 | ❌ | ❌ |
| `asset.py` | 5 | ❌ | ✅ (partial) |
| `css_optimizer.py` | 1 | ❌ | ❌ |
| `build/initialization.py` | 4 | ❌ | ❌ |
| `build/content.py` | 2 | ❌ | ❌ |
| `build/rendering.py` | 3 | ❌ | ❌ |
| `build/finalization.py` | 2 | ❌ | ❌ |
| `incremental/*.py` | 9 | ❌ | ❌ |

### Session Tracking

**Grep Result**: `grep -r "record_error" bengal/orchestration/` → **0 matches**

Build orchestration errors are not tracked in error sessions, meaning:
- Build summaries don't include orchestration failures
- No pattern detection for recurring build issues

---

## Gap Analysis

### Gap 1: No Orchestration-Specific Error Codes

**Current**: No B-series (Build/Orchestration) error codes defined in `ErrorCode` enum.

**Proposed B-series codes**:

| Code | Value | Description |
|------|-------|-------------|
| B001 | `build_phase_failed` | Generic build phase failure |
| B002 | `build_parallel_error` | Parallel processing failure with details |
| B003 | `build_incremental_failed` | Incremental build detection/cache failure |
| B004 | `menu_build_failed` | Menu building failure |
| B005 | `taxonomy_collection_failed` | Taxonomy collection failure |
| B006 | `taxonomy_page_generation_failed` | Taxonomy page generation failure |
| B007 | `asset_processing_failed` | Asset processing failure |
| B008 | `postprocess_task_failed` | Post-processing task failure |
| B009 | `section_finalization_failed` | Section finalization failure |
| B010 | `cache_initialization_failed` | Cache/tracker initialization failure |

### Gap 2: Inconsistent Error Handling Patterns

**Files with good patterns** (should be replicated):
- `render.py` — `ErrorAggregator`, `extract_error_context`
- `asset.py` — `ErrorContext`, `enrich_error`, `ErrorAggregator`
- `incremental/orchestrator.py` — `BengalError` with suggestions

**Files needing patterns**:

| File | Current | Should Have |
|------|---------|-------------|
| `taxonomy.py` | Bare exception logging | `ErrorAggregator` for parallel tag generation |
| `menu.py` | No error logging | Add `ErrorContext` + logging for build failures |
| `content.py` | Bare logging | `BengalDiscoveryError` for discovery failures |
| `postprocess.py` | Bare exception logging | `enrich_error` for task failures |
| `section.py` | Bare logging | Error codes in logs |
| `related_posts.py` | Bare logging | Error codes in logs |

### Gap 3: Missing Session Tracking

**Locations to add `record_error()`**:

| Location | When to Track |
|----------|---------------|
| `build/__init__.py:build()` | Any phase failure |
| `taxonomy.py:_generate_tag_pages_parallel()` | Tag page generation failure |
| `asset.py:_process_concurrently()` | Asset processing failure |
| `render.py:_render_parallel_*()` | Page rendering failure |
| `postprocess.py:run()` | Post-processing task failure |

### Gap 4: Missing Actionable Suggestions

**Logger calls needing suggestions**:

| File:Line | Event | Suggested Suggestion |
|-----------|-------|---------------------|
| `taxonomy.py:703` | `taxonomy_page_generation_failed` | "Check tag template 'tag.html' exists and is valid Jinja2" |
| `content.py:147` | `content_dir_not_found` | "Run 'bengal init' to create site structure, or check path spelling" |
| `postprocess.py:218` | `postprocess_task_failed` | "Check {task_name} configuration and file permissions" |
| `postprocess.py:278` | `postprocess_task_failed` | "Check {task_name} configuration and file permissions" |
| `menu.py` | (no logging exists) | Add: "Verify menu config syntax and ensure referenced pages exist" |

---

## Proposed Changes

### Phase 1: Add B-series Error Codes (15 min)

**File**: `bengal/errors/codes.py`

```python
# ============================================================
# Build/Orchestration errors (B001-B099)
# ============================================================
B001 = "build_phase_failed"              # Generic build phase failure
B002 = "build_parallel_error"             # Parallel processing failure
B003 = "build_incremental_failed"         # Incremental build failure
B004 = "menu_build_failed"                # Menu building failure
B005 = "taxonomy_collection_failed"       # Taxonomy collection failure
B006 = "taxonomy_page_generation_failed"  # Taxonomy page generation failure
B007 = "asset_processing_failed"          # Asset processing failure
B008 = "postprocess_task_failed"          # Post-processing task failure
B009 = "section_finalization_failed"      # Section finalization failure
B010 = "cache_initialization_failed"      # Cache initialization failure
```

Also add to category/subsystem mappings:

```python
categories = {
    ...
    "B": "build",  # Add
}

subsystem_map = {
    ...
    "B": "orchestration",  # Add
}
```

### Phase 2: Update taxonomy.py (30 min)

**Add ErrorAggregator to parallel tag generation** (`taxonomy.py:684-712`):

```python
# Before
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_tag = {
        executor.submit(self._create_tag_pages_for_lang, tag_slug, tag_data, lang): tag_slug
        for tag_slug, tag_data in locale_tags.items()
    }

    for future in concurrent.futures.as_completed(future_to_tag):
        tag_slug = future_to_tag[future]
        try:
            tag_pages = future.result()
            for page in tag_pages:
                page.lang = lang
            all_generated_pages.extend(tag_pages)
        except Exception as e:
            logger.error(
                "taxonomy_page_generation_failed",
                tag_slug=tag_slug,
                lang=lang,
                error=str(e),
            )

# After
from bengal.errors import ErrorAggregator, ErrorCode, extract_error_context

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_tag = {
        executor.submit(self._create_tag_pages_for_lang, tag_slug, tag_data, lang): tag_slug
        for tag_slug, tag_data in locale_tags.items()
    }

    aggregator = ErrorAggregator(total_items=len(locale_tags))
    threshold = 5

    for future in concurrent.futures.as_completed(future_to_tag):
        tag_slug = future_to_tag[future]
        try:
            tag_pages = future.result()
            for page in tag_pages:
                page.lang = lang
            all_generated_pages.extend(tag_pages)
        except Exception as e:
            context = {
                "tag_slug": tag_slug,
                "lang": lang,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_code": ErrorCode.B006.value,
                "suggestion": "Check tag template 'tag.html' exists and is valid Jinja2",
            }
            if aggregator.should_log_individual(e, context, threshold=threshold, max_samples=3):
                logger.error("taxonomy_page_generation_failed", **context)
            aggregator.add_error(e, context=context)

    aggregator.log_summary(logger, threshold=threshold, error_type="taxonomy")
```

### Phase 3: Update incremental/orchestrator.py (15 min)

**Add error codes to BengalError raises** (`orchestrator.py:163-168`):

```python
# Before
from bengal.errors import BengalError

raise BengalError(
    "Cache not initialized - call initialize() first",
    suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
)

# After
from bengal.errors import BengalError, ErrorCode

raise BengalError(
    "Cache not initialized - call initialize() first",
    code=ErrorCode.B010,
    suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
)
```

Apply same pattern to lines 220-225 and 252-257.

### Phase 4: Update content.py (20 min)

**Add BengalDiscoveryError for missing content dir** (`content.py:146-148`):

```python
# Before
if not content_dir.exists():
    logger.warning("content_dir_not_found", path=str(content_dir))
    return

# After
from bengal.errors import BengalDiscoveryError, ErrorCode

if not content_dir.exists():
    logger.warning(
        "content_dir_not_found",
        path=str(content_dir),
        error_code=ErrorCode.D001.value,
        suggestion="Run 'bengal init' to create site structure, or check path spelling",
    )
    return
```

### Phase 5: Add Session Tracking to BuildOrchestrator (20 min)

**Update build/__init__.py** — add session tracking at end of `build()` method:

```python
from bengal.errors import get_session, record_error

# At the end of build(), before returning results:
def _finalize_error_session(self) -> None:
    """Record build errors in session for pattern detection and summary."""
    session = get_session()

    # Record any errors collected during build phases
    for error in self.stats.errors:
        if hasattr(error, "phase"):
            record_error(
                error,
                file_path=f"build:{error.phase}",
                build_phase=error.phase,
            )
        else:
            record_error(error, file_path="build:unknown")

    # Log session summary if errors occurred
    if session.has_errors():
        by_category = {}
        for err in session.errors:
            cat = getattr(err, "category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

        logger.info(
            "build_error_session_summary",
            total_errors=session.error_count,
            by_category=by_category,
            recurring_patterns=len(session.get_recurring_patterns()),
        )
```

**Call location**: Add `self._finalize_error_session()` after Phase 19 (collect_stats), before Phase 20 (health).

### Phase 6: Update postprocess.py (15 min)

**Add error handling to task execution** (`postprocess.py:220-240`):

```python
# Before
try:
    task_fn()
except Exception as e:
    logger.error(
        "postprocess_task_failed",
        task=task_name,
        error=str(e),
    )

# After
from bengal.errors import BengalError, ErrorCode, ErrorContext, enrich_error, record_error

try:
    task_fn()
except Exception as e:
    context = ErrorContext(
        operation=f"post-processing task: {task_name}",
        suggestion=f"Check {task_name} configuration and file permissions",
        original_error=e,
    )
    enriched = enrich_error(e, context, BengalError)

    logger.error(
        "postprocess_task_failed",
        task=task_name,
        error=str(enriched),
        error_type=type(e).__name__,
        error_code=ErrorCode.B008.value,
        suggestion=f"Check {task_name} configuration and file permissions",
    )
    record_error(enriched, file_path=f"postprocess:{task_name}")
```

### Phase 7: Add Error Handling to menu.py (20 min)

**Current state**: `menu.py` has no `logger.error()` or `logger.warning()` calls — errors may be silently swallowed or propagate without context.

**Add error handling to menu building operations**:

```python
from bengal.errors import BengalError, ErrorCode, ErrorContext, enrich_error

def build_menu(self, menu_name: str, config: dict) -> Menu:
    """Build a menu from configuration."""
    try:
        # ... existing menu building logic ...
        return menu
    except KeyError as e:
        context = ErrorContext(
            operation=f"building menu '{menu_name}'",
            suggestion="Check menu config for missing or misspelled page references",
            original_error=e,
        )
        enriched = enrich_error(e, context, BengalError)
        logger.error(
            "menu_build_failed",
            menu_name=menu_name,
            error=str(enriched),
            error_type=type(e).__name__,
            error_code=ErrorCode.B004.value,
            suggestion="Verify menu config syntax and ensure referenced pages exist",
        )
        raise enriched from e
    except Exception as e:
        logger.error(
            "menu_build_failed",
            menu_name=menu_name,
            error=str(e),
            error_type=type(e).__name__,
            error_code=ErrorCode.B004.value,
            suggestion="Check menu configuration in site config",
        )
        raise
```

**Note**: Requires identifying specific error-prone locations in `menu.py` — add try/except wrappers around page resolution and config parsing.

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add B-series error codes to `codes.py` | 15 min | P1 |
| 2 | Update `taxonomy.py` with ErrorAggregator | 30 min | P1 |
| 3 | Update `incremental/orchestrator.py` with error codes | 15 min | P1 |
| 4 | Update `content.py` with error codes and suggestions | 20 min | P2 |
| 5 | Add session tracking to `build/__init__.py` | 20 min | P2 |
| 6 | Update `postprocess.py` with enrich_error pattern | 15 min | P2 |
| 7 | Add error handling to `menu.py` (no existing logging) | 20 min | P2 |
| 8 | Add tests for error handling | 30 min | P3 |

**Total**: ~2.75 hours

---

## Success Criteria

### Must Have

- [ ] B-series error codes (B001-B010) defined in `bengal/errors/codes.py`
- [ ] `ErrorAggregator` used in `taxonomy.py` parallel processing
- [ ] All `BengalError` raises include error codes
- [ ] All `logger.error()` calls include `error_code` field

### Should Have

- [ ] Session tracking in `BuildOrchestrator.build()`
- [ ] `enrich_error` pattern in `postprocess.py`
- [ ] All `logger.warning()` calls include `suggestion` field
- [ ] Error handling tests for orchestration

### Nice to Have

- [ ] `BengalOrchestrationError` exception subclass
- [ ] Constants file for standard orchestration suggestions
- [ ] Build phase tracking for all orchestrator methods

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing error handling | Low | Medium | Incremental changes, good test coverage |
| Test failures from new error format | Low | Low | Run `pytest tests/unit/orchestration/` after changes |
| Performance impact | Very Low | Negligible | `record_error()` is O(1) per error |
| Log format changes | Low | Low | Only adding fields, not changing existing |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/errors/codes.py` | Add B001-B010 codes + category mappings | +18 |
| `bengal/orchestration/taxonomy.py` | Add ErrorAggregator, error codes | +25 |
| `bengal/orchestration/incremental/orchestrator.py` | Add error codes to 3 `BengalError` raises | +6 |
| `bengal/orchestration/content.py` | Add error codes, suggestions | +8 |
| `bengal/orchestration/build/__init__.py` | Add `_finalize_error_session()` method | +25 |
| `bengal/orchestration/postprocess.py` | Add enrich_error pattern (2 locations) | +20 |
| `bengal/orchestration/menu.py` | Add error handling (new try/except) | +25 |
| `tests/unit/orchestration/test_error_handling.py` | New: error handling tests | +80 |
| **Total** | — | ~207 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 2/10 | 8/10 | B-series codes added |
| Bengal exception usage | 4/10 | 7/10 | All raises include codes |
| Error aggregation | 3/10 | 8/10 | Replicate render.py pattern |
| Session recording | 0/10 | 6/10 | Added to critical paths |
| Actionable suggestions | 3/10 | 8/10 | All logs have suggestions |
| Consistent patterns | 4/10 | 8/10 | Standardized across orchestrators |
| **Overall** | **5/10** | **8/10** | — |

---

## References

- `bengal/errors/codes.py` — Error code definitions (add B-series)
- `bengal/errors/exceptions.py` — BengalError base class
- `bengal/errors/aggregation.py` — ErrorAggregator for batch processing
- `bengal/errors/context.py` — ErrorContext for enrichment
- `bengal/orchestration/render.py:34-35` — Good ErrorAggregator example
- `bengal/orchestration/asset.py:726-738` — Good enrich_error example
- `bengal/orchestration/incremental/orchestrator.py:163-168` — BengalError usage
- `bengal/orchestration/build/initialization.py:148-153` — Good BengalRenderingError usage
- `tests/unit/orchestration/` — Test files for validation
