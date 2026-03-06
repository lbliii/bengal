# Bengal Parse Optimizations: parse_many + AST Caching

**Status**: Plan (ready for implementation)  
**Context**: Structural changes to reduce parse overhead in Bengal builds. Complements Patitas core optimizations (str.split fix, line index).

## Executive Summary

| Optimization | Expected Gain | Effort | Priority |
|--------------|---------------|--------|----------|
| **AST caching** (parsed_content) | 2–3× incremental | Low (validate + tune) | High |
| **parse_many** (batch parse) | 5–15% full build | Medium | Medium |

## Current Architecture

### Parse Flow (per page)

```
RenderOrchestrator.process(pages)
  → process_page_with_pipeline(page)  [per page, parallel]
    → RenderingPipeline.process_page(page)
      → try_rendered_cache()     # Skip if final HTML cached
      → try_parsed_cache()      # Skip parse if html/ast cached
      → _parse_content(page)    # parser.parse_with_toc_and_context()
      → cache_parsed_content()
      → _render_and_write()
```

**Key files**:
- `bengal/orchestration/render/orchestrator.py` — dispatches to workers
- `bengal/orchestration/render/pipeline_runner.py` — `process_page_with_pipeline`
- `bengal/rendering/pipeline/core.py` — `RenderingPipeline.process_page`, `_parse_content`
- `bengal/rendering/pipeline/cache_checker.py` — `try_parsed_cache`, `cache_parsed_content`
- `bengal/cache/build_cache/parsed_content_cache.py` — `get_parsed_content`, `store_parsed_content`
- `bengal/parsing/backends/patitas/wrapper.py` — `PatitasParser.parse_with_toc_and_context`

### Parsed Content Cache (already exists)

- **Location**: `BuildCache.parsed_content` (persisted with build cache)
- **Stores**: `html`, `toc`, `toc_items`, `links`, `excerpt`, `meta_description`, optional `ast`
- **Validation**: `is_changed(file_path)`, `metadata_hash`, `template`, `parser_version`, dependencies
- **On hit**: Skip parse, use cached html (or render from ast if only ast cached)
- **Optional AST**: `markdown.ast_cache.persist_tokens = true` stores AST for template-only rebuilds

---

## Phase 1: Validate and Tune AST Caching (High Priority)

**Goal**: Ensure parsed_content cache is effective and used correctly.

### 1.1 Add cache hit metrics

**File**: `bengal/orchestration/stats/models.py` or `BuildStats`

- `parsed_cache_hits` — already incremented in `cache_checker.try_parsed_cache`
- `rendered_cache_hits` — already incremented
- **Action**: Expose in build summary (e.g. "Parsed cache: 87 hits, 13 misses")

### 1.2 Incremental build flow (verified)

**Flow**: `IncrementalOrchestrator` → `pages_to_rebuild` (changed + cascade dependents) → `pages_to_build_objs` → `RenderOrchestrator.process(pages)` → `scheduler.render_all(pages)`.

- **Incremental**: Only affected pages are passed (changed content + pages depending on changed templates/assets).
- **Cache benefit**: When a template changes, we re-render all pages using that template. For each page, if content unchanged → `parsed_content` HIT → skip parse. If content changed → MISS → parse.
- **Conclusion**: parsed_content cache is most valuable for template-only changes (many pages re-rendered, most content unchanged).

### 1.3 Enable persist_tokens by default (optional)

**File**: `bengal/rendering/pipeline/cache_checker.py` (reads `markdown.ast_cache.persist_tokens`)

- **Current**: `persist_tokens` is off by default
- **Benefit**: When only template changes, we can re-render from AST without re-parsing
- **Tradeoff**: Larger cache (AST dicts), more serialization
- **Decision**: Keep opt-in for now. Enable via `markdown.ast_cache.persist_tokens: true` for sites with many pages and frequent template-only changes.

### 1.4 Content-hash validation (already in place)

- `get_parsed_content` uses `is_changed(file_path)` from `FileTrackingMixin`
- FileTracking uses `file_fingerprints` (mtime, size, hash)
- **Action**: Confirm `is_changed` uses content hash when available (not just mtime) to avoid false invalidations

---

## Phase 2: parse_many Integration (Medium Priority)

**Goal**: Batch-parse pages that need parsing, reducing per-page config overhead.

### 2.1 Current per-page overhead

Each `_parse_content` call:
1. `set_parse_config` / `reset_parse_config` (ContextVar)
2. `set_patitas_parse_config` / `reset_patitas_parse_config` (external Patitas)
3. Parser creation (or reuse from pool)
4. Parse
5. Config reset

With `parse_many`: set config once, parse N pages, reset once.

### 2.2 Design: Pre-parse phase

**Option A: Parse phase before render (recommended)**

```
1. Collect pages that need parsing (cache miss, not prerendered)
2. Batch-parse: contents = [p.content for p in pages]; docs = md.parse_many(contents)
3. Attach AST/html to each page (page._ast_cache, page.html_content, etc.)
4. Render phase: process_page skips _parse_content when page.html_content already set
```

**Option B: Integrate parse_many into PatitasParser**

- Add `parse_many_with_toc(sources, metadata_list, context_list)` to PatitasParser
- Returns list of (html, toc, excerpt, meta_desc) tuples
- Render orchestrator calls this once per batch of cache-miss pages

**Complexity**: PatitasParser has `parse_with_toc_and_context` which needs `context` (page, site, xref_index, VariableSubstitutionPlugin). Batch parsing with context is trickier:
- Variable substitution: `text_transformer` is per-page (depends on page context)
- Cross-references: `xref_index` is site-wide, can be shared
- **Conclusion**: Simple pages (no `{{ }}` variables) can use parse_many. Pages with variables need per-page parse.

### 2.3 Implementation steps

1. **Add `needs_parse(page)` helper**: True if `not page.html_content` and not virtual
2. **Add pre-parse batch in RenderOrchestrator**:
   - Before `_render_parallel` / `_render_sequential`, collect `pages_to_parse = [p for p in pages if needs_parse(p)]`
   - Split into "simple" (no var substitution) vs "context" (needs context)
   - For simple: `contents = [load_content(p) for p in simple_pages]`; `results = parser.parse_many_with_toc(contents)`
   - Attach results to pages
3. **Skip _parse_content** in pipeline when `page.html_content` already set (e.g. from pre-parse or WaveScheduler)
4. **PatitasParser**: Add `parse_many_with_toc(sources: list[str], metadata_list: list[dict]) -> list[tuple]`
   - Uses `Markdown.parse_many` under the hood
   - Each result: (html, toc, excerpt, meta_desc)

### 2.4 Edge cases

- **Variable substitution**: Pages with `{{ page.title }}` etc. need `parse_with_context`. Exclude from batch.
- **Cross-references**: `xref_index` is set on parser via `enable_cross_references`. Shared across batch.
- **Thread safety**: parse_many runs in main thread or a single worker. Render still parallel.
- **Memory**: Batch size limit (e.g. 50 pages) to avoid holding too much in memory.

---

## Phase 3: Patitas DictParseCache (Optional)

**Goal**: Use Patitas's `parse(..., cache=DictParseCache)` for content-addressed deduplication.

**When useful**: Multiple pages with identical content (e.g. same include, duplicated layout).

**Integration**:
- Create `DictParseCache` (or thread-safe variant) in BuildContext
- Pass to `parse_to_document` / `parse_to_ast` when available
- Patitas checks `content_hash` + `config_hash` before parsing

**Note**: Bengal's parsed_content cache is path-based. Patitas cache is content-based. They complement: path cache for "this file hasn't changed", content cache for "this exact content was parsed before".

---

## Implementation Order

1. **Phase 1.1–1.2** (1–2 hrs): Add metrics, verify incremental flow
2. **Phase 1.3** (30 min): Evaluate persist_tokens default
3. **Phase 2** (4–8 hrs): parse_many for simple pages
4. **Phase 3** (2–4 hrs): DictParseCache if Phase 1–2 show benefit

---

## Success Metrics

- **Incremental build** (1 of 100 pages changed): Parse time < 5% of full build parse time
- **Full build**: parse_many reduces total time by 5–15%
- **Build summary**: "Parsed cache: X hits, Y misses" visible in output

---

## References

- `bengal/rendering/pipeline/cache_checker.py` — try_parsed_cache, cache_parsed_content
- `bengal/cache/build_cache/parsed_content_cache.py` — get/store parsed content
- `bengal/parsing/backends/patitas/__init__.py` — parse_many, create_markdown
- `bengal/parsing/backends/patitas/wrapper.py` — PatitasParser
- `patitas/benchmarks/experiment_bengal_optimizations.py` — parse cache experiment
- `patitas/plan/patitas-bengal-performance-optimization.md` — Patitas-side optimizations
