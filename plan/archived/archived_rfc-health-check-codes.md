# RFC: Health Check Error Codes

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-24  
**Priority**: P2 (Medium)  
**Related**: `rfc-health-report-clarity.md`, `bengal/health/report.py`

---

## Problem Statement

Health check results currently lack error codes, making them:
1. **Hard to search**: Users can't search docs for "H001" like they can for build errors "T003"
2. **Difficult to ignore**: No way to suppress specific warnings in CI (`--ignore H001,H005`)
3. **Inconsistent**: Build errors have codes (A001, C001, T001...) but health checks don't
4. **Underdocumented**: No structured reference linking each check to detailed fix instructions

### Current State

**Build errors** have formal codes documented in `/docs/reference/errors/_index.md`:

```
| Prefix | Category | Description |
|--------|----------|-------------|
| A | Cache | Build cache operations errors |
| C | Config | Configuration loading and validation errors |
| T | Template Function | Shortcode, directive, and icon errors |
...
```

**Health check results** have no codes:

```python
# bengal/health/report.py:66-95
@dataclass
class CheckResult:
    status: CheckStatus
    message: str
    recommendation: str | None = None
    details: list[str] | None = None
    validator: str = ""
    metadata: dict[str, Any] | None = None
    # No code field!
```

### Evidence: 97 Check Results Across 18 Validators

```
bengal/health/validators/url_collisions.py:2
bengal/health/validators/links.py:2
bengal/health/validators/ownership_policy.py:1
bengal/health/validators/navigation.py:6
bengal/health/validators/sitemap.py:9
bengal/health/validators/rss.py:10
bengal/health/validators/tracks.py:6
bengal/health/validators/performance.py:3
bengal/health/validators/directives/checkers.py:7
bengal/health/validators/taxonomy.py:6
bengal/health/validators/output.py:5
bengal/health/validators/menu.py:2
bengal/health/validators/fonts.py:9
bengal/health/validators/assets.py:6
bengal/health/validators/cache.py:6
bengal/health/validators/rendering.py:5
bengal/health/validators/config.py:2
bengal/health/validators/connectivity.py:10
+ anchors.py, cross_ref.py, accessibility.py, autodoc.py, templates.py
```

---

## Goals

1. **Searchable codes**: Every health check has a unique code (e.g., `H101`)
2. **CI integration**: `bengal health --ignore H101,H205` to suppress specific warnings
3. **Consistent schema**: Follows build error code conventions
4. **Documented reference**: Each code links to detailed fix instructions
5. **Backward compatible**: Existing code continues to work

## Non-Goals

- Changing how validators produce results
- Changing console output format significantly
- Removing existing properties

---

## Design

### Code Schema

Use "H" prefix + 3 digits with category ranges:

| Range | Category | Validators |
|-------|----------|------------|
| H0xx | Core/Basic | Output, Config, URL Collisions, Ownership |
| H1xx | Links & Navigation | Links, Navigation, Menu, Breadcrumbs |
| H2xx | Directives | DirectiveValidator |
| H3xx | Taxonomy | Tags, Categories, Pagination |
| H4xx | Cache & Performance | Cache, Performance |
| H5xx | Feeds | RSS, Sitemap |
| H6xx | Assets | Fonts, Assets, Images |
| H7xx | Graph & References | Connectivity, Cross-refs, Anchors |
| H8xx | Tracks | Learning tracks |
| H9xx | Accessibility | WCAG checks |

### Data Model Changes

```python
# bengal/health/report.py

@dataclass
class CheckResult:
    status: CheckStatus
    message: str
    code: str | None = None  # NEW: e.g., "H101"
    recommendation: str | None = None
    details: list[str] | None = None
    validator: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def error(
        cls,
        message: str,
        code: str | None = None,  # NEW
        recommendation: str | None = None,
        details: list[str] | None = None,
        validator: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create an error result."""
        return cls(
            CheckStatus.ERROR,
            message,
            code=code,
            recommendation=recommendation,
            details=details,
            validator=validator,
            metadata=metadata,
        )

    # Similar updates for warning(), suggestion(), info()
```

### Console Output Changes

```diff
  Issues:

-   ❌ Links (1 error(s))
-     • 6 broken internal link(s)
+   ❌ Links (1 error(s))
+     • [H101] 6 broken internal link(s)
        content/docs/building/troubleshooting/_index.md: template-errors.md

-   ⚠️ Directives (1 warning(s))
-     • 3 page(s) have heavy directive usage (>10 directives)
+   ⚠️ Directives (1 warning(s))
+     • [H201] 3 page(s) have heavy directive usage (>10 directives)
```

### JSON Output Changes

```json
{
  "validators": [
    {
      "name": "Links",
      "results": [
        {
          "status": "error",
          "code": "H101",
          "message": "6 broken internal link(s)",
          "recommendation": "Fix broken internal links...",
          "details": ["content/docs/..."]
        }
      ]
    }
  ]
}
```

### CLI Integration

```bash
# Ignore specific codes
bengal health check --ignore H101,H201

# Filter by code range
bengal health check --codes H1xx  # Only link/navigation checks

# Show code documentation
bengal health explain H101
```

---

## Complete Code Catalog

### H0xx: Core/Basic Validation

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H001 | error | Output | Output directory does not exist |
| H002 | error | Output | No assets directory found in output |
| H003 | warning | Output | No CSS files found in output |
| H004 | warning | Output | No JS files found in output |
| H005 | warning | Output | Page(s) are suspiciously small |
| H010 | error | Config | Configuration validation failed |
| H011 | warning | Config | Deprecated configuration option |
| H020 | error | URLCollision | URL collision(s) detected |
| H021 | warning | URLCollision | Page(s) have same URL as section |
| H030 | warning | Ownership | Ownership violation(s) detected |

### H1xx: Links & Navigation

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H101 | error | Links | Broken internal link(s) |
| H102 | warning | Links | Broken external link(s) |
| H110 | error | Navigation | Broken next/prev links |
| H111 | error | Navigation | Breadcrumb issue(s) |
| H112 | warning | Navigation | Invalid breadcrumb trails |
| H113 | warning | Navigation | Section navigation issue(s) |
| H114 | error | Navigation | Weight-based navigation issue(s) |
| H115 | error | Navigation | Page(s) missing output_path |
| H120 | warning | Menu | Menu is empty |
| H121 | warning | Menu | Menu has broken links |

### H2xx: Directives

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H201 | error | Directives | Directive(s) have syntax errors |
| H202 | warning | Directives | Fence nesting issues |
| H203 | error | Directives | Directive(s) incomplete |
| H204 | warning | Directives | Directive(s) could be improved |
| H205 | warning | Directives | Heavy directive usage |
| H206 | warning | Directives | Tabs block has many tabs |
| H207 | error | Directives | Directive rendering errors |

### H3xx: Taxonomy

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H301 | error | Taxonomy | Tag(s) have no generated pages |
| H302 | error | Taxonomy | Orphaned tag page(s) found |
| H303 | warning | Taxonomy | No tag index page found |
| H304 | warning | Taxonomy | Section(s) have content but no index |
| H305 | error | Taxonomy | Taxonomy consistency issue(s) |
| H306 | error | Taxonomy | Pagination issue(s) |

### H4xx: Cache & Performance

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H401 | warning | Cache | Cache at legacy location |
| H402 | error | Cache | Cache file cannot be read |
| H403 | error | Cache | Cache structure invalid |
| H404 | warning | Cache | Cache entry mismatch |
| H410 | warning | Performance | Build is slower than expected |
| H411 | warning | Performance | Low throughput |
| H412 | warning | Performance | High average page render time |

### H5xx: Feeds (RSS, Sitemap)

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H501 | warning | Sitemap | Sitemap not generated |
| H502 | error | Sitemap | Sitemap XML is malformed |
| H503 | error | Sitemap | Root element is not 'urlset' |
| H504 | warning | Sitemap | Sitemap xmlns incorrect |
| H505 | warning | Sitemap | Sitemap has no URL elements |
| H506 | error | Sitemap | URL(s) missing loc element |
| H507 | error | Sitemap | URL(s) are relative |
| H508 | error | Sitemap | Duplicate URL(s) in sitemap |
| H509 | warning | Sitemap | Sitemap URL count mismatch |
| H520 | warning | RSS | RSS feed not generated |
| H521 | error | RSS | RSS XML is malformed |
| H522 | error | RSS | Root element is not 'rss' |
| H523 | warning | RSS | RSS version incorrect |
| H524 | error | RSS | No channel element found |
| H525 | error | RSS | Missing required channel elements |
| H526 | warning | RSS | RSS feed has no items |
| H527 | error | RSS | RSS item(s) missing required elements |
| H528 | warning | RSS | Channel link is relative |
| H529 | error | RSS | Item(s) have relative URLs |

### H6xx: Assets

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H601 | warning | Fonts | fonts.css not generated |
| H602 | error | Fonts | Fonts directory does not exist |
| H603 | error | Fonts | No font files found |
| H604 | warning | Fonts | Font file count mismatch |
| H605 | error | Fonts | Cannot read fonts.css |
| H606 | error | Fonts | No @font-face rules |
| H607 | error | Fonts | Font reference(s) point to missing files |
| H608 | warning | Fonts | Font file(s) are very large |
| H609 | warning | Fonts | Total font size is very large |
| H620 | warning | Assets | No assets directory found |
| H621 | warning | Assets | No CSS files found |
| H622 | warning | Assets | CSS file(s) are very large |
| H623 | warning | Assets | JavaScript file(s) are very large |
| H624 | warning | Assets | Image(s) are very large |
| H625 | warning | Assets | Total asset size is very large |

### H7xx: Graph & References

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H701 | warning | Connectivity | Orphan page(s) found |
| H702 | warning | Connectivity | Isolated cluster(s) detected |
| H703 | error | Connectivity | Broken internal references |
| H704 | warning | Connectivity | Low connectivity score |
| H710 | warning | Anchors | Duplicate anchor ID(s) |
| H711 | warning | Anchors | Broken anchor reference(s) |
| H720 | warning | CrossRef | Invalid code reference(s) |
| H721 | warning | CrossRef | Deprecated version reference(s) |
| H722 | warning | CrossRef | Broken heading anchor(s) |

### H8xx: Tracks

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H801 | error | Tracks | Invalid track structure |
| H802 | error | Tracks | Track missing 'items' field |
| H803 | error | Tracks | Track 'items' must be a list |
| H804 | warning | Tracks | Invalid track item type |
| H805 | warning | Tracks | Track has missing page(s) |
| H806 | warning | Tracks | Page has invalid track_id |

### H9xx: Accessibility

| Code | Severity | Validator | Message |
|------|----------|-----------|---------|
| H901 | warning | Accessibility | Heading level skipped |
| H902 | warning | Accessibility | Multiple h1 tags |
| H903 | warning | Accessibility | Image missing alt attribute |
| H904 | info | Accessibility | Image has empty alt text |
| H905 | warning | Accessibility | Non-descriptive link text |
| H906 | info | Accessibility | Missing ARIA landmark |

---

## Implementation Plan

### Phase 1: Data Model (Non-Breaking)

**Files**: `bengal/health/report.py`

1. Add `code: str | None = None` field to `CheckResult`
2. Update factory methods (`error()`, `warning()`, etc.) to accept `code` parameter
3. Update `to_cache_dict()` and `from_cache_dict()` to include code
4. Update JSON output in `HealthReport.format_json()`

### Phase 2: Console Output

**Files**: `bengal/health/report.py`

1. Update `_format_quiet()`, `_format_normal()`, `_format_verbose()` to display codes
2. Format: `[H101] Message text`

### Phase 3: Update Validators (Incremental)

**Files**: All validators in `bengal/health/validators/`

Update each validator to include codes. Can be done incrementally:
- Start with high-impact validators: Links, Directives, Navigation
- Add codes to remaining validators over time

Example update:

```python
# Before
CheckResult.error(
    f"{len(internal_broken)} broken internal link(s)",
    recommendation="Fix broken internal links...",
)

# After
CheckResult.error(
    f"{len(internal_broken)} broken internal link(s)",
    code="H101",
    recommendation="Fix broken internal links...",
)
```

### Phase 4: CLI Integration

**Files**: `bengal/cli/health.py`

1. Add `--ignore` option to suppress specific codes
2. Add `--codes` option to filter by code pattern
3. Add `bengal health explain H101` subcommand

### Phase 5: Documentation

**Files**: `site/content/docs/reference/`

1. Create `health-codes/_index.md` with complete code reference
2. Add cross-links from each code to detailed fix instructions
3. Update troubleshooting docs to reference codes

---

## Files Affected

| File | Changes |
|------|---------|
| `bengal/health/report.py` | Add `code` field, update factory methods, update formatters |
| `bengal/health/validators/*.py` | Add codes to all 97 check results |
| `bengal/cli/health.py` | Add `--ignore`, `--codes`, `explain` |
| `site/content/docs/reference/health-codes/` | New documentation |
| `tests/unit/test_health_report.py` | Tests for code field |

---

## Migration Notes

### For Console Users
- Codes appear in brackets before messages: `[H101] Broken internal link(s)`
- No action required, backward compatible

### For JSON Consumers
- New `code` field in results: `{"code": "H101", "message": "..."}`
- Can filter/group by code programmatically

### For CI Pipelines
- New `--ignore` flag: `bengal health check --ignore H101,H205`
- Useful for suppressing known/accepted warnings

---

## Open Questions

1. **Should codes be required or optional?**
   - Recommend: Optional initially, required in v1.0
   - Allows incremental adoption

2. **Should we generate codes automatically from validator+message hash?**
   - Recommend: No, manual assignment for stability
   - Auto-generated codes would change if messages change

3. **Should log messages also include codes?**
   - The `logger.warning("found_broken_links", ...)` messages
   - Recommend: Yes, include code in log event: `logger.warning("H101_broken_links", ...)`

4. **Documentation location?**
   - Option A: Extend `/docs/reference/errors/_index.md` with health codes
   - Option B: New `/docs/reference/health-codes/_index.md`
   - Recommend: Option B for separation of concerns

---

## Success Criteria

- [ ] `CheckResult.code` field exists and is optional
- [ ] Factory methods accept `code` parameter
- [ ] Console output shows codes in brackets
- [ ] JSON output includes `code` field
- [ ] At least Links, Navigation, Directives validators have codes
- [ ] `--ignore` CLI option works
- [ ] Documentation page lists all codes
- [ ] Tests cover code handling

---

## References

- `site/content/docs/reference/errors/_index.md` - Build error code reference
- `bengal/health/report.py` - Current CheckResult implementation
- `rfc-health-report-clarity.md` - Related data model improvements
- `bengal/health/validators/` - 18+ validators to update
