# FLOW Audit Report v2: Bengal (Expanded)

Audited: `bengal/**/*.py`
Date: 2026-03-14
Scope: Findings **12-25** (continuation of v1 report)

---

## New Findings

| # | Severity | File | Lines | Flow Issue | Suggested Fix |
|---|----------|------|-------|------------|---------------|
| 12 | **HIGH** | `orchestration/build/__init__.py` | 716-728 | Four separate passes over `site.pages` for logging summary | Single-pass classification loop |
| 13 | **HIGH** | `core/page/__init__.py` | 860-868 | `ancestors` is uncached `@property` that walks parent chain every call | `@cached_property` returning `tuple` |
| 14 | **HIGH** | `core/page/proxy.py` | 732-745 | `PageProxy.ancestors` also uncached, same parent walk | `@cached_property` returning `tuple` |
| 15 | **HIGH** | `orchestration/incremental/orchestrator.py` | 409-421 | O(changed_paths x sections) linear scan to find owning section | Build reverse `path_to_section` index |
| 16 | **HIGH** | `orchestration/menu.py` | 169, 195, 877 | Three full passes over `site.pages` during menu rebuild | Merge into single pass; reuse page_path_index |
| 17 | **MEDIUM** | `orchestration/related_posts.py` | 104-128 | Three passes over `site.pages` for exclusion set, page_tags, id_to_page | Merge into single loop |
| 18 | **MEDIUM** | `postprocess/output_formats/__init__.py` | 243-248 | Three filter passes over `pages` for content signal subsets | Single-pass classification |
| 19 | **MEDIUM** | `rendering/renderer.py` | 136-152 | Two passes over `site.sections` building `pages_in_sections` and `nested_sections` | Merge into single loop |
| 20 | **MEDIUM** | `orchestration/build/content.py` | 138-153 | Cascaded tag extraction duplicated between phase 7 and phase 12 | Compute once, pass forward |
| 21 | **MEDIUM** | `core/page/metadata.py` | 422-435 | `keywords` is uncached `@property`, builds list on every access | `@cached_property` returning `tuple` |
| 22 | **MEDIUM** | `core/page/metadata.py` | 590-603 | `edition` is uncached `@property`, builds list on every access | `@cached_property` returning `tuple` |
| 23 | **LOW** | `orchestration/menu.py` | 888, 940 | `sorted(languages)` called twice in same method | Compute once, reuse |
| 24 | **LOW** | `rendering/template_functions/collections.py` | 457-459 | `list(reversed(items))` where `items[::-1]` is cheaper | Use slice reversal |
| 25 | **LOW** | `core/section/ergonomics.py` | 297-314 | `aggregate_content` calls `get_all_pages` + `regular_pages_recursive` + `hierarchy` separately | Reuse cached properties; combine if hot |

---

## Detailed Analysis

### Finding 12 (HIGH): Four post-hoc passes in `_print_rendering_summary`

```716:728:bengal/orchestration/build/__init__.py
        tag_pages = sum(
            1
            for p in self.site.pages
            if p.is_generated and p.output_path is not None and "tag" in p.output_path.parts
        )
        archive_pages = sum(
            1 for p in self.site.pages if p.is_generated and p.assigned_template == "archive.html"
        )
        pagination_pages = sum(
            1 for p in self.site.pages if p.is_generated and "/page/" in str(p.output_path)
        )
        regular_pages = len(self.site.regular_pages)
```

Four separate O(n) scans over all pages just for a summary log line. This is the same pattern as Finding 3 in v1 but in a different call site.

**Fix:** Single-pass classification:
```python
tag = archive = pagination = regular = 0
for p in self.site.pages:
    if not p.is_generated:
        regular += 1
    elif p.output_path and "tag" in p.output_path.parts:
        tag += 1
    elif p.assigned_template == "archive.html":
        archive += 1
    elif p.output_path and "/page/" in str(p.output_path):
        pagination += 1
```

---

### Finding 13 (HIGH): `Page.ancestors` uncached

```860:868:bengal/core/page/__init__.py
    @property
    def ancestors(self) -> list[Section]:
        """Ancestor sections from immediate parent to root.

        Cost: O(d) — proportional to tree depth.
        """
        from bengal.core.page.navigation import get_ancestors

        return get_ancestors(self._section)
```

Builds a new list by walking the parent chain on **every** access. Breadcrumbs call it at least twice per page render (line 99 and 113 in `breadcrumbs.py`). For a site with 500 pages and depth 4, that's 4000 wasted list allocations per build.

**Fix:** `@cached_property` returning `tuple[Section, ...]`. The parent chain is immutable after section assignment.

---

### Finding 14 (HIGH): `PageProxy.ancestors` uncached (same issue)

```732:745:bengal/core/page/proxy.py
    @property
    def ancestors(self) -> list[Any]:
        result = []
        current = self._section
        while current:
            result.append(current)
            current = getattr(current, "parent", None)
        return result
```

Identical parent-chain walk without caching. PageProxy is the incremental build variant, so this hits the same breadcrumb path.

**Fix:** `@cached_property` returning `tuple`.

---

### Finding 15 (HIGH): O(changed_paths x sections) in cascade detection

```409:421:bengal/orchestration/incremental/orchestrator.py
            for section in self.site.sections:
                if hasattr(section, "index_page") and section.index_page is page:
                    for section_page in section.pages:
                        cascade_rebuild.add(section_page.source_path)
                    self._add_subsection_pages(section, cascade_rebuild)
                    break
                elif hasattr(section, "pages") and page in section.pages:
                    for section_page in section.pages:
                        cascade_rebuild.add(section_page.source_path)
                    break
```

For each changed path, scans ALL sections to find the owning section. With 50 sections and 10 changed files, that's 500 section scans. And `page in section.pages` is an O(n) list membership check.

**Fix:** Build a reverse index once:
```python
page_to_section = {id(p): s for s in self.site.sections for p in s.pages}
```
Then use `section = page_to_section.get(id(page))` for O(1) lookup.

---

### Finding 16 (HIGH): Three passes over `site.pages` during menu rebuild

**Pass 1** — `_build_page_path_index` (line 169):
```python
self._page_path_index = {to_posix(p.source_path): p for p in self.site.pages}
```

**Pass 2** — `_compute_menu_cache_key` (line 195):
```python
for page in self.site.pages:
    if "menu" in page.metadata:
        menu_pages.append(...)
    if content_dir and is_root_level_page(page, content_dir):
        root_level_pages.append(...)
```

**Pass 3** — `_build_full` (line 877):
```python
for page in self.site.pages:
    page_menu = page.metadata.get("menu", {})
```

**Fix:** Merge passes 1 and 2 into a single loop that builds the path index AND collects menu_pages/root_level_pages. Pass 3 can reuse the menu_pages list from pass 2 instead of re-scanning.

---

### Finding 17 (MEDIUM): Three passes in `related_posts.build_index`

```104:106:bengal/orchestration/related_posts.py
        page_tags_map = self._build_page_tags_map()      # pass 1: site.pages
        excluded_ids = self._build_exclusion_set()         # pass 2: site.pages
        id_to_page = {id(p): p for p in self.site.pages}  # pass 3: site.pages
```

Then a fourth at line 126:
```python
        for page in self.site.pages:
            if id(page) in excluded_ids:
                page.related_posts = []
```

**Fix:** Merge into a single loop that builds all three structures, then set `related_posts = []` in the same pass for excluded pages.

---

### Finding 18 (MEDIUM): Three filter passes for content signals

```243:248:bengal/postprocess/output_formats/__init__.py
        pages = self._filter_pages()
        ai_input_pages = [p for p in pages if getattr(p, "in_ai_input", True)]
        ai_train_pages = [p for p in pages if getattr(p, "in_ai_train", True)]
        search_pages = [p for p in pages if getattr(p, "in_search", True)]
```

Three comprehensions over the same filtered list. Each creates a separate list.

**Fix:** Single pass with accumulators:
```python
ai_input, ai_train, search = [], [], []
for p in pages:
    if getattr(p, "in_ai_input", True):
        ai_input.append(p)
    if getattr(p, "in_ai_train", True):
        ai_train.append(p)
    if getattr(p, "in_search", True):
        search.append(p)
```

---

### Finding 19 (MEDIUM): Two passes over `site.sections` in renderer

`_get_top_level_content` in `rendering/renderer.py` lines 136-152 iterates `site.sections` twice: once to collect `pages_in_sections`, once for `nested_sections`.

**Fix:** Merge into single loop:
```python
for section in self.site.sections:
    for p in section.pages:
        pages_in_sections.add(id(p))
    for s in section.subsections:
        nested_sections.add(id(s))
```

---

### Finding 20 (MEDIUM): Cascaded tag extraction duplicated across phases

Phase 7 (`content.py:138-153`) and phase 12 both iterate `pages_to_build` to extract tag slugs with identical normalize logic (`str(tag).lower().replace(" ", "-")`).

**Fix:** Compute the tag slug set once in phase 7 and pass it to phase 12 via the orchestrator or build context.

---

### Finding 21 (MEDIUM): `keywords` uncached property

```422:435:bengal/core/page/metadata.py
    @property
    def keywords(self) -> list[str]:
        keywords = self.metadata.get("keywords", [])
        if isinstance(keywords, str):
            return [k.strip() for k in keywords.split(",") if k.strip()]
        if isinstance(keywords, list):
            return [s for s in (str(k).strip() for k in keywords if k is not None) if s]
        return []
```

Builds a new list on every access. Used in `<meta name="keywords">` in base templates — once per page render.

**Fix:** `@cached_property` returning `tuple[str, ...]`.

---

### Finding 22 (MEDIUM): `edition` uncached property

```590:603:bengal/core/page/metadata.py
    @property
    def edition(self) -> list[str]:
        val = self.metadata.get("edition")
        if val is None:
            return []
        if isinstance(val, str):
            return [val] if val else []
        if isinstance(val, list):
            return [str(v).strip() for v in val if v is not None and str(v).strip()]
        return []
```

Called from `in_variant()` during variant filtering, which runs for every page twice (once for `pages_to_build`, once for `site.pages` in `_filter_sections_by_variant`).

**Fix:** `@cached_property` returning `tuple[str, ...]`.

---

### Finding 23 (LOW): `sorted(languages)` computed twice

`orchestration/menu.py` lines 888 and 940 both call `sorted(languages)` in the same method.

**Fix:** `sorted_languages = sorted(languages)` once at the top.

---

### Finding 24 (LOW): `list(reversed(items))` in collections

`rendering/template_functions/collections.py` line 459 uses `list(reversed(items))`.

**Fix:** `items[::-1]` — avoids the intermediate reversed iterator.

---

### Finding 25 (LOW): `aggregate_content` multiple traversals

`core/section/ergonomics.py` lines 297-314 calls `get_all_pages()`, `regular_pages_recursive`, `subsections`, and `hierarchy` separately. Most are cached, but `get_all_pages()` is not.

**Fix:** Use `regular_pages_recursive` (which IS cached) instead of `get_all_pages()` if semantics allow.

---

## Summary (v2 only)

| Severity | Count | Description |
|----------|-------|-------------|
| **High** | 5 | Multi-pass page scans, uncached parent walks, O(n x m) section lookup |
| **Medium** | 6 | Multi-pass filtering, duplicated tag extraction, uncached metadata properties |
| **Low** | 3 | Minor sort/reverse duplication, non-hot traversals |

## Combined Summary (v1 + v2)

| Severity | v1 | v2 | Total |
|----------|----|----|-------|
| **High** | 4 | 5 | **9** |
| **Medium** | 4 | 6 | **10** |
| **Low** | 2 | 3 | **5** |
| Non-issue | 1 | 0 | 1 |
| **Total** | 10 | 14 | **24** |

## Recommended Priority (v2 findings)

1. **Findings 13+14** (ancestors) — `@cached_property` + `tuple`, two-line change, eliminates thousands of allocations per build
2. **Finding 12** (summary logging) — single-pass rewrite, trivial
3. **Finding 15** (cascade section lookup) — build reverse index, eliminates O(n x m)
4. **Finding 19** (renderer sections loop) — merge two loops, trivial
5. **Finding 17** (related_posts) — merge passes, moderate refactor
6. **Finding 16** (menu three-pass) — merge passes 1+2, moderate
7. **Finding 18** (content signals) — single-pass classification, trivial
8. **Findings 21+22** (keywords/edition) — `@cached_property`, one-line each
9. **Finding 20** (cascaded tags) — pass data between phases, moderate
10. **Finding 23, 24, 25** — opportunistic when touching those files
