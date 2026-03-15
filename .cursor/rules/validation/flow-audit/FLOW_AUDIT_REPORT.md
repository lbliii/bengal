# FLOW Audit Report: Bengal

Audited: `bengal/**/*.py`
Date: 2026-03-14

---

## Findings

| # | Severity | File | Lines | Flow Issue | Suggested Fix |
|---|----------|------|-------|------------|---------------|
| 1 | **HIGH** | `orchestration/taxonomy.py` | 470-592 | Duplicate `locale_tags_by_lang` construction | Extract shared helper |
| 2 | **HIGH** | `postprocess/output_formats/index_generator.py` | 218-325, 391-484 | `_generate_single_index` and `_generate_version_index` are near-identical 80-line pipelines | Extract shared `_build_and_finalize_site_data` |
| 3 | **HIGH** | `orchestration/taxonomy.py` | 624-632 | Two post-hoc passes over `site.pages` for logging counts | Count during generation instead |
| 4 | **HIGH** | `core/section/queries.py` | 77-104, 123-154 | `regular_pages` is `tuple(self.sorted_pages)` — re-wraps an already-cached tuple | Alias directly or inline |
| 5 | **MEDIUM** | `rendering/template_functions/navigation/breadcrumbs.py` | 113-114 | `list(page.ancestors)` then `list(reversed(...))` — two materialization passes | Single `list(reversed(page.ancestors))` or slice `[::-1]` |
| 6 | **MEDIUM** | `snapshots/content.py` | 247-274 | `_resolve_navigation` builds `pages_by_path` AND `id_by_path` in two separate loops over `page_cache` | Merge into single loop |
| 7 | **MEDIUM** | `orchestration/taxonomy.py` | 166-173, 286-290 | `_page_path_key(p.source_path)` called in list comprehension at two separate points for the same pages | Compute once during collection |
| 8 | **MEDIUM** | `core/section/hierarchy.py` | 77-93, 96-111 | `depth` calls `len(self.hierarchy)` — recomputes full parent chain walk | Cache hierarchy or compute depth directly via parent count |
| 9 | **LOW** | `postprocess/output_formats/index_generator.py` | 571-574 | `page_to_summary` calls `content_text.split()` twice (once for `word_count`, once for `reading_time`) | Compute `word_count` once, derive `reading_time` from it |
| 10 | **LOW** | `core/section/queries.py` | 156-177 | `regular_pages_recursive` builds intermediate `list(self.regular_pages)` then extends with recursive results | Use itertools.chain or yield-based approach |
| 11 | **LOW** | `orchestration/render/ordering.py` | 285-287 | `_priority_sort` calls `_get_track_item_paths()` after `_maybe_sort_by_complexity` also calls it | Pass precomputed `track_item_paths` |

---

## Detailed Analysis

### Finding 1 (HIGH): Duplicate `locale_tags_by_lang` construction

`generate_dynamic_pages` (line 574-592) and `generate_dynamic_pages_for_tags_with_cache` (line 480-497) both build the identical `locale_tags_by_lang` dict with the same nested loop over tags × languages, calling `filter_pages_by_language` each time.

```157:177:bengal/orchestration/taxonomy.py
        # IPA audit Finding 11: build locale_tags_by_lang in one pass over tags
        languages = i18n_config.languages
        locale_tags_by_lang: dict[str, dict[str, Any]] = {lang: {} for lang in languages}
        for tag_slug, tag_data in self.site.taxonomies["tags"].items():
            for lang in languages:
                pages_for_lang = filter_pages_by_language(
```

**Fix:** Extract `_build_locale_tags(self) -> dict[str, dict[str, Any]]` as a private method; call from both paths.

---

### Finding 2 (HIGH): Near-identical index generation pipelines

`_generate_single_index` (218-324) and `_generate_version_index` (391-484) share ~60 lines of identical logic: mode detection, accumulated/hybrid/legacy iteration, section/tag aggregation, sorting, and JSON serialization. The only difference is the output path and version metadata.

**Fix:** Extract `_build_site_data(pages, accumulated_data) -> dict` that returns the finalized `site_data` dict. Both methods call it and only differ on path resolution and version metadata injection.

---

### Finding 3 (HIGH): Two post-hoc passes for logging counts

After generating dynamic pages, `generate_dynamic_pages` scans `site.pages` twice:

```625:632:bengal/orchestration/taxonomy.py
        tag_count = sum(
            1
            for p in self.site.pages
            if p.is_generated and p.output_path and "tag" in p.output_path.parts
        )
        pagination_count = sum(
            1 for p in self.site.pages if p.is_generated and "/page/" in str(p.output_path)
        )
```

These are O(n) scans over ALL pages just for logging. The `generated_count` is already tracked — tag vs pagination counts should be tracked during generation.

**Fix:** Increment `tag_count` / `pagination_count` inside `_generate_tag_pages_sequential` and `_generate_tag_pages_parallel` rather than scanning the full page list afterward.

---

### Finding 4 (HIGH): `regular_pages` wraps already-cached `sorted_pages`

```77:104:bengal/core/section/queries.py
    @cached_property
    def regular_pages(self) -> tuple[Page, ...]:
        # ...
        return tuple(self.sorted_pages)
```

`sorted_pages` already returns a `tuple`. Wrapping it in `tuple()` again creates a copy. Since both are `@cached_property`, `regular_pages` is literally `tuple(tuple(...))`.

**Fix:** `return self.sorted_pages` — same object, zero copy. Or if the two must diverge in the future, document why the copy is intentional.

---

### Finding 5 (MEDIUM): Double materialization of ancestors

```113:114:bengal/rendering/template_functions/navigation/breadcrumbs.py
    ancestors_list = list(page.ancestors)
    reversed_ancestors = list(reversed(ancestors_list))
```

Two `list()` calls to reverse a sequence.

**Fix:** `reversed_ancestors = list(page.ancestors)[::-1]` — single materialization with in-place reversal. Or if `page.ancestors` is already a list/tuple: `reversed_ancestors = page.ancestors[::-1]`.

---

### Finding 6 (MEDIUM): Two loops over `page_cache` in navigation resolution

```247:260:bengal/snapshots/content.py
    pages_by_path: dict[Path, PageSnapshot] = {
        page.source_path: page for page in page_cache.values()
    }

    id_by_path: dict[Path, int] = {}
    for oid, snap in page_cache.items():
        id_by_path[snap.source_path] = oid
```

Two full passes over the same cache to build two related dicts.

**Fix:** Build both in a single loop:
```python
pages_by_path: dict[Path, PageSnapshot] = {}
id_by_path: dict[Path, int] = {}
for oid, snap in page_cache.items():
    pages_by_path[snap.source_path] = snap
    id_by_path[snap.source_path] = oid
```

---

### Finding 7 (MEDIUM): Repeated `_page_path_key` computation

In `collect_and_generate` (line 167) and `collect_and_generate_incremental` (line 287-289), `_page_path_key(p.source_path)` is called for each page in each tag. The same pages appear under multiple tags, so this normalizes the same paths repeatedly.

**Fix:** Pre-compute a `{source_path: key}` map once and look up from it.

---

### Finding 8 (MEDIUM): `depth` recomputes `hierarchy`

```96:111:bengal/core/section/hierarchy.py
    @property
    def depth(self) -> int:
        return len(self.hierarchy)
```

`hierarchy` is an `@property` (not `@cached_property`) that walks the parent chain each time. Calling `depth` triggers a full parent traversal just to count.

**Fix:** Either make `hierarchy` a `@cached_property`, or compute `depth` by counting parents directly:
```python
@property
def depth(self) -> int:
    d = 1
    current = self
    while current.parent:
        d += 1
        current = current.parent
    return d
```

---

### Finding 9 (LOW): Double split in `page_to_summary`

```571:574:bengal/postprocess/output_formats/index_generator.py
        word_count = len(content_text.split())
        summary["word_count"] = word_count
        summary["reading_time"] = max(1, round(word_count / 200))
```

This is fine — `split()` is called once, `word_count` is reused. No actual issue on second look. **Reclassified as non-issue.**

---

### Finding 10 (LOW): `regular_pages_recursive` materializes intermediate lists

```174:177:bengal/core/section/queries.py
        result = list(self.regular_pages)
        for subsection in self.subsections:
            result.extend(subsection.regular_pages_recursive)
        return tuple(result)
```

Creates a mutable `list`, extends it via recursion, then wraps in `tuple`. Each recursive call creates its own intermediate list.

**Fix:** This is acceptable for cached properties where simplicity matters. The intermediate lists are short-lived. Low priority unless profiling shows this as hot.

---

### Finding 11 (LOW): `_get_track_item_paths` computed twice in some ordering paths

`_priority_sort` (line 286) calls `_get_track_item_paths()` after it may have already been computed inside `_maybe_sort_by_complexity` (line 87). The data is read-only so no correctness issue, but it's redundant parsing of `site.data.tracks`.

**Fix:** Compute once at the top of `_priority_sort` and pass to both `_maybe_sort_by_complexity` and `_partition_by_track`.

---

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **High** | 4 | Duplicate pipeline code, redundant tuple copy, post-hoc full scans |
| **Medium** | 4 | Double materializations, two-loop builds, repeated normalizations, uncached parent walks |
| **Low** | 2 | Minor intermediate structures, redundant track path lookups |
| Non-issue | 1 | Finding 9 reclassified on closer inspection |

### Impact Assessment

- **Finding 1** (duplicate locale_tags) — Affects every build with i18n. Maintainability + performance.
- **Finding 2** (duplicate index gen) — Pure maintainability debt (code volume). Performance neutral.
- **Finding 3** (post-hoc page scan) — O(n) wasted on every full build. Most impactful at scale (1000+ pages).
- **Finding 4** (tuple(tuple())) — Micro-optimization but touches every section during snapshot. Easy win.
- **Finding 6** (two-loop nav resolution) — Runs once per build on the full page set. Easy merge.
- **Finding 8** (depth recomputes hierarchy) — Called during rendering for every page. Could matter for deep section trees.

### Recommended Priority

1. Finding 4 — trivial one-line fix, zero risk
2. Finding 6 — straightforward loop merge
3. Finding 5 — single-line improvement
4. Finding 3 — track counts during generation
5. Finding 8 — cache `hierarchy` or compute `depth` directly
6. Finding 1 — extract helper, moderate refactor
7. Finding 2 — extract shared method, larger refactor
8. Finding 7, 11 — opportunistic when touching those files
