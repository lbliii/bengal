# RFC: ContextVar Downstream Patterns

**Status**: ✅ Implemented  
**Created**: 2026-01-13  
**Updated**: 2026-01-13  
**Implemented**: 2026-01-13  
**Depends on**: `rfc-contextvar-config-implementation.md` (✅ Implemented)  
**Target**: Bengal 0.2.x

---

## Executive Summary

The ContextVar configuration pattern (now implemented) decoupled configuration from instance state. This RFC proposes three downstream patterns that leverage this architectural change:

| Pattern | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Parser/Renderer Pooling** | Low | ~15% faster instantiation | P1 |
| **Metadata Accumulator** | Low | Extended page metadata | P2 |
| **Request-Scoped Context** | Medium | Cleaner architecture | P2 |

**Combined Benefit**: Estimated 10-15% reduction in per-page render time for large sites, plus architectural improvements for maintainability.

**Note**: Single-pass TOC extraction already exists via `render_ast_with_toc()` (RFC: rfc-path-to-200-pgs). Pattern 2 extends this to collect additional metadata.

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

import os
from collections import deque
from contextlib import contextmanager
from threading import local
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from bengal.parsing.backends.patitas.parser import Parser
    from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer


# Pool size rationale:
# - 8 covers typical concurrent renders per thread (parallel template includes)
# - Memory overhead: ~1KB per Parser, ~0.5KB per Renderer = ~12KB per thread
# - Configurable via environment for tuning
_DEFAULT_POOL_SIZE = 8


class ParserPool:
    """Thread-local parser instance pool.
    
    Reuses Parser instances to avoid allocation overhead.
    Thread-safe via thread-local storage.
    
    Pool Size:
        Default: 8 per thread (covers typical parallel template includes)
        Override: Set BENGAL_PARSER_POOL_SIZE environment variable
        
    Memory: ~1KB per pooled Parser instance
    """
    
    _local = local()
    _max_pool_size: int = int(os.environ.get("BENGAL_PARSER_POOL_SIZE", _DEFAULT_POOL_SIZE))
    
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
        from bengal.parsing.backends.patitas.parser import Parser
        
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
    """Thread-local renderer instance pool.
    
    Pool Size:
        Default: 8 per thread
        Override: Set BENGAL_RENDERER_POOL_SIZE environment variable
        
    Memory: ~0.5KB per pooled Renderer instance
    """
    
    _local = local()
    _max_pool_size: int = int(os.environ.get("BENGAL_RENDERER_POOL_SIZE", _DEFAULT_POOL_SIZE))
    
    @classmethod
    def _get_pool(cls) -> deque[HtmlRenderer]:
        if not hasattr(cls._local, 'pool'):
            cls._local.pool = deque(maxlen=cls._max_pool_size)
        return cls._local.pool
    
    @classmethod
    @contextmanager
    def acquire(cls, source: str = "") -> Iterator[HtmlRenderer]:
        """Acquire a renderer from pool or create new one."""
        from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer
        
        pool = cls._get_pool()
        
        if pool:
            renderer = pool.pop()
            renderer._reset(source)
        else:
            renderer = HtmlRenderer(source)
        
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
        """Reset parser for reuse with new source.
        
        Avoids full __init__ overhead by reusing existing object.
        Lexer is re-created (lightweight) to tokenize new source.
        """
        from bengal.parsing.backends.patitas.lexer import Lexer
        from bengal.parsing.backends.patitas.parsing.containers import ContainerStack
        
        self._source = source
        self._source_file = source_file
        
        # Re-tokenize with new source (Lexer is lightweight)
        lexer = Lexer(source)
        self._tokens = list(lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None
        
        # Reset per-parse state
        self._link_refs = {}
        self._containers = ContainerStack()
        self._directive_stack = []
        self._allow_setext_headings = True
```

2. **HtmlRenderer._reset()** method:

```python
# bengal/rendering/parsers/patitas/renderers/html.py
class HtmlRenderer:
    def _reset(self, source: str = "") -> None:
        """Reset renderer state for reuse.
        
        Clears per-render state while preserving object identity.
        """
        self._source = source
        self._headings = []
        self._seen_slugs = {}
        self._page_context = None
        self._current_page = None
        self._delegate = None
        self._directive_cache = None
```

### Integration

```python
# bengal/rendering/pipeline/core.py
from bengal.parsing.backends.patitas.pool import ParserPool, RendererPool

def render_page(page: Page) -> str:
    with ParserPool.acquire(page.content, page.source_path) as parser:
        ast = parser.parse()
    
    with RendererPool.acquire(page.content) as renderer:
        html = renderer.render(ast)
    
    return html
```

### Benchmark Target

| Metric | Current | With Pooling | Improvement |
|--------|---------|--------------|-------------|
| 1K pages (instantiation) | ~2.3µs/page | ~0.5µs/page | ~78% |
| Total for 1K pages | ~2.3ms | ~0.5ms | ~1.8ms saved |
| Memory (peak) | N instances | 8 per thread | ~90% reduction |

**Note**: Instantiation is a small fraction of total render time (~2.3µs vs ~2-10ms for parsing+rendering). Primary benefit is reduced GC pressure for large sites.

---

## Pattern 2: Metadata Accumulator (Extended Page Metadata)

### Current State

Bengal already implements single-pass TOC extraction via `HtmlRenderer._headings` and `render_ast_with_toc()` (RFC: rfc-path-to-200-pgs):

```python
# Current: Single-pass TOC (already implemented)
html, toc, toc_items = md.render_ast_with_toc(ast, content)
```

### Problem

Additional page metadata requires post-render analysis or AST re-walking:

```python
# Current: Separate checks after rendering
has_math = '<math' in html or '\\(' in html  # Regex/string search
has_code = '<pre' in html                     # Imprecise
word_count = len(strip_html(html).split())    # Extra pass
```

### Solution

Extend the existing heading accumulation pattern to collect additional metadata during rendering:

```python
# bengal/rendering/parsers/patitas/accumulator.py
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class RenderMetadata:
    """Extended metadata accumulated during rendering.
    
    Complements existing HtmlRenderer._headings for TOC.
    Collected during single render pass—no post-processing needed.
    """
    # Content features (for asset loading decisions)
    has_math: bool = False
    has_code_blocks: bool = False
    has_mermaid: bool = False
    has_tables: bool = False
    
    # Statistics
    word_count: int = 0
    code_languages: set[str] = field(default_factory=set)
    
    # Cross-references (for dependency tracking)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    image_refs: list[str] = field(default_factory=list)
    
    def add_words(self, text: str) -> None:
        """Accumulate word count from text content."""
        self.word_count += len(text.split())
    
    def add_code_block(self, language: str | None) -> None:
        """Record a code block."""
        self.has_code_blocks = True
        if language:
            self.code_languages.add(language)
            if language == "mermaid":
                self.has_mermaid = True


# Module-level ContextVar
_metadata: ContextVar[RenderMetadata | None] = ContextVar(
    'render_metadata', 
    default=None
)


def get_metadata() -> RenderMetadata | None:
    """Get current metadata accumulator (None if not in context)."""
    return _metadata.get()


@contextmanager
def metadata_context() -> Iterator[RenderMetadata]:
    """Context manager for metadata accumulation.
    
    Usage:
        with metadata_context() as meta:
            html = renderer.render(ast)
            if meta.has_math:
                include_mathjax()
    """
    meta = RenderMetadata()
    token = _metadata.set(meta)
    try:
        yield meta
    finally:
        _metadata.reset(token)
```

### Renderer Integration

```python
# bengal/rendering/parsers/patitas/renderers/html.py
from bengal.parsing.backends.patitas.accumulator import get_metadata

class HtmlRenderer:
    def _render_text(self, node: Text) -> str:
        # Accumulate word count
        meta = get_metadata()
        if meta:
            meta.add_words(node.content)
        
        return html_escape(node.content)
    
    def _render_fenced_code(self, node: FencedCode) -> str:
        meta = get_metadata()
        if meta:
            meta.add_code_block(node.language)
        
        # ... existing render logic
    
    def _render_math(self, node: Math) -> str:
        meta = get_metadata()
        if meta:
            meta.has_math = True
        
        # ... existing render logic
    
    def _render_table(self, node: Table) -> str:
        meta = get_metadata()
        if meta:
            meta.has_tables = True
        
        # ... existing render logic
    
    def _render_link(self, node: Link) -> str:
        meta = get_metadata()
        if meta:
            if node.url.startswith(('http://', 'https://')):
                meta.external_links.append(node.url)
            else:
                meta.internal_links.append(node.url)
        
        # ... existing render logic
```

### Integration with Pipeline

```python
# bengal/rendering/pipeline/core.py
from bengal.parsing.backends.patitas.accumulator import metadata_context

def render_page_with_metadata(page: Page) -> tuple[str, dict]:
    """Render page and extract all metadata in single pass."""
    ast = parser.parse()
    
    with metadata_context() as meta:
        # TOC still collected via _headings (existing pattern)
        html, toc, toc_items = md.render_ast_with_toc(ast, page.content)
        
        # Extended metadata available immediately
        page_metadata = {
            'toc_items': toc_items,
            'has_math': meta.has_math,
            'has_code': meta.has_code_blocks,
            'has_mermaid': meta.has_mermaid,
            'word_count': meta.word_count,
            'code_languages': list(meta.code_languages),
            'internal_links': meta.internal_links,
        }
    
    return html, page_metadata
```

### Use Cases

| Metadata | Use Case |
|----------|----------|
| `has_math` | Conditionally load MathJax/KaTeX |
| `has_mermaid` | Conditionally load Mermaid.js |
| `code_languages` | Preload specific syntax highlighters |
| `word_count` | Reading time estimate |
| `internal_links` | Dependency graph for incremental builds |

### Benchmark Target

| Metric | Current | With Accumulator | Improvement |
|--------|---------|------------------|-------------|
| Feature detection | Post-render regex | During render | ~2ms saved |
| Word count | Extra strip+split | During render | ~1ms saved |
| Link extraction | Separate AST walk | During render | ~3ms saved |

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


class RequestContextError(RuntimeError):
    """Raised when request context is required but not set."""
    pass


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Per-request context for parsing and rendering.
    
    Provides access to build-wide and page-specific state
    without parameter drilling.
    
    Thread Safety:
        ContextVar provides automatic thread/async isolation.
        Each thread/task gets its own context stack.
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


# Module-level ContextVar - default to None for fail-fast behavior
_request_context: ContextVar[RequestContext | None] = ContextVar(
    'request_context',
    default=None
)


def get_request_context() -> RequestContext:
    """Get current request context.
    
    Raises:
        RequestContextError: If no context is set (fail-fast)
    """
    ctx = _request_context.get()
    if ctx is None:
        raise RequestContextError(
            "No request context set. Use request_context() context manager "
            "or set_request_context() before parsing/rendering."
        )
    return ctx


def try_get_request_context() -> RequestContext | None:
    """Get current request context, or None if not set.
    
    Use this for optional context access where fallback behavior is acceptable.
    """
    return _request_context.get()


def set_request_context(ctx: RequestContext) -> Token[RequestContext | None]:
    """Set request context, returns token for reset."""
    return _request_context.set(ctx)


def reset_request_context(token: Token[RequestContext | None]) -> None:
    """Reset to previous context using token."""
    _request_context.reset(token)


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
    
    Nesting:
        Context managers can be nested. Inner context shadows outer.
        Token-based reset restores previous context on exit.
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
from bengal.parsing.backends.patitas.request_context import try_get_request_context

class Parser:
    def _report_error(self, error: Exception, context: str) -> None:
        """Report error via request context if available."""
        req = try_get_request_context()
        if req:
            req.report_error(error, context)
        else:
            # Fallback: log warning
            logger.warning("parse_error", error=str(error), context=context)
    
    @property
    def source_file(self) -> Path | None:
        """Get source file from request context or instance."""
        # Prefer instance attribute (backward compatibility)
        if self._source_file:
            return Path(self._source_file)
        # Fall back to request context
        req = try_get_request_context()
        return req.source_file if req else None
```

```python
# bengal/rendering/parsers/patitas/renderers/html.py
from bengal.parsing.backends.patitas.request_context import try_get_request_context

class HtmlRenderer:
    def _resolve_link(self, target: str) -> str:
        """Resolve internal link via request context."""
        req = try_get_request_context()
        if req:
            resolved = req.resolve_link(target)
            if resolved:
                return resolved
        
        # Fallback: return as-is
        return target
```

### Integration with Pipeline

```python
# bengal/rendering/pipeline/core.py
from bengal.parsing.backends.patitas.request_context import request_context

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

## ContextVar Composition

All three ContextVar patterns (config, metadata, request) compose correctly:

```python
# Complete render pipeline with all ContextVars
from bengal.parsing.backends.patitas.config import parse_config_context, ParseConfig
from bengal.parsing.backends.patitas.render_config import render_config_context, RenderConfig
from bengal.parsing.backends.patitas.request_context import request_context
from bengal.parsing.backends.patitas.accumulator import metadata_context
from bengal.parsing.backends.patitas.pool import ParserPool, RendererPool

def render_page_full(page: Page, site: Site) -> tuple[str, dict]:
    """Full render with all optimizations."""
    
    # Layer 1: Configuration (per-site, set once)
    with parse_config_context(ParseConfig(tables_enabled=True)):
        with render_config_context(RenderConfig(highlight=True)):
            
            # Layer 2: Request context (per-page)
            with request_context(page=page, site=site):
                
                # Layer 3: Metadata accumulation (per-render)
                with metadata_context() as meta:
                    
                    # Layer 4: Pooled instances (per-render)
                    with ParserPool.acquire(page.content) as parser:
                        ast = parser.parse()
                    
                    with RendererPool.acquire(page.content) as renderer:
                        html = renderer.render(ast)
                    
                    return html, {
                        'has_math': meta.has_math,
                        'word_count': meta.word_count,
                    }
```

### Nesting Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ parse_config_context (per-site)                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ render_config_context (per-site)                        │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │ request_context (per-page)                      │   │   │
│   │   │   ┌─────────────────────────────────────────┐   │   │   │
│   │   │   │ metadata_context (per-render)           │   │   │   │
│   │   │   │   ┌─────────────────────────────────┐   │   │   │   │
│   │   │   │   │ ParserPool.acquire()            │   │   │   │   │
│   │   │   │   │ RendererPool.acquire()          │   │   │   │   │
│   │   │   │   └─────────────────────────────────┘   │   │   │   │
│   │   │   └─────────────────────────────────────────┘   │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
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

### Phase 2: Request-Scoped Context (Medium Risk)

1. Create request_context module
2. Add fail-fast `get_request_context()` and safe `try_get_request_context()`
3. Migrate source_file parameter (with backward compatibility)
4. Migrate page_context parameter
5. Add link resolution
6. Add error handling
7. Update call sites gradually

**Files Modified**:
- `bengal/rendering/parsers/patitas/request_context.py` (new)
- `bengal/rendering/parsers/patitas/parser.py`
- `bengal/rendering/parsers/patitas/renderers/html.py`
- `bengal/rendering/pipeline/core.py`
- Various directive renderers

**Estimated Effort**: 6-8 hours

### Phase 3: Metadata Accumulator (Low Risk)

1. Create accumulator module
2. Instrument code/math/table/link rendering
3. Update pipeline to use accumulator
4. Add conditional asset loading based on metadata

**Files Modified**:
- `bengal/rendering/parsers/patitas/accumulator.py` (new)
- `bengal/rendering/parsers/patitas/renderers/html.py`
- `bengal/rendering/pipeline/core.py`
- `bengal/rendering/template_functions/` (asset loading)

**Estimated Effort**: 3-4 hours

---

## Risk Assessment

| Pattern | Risk | Mitigation |
|---------|------|------------|
| Pooling | Low | Pools are per-thread, no shared state; `_reinit()` fully resets state |
| Request Context | Medium | `try_get_request_context()` for optional access; backward compatible |
| Metadata Accumulator | Low | Optional (check for None), no change to existing behavior |

**Rollback Strategy**: All patterns are additive. Old code paths can remain as fallback during migration.

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Per-page instantiation | ~2.3µs | ~0.5µs | `benchmarks/test_patitas_performance.py` |
| Feature detection (math/code) | ~2ms post-render | ~0ms | Included in render |
| Parameter count (render) | 6 | 2 | Code inspection |
| Memory per 1K pages | N×(Parser+Renderer) | 16×(Parser+Renderer) | Memory profiler |

---

## Future Opportunities

These patterns unlock additional improvements:

1. **Immutable Parser** - With pooling, parsers could be frozen dataclasses
2. **Async Accumulator** - Accumulator pattern extends to async rendering
3. **Plugin ContextVar** - Same pattern for plugin/directive registration
4. **Distributed Rendering** - Request context serializable for worker processes
5. **Conditional Asset Loading** - Use metadata to only load MathJax/Mermaid when needed

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
│  │     Parser      │   │   HtmlRenderer  │   │ RenderMetadata  │       │
│  │  (lightweight)  │   │  (lightweight)  │   │ (this RFC)      │       │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘       │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                      Instance Pool                           │       │
│  │  • ParserPool (8 per thread, configurable)                   │       │
│  │  • RendererPool (8 per thread, configurable)                 │       │
│  │  (this RFC)                                                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## References

- `rfc-contextvar-config-implementation.md` - ContextVar config pattern (✅ implemented)
- `rfc-path-to-200-pgs.md` - Single-pass TOC extraction (✅ implemented)
- `patitas/plan/rfc-contextvar-config.md` - Upstream Patitas RFC
- Python PEP 567 - Context Variables
- Python 3.14t free-threading documentation
