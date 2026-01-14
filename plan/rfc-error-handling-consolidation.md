# RFC: Error Handling Consolidation

## Status: Draft
## Created: 2026-01-14
## Origin: Audit of error handling coverage across Bengal codebase

---

## Summary

**Problem**: Bengal has a well-designed error handling system with 80+ error codes across 13 categories, but adoption is incomplete:
- **Generic exceptions** (26 instances) bypass structured error benefits like documentation linking and AI investigation.
- **Missing domain classes** (5 categories) force usage of generic base classes, leading to imprecise build phase reporting.
- **Suggestion gaps** reduce the effectiveness of the CLI "Tip" feature for newer subsystems like Autodoc and Validator.

**Solution**: Complete the error handling consolidation in three phases:
1.  **Architecture**: Add specialized exception classes and register them in the suggestion engine.
2.  **Implementation**: Convert high-impact generic exceptions in cache, autodoc, and rendering pipelines.
3.  **Observability**: Enrich converted errors with `ErrorDebugPayload` for enhanced AI-assisted debugging.

**Priority**: Medium (improves debugging experience and error documentation)
**Scope**: ~150 LOC implementation + ~100 LOC tests

---

## Evidence: Current State

### What We Have

Bengal's error system is well-architected:

| Component | Location | Purpose |
|-----------|----------|---------|
| `ErrorCode` enum | `bengal/errors/codes.py` | 80+ unique codes across 13 categories |
| `BengalError` base | `bengal/errors/exceptions.py` | Rich context support |
| Domain exceptions | `bengal/errors/exceptions.py` | 8 specialized classes |
| Investigation helpers | `BengalError.get_investigation_commands()` | AI-friendly debugging |
| Error docs linking | `ErrorCode.docs_url` | Each code links to docs |

### Usage Statistics

| Metric | Count | Assessment |
|--------|-------|------------|
| Error codes defined | 80+ | ✅ Comprehensive |
| Bengal errors raised | 119 | ✅ Good adoption |
| Error codes used | 249 | ✅ Consistent |
| Generic Python exceptions | **26** | ⚠️ Gap |
| Missing exception classes | **5** | ⚠️ Gap |

---

## Problem Analysis

### 1. Missing Exception Classes

Error codes exist for these categories but lack a corresponding exception class. This results in fallback to generic classes and incorrect `BuildPhase` metadata.

| Category | Codes | Current Fallback | Proposed Class | Default Build Phase |
| :--- | :--- | :--- | :--- | :--- |
| **P** (Parsing) | P001-P006 | `BengalContentError` | `BengalParsingError` | `PARSING` |
| **T** (Template) | T001-T010 | `BengalRenderingError` | `BengalTemplateFunctionError` | `RENDERING` |
| **O** (Autodoc) | O001-O006 | `BengalContentError` | `BengalAutodocError` | `DISCOVERY` |
| **V** (Validator) | V001-V006 | `BengalError` | `BengalValidatorError` | `ANALYSIS` |
| **B** (Build) | B001-B010 | Various | `BengalBuildError` | `POSTPROCESSING` |

### 2. Generic Exceptions Lose Error System Benefits

When code raises generic Python exceptions instead of Bengal errors:

```python
# Current (loses benefits):
raise TypeError(
    f"Autodoc cache format mismatch in {context}: expected dict, got {type(p).__name__}. "
    f"Clear the cache with: rm -rf .bengal/cache/"
)

# Ideal (full error system):
raise BengalCacheError(
    f"Autodoc cache format mismatch in {context}: expected dict, got {type(p).__name__}",
    code=ErrorCode.A001,
    suggestion="Clear the cache with: rm -rf .bengal/cache/",
    file_path=cache_path,
)
```

**Lost benefits**:
- No error code for searchability (`grep -rn A001`)
- No documentation link (`/docs/reference/errors/#a001`)
- No investigation commands from `get_investigation_commands()`
- No related test file suggestions
- No build phase context

### 3. Generic Exception Locations

#### High Priority (user-facing, debugging-critical)

| File | Line(s) | Exception | Should Be |
|------|---------|-----------|-----------|
| `autodoc/base.py` | 316, 326, 336, 346, 356 | `TypeError` | `BengalCacheError` + `A001` |
| `autodoc/orchestration/orchestrator.py` | 186 | `ValueError` | `BengalCacheError` + `A001` |
| `cache/compression.py` | 243 | `ValueError` | `BengalCacheError` + `A001` |
| `rendering/pipeline/write_behind.py` | 108, 183, 186 | `RuntimeError` | `BengalRenderingError` + `R010` |

#### Medium Priority (internal validation)

| File | Line(s) | Exception | Reason to Keep/Convert |
|------|---------|-----------|------------------------|
| `rendering/parsers/patitas/directives/registry.py` | 136, 140, 147 | `TypeError/ValueError` | Plugin dev error - keep generic |
| `rendering/parsers/patitas/roles/registry.py` | 136, 140, 147 | `TypeError/ValueError` | Plugin dev error - keep generic |
| `rendering/highlighting/__init__.py` | 92, 144 | `TypeError/RuntimeError` | Backend init - convert |
| `utils/cache_registry.py` | 226 | `ValueError` | Cycle detection - convert to `A001` |

#### Low Priority (appropriate as-is)

| File | Line(s) | Exception | Reason |
|------|---------|-----------|--------|
| `rendering/parsers/patitas/directives/decorator.py` | 90 | `ValueError` | Programming error, caught at import |
| `rendering/parsers/patitas/__init__.py` | 370 | `TypeError` | API misuse, immediate feedback |
| `collections/validator.py` | 246 | `TypeError` | Schema type check, dev error |

---

## Proposed Solution

### Phase 1: Architecture and Registry (~100 LOC)

#### 1.1 Add Domain Exceptions
Add the following classes to `bengal/errors/exceptions.py`. These classes automatically set the correct `BuildPhase` and provide hooks for `get_related_test_files()`.

```python
class BengalParsingError(BengalError):
    """Errors during YAML, JSON, TOML, or Markdown parsing (BuildPhase.PARSING)."""
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("build_phase", BuildPhase.PARSING)
        super().__init__(message, **kwargs)

class BengalAutodocError(BengalError):
    """Errors during autodoc extraction (BuildPhase.DISCOVERY)."""
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("build_phase", BuildPhase.DISCOVERY)
        super().__init__(message, **kwargs)

class BengalBuildError(BengalError):
    """Errors during build orchestration (BuildPhase.POSTPROCESSING)."""
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("build_phase", BuildPhase.POSTPROCESSING)
        super().__init__(message, **kwargs)

class BengalValidatorError(BengalError):
    """Errors during health checks and validation (BuildPhase.ANALYSIS)."""
    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("build_phase", BuildPhase.ANALYSIS)
        super().__init__(message, **kwargs)

class BengalTemplateFunctionError(BengalRenderingError):
    """Errors in shortcodes or directives (BuildPhase.RENDERING)."""
    pass
```

#### 1.2 Register Suggestions
Update `bengal/errors/suggestions.py` to include registries for new error categories. This ensures the CLI provides actionable "Tips" for these errors.

```python
_SUGGESTIONS.update({
    "autodoc": {
        "extraction_failed": ActionableSuggestion(
            fix="Check if the source module is importable and has no syntax errors",
            explanation="Autodoc failed to extract elements from the specified source.",
            check_files=["bengal/autodoc/"],
            related_codes=["O001"]
        )
    },
    # Add validator, build, and parsing suggestions
})
```

**Note**: `BuildPhase` enum already covers these via existing values:
- `PARSING` → for `BengalParsingError`
- `POSTPROCESSING` → for `BengalBuildError` (or use existing phases contextually)
- `ANALYSIS` → for `BengalValidatorError` (health checks analyze site)

No enum additions needed.

### Phase 2: Convert High-Priority Generic Exceptions (~50 LOC)

#### 2.1 Autodoc Cache Errors (`autodoc/base.py`)

```python
# Before (lines 316, 326, 336, 346, 356):
raise TypeError(
    f"Autodoc cache format mismatch in {context}: expected dict, got {type(p).__name__}. "
    f"Value: {p!r}. This usually means the cache was created with an older version. "
    f"Clear the cache with: rm -rf .bengal/cache/"
)

# After:
from bengal.errors import BengalCacheError, ErrorCode

raise BengalCacheError(
    f"Autodoc cache format mismatch in {context}: expected dict, got {type(p).__name__}",
    code=ErrorCode.A001,
    suggestion="Clear the cache with: rm -rf .bengal/cache/",
    debug_payload=ErrorDebugPayload(
        context={"expected": "dict", "got": type(p).__name__, "value": repr(p)[:100]},
        grep_patterns=["autodoc_cache", "from_cache_dict"],
    ),
)
```

#### 2.2 Cache Corruption (`autodoc/orchestration/orchestrator.py:186`)

```python
# Before:
raise ValueError(
    f"Autodoc cache corrupted: {len(deserialization_failures)} element(s) "
    f"failed to deserialize in {', '.join(sorted(failed_types))}. "
    f"Cache will be invalidated and re-extracted."
)

# After:
raise BengalCacheError(
    f"Autodoc cache corrupted: {len(deserialization_failures)} element(s) failed",
    code=ErrorCode.A001,
    suggestion="Cache will be invalidated automatically. If error persists, rm -rf .bengal/cache/",
)
```

#### 2.3 Cache Compression (`cache/compression.py:243`)

```python
# Before:
raise ValueError(
    f"Cache file {json_path} contains invalid data type: {type(data).__name__}. "
    "Expected dict."
)

# After:
raise BengalCacheError(
    f"Cache file contains invalid data type: {type(data).__name__}",
    code=ErrorCode.A001,
    file_path=json_path,
    suggestion="Clear the cache with: rm -rf .bengal/cache/",
)
```

#### 2.4 Write-Behind Pipeline (`rendering/pipeline/write_behind.py`)

```python
# Before (lines 108, 183, 186):
raise RuntimeError(f"Writer thread failed: {self._error}") from self._error

# After:
raise BengalRenderingError(
    f"Background writer thread failed: {self._error}",
    code=ErrorCode.R010,
    original_error=self._error,
    suggestion="Check disk space and file permissions in output directory",
)
```

### Phase 3: Observability and Payload Enrichment (~30 LOC)

Converted errors should include an `ErrorDebugPayload` where possible to provide AI assistants with immediately searchable context.

```python
# autodoc/base.py example
raise BengalCacheError(
    f"Autodoc cache format mismatch: expected dict, got {type(p).__name__}",
    code=ErrorCode.A001,
    debug_payload=ErrorDebugPayload(
        context={"expected": "dict", "actual": type(p).__name__},
        grep_patterns=["autodoc_cache", "CACHE_VERSION"],
        test_files=["tests/unit/autodoc/test_cache.py"]
    )
)
```

## Non-Goals

The following are explicitly **not** in scope for this RFC:

1. **Converting all generic exceptions**: Some `ValueError`/`TypeError` usages are appropriate for programming errors caught at development time (e.g., plugin registration validation).

2. **Changing exception class inheritance**: Existing code catching `BengalContentError` or `BengalRenderingError` should continue to work.

3. **Adding new error codes**: This RFC uses existing codes. New codes may be added in future RFCs.

4. **Broad `except Exception` cleanup**: Most broad catches are appropriate for graceful degradation in dev server and incremental builds.

---

## Migration Strategy

### Backward Compatibility

All changes are **additive** or use existing codes:
- New exception classes extend existing `BengalError` hierarchy
- Converted exceptions use existing error codes
- No changes to error handling callsites needed

### Gradual Adoption

Phase 2 conversions can be done incrementally:
1. Start with highest-impact: autodoc cache errors (most common user complaint)
2. Then write-behind errors (affects build failures)
3. Then remaining cache/highlighting errors

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/errors/test_exceptions.py

def test_bengal_parsing_error_sets_build_phase():
    """BengalParsingError auto-sets PARSING build phase."""
    error = BengalParsingError("test", code=ErrorCode.P001)
    assert error.build_phase == BuildPhase.PARSING


def test_bengal_autodoc_error_sets_build_phase():
    """BengalAutodocError auto-sets DISCOVERY build phase."""
    error = BengalAutodocError("test", code=ErrorCode.O001)
    assert error.build_phase == BuildPhase.DISCOVERY


def test_converted_cache_error_has_code():
    """Converted cache errors include error code."""
    # Simulate what autodoc/base.py now raises
    error = BengalCacheError(
        "Cache format mismatch",
        code=ErrorCode.A001,
        suggestion="Clear cache",
    )
    assert error.code == ErrorCode.A001
    assert "A001" in str(error)
    assert error.get_docs_url() == "/docs/reference/errors/#a001"
```

### Integration Tests

```python
# tests/integration/test_error_handling.py

def test_autodoc_cache_corruption_raises_bengal_error(tmp_path):
    """Corrupted autodoc cache raises BengalCacheError with code."""
    # Create corrupted cache
    cache_path = tmp_path / ".bengal" / "cache" / "autodoc.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text('["not", "a", "dict"]')  # Invalid format
    
    with pytest.raises(BengalCacheError) as exc_info:
        # Trigger cache load
        ...
    
    assert exc_info.value.code == ErrorCode.A001
    assert "cache" in exc_info.value.suggestion.lower()
```

---

## Implementation Checklist

### Phase 1: Exception Classes
- [ ] Add `BengalParsingError` class
- [ ] Add `BengalBuildError` class
- [ ] Add `BengalAutodocError` class
- [ ] Add `BengalValidatorError` class
- [ ] Add `BengalTemplateFunctionError` class
- [ ] Update `__init__.py` exports
- [ ] Add unit tests for new classes

### Phase 2: Convert Exceptions
- [ ] Convert `autodoc/base.py` TypeErrors (5 instances)
- [ ] Convert `autodoc/orchestration/orchestrator.py:186` ValueError
- [ ] Convert `cache/compression.py:243` ValueError
- [ ] Convert `rendering/pipeline/write_behind.py` RuntimeErrors (3 instances)
- [ ] Add integration tests for converted errors

### Phase 3: Documentation
- [ ] Update error documentation to list new exception classes
- [ ] Add examples showing proper exception usage

---

## Success Criteria

1. **Zero generic exceptions** in high-priority paths (autodoc, cache, write-behind)
2. **All error code categories** have corresponding exception classes
3. **No breaking changes** to existing error handling code
4. **Tests pass** for all converted exceptions
5. **Investigation commands** work for converted errors (`get_investigation_commands()`)

---

## Appendix: Full Generic Exception Inventory

<details>
<summary>All 26 generic exception locations (click to expand)</summary>

```
HIGH PRIORITY (convert):
bengal/autodoc/base.py:316 - TypeError (cache format)
bengal/autodoc/base.py:326 - TypeError (cache format)
bengal/autodoc/base.py:336 - TypeError (cache format)
bengal/autodoc/base.py:346 - TypeError (cache format)
bengal/autodoc/base.py:356 - TypeError (cache format)
bengal/autodoc/orchestration/orchestrator.py:186 - ValueError (cache corruption)
bengal/cache/compression.py:243 - ValueError (invalid data type)
bengal/rendering/pipeline/write_behind.py:108 - RuntimeError (writer failed)
bengal/rendering/pipeline/write_behind.py:183 - RuntimeError (timeout)
bengal/rendering/pipeline/write_behind.py:186 - RuntimeError (writer failed)

MEDIUM PRIORITY (consider converting):
bengal/rendering/highlighting/__init__.py:92 - TypeError (backend class)
bengal/rendering/highlighting/__init__.py:144 - RuntimeError (no backend)
bengal/utils/cache_registry.py:226 - ValueError (cycle detected)

LOW PRIORITY (keep as-is):
bengal/rendering/parsers/patitas/directives/decorator.py:90 - ValueError
bengal/rendering/parsers/patitas/directives/registry.py:136 - TypeError
bengal/rendering/parsers/patitas/directives/registry.py:140 - TypeError
bengal/rendering/parsers/patitas/directives/registry.py:147 - ValueError
bengal/rendering/parsers/patitas/roles/registry.py:136 - TypeError
bengal/rendering/parsers/patitas/roles/registry.py:140 - TypeError
bengal/rendering/parsers/patitas/roles/registry.py:147 - ValueError
bengal/rendering/parsers/patitas/__init__.py:370 - TypeError
bengal/rendering/parsers/patitas/directives/options.py:143 - ValueError
bengal/rendering/parsers/patitas/directives/options.py:150 - ValueError
bengal/rendering/template_functions/tables.py:100 - TypeError
bengal/collections/validator.py:246 - TypeError
bengal/utils/primitives/dates.py:97 - ValueError
```

</details>

---

## References

- `bengal/errors/codes.py` - Error code definitions
- `bengal/errors/exceptions.py` - Exception class hierarchy
- `bengal/errors/__init__.py` - Public API exports
