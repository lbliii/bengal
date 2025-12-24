# RFC: Rendering Package Error System Adoption

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/rendering/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Verified**: 2025-12-24 (exception counts, error code usage, session tracking gaps)  
**Priority**: P1 (High) — Rendering is user-facing critical path with moderate adoption  
**Estimated Effort**: 2.5 hours (single dev)

---

## Executive Summary

The `bengal/rendering/` package has **moderate adoption** (~60%) of the Bengal error system. The core error infrastructure (`errors.py`, `engines/errors.py`) is well-designed with rich `TemplateRenderError` and `TemplateNotFoundError` classes extending `BengalRenderingError`. However, template functions and parsers rely primarily on `logger.warning/error` calls without error codes or session tracking.

**Current state**:
- **7/91 files** use `BengalError` or subclasses with error codes
- **5 error codes** actively used: R003, R008, C003, T010
- **41 logger.error/warning calls** across 22 files — most without error codes
- **0 ErrorAggregator** usage for batch operations
- **0 session tracking** via `record_error()`
- **126 exception catches** across 40 files — many don't enrich with Bengal errors

**Good Patterns Found**:

| File | Pattern | Evidence |
|------|---------|----------|
| `errors.py` | `TemplateRenderError(BengalRenderingError)` | Rich context, suggestions, alternatives |
| `engines/errors.py` | `TemplateNotFoundError(BengalRenderingError)` | Search paths, auto-suggestion |
| `plugins/variable_substitution.py` | `BengalRenderingError` with R003 | 4 raises with codes + suggestions |
| `template_functions/navigation/` | `BengalRenderingError` with R008 | scaffold.py, tree.py |

**Adoption Score**: 6/10 → Target: 9/10

**Recommendation**: Add error codes to all logger calls, implement session tracking in critical paths, add ErrorAggregator for batch preprocessing.

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

The rendering package is the primary user-facing subsystem—every page build goes through it. Template errors, missing images, broken cross-references, and icon failures all affect user experience. When rendering fails, users need:
- Clear error messages with error codes
- Actionable suggestions for recovery
- Pattern detection for recurring issues
- Consistent error handling across all template functions

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| Logger calls without error codes | Can't search for specific error types | No unified debugging approach |
| No session tracking | Build summaries miss rendering errors | No recurring pattern detection |
| Inconsistent patterns | Different error formats per submodule | Manual investigation required |
| Missing suggestions | Cryptic error messages | Users can't self-recover |

---

## Current State Evidence

### Error Code Usage by File

**Grep Result**: `grep -rn "ErrorCode" bengal/rendering/`

```
bengal/rendering/template_functions/navigation/scaffold.py:343: from bengal.errors import BengalRenderingError, ErrorCode
bengal/rendering/template_functions/navigation/scaffold.py:346: raise BengalRenderingError(msg, code=ErrorCode.R008)
bengal/rendering/template_functions/navigation/tree.py:111: from bengal.errors import BengalRenderingError, ErrorCode
bengal/rendering/template_functions/navigation/tree.py:117: code=ErrorCode.R008,
bengal/rendering/plugins/variable_substitution.py:246: from bengal.errors import BengalRenderingError, ErrorCode
bengal/rendering/plugins/variable_substitution.py:253: code=ErrorCode.R003,
bengal/rendering/plugins/variable_substitution.py:264: code=ErrorCode.R003,
bengal/rendering/plugins/variable_substitution.py:275: code=ErrorCode.R003,
bengal/rendering/plugins/variable_substitution.py:281: code=ErrorCode.R003,
bengal/rendering/parsers/__init__.py:126: from bengal.errors import BengalConfigError, ErrorCode
bengal/rendering/parsers/__init__.py:131: code=ErrorCode.C003,
bengal/rendering/plugins/inline_icon.py:24: from bengal.errors import ErrorCode
bengal/rendering/plugins/inline_icon.py:158: code=ErrorCode.T010.name,
bengal/rendering/template_functions/icons.py:31: from bengal.errors import ErrorCode
bengal/rendering/template_functions/icons.py:185: code=ErrorCode.T010.name,
bengal/rendering/engines/__init__.py:67: from bengal.errors import BengalConfigError, ErrorCode
bengal/rendering/engines/__init__.py:129: code=ErrorCode.C003,
bengal/rendering/engines/__init__.py:141: code=ErrorCode.C003,
bengal/rendering/engines/__init__.py:153: code=ErrorCode.C003,
```

**Summary**: 5 unique error codes used (R003, R008, C003, T010).

### BengalError Usage

**File**: `bengal/rendering/plugins/variable_substitution.py:250-282`

```python
from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    f"Access to private/protected attributes denied: '{part}' in '{expr}'",
    suggestion="Use public attributes only in template expressions",
    code=ErrorCode.R003,
)
```

**Excellent**: Uses error code, suggestion, and clear message.

**File**: `bengal/rendering/template_functions/navigation/tree.py:110-118`

```python
from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    msg,
    suggestion="Ensure content discovery has run before accessing navigation tree",
    code=ErrorCode.R008,
)
```

**Good**: Uses error code and suggestion.

### Rich Error Classes

**File**: `bengal/rendering/errors.py:102-160`

```python
class TemplateRenderError(BengalRenderingError):
    """Rich template error with all debugging information."""

    def __init__(
        self,
        error_type: str,
        message: str,
        template_context: TemplateErrorContext,
        inclusion_chain: InclusionChain | None = None,
        page_source: Path | None = None,
        suggestion: str | None = None,
        available_alternatives: list[str] | None = None,
        search_paths: list[Path] | None = None,
        ...
    )
```

**Excellent**: Extends `BengalRenderingError` with rich context including:
- Template context (file, line, surrounding code)
- Inclusion chain for template inheritance
- Available alternatives for typo correction
- Search paths for debugging

**File**: `bengal/rendering/engines/errors.py:64-94`

```python
class TemplateNotFoundError(BengalRenderingError):
    """Raised when a template cannot be found."""

    def __init__(
        self,
        name: str,
        search_paths: list[Path],
        *,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.name = name
        self.search_paths = search_paths
        paths_str = "\n  ".join(str(p) for p in search_paths)
        message = f"Template not found: '{name}'\nSearched in:\n  {paths_str}"

        if suggestion is None:
            suggestion = "Check template name and search paths."

        super().__init__(message=message, suggestion=suggestion, original_error=original_error)
```

**Excellent**: Auto-generates suggestion if not provided, includes search paths.

### Logger.error/warning Calls (41 total across 22 files)

| File | error | warning | Has error_code | Has suggestion |
|------|-------|---------|----------------|----------------|
| `engines/jinja.py` | 1 | 1 | ❌ | ❌ |
| `pipeline/core.py` | 0 | 2 | ❌ | ❌ |
| `pipeline/autodoc_renderer.py` | 1 | 1 | ❌ | ❌ |
| `template_functions/images.py` | 3 | 3 | ❌ | ✅ (partial) |
| `template_functions/files.py` | 1 | 2 | ❌ | ❌ |
| `template_functions/tables.py` | 1 | 1 | ❌ | ❌ |
| `template_functions/crossref.py` | 0 | 2 | ❌ | ✅ (via suggestions field) |
| `template_functions/icons.py` | 0 | 1 | ✅ (non-standard) | ❌ |
| `plugins/inline_icon.py` | 0 | 1 | ✅ (non-standard) | ❌ |
| `parsers/mistune/__init__.py` | 0 | 2 | ❌ | ✅ (via format_suggestion) |
| `parsers/mistune/toc.py` | 0 | 3 | ❌ | ✅ (via format_suggestion) |
| `parsers/mistune/ast.py` | 0 | 2 | ❌ | ❌ |
| `parsers/mistune/highlighting.py` | 0 | 1 | ❌ | ❌ |
| `parsers/pygments_patch.py` | 1 | 2 | ❌ | ❌ |
| `pygments_cache.py` | 0 | 2 | ❌ | ❌ |
| `template_engine/manifest.py` | 0 | 1 | ❌ | ❌ |
| `template_engine/environment.py` | 0 | 1 | ❌ | ❌ |
| `template_engine/asset_url.py` | 0 | 1 | ❌ | ❌ |
| `template_functions/strings.py` | 0 | 1 | ❌ | ❌ |
| `template_functions/taxonomies.py` | 0 | 1 | ❌ | ❌ |
| `template_functions/get_page.py` | 0 | 1 | ❌ | ❌ |
| `parsers/factory.py` | 0 | 1 | ❌ | ❌ |

### Session Tracking

**Grep Result**: `grep -r "record_error" bengal/rendering/` → **0 matches**

Rendering errors are not tracked in error sessions, meaning:
- Build summaries don't include rendering failures
- No pattern detection for recurring template issues

### ErrorAggregator Usage

**Grep Result**: `grep -r "ErrorAggregator\|enrich_error" bengal/rendering/` → **0 matches**

No batch error handling despite processing multiple pages/images.

---

## Gap Analysis

### Gap 1: Logger Calls Without Error Codes

**Current**: 41 logger calls, only 2 use error codes (and non-standardly).

**Example** (`template_functions/images.py:135`):

```python
# Current
logger.warning("image_not_found", path=path, tried_paths=tried_paths, caller="template")

# Should be
logger.warning(
    "image_not_found",
    path=path,
    tried_paths=tried_paths,
    caller="template",
    error_code=ErrorCode.X001.value,
    suggestion="Check that the image exists in assets/ or content/ directory",
)
```

**Example** (`engines/jinja.py:181-188`):

```python
# Current
except Exception as e:
    logger.error(
        "template_render_failed",
        template=name,
        error_type=type(e).__name__,
        error=truncate_error(e, 500),
        context_keys=list(context.keys()),
    )
    raise

# Should be
except Exception as e:
    logger.error(
        "template_render_failed",
        template=name,
        error_type=type(e).__name__,
        error=truncate_error(e, 500),
        context_keys=list(context.keys()),
        error_code=ErrorCode.R001.value,
        suggestion="Check template syntax and context variables",
    )
    record_error(e, file_path=name, build_phase="rendering")
    raise
```

### Gap 2: Non-Standard Error Code Field in Icon Warnings

**Current** (`plugins/inline_icon.py:155-159`):

```python
logger.warning(
    "icon_not_found",
    icon=name,
    code=ErrorCode.T010.name,  # Non-standard field name
    searched=[str(p) for p in icon_resolver.get_search_paths()],
)
```

**Should be**:

```python
logger.warning(
    "icon_not_found",
    icon=name,
    error_code=ErrorCode.T010.value,  # Standard: error_code, use .value
    searched=[str(p) for p in icon_resolver.get_search_paths()],
    suggestion="Check icon name spelling. Use 'bengal icons list' to see available icons.",
)
```

### Gap 3: No Session Tracking

**Locations to add `record_error()`**:

| Location | When to Track |
|----------|---------------|
| `engines/jinja.py:render_template()` | Template render failure |
| `pipeline/core.py:_preprocess_content()` | Preprocessing failure |
| `template_functions/images.py` | Image processing failure |
| `template_functions/files.py` | File stat failure |
| `parsers/mistune/__init__.py` | Markdown parse failure |

### Gap 4: No ErrorAggregator for Batch Operations

**Candidate location**: `pipeline/core.py:540-560` — preprocessing error handling

```python
# Current (lines 549-560): Individual page errors logged without aggregation
except Exception as e:
    if self.build_stats:
        self.build_stats.add_warning(
            str(page.source_path), truncate_error(e), "preprocessing"
        )
    else:
        logger.warning(
            "preprocessing_error",
            source_path=str(page.source_path),
            error=truncate_error(e),
        )

# Should use ErrorAggregator pattern from render.py in orchestration
```

### Gap 5: Exception Catches Without Error Enrichment

**126 exception catches** across 40 files. Many catch and log without using Bengal error patterns.

**Example** (`pipeline/core.py:549-560`):

```python
# Current
except Exception as e:
    if self.build_stats:
        self.build_stats.add_warning(str(page.source_path), truncate_error(e), "preprocessing")
    else:
        logger.warning(
            "preprocessing_error",
            source_path=str(page.source_path),
            error=truncate_error(e),
        )
    return page.content

# Should add error_code, suggestion, and consider session tracking
```

---

## Proposed Changes

### Phase 1: Add Error Codes to High-Impact Logger Calls (45 min)

**Priority files** (most user-facing):

#### 1. `template_functions/images.py` (6 calls)

```python
# Line 135: image_not_found
logger.warning(
    "image_not_found",
    path=path,
    tried_paths=tried_paths,
    caller="template",
    error_code=ErrorCode.X001.value,
    suggestion="Check that the image exists in assets/ or content/ directory",
)

# Line 161: image_read_error
logger.error(
    "image_read_error",
    path=path,
    file_path=str(file_path),
    error=str(e),
    error_type=type(e).__name__,
    caller="template",
    error_code=ErrorCode.X003.value,
    suggestion="Check image file is not corrupted and has valid format",
)
```

#### 2. `template_functions/files.py` (3 calls)

```python
# Line 122: file_not_found
logger.warning(
    "file_not_found",
    path=path,
    attempted=str(file_path),
    caller="template",
    error_code=ErrorCode.X001.value,
    suggestion="Verify file path spelling and that file exists in content/ or assets/",
)

# Line 156: file_stat_error
logger.error(
    "file_stat_error",
    path=path,
    file_path=str(file_path),
    error=str(e),
    error_type=type(e).__name__,
    caller="template",
    error_code=ErrorCode.X003.value,
    suggestion="Check file permissions and disk space",
)
```

#### 3. `engines/jinja.py` (2 calls)

```python
# Line 181: template_render_failed
logger.error(
    "template_render_failed",
    template=name,
    error_type=type(e).__name__,
    error=truncate_error(e, 500),
    context_keys=list(context.keys()),
    error_code=ErrorCode.R001.value,
    suggestion="Check template syntax and ensure all context variables are defined",
)

# Line 309: template_syntax_error
logger.warning(
    "template_syntax_error",
    template=rel_name,
    error=str(e),
    line=getattr(e, 'lineno', None),
    error_code=ErrorCode.R002.value,
    suggestion="Fix Jinja2 syntax error before building",
)
```

#### 4. `pipeline/core.py` (2 calls)

```python
# Line 543: jinja2_syntax_error
logger.warning(
    "jinja2_syntax_error",
    source_path=str(page.source_path),
    error=truncate_error(e),
    error_code=ErrorCode.R002.value,
    suggestion="Check Jinja2 syntax in page frontmatter or content",
)

# Line 555: preprocessing_error
logger.warning(
    "preprocessing_error",
    source_path=str(page.source_path),
    error=truncate_error(e),
    error_code=ErrorCode.R003.value,
    suggestion="Check page content for template syntax errors",
)
```

#### 5. `template_functions/tables.py` (2 calls)

```python
# Line 82: data_table_empty_path
logger.warning(
    "data_table_empty_path",
    caller="template",
    error_code=ErrorCode.R003.value,
    suggestion="Provide a valid data file path to data_table()",
)

# Line 126: data_table_load_error
logger.error(
    "data_table_load_error",
    path=path,
    error=data_result["error"],
    error_code=ErrorCode.R003.value,
    suggestion="Check that data file exists and is valid JSON/YAML/CSV",
)
```

### Phase 2: Standardize Icon Error Codes (15 min)

**Files**: `plugins/inline_icon.py`, `template_functions/icons.py`

```python
# Before (both files)
logger.warning(
    "icon_not_found",
    icon=name,
    code=ErrorCode.T010.name,  # Non-standard
    searched=[str(p) for p in icon_resolver.get_search_paths()],
)

# After
logger.warning(
    "icon_not_found",
    icon=name,
    error_code=ErrorCode.T010.value,  # Standard field name
    searched=[str(p) for p in icon_resolver.get_search_paths()],
    suggestion="Check icon name spelling. Run 'bengal icons list' to see available icons.",
)
```

### Phase 3: Add Session Tracking to Critical Paths (20 min)

**File**: `engines/jinja.py:render_template()`

```python
from bengal.errors import record_error

def render_template(self, name: str, context: dict[str, Any]) -> str:
    try:
        # ... existing rendering logic ...
        return result
    except Exception as e:
        record_error(e, file_path=name, build_phase="rendering")
        logger.error(
            "template_render_failed",
            template=name,
            error_type=type(e).__name__,
            error=truncate_error(e, 500),
            context_keys=list(context.keys()),
            error_code=ErrorCode.R001.value,
            suggestion="Check template syntax and ensure all context variables are defined",
        )
        raise
```

**File**: `parsers/mistune/__init__.py:parse()`

```python
from bengal.errors import record_error

except Exception as e:
    record_error(e, file_path="mistune_parser", build_phase="parsing")
    suggestion = format_suggestion("parsing", "markdown_error")
    logger.warning(
        "mistune_parsing_error",
        error=str(e),
        error_type=type(e).__name__,
        suggestion=suggestion,
        error_code=ErrorCode.P004.value,
    )
    return ""
```

### Phase 4: Add ErrorAggregator for Batch Operations (30 min)

**File**: `pipeline/core.py:540-560` — Add aggregation for preprocessing errors

**Current pattern** (individual logging per error):
```python
except Exception as e:
    if self.build_stats:
        self.build_stats.add_warning(str(page.source_path), truncate_error(e), "preprocessing")
    else:
        logger.warning("preprocessing_error", source_path=str(page.source_path), error=truncate_error(e))
```

**Target pattern** (aggregated with threshold):
```python
from bengal.errors import ErrorAggregator, ErrorCode

# At class or method level
aggregator = ErrorAggregator(total_items=len(pages))
threshold = 5

# In exception handler
except Exception as e:
    context = {
        "source_path": str(page.source_path),
        "error": truncate_error(e),
        "error_type": type(e).__name__,
        "error_code": ErrorCode.R003.value,
    }
    if aggregator.should_log_individual(e, context, threshold=threshold, max_samples=3):
        logger.warning("preprocessing_error", **context)
    aggregator.add_error(e, context=context)

    # Still update build_stats if available
    if self.build_stats:
        self.build_stats.add_warning(str(page.source_path), truncate_error(e), "preprocessing")

# After loop
aggregator.log_summary(logger, threshold=threshold, error_type="preprocessing")
```

**Note**: Preserves existing `build_stats` integration while adding aggregation.

### Phase 5: Add Suggestions to Remaining Logger Calls (20 min)

**Files needing suggestions added**:

| File | Event | Suggestion |
|------|-------|------------|
| `pygments_cache.py:179` | `unknown_lexer` | "Check language name spelling or use 'text' for plain text" |
| `pygments_cache.py:220` | `lexer_guess_failed` | "Specify language explicitly in code block" |
| `template_engine/manifest.py:160` | `asset_manifest_miss` | "Run 'bengal build' to generate asset manifest" |
| `template_engine/environment.py:272` | `theme_not_found` | "Check theme name spelling or install theme" |
| `template_functions/strings.py:366` | `replace_regex_invalid_pattern` | "Check regex syntax; escape special characters" |
| `parsers/pygments_patch.py:132` | `pygments_patch_failed` | "Upgrade Pygments or report bug" |

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add error codes to 5 high-impact files (15 calls) | 45 min | P1 |
| 2 | Standardize icon error codes (2 files) | 15 min | P1 |
| 3 | Add session tracking to jinja.py, mistune | 20 min | P1 |
| 4 | Add ErrorAggregator to pipeline/core.py | 30 min | P2 |
| 5 | Add suggestions to remaining logger calls | 20 min | P2 |
| 6 | Add tests for error handling | 30 min | P3 |

**Total**: ~2.5 hours

---

## Success Criteria

### Must Have

- [ ] All `logger.error()` calls include `error_code` field
- [ ] All `logger.warning()` calls include `suggestion` field where applicable
- [ ] Icon warnings use standard `error_code` field (not `code`)
- [ ] Session tracking in `engines/jinja.py:render_template()`

### Should Have

- [ ] Session tracking in `parsers/mistune/__init__.py`
- [ ] ErrorAggregator in `pipeline/core.py`
- [ ] All 41 logger calls have error codes

### Nice to Have

- [ ] `BengalTemplateError` exception subclass (specialized rendering error)
- [ ] Constants file for standard rendering suggestions
- [ ] Error handling tests for all template functions

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing log parsing | Low | Medium | Only adding fields, not changing existing |
| Test failures from new fields | Low | Low | Run `pytest tests/unit/rendering/` after changes |
| Performance impact | Very Low | Negligible | `record_error()` is O(1) per error |
| Template function behavior changes | Very Low | Low | Only modifying logging, not logic |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/rendering/template_functions/images.py` | Add error codes + suggestions | +12 |
| `bengal/rendering/template_functions/files.py` | Add error codes + suggestions | +8 |
| `bengal/rendering/template_functions/tables.py` | Add error codes + suggestions | +6 |
| `bengal/rendering/engines/jinja.py` | Add error codes + session tracking | +10 |
| `bengal/rendering/pipeline/core.py` | Add error codes + ErrorAggregator | +25 |
| `bengal/rendering/plugins/inline_icon.py` | Standardize error code field | +3 |
| `bengal/rendering/template_functions/icons.py` | Standardize error code field | +3 |
| `bengal/rendering/parsers/mistune/__init__.py` | Add error code + session tracking | +6 |
| `bengal/rendering/pygments_cache.py` | Add error codes + suggestions | +6 |
| `bengal/rendering/template_engine/manifest.py` | Add suggestion | +2 |
| `bengal/rendering/template_engine/environment.py` | Add suggestion | +2 |
| `bengal/rendering/template_functions/strings.py` | Add error code + suggestion | +3 |
| `bengal/rendering/parsers/pygments_patch.py` | Add error codes + suggestions | +6 |
| `tests/unit/rendering/test_error_handling.py` | New: error handling tests | +80 |
| **Total** | — | ~172 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 5/10 | 9/10 | All logger calls have codes |
| Bengal exception usage | 7/10 | 8/10 | Already good in core errors |
| Error aggregation | 0/10 | 6/10 | Added to pipeline/core.py |
| Session recording | 0/10 | 7/10 | Added to critical paths |
| Actionable suggestions | 6/10 | 9/10 | All warnings have suggestions |
| Consistent patterns | 5/10 | 9/10 | Standardized field names |
| **Overall** | **6/10** | **9/10** | — |

---

## References

- `bengal/errors/codes.py` — Error code definitions (R001-R010, X001-X006, T010)
- `bengal/errors/exceptions.py` — BengalRenderingError base class
- `bengal/errors/aggregation.py` — ErrorAggregator for batch processing
- `bengal/errors/session.py` — record_error() for session tracking
- `bengal/rendering/errors.py:102-160` — TemplateRenderError rich error class
- `bengal/rendering/engines/errors.py:64-94` — TemplateNotFoundError
- `bengal/rendering/plugins/variable_substitution.py:245-282` — Good BengalRenderingError usage
- `bengal/rendering/template_functions/navigation/tree.py:110-118` — Good error code usage
- `bengal/orchestration/render.py:34-35` — Reference ErrorAggregator pattern
- `tests/unit/rendering/` — Test files for validation
