# SDC Audit: bengal/

**Date**: 2026-03-14
**Scope**: `bengal/**/*.py`
**Auditor**: AI (::sdc-audit)

---

## Findings

| # | File | Line | Current | Suggested | Severity |
|---|------|------|---------|-----------|----------|
| 1 | `orchestration/render/ordering.py` | 304 | `normal_pages.remove(page)` in loop over `normal_pages` | Set-based partition (see below) | **High** |
| 2 | `cache/taxonomy_index.py` | 50, 392 | `page_paths: list[str]` with `in` check + `.remove()` | `page_paths: set[str]` with `.discard()` | **High** |
| 3 | `server/reload_controller.py` | 305, 702 | `any(fnmatch(p, pat) for pat in self._ignored_globs)` per-path (duplicate definition) | Extract to single method, pre-compile patterns with `fnmatch.translate` + `re.compile` | **Medium** |
| 4 | `rendering/pipeline/autodoc_renderer.py` | 458 | `element_type in ["command", "command-group"]` | `element_type in {"command", "command-group"}` | **Medium** |
| 5 | `rendering/pipeline/autodoc_renderer.py` | 465 | `element_type in ["class", "function", "method", "module"]` | `element_type in {"class", "function", "method", "module"}` | **Medium** |
| 6 | `autodoc/config.py` | 252 | `mode not in ["off", "auto", "explicit"]` | `mode not in {"off", "auto", "explicit"}` | **Low** |
| 7 | `parsing/.../inline.py` | 44-52 | Three `any()` passes over `classes` + `insert(0, ...)` | Single pass + prepend base class | **Low** |
| 8 | `orchestration/render/ordering.py` | 300-302 | `rel_str in priority_track_item_paths` (type unknown) | Ensure `priority_track_item_paths` is `set`, not `list` | **Medium** |

---

## Detail

### Finding 1 — `normal_pages.remove(page)` in loop (HIGH)

```285:310:bengal/orchestration/render/ordering.py
        if self._should_use_track_dependency_ordering():
            track_item_paths = self._get_track_item_paths()
            if track_item_paths:
                # ...
                for page in list(normal_pages):
                    # ... rel_str computation ...
                    if (
                        rel_str in priority_track_item_paths
                        or rel_no_ext in priority_track_item_paths
                    ):
                        normal_pages.remove(page)   # O(n) scan + shift
                        priority_pages.append(page)
```

**Problem**: `list.remove()` inside a loop over the same list is O(n) per call, making the block O(n²) over all pages. Every `.remove()` scans the list linearly, then shifts subsequent elements.

**Fix**: Partition in a single pass:

```python
promoted = []
remaining = []
for page in normal_pages:
    if not page.source_path:
        remaining.append(page)
        continue
    try:
        rel = page.source_path.relative_to(content_root)
    except ValueError:
        remaining.append(page)
        continue
    rel_str = to_posix(rel)
    rel_no_ext = rel_str[:-3] if rel_str.endswith(".md") else rel_str
    if rel_str in priority_track_item_paths or rel_no_ext in priority_track_item_paths:
        promoted.append(page)
    else:
        remaining.append(page)
normal_pages[:] = remaining
priority_pages.extend(promoted)
```

**Impact**: O(n) instead of O(n²). Hot path during build — runs for every page in the site.

---

### Finding 2 — `TagEntry.page_paths` is `list[str]` (HIGH)

```50:50:bengal/cache/taxonomy_index.py
    page_paths: list[str]  # Pages with this tag
```

```388:393:bengal/cache/taxonomy_index.py
            for tag_slug in affected_tags:
                if tag_slug in self.tags:
                    entry = self.tags[tag_slug]
                    if page_str in entry.page_paths:    # O(n) membership
                        entry.page_paths.remove(page_str)  # O(n) scan + shift
```

**Problem**: `page_paths` is a `list[str]` but used for membership checking (`in`) and removal (`.remove()`), both O(n). The code already converts to `set()` at line 210 for invariant checks, confirming order doesn't matter.

**Fix**: Change `page_paths: list[str]` to `page_paths: set[str]`. Use `.discard()` instead of check-then-remove. Serialize to list in `to_dict()` / deserialize back in `from_dict()`.

**Impact**: O(1) membership + removal instead of O(n). Taxonomy index is updated on every incremental build.

---

### Finding 3 — Duplicate `_is_ignored` closures (MEDIUM)

```304:305:bengal/server/reload_controller.py
        def is_ignored(p: str) -> bool:
            return any(fnmatch.fnmatch(p, pat) for pat in self._ignored_globs)
```

```701:702:bengal/server/reload_controller.py
            def _is_ignored(p: str) -> bool:
                return any(fnmatch.fnmatch(p, pat) for pat in self._ignored_globs)
```

**Problem**: Two identical closures defined in different methods. Each evaluates all glob patterns per-path with `fnmatch` (string matching each time). Patterns don't change between calls.

**Fix**:
1. Deduplicate into a single private method.
2. Pre-compile patterns once with `fnmatch.translate()` + `re.compile()` for O(1) amortized matching:

```python
def __init__(self, ...):
    self._ignored_patterns = [
        re.compile(fnmatch.translate(g)) for g in self._ignored_globs
    ]

def _is_ignored(self, p: str) -> bool:
    return any(pat.match(p) for pat in self._ignored_patterns)
```

**Impact**: Runs every file-change cycle in dev server. Pre-compiled regex avoids re-translating globs.

---

### Findings 4-5 — Literal list membership (MEDIUM)

```458:458:bengal/rendering/pipeline/autodoc_renderer.py
            if element_type in ["command", "command-group"]:
```

```465:465:bengal/rendering/pipeline/autodoc_renderer.py
            elif element_type in ["class", "function", "method", "module"]:
```

**Fix**: Replace `[...]` with `{...}` (set literal). Python optimizes `in {constants}` to a `frozenset` lookup at compile time — O(1) instead of O(n) linear scan.

---

### Finding 6 — Literal list membership (LOW)

```252:252:bengal/autodoc/config.py
                if mode not in ["off", "auto", "explicit"]:
```

**Fix**: `mode not in {"off", "auto", "explicit"}`. Same compile-time frozenset optimization. Low severity since this is config validation (runs once).

---

### Finding 7 — Triple `any()` scan + `insert(0)` (LOW)

```44:52:bengal/parsing/backends/patitas/directives/builtins/inline.py
    has_base_badge = any(cls in ("badge", "api-badge") for cls in classes)

    if not has_base_badge:
        if any(cls.startswith("api-badge") for cls in classes):
            classes.insert(0, "api-badge")
        elif any(cls.startswith("badge-") for cls in classes):
            classes.insert(0, "badge")
        else:
            classes.insert(0, "badge")
```

**Problem**: Iterates `classes` up to 3 times. `list.insert(0, x)` shifts all elements. Small N so low impact, but can be a single pass.

**Fix**:

```python
base = None
for cls in classes:
    if cls in ("badge", "api-badge"):
        return css_class  # already has base
    if base is None:
        if cls.startswith("api-badge"):
            base = "api-badge"
        elif cls.startswith("badge-"):
            base = "badge"
return f"{base or 'badge'} {css_class}"
```

---

### Finding 8 — Membership check target type (MEDIUM)

```300:302:bengal/orchestration/render/ordering.py
                        if (
                            rel_str in priority_track_item_paths
                            or rel_no_ext in priority_track_item_paths
                        ):
```

**Audit note**: `priority_track_item_paths` comes from `_get_track_item_paths_for_pages()`. If this returns a `list`, every iteration is O(n). Ensure it returns a `set` for O(1) lookups. (Related to Finding 1 — same loop body.)

---

## Not Flagged (reviewed, correct)

| Pattern | File:Line | Reason |
|---------|-----------|--------|
| `next((f for f in config_files if ...), None)` | `cache_manager.py:215`, `initialization.py:548` | 2-element list, idiomatic |
| `for method in ["get", "post", ...]` | `openapi.py:343` | Iteration, not membership |
| `text.index(start)` | `errors/utils.py:425` | String `.index()`, not list; correct usage |
| `response.index(b"\r\n\r\n")` | `injection.py:25` | Bytes `.index()` for HTTP split; correct |
| `visited.remove(neighbor)` | `path_analysis.py:531` | DFS backtracking (set); O(1) |
| `for tpl_dir in [templates_dir, *dirs]` | `provenance_filter.py:146` | List construction for iteration; fine |
| `summary += f"..."` | `content.py:588` | Single conditional append, not loop |
| `url += "/"` | `metadata.py:302` | Single conditional append, not loop |
| `line += f"..."` | `logger.py:830-841` | Display formatting, not hot path |

---

## Summary

- **High** (2): Hot path O(n²) in render ordering, O(n) membership on taxonomy `page_paths`
- **Medium** (3): Literal list membership checks, duplicated fnmatch closures, unknown type of lookup target
- **Low** (2): Config-time list membership, triple-pass badge class check

**Recommended priority**: Fix findings 1 and 2 first — they're on build hot paths and scale with site size.

---

## Resolution Status (2026-03-14)

| # | Status | Notes |
|---|--------|-------|
| 1 | ✅ Fixed | `ordering.py` uses partition approach (promoted/remaining) instead of `.remove()` in loop |
| 2 | ✅ Fixed | `TagEntry.page_paths` is `set[str]` with `.discard()` |
| 3 | ✅ Fixed | `reload_controller.py` uses pre-compiled `_ignored_patterns` with `re.compile(fnmatch.translate(g))` |
| 4 | ✅ Fixed | `autodoc_renderer.py` uses `element_type in {"command", "command-group"}` |
| 5 | ✅ Fixed | `autodoc_renderer.py` uses `element_type in {"class", "function", "method", "module"}` |
| 6 | ✅ Fixed | `autodoc/config.py` uses `mode not in {"off", "auto", "explicit"}` |
| 7 | ✅ Fixed | `inline.py` uses single-pass `ensure_badge_base_class()` with `base = None` loop |
| 8 | ✅ Fixed | `_get_track_item_paths_for_pages()` returns `set[str]` — O(1) lookups |
