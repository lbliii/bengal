# Cache & Provenance Strategy Evaluation

**Status**: Code-verified analysis  
**Date**: 2026-03-14  
**Verified**: 2026-03-14 (line references audited against source)  
**Context**: Post-reload-fragility improvements; evaluate caching and provenance for similar brittleness, weaknesses, and inefficiencies.

---

## Executive Summary

Bengal has a **dual-cache architecture** (BuildCache + ProvenanceCache) plus EffectTracer. The system is generally robust — rendered/parsed cache validation is more thorough than initially expected (asset manifest, empty-content fallback all work correctly). However, several areas of brittleness, inefficiency, and silent failure modes remain analogous to the reload pipeline issues. Priority fixes: template-change over-invalidation, provenance load silence, duplicate O(n) output dir scans, and output_sources key consistency.

---

## 1. Architecture Overview

| System | Location | Purpose |
|--------|----------|---------|
| **BuildCache** | `.bengal/cache.json[.zst]` | Fingerprints, dependencies, taxonomy, parsed/rendered output, output_sources |
| **ProvenanceCache** | `.bengal/provenance/` | Content-addressed page hashes, subvenance index |
| **EffectTracer** | `.bengal/effects.json` | Effect-based dependency tracking |

**Flow**: `phase_incremental_filter_provenance` uses ProvenanceFilter (ProvenanceCache) for page filtering, but calls `_expand_forced_changed` which uses BuildCache (dependencies, taxonomy_deps) for data/template/taxonomy triggers.

---

## 2. Brittleness & Weaknesses

### 2.1 Template Change → Full Rebuild (Inefficiency)

**Location**: `provenance_filter.py:310-323`

```python
# Gap 3: Detect template changes
# Per-page template dependencies are not yet recorded in BuildCache,
# so _get_pages_for_template() would always return empty.  Instead,
# fall back to rebuilding ALL pages when any template changes -- any
# page could reference any template via extends/includes.
changed_templates = _detect_changed_templates(cache, site)
if changed_templates:
    template_names = ", ".join(t.name for t in changed_templates)
    for page in pages:  # <-- iterates ALL pages
```

**Impact**: Any template change triggers a full rebuild. For large sites (100+ pages), a one-line footer fix rebuilds everything.

**Key finding**: The infrastructure to fix this already exists. `_get_pages_for_template()` (lines 200-230) checks `cache.reverse_dependencies` and `cache.dependencies` — the lookup code is written and working. The missing piece is that `add_dependency(page.source_path, template_path)` is never called during the render phase for templates. The fallback at line 316 could then be replaced with per-page template lookups.

**Recommendation**: Wire up `cache.add_dependency(page, template)` during rendering (likely in `cache_checker.py:cache_rendered_output` or during template resolution). Then replace the all-pages fallback with `_get_pages_for_template()`. Effort: **Low-Medium** (infrastructure exists, wiring + tests needed).

---

### 2.2 ProvenanceCache Load Failure — Silent Fallback

**Location**: `provenance/store.py:94-109` (`_load_index_data`), `111-118` (`_load_subvenance_data`), `120-134` (`_get_record`)

All three methods swallow `FileNotFoundError`, `JSONDecodeError`, `KeyError` with **zero logging**:

```python
# store.py:108-109
except FileNotFoundError, JSONDecodeError, KeyError:
    return ({}, {}, None)

# store.py:117-118
except FileNotFoundError, JSONDecodeError, KeyError:
    return {}

# store.py:133-134  (also silent)
except FileNotFoundError, JSONDecodeError, KeyError:
    return None
```

**Impact**: Corrupt or missing provenance index silently becomes "empty cache" → full rebuild. No visibility into why incremental filtering failed. `_get_record` silently returning `None` on corrupt individual records is especially insidious — provenance lookups silently degrade.

**Contrast**: `BuildCache.load` (core.py:234-245) logs `cache_load_failed` at warning level with path, error type, error code, and action. ProvenanceCache has none of this.

**Recommendation**: Add `logger.warning` to all three methods when the exception is NOT `FileNotFoundError` (missing file is expected on first build). Pattern:

```python
except FileNotFoundError:
    return ({}, {}, None)
except (JSONDecodeError, KeyError) as e:
    logger.warning("provenance_index_load_failed", path=str(index_path), error=str(e))
    return ({}, {}, None)
```

Effort: 1 hour.

---

### 2.3 Dual Cache Systems — No Single Source of Truth

**Observation**: BuildCache and ProvenanceCache can diverge:

- BuildCache tracks dependencies, output_sources, taxonomy.
- ProvenanceCache tracks content-addressed page hashes.
- ProvenanceFilter uses both; CacheManager saves BuildCache; `save_provenance_cache` saves ProvenanceCache.

**Risk**: If one is stale (e.g., ProvenanceCache cleared but BuildCache warm), behavior is undefined. Recovery path (provenance_filter.py:467-570) tries to reconcile with ~100 lines of sample-based provenance validation, conditional cache clearing, and re-discovery — this complexity is itself a code smell.

**Recommendation**: Document the relationship explicitly. Consider a "cache generation" or "build id" that ties both caches to the same build. ProvenanceCache already stores `last_build_time` in its index (store.py:333); BuildCache stores `last_build` (core.py:592). A shared build UUID written to both would make divergence detectable. Lower priority than 2.1–2.2.

---

### 2.4 output_sources Key Consistency

**Location**: `provenance_filter.py:765-798`, `file_tracking.py:256-273`

Missing output detection (provenance_filter.py:765-771):
```python
skipped_by_source = {
    content_key(page.source_path, site.root_path): page
    for page in result.pages_skipped
}
for rel_output, source_str in (cache.output_sources or {}).items():
    page = skipped_by_source.get(source_str)
```

Storage side (file_tracking.py:268-270):
```python
rel_output = str(output_path.relative_to(output_dir))
self.output_sources[rel_output] = self._cache_key(source_path)
```

**Source key match**: Both sides use `content_key` — the `source_str` values will match correctly.

**Output key risk**: `rel_output` is `str(output_path.relative_to(output_dir))`, which uses OS-native path separators. On Windows this produces `blog\post\index.html` instead of `blog/post/index.html`. Since `rel_output` is only used as a dict key (not compared with `content_key`), this is self-consistent on a single OS. But cache portability across OS would break.

**Recommendation**: Normalize `rel_output` through `to_posix()` in `track_output`. Add a cross-platform test. Document the key contract in `track_output` docstring. Effort: Low.

---

### 2.5 Cache Version Migration — All-or-Nothing

**Location**: `build_cache/core.py:270-279`

```python
found_version = data.get("version", 0)
if found_version < 8:
    # V8: cache path key alignment - old keys are unreliable, clean migration
    logger.info(
        "cache_version_migration",
        from_version=found_version,
        to_version=8,
        action="clearing_cache_for_key_normalization",
    )
    return cls()
```

**Impact**: Version bump wipes everything. Correct for V8 (key normalization makes old keys unreliable). Painful for large sites with warm caches.

**Recommendation**: Acceptable for V8. Document in CHANGELOG when cache version bumps occur. Consider a `--migrate-cache` flag for future partial migrations if needed. No action required.

---

### 2.6 Cold Build Detection — Duplicate O(n) on Output Dir

**Location**: `provenance_filter.py:415` AND `provenance_filter.py:727`

The same O(n) pattern appears **twice** in the same function:

```python
# Line 415 (early cold build check)
output_html_missing = not output_dir.exists() or len(list(output_dir.iterdir())) == 0

# Line 727 (post-filter output missing check)
output_html_missing = not output_dir.exists() or len(list(output_dir.iterdir())) == 0
```

`list(output_dir.iterdir())` materializes every entry in the output directory. For large sites (1000+ files), this adds latency **twice** per incremental filter call.

**Recommendation**: Replace both occurrences with `next(output_dir.iterdir(), None) is None` for an O(1) emptiness check, or check for a sentinel file (e.g., `output_dir / "index.html"`). Better yet, extract a helper:

```python
def _output_dir_empty(output_dir: Path) -> bool:
    if not output_dir.exists():
        return True
    return next(output_dir.iterdir(), None) is None
```

Effort: 30 min.

---

### 2.7 Data File Fingerprint Update — Full Scan Every Save

**Location**: `cache_manager.py:357-391`

```python
def _update_data_file_fingerprints(self) -> None:
    # ...
    for data_file in data_dir.rglob("*"):
        if not data_file.is_file():
            continue
        if data_file.suffix not in data_extensions:
            continue
        self.cache.update_file(data_file)  # stat() + hash_file() per file
```

Full `rglob("*")` scan on every save. Each `update_file` call does `stat()` + `hash_file()` (SHA256 read), so the cost is 2 I/O ops per data file per build. For a data directory with 50+ files, this is measurable.

**Recommendation**: Incremental update — only fingerprint files that were read during the build (track via `_detect_changed_data_files` which already scans). Or skip fingerprint update for files whose mtime hasn't changed since last save. Effort: 1 day.

---

### 2.8 Taxonomy Index Key Normalization

**Location**: `provenance_filter.py:253-268`, `taxonomy_index_mixin.py:66-77`

Lookup chain:
```python
# provenance_filter.py:253
member_key = cache.cache_key(member_path)       # → content_key format

# provenance_filter.py:256 → core.py:158 → taxonomy_index_mixin.py:76
tags = cache.get_page_tags(member_key)
#   → self.page_tags.get(page_key, set())       # must match content_key format
```

The lookup works IF `page_tags` was populated with the same `content_key` format. This is consistent for real pages. **But**: taxonomy term pages use synthetic paths that bypass `content_key`:

```python
# provenance_filter.py:263-264
tag_key = f"tag:{str(tag).lower().replace(' ', '-')}"
term_page_key = f"_generated/tags/{tag_key}"      # not a content_key
```

These synthetic keys are also used in `taxonomy_index_mixin.py:update_page_tags` for virtual pages. The formats are self-consistent (both caller and callee use the raw string), but there's no contract enforcing this. A refactor that normalizes one side through `content_key` would silently break the other.

**Recommendation**: Add a `synthetic_key()` helper (or document the convention) for virtual/generated page keys, separate from `content_key`. Add a regression test. Effort: Low.

---

### 2.9 Rendered/Parsed Cache Validation — VERIFIED CORRECT

**Location**: `cache_checker.py:85-253`, `rendered_output_cache.py:134-213`

**Code audit result** — all three original concerns are handled correctly:

1. **Asset manifest invalidation**: `get_rendered_output` (rendered_output_cache.py:196-211) compares `asset_manifest_mtime` and returns `MISSING` when the manifest changes. Fingerprinted CSS/JS URLs in cached HTML are correctly invalidated.

2. **Empty parsed content fallback**: `try_parsed_cache` (cache_checker.py:197-203) checks `if not parsed_content:`, logs `parsed_cache_empty` warning, and returns `False` — pipeline correctly falls back to full parse+render.

3. **Empty rendered HTML fallback**: `try_parsed_cache` (cache_checker.py:231-238) checks `if not page.rendered_html:`, logs `rendered_html_empty_after_cache` warning, and returns `False` — pipeline correctly falls back.

**Status**: No action needed. The rendered/parsed cache validation is more robust than initially assessed. The five-point validation in `get_rendered_output` (content, metadata hash, template name, dependency mtime, asset manifest mtime) is thorough.

---

### 2.10 No Observability for "Cache Unusable"

**Location**: `build_cache/core.py:234-245`

```python
except Exception as e:
    logger.warning(
        "cache_load_failed",
        cache_path=str(cache_path),
        error=str(e),
        error_type=type(e).__name__,
        action="using_fresh_cache",
        error_code=ErrorCode.A003.value,
    )
    return cls()  # fresh instance — no flag indicating recovery
```

Downstream code receives a `BuildCache()` that looks identical to a first-ever build. No way to distinguish "never built" from "cache was corrupt and discarded" without grepping logs.

**Recommendation**: Add a field to the returned instance:

```python
@dataclass
class BuildCache:
    # ...
    _recovered_from_error: bool = field(default=False, repr=False)
```

Set it in the `except` block. Downstream can then log/metric on `cache._recovered_from_error` without parsing log output. Effort: 30 min.

---

## 3. Findings Summary

| # | Issue | Severity | Effort | Verified | Action |
|---|-------|----------|--------|----------|--------|
| 2.1 | Template change → full rebuild | High | Low-Med | Yes | Wire up existing `_get_pages_for_template()` |
| 2.2 | Provenance load silence (3 methods) | Medium | Low | Yes | Add `logger.warning` for non-FNFE exceptions |
| 2.3 | Dual cache divergence risk | Medium | Medium | Yes | Add shared build UUID |
| 2.4 | output_sources key: POSIX portability | Low | Low | Yes | Normalize `rel_output` via `to_posix()` |
| 2.5 | Cache version all-or-nothing | — | — | Yes | Acceptable, no action |
| 2.6 | Duplicate O(n) iterdir on output dir | Low | Low | Yes | Replace with `next(iterdir(), None)` |
| 2.7 | Data file full scan on save | Low | Medium | Yes | Incremental fingerprinting |
| 2.8 | Taxonomy synthetic key convention | Low | Low | Yes | Document/formalize `synthetic_key()` |
| 2.9 | Rendered/parsed cache validation | — | — | Yes | **No action** — already correct |
| 2.10 | No cache-unusable observability flag | Low | Low | Yes | Add `_recovered_from_error` field |

---

## 4. Recommendations (Priority Order)

### Quick wins (< 1 hour each)

1. **Log when ProvenanceCache load fails** (2.2) — Add `logger.warning` to `_load_index_data`, `_load_subvenance_data`, `_get_record` for `JSONDecodeError`/`KeyError`. 1 hour.
2. **Fix duplicate O(n) iterdir** (2.6) — Extract `_output_dir_empty()` helper using `next(iterdir(), None)`. 30 min.
3. **Normalize output_sources keys** (2.4) — Wrap `rel_output` in `to_posix()` in `track_output`. Add cross-platform test. 30 min.
4. **Add `_recovered_from_error` flag** (2.10) — Field on BuildCache set during load failure. 30 min.

### Medium effort (1-2 days)

5. **Template dependency tracking** (2.1) — Wire `cache.add_dependency(page, template)` during rendering. Replace all-pages fallback with `_get_pages_for_template()` lookups. Infrastructure exists; needs wiring + tests. 1-2 days.
6. **Document synthetic key convention** (2.8) — Formalize `synthetic_key()` for virtual pages. Add regression test for taxonomy term key round-trip. 1 day.

### Deferred

7. **Data file incremental fingerprinting** (2.7) — Track which data files were read during build; only update those. 1 day.
8. **Shared build generation ID** (2.3) — UUID written to both BuildCache and ProvenanceCache to detect divergence. Requires design on what to do when mismatch detected. RFC recommended.

---

## 5. Verification Notes

Section 2.9 was originally flagged as a concern but code audit confirmed all three validation paths work correctly:
- Asset manifest mtime is checked in `get_rendered_output` (rendered_output_cache.py:196-211)
- Empty parsed content returns `False` in `try_parsed_cache` (cache_checker.py:197-203)
- Empty rendered HTML returns `False` in `try_parsed_cache` (cache_checker.py:231-238)

This demonstrates that the rendered output cache is one of the more robust subsystems in the cache architecture. Pattern worth replicating for ProvenanceCache (2.2).

---

## 6. Related Documents

- `plan/reload-fragility-improvements.md` — Reload pipeline fixes (analogous patterns)
- `plan/rfc-cache-invalidation-architecture.md` — CacheCoordinator design
- `plan/rfc-output-cache-architecture.md` — Output cache design
- `bengal/build/contracts/keys.py` — Canonical key functions (path-keys rule)

## 7. Key Source Files

| File | Role |
|------|------|
| `bengal/orchestration/build/provenance_filter.py` | Incremental filtering, dependency expansion, cold build detection |
| `bengal/build/provenance/store.py` | ProvenanceCache: content-addressed page hash storage |
| `bengal/cache/build_cache/core.py` | BuildCache: fingerprints, dependencies, version migration |
| `bengal/cache/build_cache/file_tracking.py` | File fingerprinting, dependency graphs, output tracking |
| `bengal/cache/build_cache/rendered_output_cache.py` | Rendered HTML caching with 5-point validation |
| `bengal/rendering/pipeline/cache_checker.py` | Cache hit/miss dispatch for render pipeline |
| `bengal/cache/build_cache/taxonomy_index_mixin.py` | Bidirectional tag/page indexes |
| `bengal/orchestration/incremental/cache_manager.py` | Cache persistence, data file fingerprint updates |
