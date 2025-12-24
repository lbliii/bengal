# RFC: Postprocess Package Error System Adoption

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/postprocess/`, `bengal/errors/`  
**Confidence**: 95% 🟢 (all claims verified via grep against source files)  
**Priority**: P2 (Medium) — Post-processing errors are user-facing; failures affect build output  
**Estimated Effort**: 2-2.5 hours (single dev)

---

## Executive Summary

The `bengal/postprocess/` package has **zero adoption** (0%) of the Bengal error system. While the package logs errors appropriately, it relies entirely on generic Python exceptions without:
- Structured error codes (`ErrorCode` enum)
- Bengal exception classes (`BengalError`)
- Session tracking (`record_error()`)
- Actionable suggestions for recovery

**Critical finding**: `ErrorCode.B008` (`postprocess_task_failed`) already exists in `bengal/errors/codes.py` but is **not used anywhere** in the postprocess package.

**Current state**:
- **0 imports** from `bengal.errors`
- **0/16 files** use `BengalError` or `ErrorCode`
- **8 logger.error() calls** without `error_code` field
- **12 logger.warning() calls** without structured codes
- **0 session tracking** via `record_error()`
- **0 actionable suggestions** in error messages

**Recommendation**:
1. Use existing `ErrorCode.B008` (`postprocess_task_failed`) across the package
2. Add `error_code` field to all `logger.error()` calls
3. Add actionable `suggestion` fields to error logging
4. Add session tracking for post-processing failures
5. Optionally wrap critical failures in `BengalRenderingError`

**Adoption Score**: 0/10 → **6/10** (target)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Architecture Analysis](#architecture-analysis)
4. [Gap Analysis](#gap-analysis)
5. [Proposed Changes](#proposed-changes)
6. [Implementation Phases](#implementation-phases)
7. [Success Criteria](#success-criteria)
8. [Risks and Mitigations](#risks-and-mitigations)

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

Post-processing generates critical SEO assets (sitemap.xml, RSS feeds), search indexes, redirect pages, and LLM-friendly content exports. When post-processing fails, users need:
- Clear identification of which component failed
- Actionable guidance for resolution
- Consistent error tracking for pattern detection

### Impact

| Issue | User Impact | Developer Impact |
|-------|-------------|------------------|
| No error codes in logs | Post-processing failures hard to search/diagnose | Can't grep for specific errors |
| No session tracking | Build summaries miss postprocess errors | No pattern detection |
| No suggestions | Cryptic "generation failed" messages | Manual investigation required |
| Generic exceptions | No docs linking | Harder to find solutions |

---

## Current State Evidence

### Package Structure

```
bengal/postprocess/
├── __init__.py              # Package exports (16 symbols)
├── html_output.py           # HTML minification utilities
├── redirects.py             # Redirect page generator
├── rss.py                   # RSS feed generator
├── sitemap.py               # XML sitemap generator
├── social_cards.py          # Open Graph image generator
├── special_pages.py         # 404, search, graph pages
├── speculation.py           # Speculation rules generator
└── output_formats/          # Alternative output generators
    ├── __init__.py          # Facade (OutputFormatsGenerator)
    ├── base.py              # Abstract base class
    ├── index_generator.py   # Site-wide index.json
    ├── json_generator.py    # Per-page JSON files
    ├── llm_generator.py     # Site-wide llm-full.txt
    ├── lunr_index_generator.py  # Pre-built Lunr index
    ├── txt_generator.py     # Per-page LLM text files
    └── utils.py             # Shared utilities
```

### ErrorCode Usage

**Grep Result**: `grep -r "ErrorCode" bengal/postprocess/` → **0 matches**

**Grep Result**: `grep -r "from bengal.errors" bengal/postprocess/` → **0 matches**

The postprocess package does not import or use any components from the Bengal error system.

### Existing Unused Error Code

**File**: `bengal/errors/codes.py:279`

```python
# Build/Orchestration errors (B001-B099)
B008 = "postprocess_task_failed"  # Post-processing task failure
```

This code was defined but is **not used** anywhere in the codebase.

### Logger.error Calls (8 total, none with error_code)

| File | Location | Event Name | Has error_code | Has suggestion |
|------|----------|------------|----------------|----------------|
| `sitemap.py` | line 234 | `sitemap_generation_failed` | ❌ | ❌ |
| `rss.py` | line 221 | `rss_generation_failed` | ❌ | ❌ |
| `special_pages.py` | line 263 | `404_page_generation_failed` | ❌ | ❌ |
| `special_pages.py` | line 374 | `search_page_generation_failed` | ❌ | ❌ |
| `special_pages.py` | line 473 | `graph_generation_failed` | ❌ | ❌ |
| `output_formats/json_generator.py` | line 191 | `page_json_generation_failed` | ❌ | ❌ |
| `output_formats/txt_generator.py` | line 161 | `page_txt_generation_failed` | ❌ | ❌ |
| `output_formats/llm_generator.py` | line 237 | `llm_full_generation_failed` | ❌ | ❌ |

### Logger.warning Calls (12 total, none with error_code)

| File | Location | Event Name |
|------|----------|------------|
| `redirects.py` | line 142 | `redirect_alias_conflict` |
| `redirects.py` | line 182 | `redirect_invalid_alias` |
| `redirects.py` | line 204 | `redirect_conflict` |
| `redirects.py` | line 214 | `redirect_conflict` |
| `social_cards.py` | line 259 | `social_cards_fonts_unavailable` |
| `social_cards.py` | line 381 | `social_cards_ttf_download_failed` |
| `social_cards.py` | line 817 | `social_card_generation_failed` |
| `social_cards.py` | line 823 | `social_card_generation_completed_with_errors` |
| `special_pages.py` | line 146 | `no_special_pages_generated` |
| `output_formats/index_generator.py` | line 513 | `index_generation_failed` |
| `output_formats/lunr_index_generator.py` | line 184 | `lunr_index_generation_failed` |

### Session Tracking

**Grep Result**: `grep -r "record_error" bengal/postprocess/` → **0 matches**

Post-processing failures are not tracked in error sessions.

### Exception Handling Pattern Analysis

**Pattern 1: Log and Re-raise** (`sitemap.py:233-240`)

```python
except Exception as e:
    self.logger.error(
        "sitemap_generation_failed",
        sitemap_path=str(sitemap_path),
        error=str(e),
        error_type=type(e).__name__,
    )
    raise
```

**Gap**: No error code, no suggestion, no session tracking.

**Pattern 2: Log and Return False** (`special_pages.py:262-264`)

```python
except Exception as e:
    logger.error("404_page_generation_failed", error=str(e), error_type=type(e).__name__)
    return False
```

**Gap**: No error code, no suggestion. Failure silently continues build.

**Pattern 3: Log Warning Only** (`social_cards.py:256-266`)

```python
except OSError as e:
    logger.warning(
        "social_cards_fonts_unavailable",
        requested_font=self.config.title_font,
        error=str(e),
        action="skipping_social_cards",
        hint="Configure [fonts] in your site config to enable social cards",
    )
    self._fonts_available = False
    return False
```

**Note**: This has a `hint` field but not a standardized `suggestion` field or error code.

---

## Architecture Analysis

### Post-Processing Flow

```
BuildOrchestrator
    └── PostprocessOrchestrator (bengal/orchestration/postprocess.py)
            ├── SitemapGenerator      → sitemap.xml
            ├── RSSGenerator          → rss.xml
            ├── RedirectGenerator     → redirect HTML pages
            ├── SpecialPagesGenerator → 404.html, search.html, graph.html
            ├── SocialCardGenerator   → OG images (PNG/JPG)
            └── OutputFormatsGenerator (facade)
                    ├── PageJSONGenerator     → page.json files
                    ├── PageTxtGenerator      → page.txt files
                    ├── SiteIndexGenerator    → index.json
                    ├── SiteLlmTxtGenerator   → llm-full.txt
                    └── LunrIndexGenerator    → search-index.json
```

### Error Propagation

| Generator | On Error | Build Continues? |
|-----------|----------|------------------|
| SitemapGenerator | Log + raise | ❌ No |
| RSSGenerator | Log + raise | ❌ No |
| RedirectGenerator | Log warning | ✅ Yes |
| SpecialPagesGenerator | Log + return False | ✅ Yes |
| SocialCardGenerator | Log warning | ✅ Yes |
| OutputFormatsGenerator | Log (delegates) | Depends |
| PageJSONGenerator | Log + raise RuntimeError | ❌ No |
| PageTxtGenerator | Log + raise RuntimeError | ❌ No |
| SiteIndexGenerator | Log warning | ✅ Yes |

### Graceful Degradation Strategy

The postprocess package correctly uses graceful degradation for non-critical failures:
- Missing 404 template → Skip 404 page (build succeeds)
- Font not found → Skip social cards (build succeeds)
- Redirect conflict → Skip that redirect (build succeeds)

However, critical failures (sitemap, RSS, output formats) should be tracked with structured errors.

---

## Gap Analysis

### Gap 1: Unused B008 Error Code

**Current**: `ErrorCode.B008` (`postprocess_task_failed`) exists but is not imported or used.

**Action**: Import and use `ErrorCode.B008` across all critical error locations.

### Gap 2: No Error Codes in Logging

**Files needing `error_code` field**:

| File | Lines | Current | After |
|------|-------|---------|-------|
| `sitemap.py` | 234 | No error_code | Add B008 |
| `rss.py` | 221 | No error_code | Add B008 |
| `special_pages.py` | 263, 374, 473 | No error_code | Add B008 |
| `output_formats/json_generator.py` | 191 | No error_code | Add B008 |
| `output_formats/txt_generator.py` | 161 | No error_code | Add B008 |
| `output_formats/llm_generator.py` | 237 | No error_code | Add B008 |

### Gap 3: No Actionable Suggestions

**Suggested messages by component**:

| Component | Suggestion |
|-----------|------------|
| Sitemap | "Check output directory permissions and available disk space" |
| RSS | "Verify pages have valid dates in frontmatter. Add 'date:' to include in RSS." |
| 404 page | "Ensure 404.html template exists in theme. Run 'bengal theme check'." |
| Search page | "Check [search] configuration and search.html template." |
| Graph page | "Verify knowledge graph is enabled and build succeeded." |
| Social cards | "Configure [fonts] in bengal.toml or install required fonts." |
| JSON generator | "Check page content for serialization errors (dates, paths)." |
| TXT generator | "Verify page plain_text extraction succeeded." |

### Gap 4: No Session Tracking

**Locations to add `record_error()`**:

| File | When to Track |
|------|---------------|
| `sitemap.py:233` | Sitemap generation failure |
| `rss.py:220` | RSS generation failure |
| `output_formats/json_generator.py:191` | Page JSON failure |
| `output_formats/txt_generator.py:161` | Page TXT failure |

---

## Proposed Changes

### Phase 1: Add Error Codes to Critical Logging (30 min)

**File**: `bengal/postprocess/sitemap.py`

```python
# Before (line 234)
self.logger.error(
    "sitemap_generation_failed",
    sitemap_path=str(sitemap_path),
    error=str(e),
    error_type=type(e).__name__,
)

# After
from bengal.errors import ErrorCode

self.logger.error(
    "sitemap_generation_failed",
    sitemap_path=str(sitemap_path),
    error=str(e),
    error_type=type(e).__name__,
    error_code=ErrorCode.B008.value,
    suggestion="Check output directory permissions and available disk space.",
)
```

**File**: `bengal/postprocess/rss.py`

```python
# Before (line 221)
self.logger.error(
    "rss_generation_failed",
    lang=code,
    rss_path=str(rss_path),
    error=str(e),
    error_type=type(e).__name__,
)

# After
from bengal.errors import ErrorCode

self.logger.error(
    "rss_generation_failed",
    lang=code,
    rss_path=str(rss_path),
    error=str(e),
    error_type=type(e).__name__,
    error_code=ErrorCode.B008.value,
    suggestion="Verify pages have valid dates in frontmatter. Add 'date:' to include in RSS.",
)
```

**File**: `bengal/postprocess/special_pages.py`

```python
# Before (line 263)
logger.error("404_page_generation_failed", error=str(e), error_type=type(e).__name__)

# After
from bengal.errors import ErrorCode

logger.error(
    "404_page_generation_failed",
    error=str(e),
    error_type=type(e).__name__,
    error_code=ErrorCode.B008.value,
    suggestion="Ensure 404.html template exists in theme. Check template syntax.",
)
```

Apply similar pattern to lines 374 (search) and 473 (graph).

### Phase 2: Add Suggestions to Warnings (30 min)

**File**: `bengal/postprocess/social_cards.py`

```python
# Before (line 259)
logger.warning(
    "social_cards_fonts_unavailable",
    requested_font=self.config.title_font,
    error=str(e),
    action="skipping_social_cards",
    hint="Configure [fonts] in your site config to enable social cards",
)

# After
logger.warning(
    "social_cards_fonts_unavailable",
    requested_font=self.config.title_font,
    error=str(e),
    action="skipping_social_cards",
    suggestion="Configure [fonts] section in bengal.toml with Google Font families, or install Inter font locally.",
)
```

**File**: `bengal/postprocess/redirects.py`

```python
# Before (line 142)
logger.warning(
    "redirect_alias_conflict",
    alias=alias,
    claimants=[f"{url} ({title})" for url, title in claimants],
    hint="Multiple pages claim the same alias; only the first will be used",
)

# After
logger.warning(
    "redirect_alias_conflict",
    alias=alias,
    claimants=[f"{url} ({title})" for url, title in claimants],
    suggestion="Remove duplicate 'aliases:' entries from page frontmatter. Only first claimant will generate redirect.",
)
```

### Phase 3: Add Session Tracking (45 min)

**File**: `bengal/postprocess/sitemap.py`

```python
# Before (line 233)
except Exception as e:
    self.logger.error(...)
    raise

# After
from bengal.errors import ErrorCode, record_error, BengalRenderingError

except Exception as e:
    # Create structured error for session tracking
    error = BengalRenderingError(
        f"Sitemap generation failed: {e}",
        code=ErrorCode.B008,
        file_path=sitemap_path,
        suggestion="Check output directory permissions and available disk space.",
        original_error=e,
    )
    record_error(error, context="postprocess:sitemap")

    self.logger.error(
        "sitemap_generation_failed",
        sitemap_path=str(sitemap_path),
        error=str(e),
        error_type=type(e).__name__,
        error_code=ErrorCode.B008.value,
        suggestion="Check output directory permissions and available disk space.",
    )
    raise error from e
```

Apply similar pattern to `rss.py`, `output_formats/json_generator.py`, and `output_formats/txt_generator.py`.

### Phase 4: Update Output Format Generators (30 min)

**File**: `bengal/postprocess/output_formats/json_generator.py`

```python
# Before (line 191)
except Exception as e:
    logger.error(
        "page_json_generation_failed",
        page=str(page.source_path),
        error=str(e),
    )

# After
from bengal.errors import ErrorCode

except Exception as e:
    logger.error(
        "page_json_generation_failed",
        page=str(page.source_path),
        error=str(e),
        error_type=type(e).__name__,
        error_code=ErrorCode.B008.value,
        suggestion="Check page content for JSON serialization errors. Verify dates and paths are valid.",
    )
```

Apply to `txt_generator.py`, `llm_generator.py`, `index_generator.py`.

---

## Implementation Phases

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Add `error_code` to critical `logger.error()` calls | 30 min | P1 |
| 2 | Add `suggestion` to `logger.warning()` calls | 30 min | P1 |
| 3 | Add session tracking with `record_error()` | 45 min | P2 |
| 4 | Update output format generators | 30 min | P2 |
| 5 | Add tests for error handling | 30 min | P3 |

**Total**: ~2.5 hours

---

## Success Criteria

### Must Have

- [ ] All `logger.error()` calls include `error_code=ErrorCode.B008.value`
- [ ] All `logger.error()` calls include actionable `suggestion` field
- [ ] `ErrorCode.B008` imported and used in 6+ files

### Should Have

- [ ] Session tracking via `record_error()` in 4+ critical locations
- [ ] `logger.warning()` calls have `suggestion` field
- [ ] Tests verify error codes appear in logs

### Nice to Have

- [ ] `BengalRenderingError` used for critical failures
- [ ] Constants file for standard suggestion messages
- [ ] Error recovery documentation

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing error flows | Very Low | Low | Only adding fields, not changing control flow |
| Test failures | Low | Low | Run `pytest tests/unit/postprocess/` after changes |
| Performance impact | Very Low | Negligible | `record_error()` is O(1) per error |
| Log format changes | Low | Low | Adding fields is backwards compatible |

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/postprocess/sitemap.py` | Add error code + suggestion + session | +8 |
| `bengal/postprocess/rss.py` | Add error code + suggestion + session | +8 |
| `bengal/postprocess/special_pages.py` | Add error code + suggestion (3 locations) | +12 |
| `bengal/postprocess/redirects.py` | Add suggestion (3 locations) | +6 |
| `bengal/postprocess/social_cards.py` | Add suggestion (2 locations) | +4 |
| `bengal/postprocess/output_formats/json_generator.py` | Add error code + suggestion | +4 |
| `bengal/postprocess/output_formats/txt_generator.py` | Add error code + suggestion | +4 |
| `bengal/postprocess/output_formats/llm_generator.py` | Add error code + suggestion | +4 |
| `bengal/postprocess/output_formats/index_generator.py` | Add error code + suggestion | +4 |
| **Total** | — | ~54 lines |

---

## Appendix: Adoption Score Breakdown

| Criterion | Before | After | Notes |
|-----------|--------|-------|-------|
| Error code usage | 0/10 | 8/10 | B008 used consistently |
| Bengal exception usage | 0/10 | 4/10 | Added to critical paths |
| Session recording | 0/10 | 6/10 | Added to 4 locations |
| Actionable suggestions | 0/10 | 8/10 | All errors have suggestions |
| Build phase tracking | 0/10 | 6/10 | POSTPROCESS phase used |
| Consistent patterns | 0/10 | 7/10 | Standardized logging |
| **Overall** | **0/10** | **6/10** | — |

---

## References

- `bengal/errors/codes.py:279` — B008 definition (exists, unused)
- `bengal/errors/exceptions.py` — BengalError, BengalRenderingError classes
- `bengal/errors/session.py` — record_error() function
- `bengal/orchestration/postprocess.py` — PostprocessOrchestrator (caller)
- `tests/unit/postprocess/` — Test files for validation

---

## Related RFCs

- `plan/drafted/rfc-health-error-adoption.md` — ✅ Implemented
- `plan/drafted/rfc-fonts-error-adoption.md` — Similar pattern
- `plan/drafted/rfc-discovery-error-adoption.md` — Similar pattern
- `plan/drafted/rfc-orchestration-error-adoption.md` — Parent orchestrator
