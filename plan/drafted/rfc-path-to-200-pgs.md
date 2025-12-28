# RFC: Path to 200 pg/s — Zero-Overhead Architecture

| Field | Value |
|-------|-------|
| **RFC ID** | `rfc-path-to-200-pgs` |
| **Status** | Draft |
| **Created** | 2025-12-28 |
| **Author** | AI Assistant + Lawrence Lane |
| **Target** | Bengal Core, Patitas (Parser), RenderingPipeline |
| **Depends On** | `rfc-patitas-markdown-parser`, `rfc-zero-copy-lexer-handoff` |
| **Baseline** | 113 pg/s (1,436 pages in 12.7s, M-series Mac) |

---

## Executive Summary

Bengal has achieved **113 pg/s** throughput through state-machine parsing (Patitas) and free-threading readiness. This RFC proposes targeted optimizations to reach **200+ pg/s** by eliminating post-render processing passes and overlapping compute with I/O.

**Key optimizations**:
1. **Single-Pass Heading Decoration**: Generate heading IDs during AST rendering, eliminating regex post-processing
2. **Inline Cross-Reference Resolution**: Resolve `[[links]]` during render, not as HTML substitution
3. **I/O Decoupling**: Async write-behind buffer to overlap CPU and disk work
4. **Free-Threading Polish**: Ensure GIL-free operation under Python 3.14t

---

## Current Architecture Analysis

### What's Already Optimized

The main render path **already consumes typed AST nodes directly**:

```python
# wrapper.py:108 - Main path does NOT use asdict()
html = self._md(content)

# __init__.py:363-366 - Internal flow uses typed nodes
def __call__(self, source: str, ...) -> str:
    ast = self._parse_to_ast(source, ...)     # Returns Sequence[Block]
    return self._render_ast(ast, source, ...)  # Consumes slots directly
```

The `asdict()` call exists only for optional AST caching (`parse_to_ast()` public API), not in the hot render path.

### Remaining Bottlenecks

**Bottleneck 1: Post-Render Heading ID Injection**

After rendering HTML, `_inject_heading_ids()` re-scans the output with regex:

```python
# wrapper.py:311-333
def _inject_heading_ids(self, html: str) -> str:
    def replace_heading(match: re.Match[str]) -> str:
        # ... generate slug, inject id attribute
    return _HEADING_PATTERN.sub(replace_heading, html)
```

This duplicates work: the renderer already walked every heading node.

**Bottleneck 2: Cross-Reference Post-Processing**

`_apply_post_processing()` performs string substitution for `[[wiki-links]]`:

```python
# wrapper.py:288-309
def _apply_post_processing(self, html: str, metadata: dict[str, Any]) -> str:
    if self._xref_enabled and self._xref_plugin:
        html = self._xref_plugin._substitute_xrefs(html)
    return html
```

This scans the entire HTML output looking for placeholders.

**Bottleneck 3: Synchronous File I/O**

`write_output()` performs blocking writes. On cold builds with 1,400+ pages, I/O latency accumulates.

**Bottleneck 4: Template Rendering**

Jinja2 template compilation and context assembly are significant but out of scope for this RFC. See future `rfc-kida-template-acceleration`.

---

## Proposed Optimizations

### 1. Single-Pass Heading Decoration

**Goal**: Generate heading IDs during AST rendering, eliminating `_inject_heading_ids()`.

**Design**: Add a `HeadingDecorator` callback to `HtmlRenderer`:

```python
# bengal/rendering/parsers/patitas/renderers/html.py

@dataclass
class HeadingInfo:
    """Heading metadata collected during rendering."""
    level: int
    text: str
    slug: str

class HtmlRenderer:
    def __init__(
        self,
        source: str,
        highlight: bool = True,
        heading_decorator: Callable[[Heading], str] | None = None,  # NEW
        ...
    ):
        self._heading_decorator = heading_decorator or self._default_slug
        self._headings: list[HeadingInfo] = []  # Collected during render

    def _render_heading(self, node: Heading, sb: StringBuilder) -> None:
        # Extract text from inline children (already walking them)
        text = self._extract_plain_text(node.children)

        # Generate slug ONCE during this walk
        slug = self._heading_decorator(node) if self._heading_decorator else slugify(text)

        # Collect for TOC (replaces _extract_toc post-pass)
        self._headings.append(HeadingInfo(node.level, text, slug))

        # Emit with ID already included
        sb.append(f'<h{node.level} id="{slug}">')
        self._render_inline(node.children, sb)
        sb.append(f'</h{node.level}>\n')
```

**Changes**:
- Remove `_inject_heading_ids()` from `wrapper.py`
- Remove `_extract_toc()` AST walk (headings collected during render)
- `parse_with_toc()` returns `(html, self.renderer.get_toc_html())`

**Estimated Gain**: +15-20 pg/s (eliminates regex scan of full HTML)

### 2. Inline Cross-Reference Resolution

**Goal**: Resolve `[[wiki-links]]` during parsing, not as HTML post-substitution.

**Design**: The Patitas lexer already recognizes `[[...]]` syntax. Extend the AST node to store resolved URLs:

```python
# Currently: CrossReference stores raw target, resolved during HTML substitution
# Proposed: Resolve during parsing when xref_index is available

@dataclass(frozen=True, slots=True)
class CrossReference(Inline):
    target: str           # Original [[target]]
    display: str | None   # Optional |display text
    resolved_url: str | None = None  # NEW: Pre-resolved URL
    anchor: str | None = None        # NEW: Pre-resolved anchor

# In parser, when xref_index is provided:
def _parse_cross_reference(self, token: Token) -> CrossReference:
    target, display = parse_xref_syntax(token.value)
    resolved_url, anchor = self._xref_index.resolve(target) if self._xref_index else (None, None)
    return CrossReference(target, display, resolved_url, anchor)
```

**Changes**:
- Pass `xref_index` to parser/renderer (already available in `PatitasParser`)
- Remove `_substitute_xrefs()` post-processing
- Renderer emits resolved links directly

**Estimated Gain**: +5-10 pg/s (eliminates full HTML regex scan)

### 3. Async Write-Behind I/O

**Goal**: Overlap CPU-bound rendering with I/O-bound file writes.

**Design**: Introduce `WriteBehindCollector` that queues rendered pages for async flush:

```python
# bengal/rendering/pipeline/write_behind.py

from queue import Queue
from threading import Thread
from pathlib import Path

class WriteBehindCollector:
    """Async write-behind buffer for rendered pages.

    Worker threads push (path, content) pairs; dedicated I/O thread drains to disk.
    """

    def __init__(self, max_buffer_mb: int = 64):
        self._queue: Queue[tuple[Path, str] | None] = Queue(maxsize=1000)
        self._writer_thread = Thread(target=self._drain_loop, daemon=True)
        self._writer_thread.start()

    def enqueue(self, output_path: Path, html: str) -> None:
        """Non-blocking enqueue. May block if buffer full."""
        self._queue.put((output_path, html))

    def _drain_loop(self) -> None:
        """Background thread: drain queue to disk."""
        while True:
            item = self._queue.get()
            if item is None:  # Shutdown signal
                break
            path, content = item
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def flush_and_close(self) -> None:
        """Wait for all writes to complete."""
        self._queue.put(None)
        self._writer_thread.join()
```

**Integration**:
```python
# In RenderOrchestrator.render_pages():
collector = WriteBehindCollector()
for page in pages:
    html = pipeline.render_page(page)
    collector.enqueue(page.output_path, html)  # Non-blocking
collector.flush_and_close()  # Wait at end
```

**Estimated Gain**: +10-15 pg/s on cold builds (I/O overlapped with render)

### 4. Free-Threading Readiness (Python 3.14t)

**Goal**: Ensure linear scaling when GIL is disabled.

**Audit Checklist**:
- [ ] `HtmlRenderer`: Verify no shared mutable state
- [ ] `StringBuilder`: Confirm thread-local allocation
- [ ] `Rosettes` lexers: Audit for module-level caches
- [ ] `Kida` template cache: Add per-thread LRU or lock-free design
- [ ] Declare `Py_mod_gil = Py_MOD_GIL_NOT_USED` in C extensions (if any)

**Current State**: Patitas is already designed for free-threading (immutable AST, no shared state). Rosettes uses thread-local lexer instances. Main risk is template engine cache contention.

**Estimated Gain**: +40-50 pg/s on 16+ core systems (true parallelism)

---

## Performance Targets

| Metric | Current (113 pg/s) | Target | Optimization |
|--------|-------------------|--------|--------------|
| **Heading decoration** | Regex post-pass | AST-integrated | Single-pass decoration |
| **Cross-ref resolution** | HTML substitution | Parse-time | Inline resolution |
| **File writes** | Synchronous | Overlapped | Write-behind buffer |
| **Core scaling** | Limited by GIL | Linear | Free-threading polish |

---

## Implementation Roadmap

### Phase I: Single-Pass Decoration (Low Risk)

**Scope**: Eliminate `_inject_heading_ids()` and `_extract_toc()` post-passes.

**Changes**:
- [ ] Add `_headings` collection to `HtmlRenderer`
- [ ] Generate IDs during `_render_heading()`
- [ ] Add `get_toc_items()` and `get_toc_html()` methods
- [ ] Update `PatitasParser.parse_with_toc()` to use renderer's collected headings
- [ ] Remove `_inject_heading_ids()` from `wrapper.py`
- [ ] Benchmark before/after

**Risk**: Low (internal refactor, no API changes)

**Estimated Gain**: +15-20 pg/s

### Phase II: Inline Cross-Reference Resolution (Medium Risk)

**Scope**: Resolve `[[links]]` during parsing instead of HTML substitution.

**Changes**:
- [ ] Extend `CrossReference` node with `resolved_url` field
- [ ] Pass `xref_index` to parser
- [ ] Resolve during `_parse_cross_reference()`
- [ ] Update renderer to emit resolved links directly
- [ ] Remove `_substitute_xrefs()` post-processing
- [ ] Benchmark before/after

**Risk**: Medium (changes AST node signature)

**Estimated Gain**: +5-10 pg/s

### Phase III: Write-Behind I/O (Medium Risk)

**Scope**: Overlap file writes with rendering.

**Changes**:
- [ ] Implement `WriteBehindCollector`
- [ ] Integrate with `RenderOrchestrator`
- [ ] Add graceful shutdown handling
- [ ] Benchmark on HDD vs SSD vs NVMe
- [ ] Consider optional `mmap` for large files

**Risk**: Medium (concurrency, error handling)

**Estimated Gain**: +10-15 pg/s (cold builds)

### Phase IV: Free-Threading Audit (Low Risk)

**Scope**: Prepare for Python 3.14t GIL-free operation.

**Changes**:
- [ ] Audit all module-level mutable state
- [ ] Run ThreadSanitizer on 3.14t beta
- [ ] Profile with `threading` vs `concurrent.futures`
- [ ] Document thread-safety guarantees

**Risk**: Low (audit and fixes, no architectural changes)

**Estimated Gain**: +40-50 pg/s (on 16+ cores with 3.14t)

---

## Profiling Requirements

Before implementing, establish baselines with `py-spy` or `cProfile`:

```bash
# Generate flame graph for 1,000-page build
py-spy record -o profile.svg -- python -m bengal build site/

# Measure specific functions
python -c "
import cProfile
from bengal.rendering.parsers.patitas.wrapper import PatitasParser
# ... profile parse_with_toc on representative content
"
```

**Metrics to capture**:
- Time in `_inject_heading_ids()` vs total render time
- Time in `_substitute_xrefs()` vs total render time
- I/O wait time vs compute time
- Memory allocations per page

---

## Success Criteria

1. **Throughput**: ≥200 pg/s on 1,400-page cold build (current hardware)
2. **No Regressions**: All existing tests pass; output HTML unchanged
3. **Measured Gains**: Each phase demonstrates ≥80% of estimated gain
4. **Thread Safety**: No data races under ThreadSanitizer (Python 3.14t)

---

## Future Work (Out of Scope)

- **Template Acceleration**: Kida template compilation, partial pre-rendering
- **Incremental Rendering**: Skip unchanged pages (already partially implemented)
- **Memory Mapping**: `mmap` for large output files
- **SIMD Text Processing**: Vectorized HTML escaping (requires C extension)

---

## References

- `plan/drafted/rfc-patitas-markdown-parser.md` — Parser architecture
- `plan/drafted/rfc-zero-copy-lexer-handoff.md` — ZCLH protocol
- `bengal/rendering/parsers/patitas/wrapper.py` — Current wrapper implementation
- `bengal/rendering/parsers/patitas/renderers/html.py` — HTML renderer
- `bengal/rendering/pipeline/core.py` — RenderingPipeline
