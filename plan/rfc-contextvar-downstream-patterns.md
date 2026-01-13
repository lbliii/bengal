# RFC: ContextVar Downstream Patterns

**Status**: Draft  
**Created**: 2026-01-13  
**Depends on**: `rfc-contextvar-config-implementation.md` (✅ Implemented)  
**Target**: Bengal 0.2.x

---

## Executive Summary

The ContextVar configuration pattern (now implemented) decoupled configuration from instance state. This RFC proposes three downstream patterns that leverage this architectural change:

| Pattern | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Parser/Renderer Pooling** | Low | ~20% faster instantiation | P1 |
| **Render Accumulator** | Medium | ~30% faster (single-pass TOC) | P1 |
| **Request-Scoped Context** | Medium | Cleaner architecture | P2 |

**Combined Benefit**: Estimated 15-25% reduction in per-page render time for large sites.

---

## Motivation

With ContextVar handling configuration, Parser and HtmlRenderer instances are now:

1. **Lightweight** - Only 9 and 7 slots respectively (down from 18 and 14)
2. **Stateless** (config-wise) - Config read from ContextVar, not instance
3. **Reusable** - No config state to reset between uses

These properties unlock patterns that were previously impractical.

---

## Pattern 1: Parser/Renderer Pooling

### Problem

Bengal creates new Parser and HtmlRenderer instances per page:

```python
# Current: New instance per page (rendering/pipeline/core.py)
for page in pages:
    parser = Parser(page.content)      # Allocate
    ast = parser.parse()
    renderer = HtmlRenderer()          # Allocate
    html = renderer.render(ast, page.content)
    # Instances discarded, GC'd later
```

For a 1,000-page site, that's 2,000 allocations + GC pressure.

### Solution

Pool and reuse instances:

```python
# bengal/rendering/parsers/patitas/pool.py
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from threading import local
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.parser import Parser
    from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer


class ParserPool:
    """Thread-local parser instance pool.
    
    Reuses Parser instances to avoid allocation overhead.
    Thread-safe via thread-local storage.
    """
    
    _local = local()
    _max_pool_size: int = 8  # Per thread
    
    @classmethod
    def _get_pool(cls) -> deque[Parser]:
        if not hasattr(cls._local, 'pool'):
            cls._local.pool = deque(maxlen=cls._max_pool_size)
        return cls._local.pool
    
    @classmethod
    @contextmanager
    def acquire(cls, source: str, source_file: str | None = None) -> Iterator[Parser]:
        """Acquire a parser from pool or create new one.
        
        Usage:
            with ParserPool.acquire(content) as parser:
                ast = parser.parse()
        """
        from bengal.rendering.parsers.patitas.parser import Parser
        
        pool = cls._get_pool()
        
        if pool:
            parser = pool.pop()
            parser._reinit(source, source_file)
        else:
            parser = Parser(source, source_file)
        
        try:
            yield parser
        finally:
            # Return to pool if not full
            if len(pool) < cls._max_pool_size:
                pool.append(parser)


class RendererPool:
    """Thread-local renderer instance pool."""
    
    _local = local()
    _max_pool_size: int = 8
    
    @classmethod
    def _get_pool(cls) -> deque[HtmlRenderer]:
        if not hasattr(cls._local, 'pool'):
            cls._local.pool = deque(maxlen=cls._max_pool_size)
        return cls._local.pool
    
    @classmethod
    @contextmanager
    def acquire(cls) -> Iterator[HtmlRenderer]:
        """Acquire a renderer from pool or create new one."""
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer
        
        pool = cls._get_pool()
        
        if pool:
            renderer = pool.pop()
            renderer._reset()
        else:
            renderer = HtmlRenderer()
        
        try:
            yield renderer
        finally:
            if len(pool) < cls._max_pool_size:
                pool.append(renderer)
```

### Required Changes

1. **Parser._reinit()** method to reset source without full __init__:

```python
# bengal/rendering/parsers/patitas/parser.py
class Parser:
    def _reinit(self, source: str, source_file: str | None = None) -> None:
        """Reset parser for reuse with new source."""
        self._source = source
        self._source_file = source_file
        self._tokens = tuple(self._lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None
        self._link_refs = {}
        self._containers = []
        self._directive_stack = []
        self._allow_setext_headings = True
```

2. **HtmlRenderer._reset()** method:

```python
# bengal/rendering/parsers/patitas/renderers/html.py
class HtmlRenderer:
    def _reset(self) -> None:
        """Reset renderer state for reuse."""
        self._source = ""
        self._headings = []
        self._seen_slugs = {}
        self._page_context = None
        self._current_page = None
```

### Integration

```python
# bengal/rendering/pipeline/core.py
from bengal.rendering.parsers.patitas.pool import ParserPool, RendererPool

def render_page(page: Page) -> str:
    with ParserPool.acquire(page.content, page.source_path) as parser:
        ast = parser.parse()
    
    with RendererPool.acquire() as renderer:
        html = renderer.render(ast, page.content)
    
    return html
```

### Benchmark Target

| Metric | Current | With Pooling | Improvement |
|--------|---------|--------------|-------------|
| 1K pages (instantiation) | ~2.3ms | ~0.5ms | ~78% |
| Memory (peak) | N instances | 8 per thread | ~90% reduction |

---

## Pattern 2: Render Accumulator (Single-Pass TOC/Footnotes)

### Problem

Currently, extracting TOC and footnotes requires separate passes:

```python
# Current multi-pass approach
ast = parser.parse()
html = renderer.render(ast, source)      # Pass 1: Render
toc = extract_toc(ast)                    # Pass 2: Walk AST again
footnotes = extract_footnotes(ast)        # Pass 3: Walk AST again
```

For documents with 100+ headings, this is wasteful.

### Solution

Accumulate metadata during rendering via ContextVar:

```python
# bengal/rendering/parsers/patitas/accumulator.py
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class TocItem:
    """Table of contents item."""
    level: int
    text: str
    id: str
    children: list[TocItem] = field(default_factory=list)


@dataclass
class FootnoteRef:
    """Footnote reference."""
    id: str
    content: str
    backref_id: str


@dataclass
class RenderAccumulator:
    """Accumulated state during rendering.
    
    Collects TOC items, footnotes, cross-references, and other
    metadata in a single rendering pass.
    """
    toc_items: list[TocItem] = field(default_factory=list)
    footnotes: dict[str, FootnoteRef] = field(default_factory=dict)
    cross_refs: list[tuple[str, str]] = field(default_factory=list)  # (target, text)
    word_count: int = 0
    has_code_blocks: bool = False
    has_math: bool = False
    
    def add_heading(self, level: int, text: str, id: str) -> None:
        """Record a heading for TOC generation."""
        self.toc_items.append(TocItem(level=level, text=text, id=id))
    
    def add_footnote(self, id: str, content: str, backref_id: str) -> None:
        """Record a footnote definition."""
        self.footnotes[id] = FootnoteRef(id=id, content=content, backref_id=backref_id)
    
    def build_toc_tree(self) -> list[TocItem]:
        """Convert flat TOC items to nested tree structure."""
        if not self.toc_items:
            return []
        
        root: list[TocItem] = []
        stack: list[tuple[int, list[TocItem]]] = [(0, root)]
        
        for item in self.toc_items:
            while stack and stack[-1][0] >= item.level:
                stack.pop()
            
            parent = stack[-1][1] if stack else root
            parent.append(item)
            stack.append((item.level, item.children))
        
        return root


# Module-level ContextVar
_accumulator: ContextVar[RenderAccumulator | None] = ContextVar(
    'render_accumulator', 
    default=None
)


def get_accumulator() -> RenderAccumulator | None:
    """Get current render accumulator (None if not in accumulator context)."""
    return _accumulator.get()


@contextmanager
def accumulator_context() -> Iterator[RenderAccumulator]:
    """Context manager for render accumulation.
    
    Usage:
        with accumulator_context() as acc:
            html = renderer.render(ast, source)
            toc = acc.build_toc_tree()
            footnotes = acc.footnotes
    """
    acc = RenderAccumulator()
    token = _accumulator.set(acc)
    try:
        yield acc
    finally:
        _accumulator.reset(token)
```

### Renderer Integration

```python
# bengal/rendering/parsers/patitas/renderers/html.py
from bengal.rendering.parsers.patitas.accumulator import get_accumulator

class HtmlRenderer:
    def _render_heading(self, node: Heading) -> str:
        text = self._render_children(node.children)
        slug = self._slugify(text)
        
        # Accumulate if in accumulator context
        acc = get_accumulator()
        if acc:
            acc.add_heading(level=node.level, text=text, id=slug)
        
        return f'<h{node.level} id="{slug}">{text}</h{node.level}>\n'
    
    def _render_fenced_code(self, node: FencedCode) -> str:
        acc = get_accumulator()
        if acc:
            acc.has_code_blocks = True
        
        # ... existing render logic
    
    def _render_math(self, node: Math) -> str:
        acc = get_accumulator()
        if acc:
            acc.has_math = True
        
        # ... existing render logic
```

### Integration with Pipeline

```python
# bengal/rendering/pipeline/core.py
from bengal.rendering.parsers.patitas.accumulator import accumulator_context

def render_page_with_metadata(page: Page) -> tuple[str, dict]:
    """Render page and extract metadata in single pass."""
    ast = parser.parse()
    
    with accumulator_context() as acc:
        html = renderer.render(ast, page.content)
        
        metadata = {
            'toc': acc.build_toc_tree(),
            'toc_html': render_toc(acc.build_toc_tree()),
            'footnotes': acc.footnotes,
            'word_count': acc.word_count,
            'has_code': acc.has_code_blocks,
            'has_math': acc.has_math,
        }
    
    return html, metadata
```

### Benchmark Target

| Metric | Current (3 passes) | Single Pass | Improvement |
|--------|-------------------|-------------|-------------|
| 100-heading doc | ~15ms | ~10ms | ~33% |
| Memory allocations | 3x AST walk | 1x | ~67% |

---

## Pattern 3: Request-Scoped Context

### Problem

Currently, per-parse information (source file, error handler, page context) is passed via parameters:

```python
# Current: Parameter drilling
parser = Parser(source, source_file=path)
renderer = HtmlRenderer()
renderer.render(ast, source, page_context=ctx, error_handler=handler)
```

This leads to:
- Long parameter lists
- Inconsistent availability (some methods have context, some don't)
- Hard to add new context without changing signatures

### Solution

Unify all per-request state in a single ContextVar:

```python
# bengal/rendering/parsers/patitas/request_context.py
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Per-request context for parsing and rendering.
    
    Provides access to build-wide and page-specific state
    without parameter drilling.
    """
    # Source information
    source_file: Path | None = None
    source_content: str = ""
    
    # Page context (for rendering)
    page: Page | None = None
    site: Site | None = None
    
    # Error handling
    error_handler: Callable[[Exception, str], None] | None = None
    strict_mode: bool = False
    
    # Link resolution
    link_resolver: Callable[[str], str | None] | None = None
    
    # Debug/profiling
    trace_enabled: bool = False
    
    def resolve_link(self, target: str) -> str | None:
        """Resolve a link target to URL."""
        if self.link_resolver:
            return self.link_resolver(target)
        return None
    
    def report_error(self, error: Exception, context: str) -> None:
        """Report an error with context."""
        if self.error_handler:
            self.error_handler(error, context)
        elif self.strict_mode:
            raise error


# Module-level ContextVar
_request_context: ContextVar[RequestContext] = ContextVar(
    'request_context',
    default=RequestContext()
)


def get_request_context() -> RequestContext:
    """Get current request context."""
    return _request_context.get()


def set_request_context(ctx: RequestContext) -> Token[RequestContext]:
    """Set request context, returns token for reset."""
    return _request_context.set(ctx)


def reset_request_context(token: Token[RequestContext] | None = None) -> None:
    """Reset to previous context."""
    if token:
        _request_context.reset(token)
    else:
        _request_context.set(RequestContext())


@contextmanager
def request_context(
    source_file: Path | None = None,
    source_content: str = "",
    page: Page | None = None,
    site: Site | None = None,
    error_handler: Callable[[Exception, str], None] | None = None,
    strict_mode: bool = False,
    link_resolver: Callable[[str], str | None] | None = None,
    trace_enabled: bool = False,
) -> Iterator[RequestContext]:
    """Context manager for request-scoped state.
    
    Usage:
        with request_context(source_file=path, page=page, site=site):
            html = render(page.content)
            # All nested code can access context via get_request_context()
    """
    ctx = RequestContext(
        source_file=source_file,
        source_content=source_content,
        page=page,
        site=site,
        error_handler=error_handler,
        strict_mode=strict_mode,
        link_resolver=link_resolver,
        trace_enabled=trace_enabled,
    )
    token = set_request_context(ctx)
    try:
        yield ctx
    finally:
        reset_request_context(token)
```

### Usage in Parser/Renderer

```python
# bengal/rendering/parsers/patitas/parser.py
from bengal.rendering.parsers.patitas.request_context import get_request_context

class Parser:
    def _report_error(self, error: Exception, context: str) -> None:
        """Report error via request context."""
        req = get_request_context()
        req.report_error(error, context)
    
    @property
    def source_file(self) -> Path | None:
        """Get source file from request context."""
        return get_request_context().source_file
```

```python
# bengal/rendering/parsers/patitas/renderers/html.py
class HtmlRenderer:
    def _resolve_link(self, target: str) -> str:
        """Resolve internal link via request context."""
        req = get_request_context()
        resolved = req.resolve_link(target)
        if resolved:
            return resolved
        
        # Fallback: return as-is
        return target
```

### Integration with Pipeline

```python
# bengal/rendering/pipeline/core.py
from bengal.rendering.parsers.patitas.request_context import request_context

def render_page(page: Page, site: Site) -> str:
    """Render page with full context."""
    
    def resolve_link(target: str) -> str | None:
        # Resolve {doc}`path` and {ref}`anchor` links
        return site.resolve_internal_link(target, page)
    
    with request_context(
        source_file=page.source_path,
        source_content=page.raw_content,
        page=page,
        site=site,
        link_resolver=resolve_link,
        strict_mode=site.config.strict,
    ):
        # All nested code can access context
        html = patitas_render(page.content)
    
    return html
```

---

## Implementation Phases

### Phase 1: Parser/Renderer Pooling (Low Risk)

1. Add `_reinit()` to Parser
2. Add `_reset()` to HtmlRenderer
3. Create pool module
4. Update pipeline to use pools
5. Benchmark

**Files Modified**:
- `bengal/rendering/parsers/patitas/parser.py`
- `bengal/rendering/parsers/patitas/renderers/html.py`
- `bengal/rendering/parsers/patitas/pool.py` (new)
- `bengal/rendering/pipeline/core.py`

**Estimated Effort**: 2-3 hours

### Phase 2: Render Accumulator (Medium Risk)

1. Create accumulator module
2. Instrument heading/footnote/math rendering
3. Update pipeline to use accumulator
4. Remove separate TOC extraction pass
5. Benchmark

**Files Modified**:
- `bengal/rendering/parsers/patitas/accumulator.py` (new)
- `bengal/rendering/parsers/patitas/renderers/html.py`
- `bengal/rendering/pipeline/core.py`
- `bengal/rendering/pipeline/toc.py` (deprecate multi-pass)

**Estimated Effort**: 4-6 hours

### Phase 3: Request-Scoped Context (Medium Risk)

1. Create request_context module
2. Migrate source_file parameter
3. Migrate page_context parameter
4. Add link resolution
5. Add error handling
6. Update all call sites

**Files Modified**:
- `bengal/rendering/parsers/patitas/request_context.py` (new)
- `bengal/rendering/parsers/patitas/parser.py`
- `bengal/rendering/parsers/patitas/renderers/html.py`
- `bengal/rendering/pipeline/core.py`
- Various directive renderers

**Estimated Effort**: 6-8 hours

---

## Risk Assessment

| Pattern | Risk | Mitigation |
|---------|------|------------|
| Pooling | Low | Pools are per-thread, no shared state |
| Accumulator | Medium | Optional (check for None), gradual rollout |
| Request Context | Medium | Backward compatible defaults |

**Rollback Strategy**: All patterns are additive. Old code paths can remain as fallback during migration.

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Per-page instantiation | ~2.3µs | ~0.5µs | `benchmarks/test_patitas_performance.py` |
| TOC extraction (100 headings) | ~5ms | ~0ms (included) | `benchmarks/test_toc_extraction.py` |
| Parameter count (render) | 6 | 2 | Code inspection |
| Memory per 1K pages | N×(Parser+Renderer) | 16×(Parser+Renderer) | Memory profiler |

---

## Future Opportunities

These patterns unlock additional improvements:

1. **Immutable Parser** - With pooling, parsers could be frozen dataclasses
2. **Async Accumulator** - Accumulator pattern extends to async rendering
3. **Plugin ContextVar** - Same pattern for plugin/directive registration
4. **Distributed Rendering** - Request context serializable for worker processes

---

## Appendix: ContextVar Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ContextVar Architecture                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │  ParseConfig    │   │  RenderConfig   │   │ RequestContext  │       │
│  │  (implemented)  │   │  (implemented)  │   │ (this RFC)      │       │
│  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘       │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                     ContextVar Layer                         │       │
│  │  • Thread-isolated                                           │       │
│  │  • Async-safe                                                │       │
│  │  • Token-based nesting                                       │       │
│  └─────────────────────────────────────────────────────────────┘       │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │     Parser      │   │   HtmlRenderer  │   │  Accumulator    │       │
│  │  (lightweight)  │   │  (lightweight)  │   │  (this RFC)     │       │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘       │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                      Instance Pool                           │       │
│  │  • ParserPool (8 per thread)                                 │       │
│  │  • RendererPool (8 per thread)                               │       │
│  │  (this RFC)                                                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## References

- `rfc-contextvar-config-implementation.md` - ContextVar config pattern (✅ implemented)
- `patitas/plan/rfc-contextvar-config.md` - Upstream Patitas RFC
- Python PEP 567 - Context Variables
- Python 3.14t free-threading documentation
