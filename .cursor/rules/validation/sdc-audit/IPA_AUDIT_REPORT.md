# IPA Audit: bengal/

**Date**: 2026-03-14
**Scope**: `bengal/**/*.py`
**Auditor**: AI (::ipa-audit)

---

## Findings

| # | File | Line | Interaction Issue | Severity |
|---|------|------|-------------------|----------|
| 1 | `rendering/engines/kida.py` | 334 | Menu cache invalidated on every `render_template()` call | **High** |
| 2 | `rendering/renderer.py` | 824-846 | Multiple full template loads per page for existence checks | **High** |
| 3 | `orchestration/incremental/orchestrator.py` | 203, 264 | Duplicate `rglob("*.html")` walks for template change detection | **High** |
| 4 | `server/build_trigger.py` | 273, 420 | `_get_template_change_info()` computed twice per build | **High** |
| 5 | `orchestration/menu.py` | 657-711 | Full page scan per menu per locale: O(menus x langs x pages) | **High** |
| 6 | `health/validators/links.py` + `core/page/operations.py` | 83, 565 | New `LinkValidator` + full index rebuild per page | **High** |
| 7 | `orchestration/build/provenance_filter.py` | 523 | Set comprehension rebuilt inside loop over taxonomy pages | **Medium** |
| 8 | `orchestration/menu.py` | 480-486 | O(sections x menu_items) nested scan for dropdown matching | **Medium** |
| 9 | `orchestration/menu.py` | 176-244 | Two full scans of `site.pages` in `_compute_menu_cache_key` | **Medium** |
| 10 | `cache/taxonomy_index.py` | 336, 411, 420 | `get_all_tags()` / `get_valid_entries()` / `get_invalid_entries()` rebuild filtered dicts every call | **Medium** |
| 11 | `orchestration/taxonomy.py` | 375-430 | `locale_tags` dict rebuilt per language in loop | **Medium** |
| 12 | `rendering/template_functions/collections.py` | 104-114 | `operators` dict rebuilt on every `where()` call | **Medium** |
| 13 | `rendering/engines/kida.py` | 347 | `_track_referenced_templates()` recursive template loading per render | **Medium** |
| 14 | `server/build_trigger.py` | 262, 385 | Path -> str -> Path round-trip conversion | **Medium** |
| 15 | `orchestration/build/provenance_filter.py` | 336, 462 | Repeated `list(site.pages)` materializations in same phase | **Medium** |
| 16 | `health/validators/links.py` | 106-175 | Three full iterations over `site.pages` to build URL, source path, and auxiliary indexes | **Medium** |
| 17 | `orchestration/incremental/orchestrator.py` | 532-538 | Nested loops with per-file `stat()` I/O for shared content changes | **Medium** |
| 18 | `orchestration/build/inputs.py` | 109-110 | `changed_paths` iterated twice (once for Options, once for Input) | **Low** |
| 19 | `orchestration/taxonomy.py` | 409 | `get_all_tags()` returns full dict when caller only needs keys | **Low** |
| 20 | `rendering/template_functions/collections.py` | 230, 274, 478, 521 | `sorted()` in hot-path template filters (per-page) | **Low** |

---

## Detail

### Finding 1 — Menu cache invalidated per render (HIGH)

```334:334:bengal/rendering/engines/kida.py
        invalidate_menu_cache()
```

**Problem**: `invalidate_menu_cache()` is called at the start of every `render_template()` invocation. Since `render_template()` runs once per page, the menu cache is destroyed and rebuilt for every page in the site. For a 500-page site, the menu structure is computed 500 times instead of once.

**Fix**: Only invalidate when menu-affecting data has changed (navigation config, page metadata changes), not on every render. The cache key computation in `menu.py` already handles staleness detection.

**Impact**: O(pages^2) work during render phase. This is the single highest-impact finding.

---

### Finding 2 — Template existence check does full load (HIGH)

```824:846:bengal/rendering/renderer.py
    # _get_template_name tries up to 4 candidates per page
    for template_name in templates_to_try:
        if self._template_exists(template_name):  # full template load!
            ...

    def _template_exists(self, template_name):
        self.template_engine.env.get_template(template_name)  # loads/compiles
```

**Problem**: Section-based template resolution tries up to 4 template names per page (`section/single.html`, `single.html`, etc.). Each `_template_exists()` call does `env.get_template()`, which loads and potentially compiles the template, just to check if it exists. For N pages with S sections, this is up to 4N template loads.

**Fix**: Add a lightweight `template_exists()` method that checks the loader without compiling, or cache the resolved template name per section so it's computed once per section instead of once per page.

---

### Finding 3 — Duplicate template directory walks (HIGH)

```203:274:bengal/orchestration/incremental/orchestrator.py
    # _detect_template_changes: walks templates_dir.rglob("*.html")
    # _detect_template_affected_pages: walks templates_dir.rglob("*.html") AGAIN
    # Both called from find_work_early / _detect_changes
```

**Problem**: Two separate functions each do `templates_dir.rglob("*.html")` and call `self.cache.is_changed()` per file. The second function re-walks the same directory tree and re-checks which templates changed.

**Fix**: Merge into a single function that walks once, detects changed templates, and collects affected pages in one pass. Return both results from a single traversal.

---

### Finding 4 — Template change info computed twice (HIGH)

```273:420:bengal/server/build_trigger.py
    # _needs_full_rebuild calls _get_template_change_info(changed_paths)
    # _execute_build calls _get_template_change_info(changed_paths) again
```

**Problem**: Full template change analysis (template dirs scan, HTML filter, cache lookups, affected pages) is computed once to decide if a full rebuild is needed, then computed again to populate build options.

**Fix**: Compute once, pass the result through. Have `_needs_full_rebuild` return the `template_info` alongside its decision, or cache it on the instance.

---

### Finding 5 — Full page scan per menu per locale (HIGH)

```657:711:bengal/orchestration/menu.py
    for menu_name, items in menu_config.items():
        for page in self.site.pages:         # full scan
            ...
        for lang in languages:
            for page in self.site.pages:     # full scan again
                ...
```

**Problem**: Menu building scans all pages for each menu definition and then again for each language. For M menus, L languages, and P pages, this is O(M x L x P) total iterations.

**Fix**: Build a single `page_url_to_page` or `page_path_to_page` index once, then do O(1) lookups per menu item. The page-to-menu mapping can be computed in a single pass.

---

### Finding 6 — LinkValidator rebuilt per page (HIGH)

```83:84:bengal/core/page/operations.py
    # Page.validate_links() creates new LinkValidator() per page

565:565:bengal/health/validators/links.py
    # validate_links(page, site) creates LinkValidator(site) per call
```

**Problem**: Each `validate_links()` call creates a new `LinkValidator`, which builds a `page_url_index` (iterates all pages), a `source_path_index` (iterates all pages again), and optionally an `auxiliary_url_index` (iterates all pages a third time). When called per page during rendering, this is O(pages^2) total work.

**Fix**: Create one `LinkValidator` instance at the start of the render phase and pass it to all page validations, or cache the indexes on the `Site` object.

---

### Finding 7 — Set rebuilt inside taxonomy page loop (MEDIUM)

```523:523:bengal/orchestration/build/provenance_filter.py
    for page in taxonomy_pages:
        affected_lower = {t.lower() for t in result.affected_tags}  # rebuilt every iteration
```

**Fix**: Hoist `affected_lower` above the loop.

---

### Finding 8 — Nested scan for dropdown sections (MEDIUM)

```480:486:bengal/orchestration/menu.py
    for section in sections_with_dropdown:
        for item in menu_items:
            if item.url == section_url or item.identifier == section.name:
                ...
```

**Fix**: Build `{url: item for item in menu_items}` once, then O(1) lookup per section.

---

### Finding 9 — Double page scan in menu cache key (MEDIUM)

```176:244:bengal/orchestration/menu.py
    menu_pages = [p for p in self.site.pages if ...]      # first scan
    root_level_pages = [p for p in self.site.pages if ...] # second scan
```

**Fix**: Single-pass partition into `menu_pages` and `root_level_pages`.

---

### Finding 10 — Taxonomy index filter dicts rebuilt every call (MEDIUM)

```336:336:bengal/cache/taxonomy_index.py
    def get_all_tags(self):
        return {slug: entry for slug, entry in self.tags.items() if entry.is_valid}

411:411:  # get_valid_entries — identical to get_all_tags
420:420:  # get_invalid_entries — same pattern, negated
```

**Fix**: Cache valid/invalid views. Invalidate on `update_tag()`, `invalidate_tag()`, `clear()`.

---

### Finding 11 — Locale tags rebuilt per language (MEDIUM)

```375:430:bengal/orchestration/taxonomy.py
    for lang in languages:
        locale_tags = {slug: entry for slug, entry in taxonomies["tags"].items() if ...}
```

**Fix**: Build locale-keyed tag dict once before the language loop.

---

### Finding 12 — `operators` dict rebuilt per `where()` call (MEDIUM)

```104:114:bengal/rendering/template_functions/collections.py
    def where(items, key, operator="==", value=None):
        operators = {"==": ..., "!=": ..., ...}  # rebuilt every call
```

**Fix**: Promote `operators` to module-level constant.

---

### Finding 13 — Recursive template tracking per render (MEDIUM)

```347:347:bengal/rendering/engines/kida.py
    _track_referenced_templates(name)  # recursive template load per render
```

**Fix**: Cache the dependency graph. Templates don't change during a build, so the graph computed for template A is stable. Use a `{template_name: set[str]}` cache.

---

### Finding 14 — Path/str/Path round-trip (MEDIUM)

```262:385:bengal/server/build_trigger.py
    changed_files = [str(p) for p in changed_paths]
    # ... later ...
    changed_sources={Path(p) for p in changed_files}
```

**Fix**: Build `changed_sources` directly from `changed_paths`.

---

### Finding 15 — Repeated `list(site.pages)` in same phase (MEDIUM)

```336:463:bengal/orchestration/build/provenance_filter.py
    pages_list_for_deps = list(site.pages)  # first materialization
    # ... later ...
    pages_list = list(site.pages)           # second materialization
```

**Fix**: Materialize once, reuse.

---

### Finding 16 — Three page iterations for link validator indexes (MEDIUM)

```106:175:bengal/health/validators/links.py
    _build_page_url_index(site)       # iterates site.pages
    _build_source_path_index(site)    # iterates site.pages again
    _build_auxiliary_url_index(site)   # iterates site.pages a third time
```

**Fix**: Build all three indexes in a single pass over `site.pages`.

---

### Finding 17 — Nested loop with per-file stat I/O (MEDIUM)

```532:538:bengal/orchestration/incremental/orchestrator.py
    for shared_path in version_config.shared:
        for file_path in shared_dir.rglob("*.md"):
            self.cache.is_changed(file_path)  # stat() per file
```

**Fix**: Batch change detection using directory mtime first, then individual files only if directory changed.

---

## Not Flagged (reviewed, correct)

| Pattern | File:Line | Reason |
|---------|-----------|--------|
| `{id(p): i for i, p in enumerate(pages)}` | `navigation.py:44` | Already cached with `_index_cache` |
| `set()` in `build_cache/core.py` `__post_init__` | `core.py:195` | One-time at load, not per-call |
| `sorted()` in `content_discovery.py` | `content_discovery.py:224` | Runs once per build for deterministic ordering |
| `operators` in `collections.py` template filters | N/A | `sorted()` calls are inherent to `sort_by`/`group_by` semantics |
| TOC `.append()` patterns | `toc.py:59-165` | Single-pass tree builds, O(n) |
| `{k: set(v) for ...}` in cache save/load | `core.py:291-438` | One-time serialization boundary |

---

## Summary

- **High** (6): Menu cache thrashed per render, template existence doing full loads, duplicate rglob walks, duplicate template change analysis, O(M x L x P) menu building, LinkValidator rebuilt per page
- **Medium** (11): Rebuilt indexes/sets in loops, duplicate page scans, nested section scans, chatty per-file I/O, path type conversions
- **Low** (3): Redundant iterations, unnecessary dict returns, template filter sorts

**Recommended priority**: Fix findings 1, 2, 5, and 6 first. They all create O(pages^2) or worse interactions on the build hot path and dominate build time for large sites. Findings 3 and 4 are high-impact for incremental/dev-server builds specifically.
