# RFC: ContextVar Configuration Pattern - Bengal Implementation

**Status**: ✅ Implemented  
**Created**: 2026-01-13  
**Implemented**: 2026-01-13  
**Depends on**: `patitas/plan/rfc-contextvar-config.md`, `rfc-contextvar-config-analysis.md`  
**Benchmark Validated**: ✅ Parser 1.99x, Renderer 1.31x speedup (Python 3.12.2, 100K iterations)  
**Extended by**: `rfc-contextvar-downstream-patterns.md` (✅ Implemented)

---

## Executive Summary

Implement the ContextVar configuration pattern for Bengal's embedded Patitas components:

| Component | Speedup | Slot Reduction | Priority |
|-----------|---------|----------------|----------|
| **Parser** | 1.99x | 50% (18→9) | Phase 2 |
| **HTMLRenderer** | 1.31x | 50% (14→7) | Phase 3 |
| **Lexer** | ~2.0x (est.) | 47% (19→10) | Future |

**Combined Benefit**: ~0.23ms saved per 1K pages (instantiation) + smaller memory footprint.

---

## Synchronization Strategy

Bengal embeds a copy of Patitas (not a pip dependency). The standalone Patitas RFC has been implemented. This RFC:

1. **Aligns** Bengal's embedded copy with the standalone Patitas pattern
2. **Extends** the pattern with `RenderConfig` (Bengal-specific, not in standalone Patitas)
3. **Maintains** API compatibility with Bengal's `PatitasParser` wrapper

**Future**: Consider extracting Patitas as a shared dependency to avoid drift.

---

## 1. Current Architecture

### Parser (`bengal/rendering/parsers/patitas/parser.py`)

```python
class Parser:
    __slots__ = (
        # Per-parse state (9 slots) - KEEP
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
        
        # Configuration (9 slots) - EXTRACT TO ContextVar
        "_text_transformer",
        "_tables_enabled",
        "_strikethrough_enabled",
        "_task_lists_enabled",
        "_footnotes_enabled",
        "_math_enabled",
        "_autolinks_enabled",
        "_directive_registry",
        "_strict_contracts",
    )  # 18 slots total
```

### HTMLRenderer (`bengal/rendering/parsers/patitas/renderers/html.py`)

```python
class HtmlRenderer:
    __slots__ = (
        # Per-render state (7 slots) - KEEP
        "_source",
        "_delegate",
        "_headings",
        "_seen_slugs",
        "_page_context",
        "_current_page",
        "_directive_cache",      # Per-site cache, passed in (not config)
        
        # Configuration (7 slots) - EXTRACT TO ContextVar
        "_highlight",
        "_highlight_style",
        "_directive_registry",
        "_role_registry",
        "_text_transformer",
        "_slugify",
        "_rosettes_available",   # Import check - computed once, config-like
    )  # 14 slots total
```

**Design Decisions**:

| Attribute | Classification | Rationale |
|-----------|---------------|-----------|
| `_directive_cache` | **Per-render** (kept) | Injected per-site, not global config |
| `_rosettes_available` | **Config** (extracted) | Import check computed once at startup |

---

## 2. Proposed Design

### 2.1 ParseConfig (Mirrors Patitas RFC)

**File**: `bengal/rendering/parsers/patitas/config.py`

```python
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.directives import DirectiveRegistry

@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Immutable parse configuration.
    
    Set once per Markdown instance, read by all parsers in the context.
    Frozen dataclass ensures thread-safety (immutable after creation).
    """
    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: DirectiveRegistry | None = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None


# Module-level default (singleton, never recreated)
_DEFAULT_PARSE_CONFIG: ParseConfig = ParseConfig()

# Thread-local configuration
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=_DEFAULT_PARSE_CONFIG
)


def get_parse_config() -> ParseConfig:
    """Get current parse configuration (thread-local)."""
    return _parse_config.get()


def set_parse_config(config: ParseConfig) -> Token[ParseConfig]:
    """Set parse configuration for current context.
    
    Returns a token that can be used to restore the previous value.
    """
    return _parse_config.set(config)


def reset_parse_config(token: Token[ParseConfig] | None = None) -> None:
    """Reset parse configuration.
    
    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to the default configuration.
    """
    if token is not None:
        _parse_config.reset(token)
    else:
        _parse_config.set(_DEFAULT_PARSE_CONFIG)


@contextmanager
def parse_config_context(config: ParseConfig) -> Iterator[ParseConfig]:
    """Context manager for scoped parse configuration.
    
    Properly restores previous config on exit (supports nesting).
    
    Usage:
        with parse_config_context(ParseConfig(tables_enabled=True)) as cfg:
            parser = Parser(source)
            # cfg.tables_enabled is True
    """
    token = set_parse_config(config)
    try:
        yield config
    finally:
        reset_parse_config(token)
```

### 2.2 RenderConfig (New for Bengal)

**File**: `bengal/rendering/parsers/patitas/render_config.py`

```python
from __future__ import annotations

from contextvars import ContextVar, Token
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterator, Literal

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.directives import DirectiveRegistry
    from bengal.rendering.parsers.patitas.roles import RoleRegistry


def _check_rosettes_available() -> bool:
    """Check if rosettes syntax highlighter is available (computed once)."""
    try:
        import rosettes
        return True
    except ImportError:
        return False


# Module-level singleton for rosettes availability (computed once at import)
_ROSETTES_AVAILABLE: bool = _check_rosettes_available()


@dataclass(frozen=True, slots=True)
class RenderConfig:
    """Immutable render configuration.
    
    Set once per render context, read by all renderers.
    Frozen dataclass ensures thread-safety.
    
    Note: rosettes_available uses a factory default to capture
    module-level import check result.
    """
    highlight: bool = False
    highlight_style: Literal["semantic", "pygments"] = "semantic"
    directive_registry: DirectiveRegistry | None = None
    role_registry: RoleRegistry | None = None
    text_transformer: Callable[[str], str] | None = None
    slugify: Callable[[str], str] | None = None
    rosettes_available: bool = field(default_factory=lambda: _ROSETTES_AVAILABLE)


# Module-level default (singleton)
_DEFAULT_RENDER_CONFIG: RenderConfig = RenderConfig()

# Thread-local configuration
_render_config: ContextVar[RenderConfig] = ContextVar(
    'render_config',
    default=_DEFAULT_RENDER_CONFIG
)


def get_render_config() -> RenderConfig:
    """Get current render configuration (thread-local)."""
    return _render_config.get()


def set_render_config(config: RenderConfig) -> Token[RenderConfig]:
    """Set render configuration for current context.
    
    Returns a token that can be used to restore the previous value.
    """
    return _render_config.set(config)


def reset_render_config(token: Token[RenderConfig] | None = None) -> None:
    """Reset render configuration.
    
    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to the default configuration.
    """
    if token is not None:
        _render_config.reset(token)
    else:
        _render_config.set(_DEFAULT_RENDER_CONFIG)


@contextmanager
def render_config_context(config: RenderConfig) -> Iterator[RenderConfig]:
    """Context manager for scoped render configuration.
    
    Properly restores previous config on exit (supports nesting).
    
    Usage:
        with render_config_context(RenderConfig(highlight=True)) as cfg:
            renderer = HtmlRenderer(source)
            # cfg.highlight is True
    """
    token = set_render_config(config)
    try:
        yield config
    finally:
        reset_render_config(token)
```

### 2.3 Refactored Parser

```python
# bengal/rendering/parsers/patitas/parser.py

from bengal.rendering.parsers.patitas.config import get_parse_config, ParseConfig

class Parser:
    __slots__ = (
        # Per-parse state only (9 slots)
        "_source",
        "_tokens",
        "_pos",
        "_current",
        "_source_file",
        "_directive_stack",
        "_link_refs",
        "_containers",
        "_allow_setext_headings",
    )
    
    def __init__(
        self,
        source: str,
        source_file: str | None = None,
    ) -> None:
        """Initialize parser with source text only.
        
        Configuration is read from ContextVar, not passed as parameters.
        """
        self._source = source
        self._source_file = source_file
        self._tokens: list = []
        self._pos = 0
        self._current = None
        self._directive_stack: list = []
        self._link_refs: dict = {}
        self._containers = ContainerStack()
        self._allow_setext_headings = True
    
    # Config access via properties (cached reference pattern)
    @property
    def _config(self) -> ParseConfig:
        return get_parse_config()
    
    @property
    def _tables_enabled(self) -> bool:
        return self._config.tables_enabled
    
    @property
    def _strikethrough_enabled(self) -> bool:
        return self._config.strikethrough_enabled
    
    @property
    def _task_lists_enabled(self) -> bool:
        return self._config.task_lists_enabled
    
    @property
    def _footnotes_enabled(self) -> bool:
        return self._config.footnotes_enabled
    
    @property
    def _math_enabled(self) -> bool:
        return self._config.math_enabled
    
    @property
    def _autolinks_enabled(self) -> bool:
        return self._config.autolinks_enabled
    
    @property
    def _directive_registry(self):
        return self._config.directive_registry
    
    @property
    def _strict_contracts(self) -> bool:
        return self._config.strict_contracts
    
    @property
    def _text_transformer(self):
        return self._config.text_transformer
```

### 2.4 Refactored HTMLRenderer

```python
# bengal/rendering/parsers/patitas/renderers/html.py

from bengal.rendering.parsers.patitas.render_config import get_render_config, RenderConfig

class HtmlRenderer:
    __slots__ = (
        # Per-render state only (7 slots)
        "_source",
        "_delegate",
        "_headings",
        "_seen_slugs",
        "_page_context",
        "_current_page",
        "_directive_cache",
    )
    
    def __init__(
        self,
        source: str = "",
        *,
        delegate: LexerDelegate | None = None,
        page_context: Any | None = None,
        directive_cache: DirectiveCache | None = None,
    ) -> None:
        """Initialize renderer with source and per-render state only.
        
        Configuration is read from ContextVar.
        """
        self._source = source
        self._delegate = delegate
        self._headings: list = []
        self._seen_slugs: set = set()
        self._page_context = page_context
        self._current_page = page_context
        self._directive_cache = directive_cache
    
    # Config access via properties (all read from ContextVar)
    @property
    def _config(self) -> RenderConfig:
        return get_render_config()
    
    @property
    def _highlight(self) -> bool:
        return self._config.highlight
    
    @property
    def _highlight_style(self) -> str:
        return self._config.highlight_style
    
    @property
    def _directive_registry(self):
        return self._config.directive_registry
    
    @property
    def _role_registry(self):
        return self._config.role_registry
    
    @property
    def _text_transformer(self):
        return self._config.text_transformer
    
    @property
    def _slugify(self):
        return self._config.slugify
    
    @property
    def _rosettes_available(self) -> bool:
        """Check if rosettes highlighter is available (from config)."""
        return self._config.rosettes_available
```

### 2.5 Integration Point: PatitasParser Wrapper

**File**: `bengal/rendering/parsers/patitas/wrapper.py`

```python
from bengal.rendering.parsers.patitas.config import (
    ParseConfig, set_parse_config, reset_parse_config
)
from bengal.rendering.parsers.patitas.render_config import (
    RenderConfig, set_render_config, reset_render_config
)

class PatitasParser(BaseMarkdownParser):
    """Parser using Patitas library (modern Markdown parser)."""
    
    def __init__(
        self,
        *,
        plugins: list[str] | None = None,
        directive_registry: DirectiveRegistry | None = None,
        role_registry: RoleRegistry | None = None,
        highlight: bool = False,
        highlight_style: str = "semantic",
        text_transformer: Callable[[str], str] | None = None,
        slugify: Callable[[str], str] | None = None,
    ) -> None:
        self._plugins = plugins or []
        
        # Build immutable configs once (reused for all parses)
        self._parse_config = ParseConfig(
            tables_enabled="tables" in self._plugins,
            strikethrough_enabled="strikethrough" in self._plugins,
            task_lists_enabled="task_lists" in self._plugins,
            footnotes_enabled="footnotes" in self._plugins,
            math_enabled="math" in self._plugins,
            autolinks_enabled="autolinks" in self._plugins,
            directive_registry=directive_registry,
            text_transformer=text_transformer,
        )
        
        self._render_config = RenderConfig(
            highlight=highlight,
            highlight_style=highlight_style,
            directive_registry=directive_registry,
            role_registry=role_registry,
            text_transformer=text_transformer,
            slugify=slugify,
            # rosettes_available uses default (computed at module import)
        )
    
    def parse(self, content: str, source_file: str | None = None) -> str:
        """Parse markdown to HTML.
        
        Uses token-based ContextVar reset for proper nesting support.
        """
        # Set configs for this parse (thread-local), capture tokens
        parse_token = set_parse_config(self._parse_config)
        render_token = set_render_config(self._render_config)
        
        try:
            # Parse to AST
            parser = Parser(content, source_file)
            doc = parser.parse()
            
            # Render to HTML
            renderer = HtmlRenderer(content)
            return renderer.render(doc)
        finally:
            # Restore previous configs (supports nesting)
            reset_parse_config(parse_token)
            reset_render_config(render_token)
```

**Why Token-Based Reset?**

The token pattern from PEP 567 properly handles nested contexts:

```python
# Without tokens (incorrect for nesting)
set_parse_config(ConfigA)
    set_parse_config(ConfigB)  # Nested
    reset_parse_config()        # Resets to DEFAULT, not ConfigA! ❌

# With tokens (correct)
token_a = set_parse_config(ConfigA)
    token_b = set_parse_config(ConfigB)
    reset_parse_config(token_b)  # Restores ConfigA ✅
reset_parse_config(token_a)      # Restores DEFAULT ✅
```

Bengal's current usage doesn't nest, but the pattern is correct and future-proof.

---

## 3. Thread Safety Analysis

### ContextVar Guarantees

```python
# Thread 1                              Thread 2
set_parse_config(ConfigA)               set_parse_config(ConfigB)
set_render_config(RenderConfigA)        set_render_config(RenderConfigB)
parser1 = Parser(src1)                  parser2 = Parser(src2)
parser1._math_enabled  # → ConfigA      parser2._math_enabled  # → ConfigB
```

ContextVars are **thread-local by design**:
- Each thread has independent storage
- Bengal's ThreadPoolExecutor parallel rendering is safe
- No locks needed, no race conditions

### Validation Test

```python
def test_thread_isolation():
    """Verify config isolation across Bengal worker threads."""
    from concurrent.futures import ThreadPoolExecutor
    
    results = {}
    
    def worker(thread_id: int, parse_cfg: ParseConfig, render_cfg: RenderConfig):
        set_parse_config(parse_cfg)
        set_render_config(render_cfg)
        
        parser = Parser("# Test")
        renderer = HtmlRenderer("<p>Test</p>")
        
        results[thread_id] = {
            "tables": parser._tables_enabled,
            "highlight": renderer._highlight,
        }
    
    configs = [
        (ParseConfig(tables_enabled=True), RenderConfig(highlight=True)),
        (ParseConfig(tables_enabled=False), RenderConfig(highlight=True)),
        (ParseConfig(tables_enabled=True), RenderConfig(highlight=False)),
        (ParseConfig(tables_enabled=False), RenderConfig(highlight=False)),
    ]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(worker, i, pc, rc)
            for i, (pc, rc) in enumerate(configs)
        ]
        for f in futures:
            f.result()
    
    # Verify each thread saw its own config
    assert results[0] == {"tables": True, "highlight": True}
    assert results[1] == {"tables": False, "highlight": True}
    assert results[2] == {"tables": True, "highlight": False}
    assert results[3] == {"tables": False, "highlight": False}
```

---

## 4. Migration Path

### Phase 1: Foundation (Day 1)

**Goal**: Add config infrastructure without breaking changes.

- [ ] Create `bengal/rendering/parsers/patitas/config.py`
  - [ ] `ParseConfig` frozen dataclass
  - [ ] `_DEFAULT_PARSE_CONFIG` singleton
  - [ ] `_parse_config` ContextVar
  - [ ] `get_parse_config()`, `set_parse_config()`, `reset_parse_config()` with token support
  - [ ] `parse_config_context()` context manager

- [ ] Create `bengal/rendering/parsers/patitas/render_config.py`
  - [ ] `RenderConfig` frozen dataclass with `rosettes_available` field
  - [ ] `_ROSETTES_AVAILABLE` module-level singleton (computed once at import)
  - [ ] `_DEFAULT_RENDER_CONFIG` singleton
  - [ ] `_render_config` ContextVar
  - [ ] `get_render_config()`, `set_render_config()`, `reset_render_config()` with token support
  - [ ] `render_config_context()` context manager

- [ ] Run benchmark to validate performance claims
- [ ] Add thread isolation tests
- [ ] Add nesting tests (verify token-based reset)

**Exit Criteria**: New modules exist, benchmarks pass, tests pass.

---

### Phase 2: Parser Refactor (Day 1-2)

**Goal**: Refactor Parser to use ContextVar config.

- [ ] Add property accessors to Parser:
  - [ ] `_config` → `get_parse_config()`
  - [ ] `_tables_enabled` → `self._config.tables_enabled`
  - [ ] `_strikethrough_enabled` → `self._config.strikethrough_enabled`
  - [ ] `_task_lists_enabled` → `self._config.task_lists_enabled`
  - [ ] `_footnotes_enabled` → `self._config.footnotes_enabled`
  - [ ] `_math_enabled` → `self._config.math_enabled`
  - [ ] `_autolinks_enabled` → `self._config.autolinks_enabled`
  - [ ] `_directive_registry` → `self._config.directive_registry`
  - [ ] `_strict_contracts` → `self._config.strict_contracts`
  - [ ] `_text_transformer` → `self._config.text_transformer`

- [ ] Remove config slots from `__slots__`

- [ ] Update `__init__()` signature (remove config params)

- [ ] Update sub-parser creation in `_parse_nested_content()`:
  ```python
  # Before: Manual config copying
  sub_parser._tables_enabled = self._tables_enabled
  # ... 6 more lines
  
  # After: Automatic via ContextVar
  sub_parser = Parser(content, self._source_file)
  ```

- [ ] Update mixin Protocols if needed

- [ ] Run full test suite

**Exit Criteria**: Parser slots reduced 18→9, all tests pass.

---

### Phase 3: HTMLRenderer Refactor (Day 2)

**Goal**: Refactor HTMLRenderer to use ContextVar config.

- [ ] Add property accessors to HtmlRenderer:
  - [ ] `_config` → `get_render_config()`
  - [ ] `_highlight` → `self._config.highlight`
  - [ ] `_highlight_style` → `self._config.highlight_style`
  - [ ] `_directive_registry` → `self._config.directive_registry`
  - [ ] `_role_registry` → `self._config.role_registry`
  - [ ] `_text_transformer` → `self._config.text_transformer`
  - [ ] `_slugify` → `self._config.slugify`
  - [ ] `_rosettes_available` → `self._config.rosettes_available`

- [ ] Remove config slots from `__slots__` (7 slots removed)

- [ ] Remove `_check_rosettes()` method (moved to config module)

- [ ] Update `__init__()` signature (remove config params)

- [ ] Run full test suite

**Exit Criteria**: HTMLRenderer slots reduced 14→7, all tests pass.

---

### Phase 4: PatitasParser Integration (Day 2)

**Goal**: Update wrapper to set/reset ContextVars.

- [ ] Update `PatitasParser.__init__()`:
  - [ ] Build `ParseConfig` from plugins
  - [ ] Build `RenderConfig` from parameters

- [ ] Update `PatitasParser.parse()`:
  - [ ] Set both configs at start
  - [ ] Add try/finally with reset

- [ ] Update `PatitasParser.render_ast()` if applicable

- [ ] Verify thread-local caching still works in `get_thread_parser()`

**Exit Criteria**: PatitasParser wrapper correctly manages ContextVars.

---

### Phase 5: Validation & Cleanup (Day 3)

**Goal**: Comprehensive validation and documentation.

- [ ] Run full test suite
- [ ] Run CommonMark compliance tests (if applicable)
- [ ] Benchmark before/after on real site (1K+ pages)
- [ ] Run parallel build tests (verify thread isolation)
- [ ] Update docstrings
- [ ] Update type hints
- [ ] Remove any deprecated code paths

**Exit Criteria**: All tests pass, benchmarks show improvement.

---

## 5. Files to Modify

| File | Changes |
|------|---------|
| `bengal/rendering/parsers/patitas/config.py` | **NEW** - ParseConfig + ContextVar + context manager |
| `bengal/rendering/parsers/patitas/render_config.py` | **NEW** - RenderConfig + ContextVar + rosettes check + context manager |
| `bengal/rendering/parsers/patitas/parser.py` | Remove 9 slots, add 10 properties |
| `bengal/rendering/parsers/patitas/renderers/html.py` | Remove 7 slots, add 8 properties, remove `_check_rosettes()` |
| `bengal/rendering/parsers/patitas/wrapper.py` | Set/reset ContextVars with token pattern |
| `bengal/rendering/parsers/patitas/parsing/blocks/*.py` | Remove config param passing |
| `tests/unit/rendering/parsers/patitas/*.py` | Use `parse_config_context()` and `render_config_context()` |

---

## 6. Risks and Mitigations

### Risk 1: ContextVar Not Set

**Problem**: Parser/Renderer used without config set.

**Mitigation**: Default configs are sensible (all extensions disabled):
```python
_parse_config: ContextVar[ParseConfig] = ContextVar(
    'parse_config',
    default=_DEFAULT_PARSE_CONFIG  # Safe defaults
)
```

**Severity**: Low

---

### Risk 2: Config Leaking Between Parses

**Problem**: Previous parse's config affects next parse.

**Mitigation**: Always use token-based try/finally:
```python
parse_token = set_parse_config(self._parse_config)
render_token = set_render_config(self._render_config)
try:
    return self._do_parse(content)
finally:
    reset_parse_config(parse_token)
    reset_render_config(render_token)
```

**Severity**: Low with token-based try/finally

---

### Risk 3: Property Access in Hot Paths

**Problem**: Config checks in tight loops may slow parsing.

**Mitigation**: Cache config reference in methods with many accesses:
```python
def _parse_paragraph(self, lines: list[str]) -> Block:
    config = self._config  # Single ContextVar lookup
    if config.tables_enabled and len(lines) >= 2:
        ...
```

**Severity**: Low (ContextVar lookup is 57.8M ops/sec)

---

### Risk 4: Breaking Tests

**Problem**: Tests that create Parser directly without ContextVar setup.

**Mitigation**: Use built-in context managers:
```python
def test_tables():
    with parse_config_context(ParseConfig(tables_enabled=True)) as cfg:
        parser = Parser("| a | b |")
        assert parser._tables_enabled == cfg.tables_enabled

def test_highlighting():
    with render_config_context(RenderConfig(highlight=True)):
        renderer = HtmlRenderer("<p>test</p>")
        assert renderer._highlight is True
```

**Severity**: Medium (need to update test patterns)

---

### Risk 5: Thread-Local Cache Interaction

**Problem**: Bengal's `get_thread_parser()` caches parser per thread.

**Mitigation**: Thread-local cache is orthogonal to ContextVar config:
- Cache stores parser instances
- ContextVar stores config
- Each parse call sets its own config

**Severity**: Low

---

### Risk 6: Rosettes Import at Module Load

**Problem**: Moving `_check_rosettes()` to module-level means the import check happens at module import time, not lazily.

**Mitigation**: 
- Import check is fast (~1µs)
- Only happens once per Python interpreter
- Fail-safe: defaults to `False` if import fails
- Can be overridden in `RenderConfig(rosettes_available=True)` for testing

**Severity**: Low

---

### Risk 7: Token Loss in Exception Handlers

**Problem**: If code between `set_*_config()` and `try:` raises, token is lost.

**Mitigation**: Capture token inline with set:
```python
# Good: token captured immediately
parse_token = set_parse_config(self._parse_config)
try:
    ...
finally:
    reset_parse_config(parse_token)
```

**Severity**: Low (pattern is simple and correct)

---

## 7. Success Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Parser slots | 18 | 9 | `grep __slots__` |
| HTMLRenderer slots | 14 | 7 | `grep __slots__` |
| Parser instantiation | 35.8ms/100K | <20ms/100K | `benchmarks/test_contextvar_config.py` |
| Renderer instantiation | 22.9ms/100K | <18ms/100K | `benchmarks/test_contextvar_config.py` |
| Test suite | Pass | Pass | `pytest` |
| Thread isolation | N/A | Pass | `test_thread_isolation()` |
| Nesting support | N/A | Pass | `test_config_nesting()` |

---

## 8. Implementation Checklist

### Phase 1: Foundation
- [ ] Create `config.py` with `ParseConfig`
  - [ ] Frozen dataclass with slots
  - [ ] Token-based `set_parse_config()` / `reset_parse_config()`
  - [ ] `parse_config_context()` context manager
- [ ] Create `render_config.py` with `RenderConfig`
  - [ ] Frozen dataclass with slots
  - [ ] `_ROSETTES_AVAILABLE` module singleton
  - [ ] Token-based `set_render_config()` / `reset_render_config()`
  - [ ] `render_config_context()` context manager
- [ ] Validate benchmarks
- [ ] Add thread isolation tests
- [ ] Add nesting tests (token-based reset)

### Phase 2: Parser
- [ ] Add 10 property accessors
- [ ] Remove 9 config slots
- [ ] Update `__init__()` signature
- [ ] Simplify sub-parser creation
- [ ] Run test suite

### Phase 3: HTMLRenderer
- [ ] Add 8 property accessors (including `_rosettes_available`)
- [ ] Remove 7 config slots
- [ ] Remove `_check_rosettes()` method
- [ ] Update `__init__()` signature
- [ ] Run test suite

### Phase 4: Integration
- [ ] Update `PatitasParser` wrapper
- [ ] Use token-based try/finally pattern
- [ ] Verify thread-local caching
- [ ] Update `render_ast()` if applicable

### Phase 5: Validation
- [ ] Full test suite
- [ ] Parallel build tests
- [ ] Real site benchmark (1K+ pages)
- [ ] Update docstrings and type hints
- [ ] Remove deprecated code paths

---

## 9. Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Foundation | 0.5 day | None |
| Phase 2: Parser | 0.5 day | Phase 1 |
| Phase 3: HTMLRenderer | 0.5 day | Phase 1 |
| Phase 4: Integration | 0.5 day | Phase 2, 3 |
| Phase 5: Validation | 1 day | Phase 4 |
| **Total** | **3 days** | |

---

## 10. Future Work

### Lexer ContextVar Pattern (Not in Scope)

The Lexer has similar potential for slot reduction:

| Metric | Current | After | Improvement |
|--------|---------|-------|-------------|
| Slots | 19 | ~10 | 47% |
| Speedup | — | ~2.0x (estimated) | — |

**Why Not Now**:
- Lexer is instantiated once per parse (less frequent than Parser/Renderer)
- Parser delegates to Lexer, so Lexer config would need coordination
- Smaller impact (Lexer instantiation is ~5ms/100K)

**Recommendation**: Evaluate after Parser/Renderer are complete.

---

## 11. Decision Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Token-based reset | Proper nesting support per PEP 567 | Simple reset (would break nesting) |
| `_rosettes_available` in config | Import check is config-like (computed once) | Keep in slots (per-render check wasteful) |
| `_directive_cache` in slots | Per-site cache, injected externally | Move to config (would require site context in config) |
| Frozen dataclass | Thread-safety, immutability | Regular class (would need synchronization) |
| Context managers | Clean test patterns | Manual set/reset (error-prone) |

---

## 12. References

- `patitas/plan/rfc-contextvar-config.md` — Original pattern design (Status: Implemented)
- `patitas/plan/rfc-free-threading-patterns.md` — Thread safety validation
- `bengal/plan/rfc-contextvar-config-analysis.md` — Bengal-specific analysis with benchmarks
- `bengal/benchmarks/test_contextvar_config.py` — Benchmark validation script
- [PEP 567: Context Variables](https://peps.python.org/pep-0567/) — Python specification
