# RFC: Content Layer Package Error System Adoption

**Status**: Drafted  
**Created**: 2025-12-24  
**Last Verified**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/content_layer/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified against source; N011-N015 conflict resolved)  
**Priority**: P2 (Medium) — Remote content fetching is user-facing; errors need actionable context  
**Estimated Effort**: 2.25 hours (single dev)

---

## Executive Summary

The `bengal/content_layer/` package has **partial adoption** of the Bengal error system. Configuration validation properly uses `BengalConfigError` with error codes, but network/API failures, content fetch errors, and cache operations use generic logging and raw exceptions instead of the Bengal error framework.

**Current state**:
- **7 uses** of Bengal error framework (all for config validation)
- **2 error codes used**: `C002` (missing config), `C003` (invalid value)
- **0 content layer-specific codes**: No D0xx or N0xx codes for fetch/parse errors
- **8 locations** with generic `except Exception` handling
- **9 locations** use `logger.error()` or `logger.warning()` instead of raising
- **0 `record_error()` calls**: No session tracking

**Adoption Score**: 5/10

**Recommendation**: Add content layer-specific error codes (D008-D011, N016), wrap fetch/parse errors in Bengal exceptions, replace raw `ImportError` with `BengalConfigError`, and add `record_error()` for session tracking.

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
- **Error session recording** for build summaries
- **Investigation helpers** (grep commands, related files)
- **Actionable suggestions** for user recovery

The content layer package handles remote content fetching from GitHub, REST APIs, and Notion. These operations are prone to failures (network issues, auth errors, rate limits) that users need actionable guidance to resolve.

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No fetch error codes | Can't search docs for API errors | No categorized error tracking |
| Silent return on 404/403 | Content silently missing | Hard-to-debug empty collections |
| Raw `ImportError` | Confusing dependency errors | Not tracked in error sessions |
| No session recording | Build summaries miss content errors | No recurring pattern detection |
| Generic exceptions | Vague "fetch failed" messages | No investigation helpers |

---

## Current State Evidence

### Files in Package

| File | Purpose | Lines |
|------|---------|-------|
| `__init__.py` | Package exports | 82 |
| `entry.py` | `ContentEntry` data class | 154 |
| `loaders.py` | Factory functions for sources | 254 |
| `manager.py` | `ContentLayerManager` orchestrator | 407 |
| `source.py` | `ContentSource` abstract base | 190 |
| `sources/__init__.py` | Source registry | 86 |
| `sources/local.py` | `LocalSource` filesystem loader | 300 |
| `sources/github.py` | `GitHubSource` API loader | 306 |
| `sources/rest.py` | `RESTSource` generic API loader | 297 |
| `sources/notion.py` | `NotionSource` Notion API loader | 576 |

### Error Framework Usage Summary

| Category | Count | Locations |
|----------|-------|-----------|
| Uses `BengalConfigError` | 7 | Config validation in sources |
| Uses `BengalError` | 1 | Offline mode in manager |
| Uses raw `ImportError` | 6 | Module-level and factories |
| Uses `logger.error()` only | 5 | 404/403/401 responses |
| Uses `logger.warning()` only | 4 | Parse failures, fallbacks |
| Bare `except Exception` | 3 | Fetch failures |

### Locations Using Bengal Framework (✅ Good)

**1. LocalSource config validation** (`local.py:102-109`):

```python
from bengal.errors import BengalConfigError, ErrorCode

if "directory" not in config:
    raise BengalConfigError(
        f"LocalSource '{name}' requires 'directory' in config",
        suggestion="Add 'directory' to LocalSource configuration",
        code=ErrorCode.C002,
    )
```

**2. GitHubSource config validation** (`github.py:88-95`):

```python
from bengal.errors import BengalConfigError, ErrorCode

if "repo" not in config:
    raise BengalConfigError(
        f"GitHubSource '{name}' requires 'repo' in config",
        suggestion="Add 'repo' to GitHubSource configuration",
        code=ErrorCode.C002,
    )
```

**3. RESTSource config validation** (`rest.py:73-80`):

```python
from bengal.errors import BengalConfigError, ErrorCode

if "url" not in config:
    raise BengalConfigError(
        f"RESTSource '{name}' requires 'url' in config",
        suggestion="Add 'url' to RESTSource configuration",
        code=ErrorCode.C002,
    )
```

**4. NotionSource config validation** (`notion.py:99-126`):

```python
from bengal.errors import BengalConfigError, ErrorCode

if "database_id" not in config:
    raise BengalConfigError(
        f"NotionSource '{name}' requires 'database_id' in config",
        suggestion="Add 'database_id' to NotionSource configuration",
        code=ErrorCode.C002,
    )

# ...

if not self.token:
    raise BengalConfigError(
        f"NotionSource '{name}' requires a token...",
        suggestion="Set NOTION_TOKEN environment variable or add 'token' to config",
        code=ErrorCode.C002,
    )
```

**5. ContentLayerManager source type validation** (`manager.py:97-107`):

```python
if source_type not in SOURCE_REGISTRY:
    available = ", ".join(sorted(SOURCE_REGISTRY.keys()))
    from bengal.errors import ErrorCode

    raise BengalConfigError(
        f"Unknown source type: {source_type!r}\n"
        f"Available types: {available}\n"
        f"For remote sources, install extras: pip install bengal[{source_type}]",
        suggestion=f"Use one of the available source types: {available}",
        code=ErrorCode.C003,
    )
```

**6. ContentLayerManager offline mode** (`manager.py:199-202`):

```python
raise BengalError(
    f"Cannot fetch from '{name}' in offline mode (no cache available)",
    suggestion="Run with online mode or ensure cache is available",
)
```

### Locations Using Raw Exceptions (❌ Gap)

**1. Module-level ImportError in github.py** (`github.py:24-29`):

```python
try:
    import aiohttp
except ImportError as e:
    raise ImportError(
        "GitHubSource requires aiohttp.\nInstall with: pip install bengal[github]"
    ) from e
```

**2. Module-level ImportError in rest.py** (`rest.py:16-19`):

```python
try:
    import aiohttp
except ImportError as e:
    raise ImportError("RESTSource requires aiohttp.\nInstall with: pip install bengal[rest]") from e
```

**3. Module-level ImportError in notion.py** (`notion.py:22-27`):

```python
try:
    import aiohttp
except ImportError as e:
    raise ImportError(
        "NotionSource requires aiohttp.\nInstall with: pip install bengal[notion]"
    ) from e
```

**4-6. Factory function ImportErrors in loaders.py** (`loaders.py:94-99`, `loaders.py:158-163`, `loaders.py:226-231`):

```python
except ImportError as e:
    raise ImportError(
        "github_loader requires aiohttp.\nInstall with: pip install bengal[github]"
    ) from e
```

### Locations Using Logger Only (❌ Gap)

**1. GitHub 404 response** (`github.py:126-128`):

```python
if resp.status == 404:
    logger.error(f"Repository not found: {self.repo}")
    return  # Silent return - no entries
```

**2. GitHub 403 response** (`github.py:129-131`):

```python
if resp.status == 403:
    logger.error(f"Rate limit exceeded or access denied for {self.repo}")
    return  # Silent return - no entries
```

**3. Notion 404 response** (`notion.py:179-181`):

```python
if resp.status == 404:
    logger.error(f"Database not found: {self.database_id}")
    return
```

**4. Notion 401 response** (`notion.py:182-184`):

```python
if resp.status == 401:
    logger.error("Invalid Notion token or database not shared with integration")
    return
```

**5. Local frontmatter parse failure** (`local.py:58-60`):

```python
except Exception as e:
    logger.warning(f"Failed to parse frontmatter: {e}")
    return {}, content
```

**6. Local file read failure** (`local.py:200-204`):

```python
except Exception as e:
    logger.warning(f"Failed to read {path}: {e}")
    return None
```

### Locations Using Bare Exception Handling (❌ Gap)

**1. Manager fetch failure** (`manager.py:208-217`):

```python
try:
    async for entry in source.fetch_all():
        entries.append(entry)
except Exception as e:
    # Try to fall back to cache on error
    cached = self._load_cache(name)
    if cached:
        logger.warning(f"Fetch failed for '{name}', using cached content: {e}")
        return cached
    raise  # Re-raises generic exception
```

**2. GitHub file fetch failure** (`github.py:177-183`):

```python
for coro in asyncio.as_completed(tasks):
    try:
        entry = await coro
        if entry:
            yield entry
    except Exception as e:
        failed_count += 1
        logger.error(f"Failed to fetch file: {e}")
```

**3. Notion page processing failure** (`notion.py:209-216`):

```python
for coro in asyncio.as_completed(tasks):
    try:
        entry = await coro
        if entry:
            yield entry
    except Exception as e:
        failed_count += 1
        logger.error(f"Failed to process page: {e}")
```

### Existing Error Codes Applicable to Content Layer

**Discovery codes (D-series)** that could be reused:

| Code | Value | Potential Use |
|------|-------|---------------|
| D001 | `content_dir_not_found` | Local source directory missing |
| D007 | `permission_denied` | File permission errors |

**Content codes (N-series)** that could be reused:

| Code | Value | Potential Use |
|------|-------|---------------|
| N001 | `frontmatter_invalid` | Parse failures in local source |
| N003 | `content_file_encoding` | UTF-8 encoding errors |
| N004 | `content_file_not_found` | Missing content files |

**Note**: N011-N015 already exist for collections (added via `rfc-collections-error-adoption.md`).

---

## Gap Analysis

### Gap 1: No Content Layer-Specific Error Codes

**Current**: Only uses `C002` and `C003` (config codes)  
**Expected**: Discovery/Content codes for fetch and parse operations

**Proposed new codes** (add to `bengal/errors/codes.py`):

```python
# Discovery errors (D001-D099) - continued: Content Layer
# Add after D007:
D008 = "content_source_fetch_failed"     # Remote source fetch failure
D009 = "content_source_offline"          # Offline mode with no cache
D010 = "content_source_auth_failed"      # 401/403 authentication error
D011 = "content_source_not_found"        # 404 source/repo/database not found

# Content errors (N001-N099) - continued: Content Layer
# Add after N015 (N011-N015 already exist for collections):
N016 = "content_entry_parse_failed"      # Remote entry parse/conversion error

# Note: Use N001 for local frontmatter errors, N016 for remote content parsing
# (e.g., Notion block conversion, REST API response parsing)
```

### Gap 2: ImportError Not Wrapped in Bengal Exception

**Current**: Raw `ImportError` at module level and in factories  
**Impact**: Errors not searchable, no investigation helpers, no session tracking

**Example fix** (`loaders.py:94-99`):

```python
# Before
except ImportError as e:
    raise ImportError(
        "github_loader requires aiohttp.\nInstall with: pip install bengal[github]"
    ) from e

# After
except ImportError as e:
    from bengal.errors import BengalConfigError, ErrorCode

    raise BengalConfigError(
        "github_loader requires aiohttp",
        code=ErrorCode.C002,
        suggestion="Install with: pip install bengal[github]",
        original_error=e,
    ) from e
```

### Gap 3: Network Errors Not Wrapped in Bengal Exceptions

**Current**: `logger.error()` + silent return for 404/403/401  
**Impact**: Users see empty content with no error message or guidance

**Example fix** (`github.py:126-131`):

```python
# Before
if resp.status == 404:
    logger.error(f"Repository not found: {self.repo}")
    return

# After
if resp.status == 404:
    from bengal.errors import BengalDiscoveryError, ErrorCode

    raise BengalDiscoveryError(
        f"GitHub repository not found: {self.repo}",
        code=ErrorCode.D011,  # content_source_not_found
        suggestion=f"Verify repository exists: https://github.com/{self.repo}",
    )
```

### Gap 4: Manager Uses Generic Exception Handling

**Current**: Bare `except Exception` with `logger.warning()`  
**Impact**: No session tracking, no actionable suggestions, generic error messages

**Example fix** (`manager.py:208-217`):

```python
# Before
except Exception as e:
    cached = self._load_cache(name)
    if cached:
        logger.warning(f"Fetch failed for '{name}', using cached content: {e}")
        return cached
    raise

# After
except Exception as e:
    from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

    # Try to fall back to cache
    cached = self._load_cache(name)
    if cached:
        # Record but continue with cache
        warning = BengalDiscoveryError(
            f"Fetch failed for '{name}', using cached content",
            code=ErrorCode.D008,  # content_source_fetch_failed
            suggestion=f"Check network connectivity and source configuration for '{name}'",
            original_error=e,
        )
        record_error(warning, file_path=str(self.cache_dir / f"{name}.json"))
        logger.warning(f"Fetch failed for '{name}', using cached content: {e}")
        return cached

    # No cache fallback - raise proper exception
    error = BengalDiscoveryError(
        f"Failed to fetch content from '{name}': {e}",
        code=ErrorCode.D008,
        suggestion=f"Check network connectivity and source configuration for '{name}'",
        original_error=e,
    )
    record_error(error)
    raise error from e
```

### Gap 5: No Error Session Recording

**Current**: 0 calls to `record_error()` in content_layer package  
**Impact**: Build summaries don't include content layer errors; no pattern detection

### Gap 6: Local Source Errors Not Properly Handled

**Current**: `logger.warning()` for file read/parse failures  
**Expected**: Use `BengalContentError` with appropriate codes

**Example fix** (`local.py:200-204`):

```python
# Before
except Exception as e:
    logger.warning(f"Failed to read {path}: {e}")
    return None

# After
except Exception as e:
    from bengal.errors import BengalContentError, ErrorCode, record_error

    error = BengalContentError(
        f"Failed to read content file: {path}",
        code=ErrorCode.N003,  # content_file_encoding (or N004 for not found)
        file_path=path,
        suggestion="Check file encoding (UTF-8 expected) and permissions",
        original_error=e,
    )
    record_error(error, file_path=str(path))
    logger.warning(f"Failed to read {path}: {e}")
    return None  # Still graceful degradation
```

---

## Proposed Changes

### Phase 1: Add Error Codes (10 min)

**File**: `bengal/errors/codes.py`

Add after D007 (line ~163):

```python
# Discovery errors - Content Layer
D008 = "content_source_fetch_failed"     # Remote source fetch failure
D009 = "content_source_offline"          # Offline mode with no cache
D010 = "content_source_auth_failed"      # 401/403 authentication error
D011 = "content_source_not_found"        # 404 source/repo/database not found
```

Add after N015 (line ~138) — N011-N015 already exist for collections:

```python
N016 = "content_entry_parse_failed"      # Entry parse/conversion error
```

### Phase 2: Update Loader Factories (15 min)

**File**: `bengal/content_layer/loaders.py`

Update all 4 factory functions to use `BengalConfigError`:

```python
def github_loader(...) -> ContentSource:
    try:
        from bengal.content_layer.sources.github import GitHubSource
    except ImportError as e:
        from bengal.errors import BengalConfigError, ErrorCode

        raise BengalConfigError(
            "github_loader requires aiohttp",
            code=ErrorCode.C002,
            suggestion="Install with: pip install bengal[github]",
            original_error=e,
        ) from e
    # ... rest of function
```

Repeat for `rest_loader`, `notion_loader`.

### Phase 3: Update Manager Error Handling (30 min)

**File**: `bengal/content_layer/manager.py`

#### 3.1 Update offline mode error (`manager.py:199-202`)

```python
raise BengalDiscoveryError(
    f"Cannot fetch from '{name}' in offline mode (no cache available)",
    code=ErrorCode.D009,  # content_source_offline
    suggestion="Run with online mode first to populate cache, or check cache directory",
)
```

#### 3.2 Update fetch failure handling (`manager.py:208-217`)

Wrap in `BengalDiscoveryError`, add `record_error()` call.

#### 3.3 Update aggregation error handling (`manager.py:150-158`)

```python
if isinstance(result, Exception):
    from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

    error = BengalDiscoveryError(
        f"Failed to fetch from source '{name}': {result}",
        code=ErrorCode.D008,
        original_error=result,
    )
    record_error(error)
    logger.error(f"Failed to fetch from source '{name}': {result}")
    # ... existing cache fallback logic
```

### Phase 4: Update GitHubSource (30 min)

**File**: `bengal/content_layer/sources/github.py`

#### 4.1 Remove module-level ImportError, use lazy import pattern

Move aiohttp import inside methods or catch at usage point.

#### 4.2 Update 404/403 handling

```python
if resp.status == 404:
    from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

    error = BengalDiscoveryError(
        f"GitHub repository not found: {self.repo}",
        code=ErrorCode.D011,
        suggestion=f"Verify repository exists and is accessible: https://github.com/{self.repo}",
    )
    record_error(error)
    raise error

if resp.status == 403:
    from bengal.errors import BengalDiscoveryError, ErrorCode, record_error

    error = BengalDiscoveryError(
        f"Access denied to GitHub repository: {self.repo}",
        code=ErrorCode.D010,
        suggestion="Check GITHUB_TOKEN is set and has read access to the repository",
    )
    record_error(error)
    raise error
```

#### 4.3 Update file fetch error handling

Wrap individual file fetch failures in `BengalContentError`.

### Phase 5: Update RESTSource (20 min)

**File**: `bengal/content_layer/sources/rest.py`

Apply same patterns as GitHubSource:
- Lazy import for aiohttp
- Wrap HTTP errors in `BengalDiscoveryError`
- Add `record_error()` calls

### Phase 6: Update NotionSource (20 min)

**File**: `bengal/content_layer/sources/notion.py`

Apply same patterns:
- Lazy import for aiohttp
- Wrap 404/401 in `BengalDiscoveryError` with appropriate codes
- Add `record_error()` calls

### Phase 7: Update LocalSource (15 min)

**File**: `bengal/content_layer/sources/local.py`

#### 7.1 Update frontmatter parse error

```python
except Exception as e:
    from bengal.errors import BengalContentError, ErrorCode, record_error

    # Record but continue - graceful degradation
    error = BengalContentError(
        f"Failed to parse frontmatter in content",
        code=ErrorCode.N001,  # frontmatter_invalid (existing code)
        suggestion="Check YAML syntax in frontmatter block",
        original_error=e,
    )
    record_error(error)
    logger.warning(f"Failed to parse frontmatter: {e}")
    return {}, content
```

#### 7.2 Update file read error

```python
except Exception as e:
    from bengal.errors import BengalContentError, ErrorCode, record_error

    error = BengalContentError(
        f"Failed to read content file: {path}",
        code=ErrorCode.N003,
        file_path=path,
        suggestion="Check file encoding (UTF-8 expected) and permissions",
        original_error=e,
    )
    record_error(error, file_path=str(path))
    logger.warning(f"Failed to read {path}: {e}")
    return None
```

### Phase 8: Add Test Mapping (5 min)

**File**: `bengal/errors/exceptions.py`

Add content_layer to test file mapping:

```python
test_mapping: dict[type, list[str]] = {
    # ... existing mappings ...
    BengalDiscoveryError: [
        "tests/unit/discovery/",
        "tests/unit/content_layer/",  # ADD
        "tests/integration/test_discovery.py",
    ],
}
```

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add error codes D008-D011, N016 | 10 min | P1 |
| 2 | Update `loaders.py` factory ImportErrors | 15 min | P1 |
| 3 | Update `manager.py` fetch error handling | 30 min | P1 |
| 4 | Update `github.py` error handling | 30 min | P1 |
| 5 | Update `rest.py` error handling | 20 min | P1 |
| 6 | Update `notion.py` error handling | 20 min | P1 |
| 7 | Update `local.py` file read/parse errors | 15 min | P2 |
| 8 | Add test mapping | 5 min | P2 |

**Total**: ~2.25 hours

---

## Success Criteria

### Must Have

- [ ] D008-D011 error codes defined in `codes.py`
- [ ] N016 error code defined in `codes.py`
- [ ] All `ImportError` raises in loaders/sources use `BengalConfigError`
- [ ] 404/403/401 responses raise `BengalDiscoveryError` with codes
- [ ] Manager fetch failures wrapped in `BengalDiscoveryError`
- [ ] `record_error()` called for all error conditions

### Should Have

- [ ] LocalSource file read/parse errors use `BengalContentError`
- [ ] Test mapping updated for content_layer
- [ ] All existing tests pass after changes

### Nice to Have

- [ ] Rate limit errors (429) use exponential backoff with warning tracking
- [ ] Cache corruption detection uses `BengalCacheError`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking exception handlers | Low | Medium | Changes wrap existing exceptions, don't change types |
| Silent failures now raise | Medium | Low | Add `strict` mode flag, default to graceful degradation |
| Performance of record_error | Very Low | Negligible | O(1) per error |
| Test failures | Low | Low | Run `pytest tests/` after changes |
| Circular imports | Low | Medium | Use lazy imports inside functions |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/errors/codes.py` | Add error codes D008-D011, N016 | +5 |
| `bengal/content_layer/loaders.py` | Update ImportError handling | +20 |
| `bengal/content_layer/manager.py` | Wrap fetch errors, add recording | +30 |
| `bengal/content_layer/sources/github.py` | Wrap HTTP errors, add recording | +25 |
| `bengal/content_layer/sources/rest.py` | Wrap HTTP errors, add recording | +20 |
| `bengal/content_layer/sources/notion.py` | Wrap HTTP errors, add recording | +25 |
| `bengal/content_layer/sources/local.py` | Wrap file errors, add recording | +15 |
| `bengal/errors/exceptions.py` | Add test mapping | +1 |
| **Total** | — | ~141 |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 3/10 | 9/10 | All error paths get codes |
| Bengal exception usage | 5/10 | 9/10 | Network/parse errors wrapped |
| Session recording | 0/10 | 9/10 | `record_error()` throughout |
| Actionable suggestions | 5/10 | 9/10 | All errors have suggestions |
| Build phase tracking | 4/10 | 9/10 | Via BengalDiscoveryError |
| Silent failure handling | 4/10 | 8/10 | Errors recorded even in fallback |
| **Overall** | **5/10** | **9/10** | — |

---

## References

- `bengal/errors/codes.py:155-163` — D-series discovery codes (D001-D007)
- `bengal/errors/codes.py:121-138` — N-series content codes (N001-N015)
- `bengal/errors/exceptions.py` — BengalDiscoveryError, BengalContentError definitions
- `bengal/content_layer/manager.py:199-217` — Current fetch error handling
- `bengal/content_layer/sources/github.py:126-131` — Current 404/403 handling
- `plan/drafted/rfc-collections-error-adoption.md` — Related RFC for collections (N011-N015 already implemented)
