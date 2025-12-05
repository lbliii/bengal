# RFC: Post-Processing Pipeline Optimization

**Status**: Draft  
**Created**: 2025-12-05  
**Author**: AI-assisted analysis  
**Related**: `bengal/postprocess/`, `bengal/rendering/pipeline.py`

---

## Summary

Optimize post-processing by moving output format generation (JSON, LLM txt) earlier in the pipeline, eliminating redundant page iteration and leveraging data that's already available during rendering.

**Current Performance** (773 pages):
- Rendering: 3.31s
- Post-processing: 1.31s (40% of rendering time!)

**Target**: Reduce post-processing to <500ms by moving data preparation to rendering phase.

---

## Problem Statement

### Current Architecture

```
Phase 14: Rendering (3.31s)
├── For each page:
│   ├── Parse markdown → page.parsed_ast (HTML)
│   ├── Render template → page.rendered_html
│   └── Write HTML to disk
│
Phase 17: Post-processing (1.31s)
├── Output Formats (slow):
│   ├── For each page AGAIN:
│   │   ├── Access page.plain_text (strips HTML via regex)
│   │   ├── Build JSON data structure
│   │   └── Write page.json to disk
│   └── Generate llm-full.txt (iterates all pages)
├── Sitemap (fast)
├── RSS (fast)
└── Redirects (fast)
```

### Issues

1. **Double Iteration**: All 773 pages iterated during rendering, then again during post-processing
2. **Deferred Computation**: `plain_text` computed lazily in post-processing, but `parsed_ast` was available during rendering
3. **Sequential Data Prep**: JSON data structures built sequentially, only file writes parallelized
4. **The Pause**: Gap between "✓ Post-process" and build completion is Health Check (Phase 20)

---

## Evidence

### `bengal/postprocess/output_formats/json_generator.py:62-106`
```python
def generate(self, pages: list[Page]) -> int:
    # Prepare all page data first (sequential!)
    page_items: list[tuple[Any, dict[str, Any]]] = []
    for page in pages:  # <-- Iterating all pages AGAIN
        json_path = get_page_json_path(page)
        page_data = self.page_to_json(page)  # <-- Accesses page.plain_text
        page_items.append((json_path, page_data))

    # Write files in parallel (good!)
    with ThreadPoolExecutor(max_workers=8) as executor:
        ...
```

### `bengal/core/page/content.py:114-143`
```python
@property
def plain_text(self) -> str:
    if self._plain_text_cache is not None:
        return self._plain_text_cache

    # This regex strip happens here, not during rendering
    html_content = getattr(self, "parsed_ast", None) or ""
    text = self._strip_html_to_text(html_content)
    ...
```

### Build Output (from terminal)
```
✓ Rendering 3310ms (773 pages)
🔧 Post-processing:
✓ Post-process 1309ms        <-- 40% of rendering time!

[PAUSE]  <-- Health Check running

🏥 Health Check Report
...
```

---

## Proposed Solution

### Option A: Eager Plain Text Computation (Minimal Change)

**Change**: Compute and cache `plain_text` during rendering when `parsed_ast` is set.

```python
# bengal/rendering/pipeline.py - after markdown parsing
page.parsed_ast = parsed_content
page._plain_text_cache = page._strip_html_to_text(parsed_content)  # Eager!
```

**Benefit**: Post-processing JSON generation becomes pure I/O (no computation)
**Effort**: Low (2-3 lines)
**Impact**: ~200-400ms saved

### Option B: Accumulate Output Data During Rendering (Medium Change)

**Change**: Build JSON data structures during rendering, accumulate in BuildContext.

```python
# bengal/rendering/pipeline.py
def process_page(self, page: Page) -> None:
    ...
    # After rendering
    if self.build_context and self.build_context.output_formats_enabled:
        json_data = self._build_page_json(page)
        self.build_context.accumulated_json.append((page, json_data))
```

```python
# bengal/orchestration/postprocess.py
def _generate_output_formats(self, graph_data):
    # Just write pre-computed data
    for page, json_data in ctx.accumulated_json:
        write_json(page.output_path, json_data)
```

**Benefit**: Eliminates double iteration entirely
**Effort**: Medium (new BuildContext fields, refactor OutputFormatsGenerator)
**Impact**: ~500-700ms saved

### Option C: True AST Architecture (Future - Already Planned)

**Reference**: `plan/active/rfc-content-ast-architecture.md`

When true AST is implemented:
- `page.ast` holds parsed tokens (not HTML)
- `plain_text` becomes O(n) AST walk (faster than regex)
- Multiple outputs (HTML, text, search index) from single parse

**Benefit**: Parse once, output many formats efficiently
**Effort**: High (already in progress per RFC)
**Impact**: Significant long-term improvement

---

## Recommendation

**Phase 1** (Immediate): Implement Option A
- Minimal code change
- No architectural changes
- Measurable improvement (~200-400ms)

**Phase 2** (Near-term): Implement Option B
- Better separation of concerns
- Eliminates redundant iteration
- Sets up for streaming/memory-optimized builds

**Phase 3** (Long-term): Continue AST migration
- Already planned in `rfc-content-ast-architecture.md`
- Will unlock further optimizations

---

## The "Pause" Issue

The gap between "✓ Post-process" and rest of build output is **Phase 20: Health Check**.

```python
# bengal/orchestration/build/finalization.py:97-163
def run_health_check(orchestrator, profile, incremental):
    health_check = HealthCheck(orchestrator.site)
    report = health_check.run(...)  # <-- This takes time
    cli.info(report.format_console())  # <-- And this prints
```

**Observations**:
- Health check runs all validators (directives, links, output)
- Report formatting happens synchronously
- No timing output for health check phase itself

**Quick Fix**: Add timing to health check:
```python
with orchestrator.logger.phase("health_check"):
    # existing code
cli.phase("Health check", duration_ms=health_check_time_ms)  # New
```

---

## Implementation Plan

### Phase 1: Eager Plain Text (1-2 hours)

1. Modify `RenderingPipeline.process_page()` to compute plain_text after parsing
2. Add `_compute_plain_text_cache()` method to Page or pipeline
3. Verify JSON/LLM generation still works
4. Benchmark: expect ~200-400ms improvement

### Phase 2: Accumulated Output Data (4-6 hours)

1. Add `accumulated_page_json: list[tuple]` to BuildContext
2. Modify pipeline to accumulate JSON data during rendering
3. Modify OutputFormatsGenerator to consume accumulated data
4. Consider memory implications for large sites
5. Benchmark: expect ~500-700ms improvement total

### Phase 3: Health Check Timing (30 min)

1. Add timing instrumentation to health check phase
2. Add CLI output for health check duration
3. Consider parallelizing validators (if not already)

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Memory increase from accumulated data | Option B can stream-write periodically |
| Breaking change to OutputFormatsGenerator API | Internal API, low impact |
| Plain text quality regression | Unit tests for plain_text property |
| Incremental build compatibility | BuildContext already handles incremental |

---

## Success Criteria

- [ ] Post-processing time reduced to <500ms (from 1300ms)
- [ ] No regression in output quality (JSON, LLM txt)
- [ ] Health check timing visible in build output
- [ ] All existing tests pass
- [ ] Benchmark on test-basic site shows improvement

---

## Related Files

- `bengal/rendering/pipeline.py` - Main rendering pipeline
- `bengal/postprocess/output_formats/` - JSON, LLM generators
- `bengal/core/page/content.py` - plain_text property
- `bengal/orchestration/build/finalization.py` - Post-process and health check phases
- `plan/active/rfc-content-ast-architecture.md` - AST migration plan

---

## Questions for Review

1. Should accumulated JSON data be written during rendering (streaming) or batched in post-process?
2. Is memory overhead of accumulated data acceptable for large sites (10k+ pages)?
3. Should health check run in parallel with post-processing (both are mostly independent)?
