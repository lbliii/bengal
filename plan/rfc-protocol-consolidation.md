# RFC: Protocol Consolidation and Cross-Package Contracts

**Status**: Implemented  
**Created**: 2026-01-12  
**Author**: Bengal Team  
**Related**: `rfc-patitas-external-migration.md`, `rfc-rosettes-extraction.md`

---

## Executive Summary

As Bengal extracts core components into standalone packages (Kida, Rosettes, Patitas), the protocol system needs consolidation. This RFC proposes:

1. Removing protocol duplication
2. Creating bridge protocols for clean package boundaries (including Patitas handlers)
3. Aligning extracted package protocols with Bengal's expectations
4. Unifying ABC/Protocol patterns for infrastructure contracts
5. Mandating thread-safety and dependency constraints for the protocol layer

---

## Problem Statement

### 1. Protocol Duplication (Critical)

`SectionLike` is defined in two locations with **incompatible interfaces**:

```python
# bengal/core/section/protocols.py:36
@runtime_checkable
class SectionLike(Protocol):
    """Protocol for section-like objects."""
    name: str
    title: str
    path: Path | None          # <-- Path object, optional
    href: str
    pages: list[PageLike]
    subsections: list[SectionLike]  # <-- "subsections"
    parent: SectionLike | None
    index_page: PageLike | None
    is_root: bool

# bengal/orchestration/types.py:196
@runtime_checkable
class SectionLike(Protocol):
    """Protocol for section-like objects in menu building."""
    title: str
    pages: list[Page]
    children: list[Section]    # <-- "children" (different name!)
    path: str                  # <-- str (different type!)
```

**Impact**: Code using `section.subsections` will fail if given the orchestration version. Code expecting `path: str` will break with `Path | None`.

### 2. Misaligned Package Boundaries

Extracted packages define protocols that don't match Bengal's interface:

| Component | Bengal Expects | Package Provides | Gap |
|-----------|---------------|------------------|-----|
| Highlighting | `HighlightBackend.highlight(code, lang, hl_lines, show_linenos)` | Patitas: `Highlighter.__call__(code, lang)` | Missing `hl_lines`, `show_linenos` |
| Highlighting | `HighlightBackend.supports_language(lang)` | Patitas: Not present | Missing entirely |
| Highlighting | `HighlightBackend.name` property | Patitas: Not present | Missing entirely |
| Tokenization | Rosettes: `Lexer.tokenize()` + `Formatter.format()` | Bengal: monolithic `highlight()` | Composable vs. monolithic |

### 3. ABC vs Protocol Inconsistency

Infrastructure contracts use mixed patterns:

| Contract | Current Pattern | Location |
|----------|----------------|----------|
| `BaseMarkdownParser` | ABC | `bengal/rendering/parsers/base.py` |
| `ContentSource` | ABC | `bengal/content_layer/source.py` |
| `TemplateEngineProtocol` | Protocol | `bengal/rendering/engines/protocol.py` |
| `HighlightBackend` | Protocol | `bengal/rendering/highlighting/protocol.py` |
| `RoleHandler` | Protocol | `bengal/rendering/parsers/patitas/roles/protocol.py` |
| `DirectiveHandler` | Protocol | `bengal/rendering/parsers/patitas/directives/protocol.py` |

Both ABCs and Protocols work, but the inconsistency complicates documentation and understanding. Protocols are preferred for:
- Duck typing without inheritance
- Easier testing with minimal mocks  
- Gradual adoption in extracted packages

### 4. Large Protocol Surface Areas

`TemplateEngineProtocol` requires 8+ methods, making minimal implementations verbose:

```python
# Current: Must implement ALL of these
class TemplateEngineProtocol(Protocol):
    site: Site
    template_dirs: list[Path]
    
    def render_template(self, name: str, context: dict) -> str: ...
    def render_string(self, template: str, context: dict) -> str: ...
    def template_exists(self, name: str) -> bool: ...
    def get_template_path(self, name: str) -> Path | None: ...
    def list_templates(self) -> list[str]: ...
    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]: ...
    def capabilities(self) -> EngineCapability: ...
    def has_capability(self, cap: EngineCapability) -> bool: ...
```

---

## Migration Scope

### Current State (Quantified)

| Protocol | Import Locations | Internal References | Test Files |
|----------|-----------------|---------------------|------------|
| `SectionLike` (core) | 0 direct | ~5 type hints | ~3 |
| `SectionLike` (orchestration) | 0 direct | ~2 type hints | ~1 |
| `HighlightBackend` | 2 files | ~4 references | ~2 |
| `TemplateEngineProtocol` | 8 files | ~30 references | ~5 |
| `RoleHandler` | 5 files | ~15 references | ~3 |
| `DirectiveHandler` | 10 files | ~25 references | ~5 |

### Estimated Changes

| Phase | Files Changed | LOC Added | LOC Removed | Risk |
|-------|--------------|-----------|-------------|------|
| 1: Consolidation | 5 | ~150 | ~50 | Low |
| 2: Bridge Protocols | 3 | ~200 | 0 | Low |
| 3: Protocol Composition | 2 | ~100 | ~80 | Medium |
| 4: Package Alignment | 2 (external) | ~50 | ~20 | Low |
| **Total** | **12** | **~500** | **~150** | **Low-Medium** |

---

## Proposed Solution

### Phase 1: Consolidation (Breaking Change, Minor)

#### 1.1 Single Source of Truth for Core Protocols

Create `bengal/protocols/__init__.py` as the canonical location:

```python
# bengal/protocols/__init__.py
"""
Canonical protocol definitions for Bengal.

All protocols should be imported from this module.
Internal modules may define implementation-specific protocols,
but cross-module contracts belong here.
"""

from bengal.protocols.core import (
    PageLike,
    SectionLike,
    SiteLike,
    NavigableSection,
    QueryableSection,
)
from bengal.protocols.rendering import (
    TemplateRenderer,
    TemplateIntrospector,
    TemplateEnvironment,
    HighlightService,
    RoleHandler,
    DirectiveHandler,
)
from bengal.protocols.infrastructure import (
    ProgressReporter,
    Cacheable,
    OutputCollector,
    ContentSourceProtocol,
    OutputTarget,
)

__all__ = [
    # Core
    "PageLike",
    "SectionLike", 
    "SiteLike",
    "NavigableSection",
    "QueryableSection",
    # Rendering
    "TemplateRenderer",
    "TemplateIntrospector",
    "TemplateEnvironment",
    "HighlightService",
    "RoleHandler",
    "DirectiveHandler",
    # Infrastructure
    "ProgressReporter",
    "Cacheable",
    "OutputCollector",
    "ContentSourceProtocol",
    "OutputTarget",
]
```

#### 1.2 Remove Duplicates

Delete `SectionLike` from `bengal/orchestration/types.py` and update imports.

#### 1.3 Deprecation Path

```python
# bengal/core/section/protocols.py
import warnings
from bengal.protocols import SectionLike as _SectionLike

def __getattr__(name: str):
    if name == "SectionLike":
        warnings.warn(
            "Import SectionLike from bengal.protocols instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return _SectionLike
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

#### 1.4 Dependency Constraints (Architecture)

To prevent circular dependencies during the extraction process, the `bengal.protocols` package must adhere to a **Leaf-Node Strategy**:

1.  **No Internal Imports**: `bengal.protocols` must NEVER import from `bengal.core`, `bengal.rendering`, or `bengal.orchestration`.
2.  **Forward References**: All non-protocol type hints (e.g., `Site`, `Page`, `Section`) MUST use string forward references or the `TYPE_CHECKING` pattern with `from __future__ import annotations`.
3.  **Primitive Consistency**: Use standard library types where possible (e.g., `pathlib.Path` instead of a custom `PathLike` if it avoids an internal import).

### Phase 2: Bridge Protocols

#### 2.1 HighlightService Protocol

Bridge between Bengal and any highlighting backend:

```python
# bengal/protocols/rendering.py

@runtime_checkable
class HighlightService(Protocol):
    """
    Unified interface for syntax highlighting.
    
    This protocol bridges Bengal with highlighting backends (Rosettes,
    Pygments, tree-sitter, etc.). Implementations handle the translation
    from this interface to backend-specific APIs.
    
    Thread Safety:
        Implementations must be thread-safe. The highlight() method
        may be called concurrently from multiple render threads.
    
    Example (Rosettes adapter):
        >>> class RosettesHighlightService:
        ...     def __init__(self):
        ...         self._formatter = HtmlFormatter()
        ...     
        ...     @property
        ...     def name(self) -> str:
        ...         return "rosettes"
        ...     
        ...     def highlight(self, code, language, hl_lines=None, linenos=False):
        ...         lexer = get_lexer(language)
        ...         config = FormatConfig(hl_lines=hl_lines, linenos=linenos)
        ...         return self._formatter.format_string(lexer.tokenize(code), config)
        ...     
        ...     def supports_language(self, language):
        ...         return has_lexer(language)
    
    """

    @property
    def name(self) -> str:
        """Backend identifier (e.g., 'rosettes', 'pygments')."""
        ...

    def highlight(
        self,
        code: str,
        language: str,
        *,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
        **options: Any,
    ) -> str:
        """
        Render code with syntax highlighting.

        Args:
            code: Source code to highlight
            language: Programming language identifier
            hl_lines: 1-indexed line numbers to emphasize (optional)
            show_linenos: Include line numbers in output
            **options: Backend-specific options (passed through)

        Returns:
            HTML string with highlighted code

        Contract:
            - MUST return valid HTML (never raise for bad input)
            - MUST escape HTML entities in code
            - MUST use CSS classes (not inline styles)
            - SHOULD fall back to plain text for unknown languages
        """
        ...

    def supports_language(self, language: str) -> bool:
        """
        Check if backend supports the given language.

        Args:
            language: Language identifier or alias

        Returns:
            True if highlighting is available

        Contract:
            - MUST NOT raise exceptions
            - SHOULD handle common aliases (js -> javascript)
        """
        ...
```

#### 2.2 ContentSourceProtocol

Create a Protocol version alongside the existing ABC for duck-typing flexibility:

```python
@runtime_checkable
class ContentSourceProtocol(Protocol):
    """
    Protocol interface for content sources.
    
    This is the Protocol version of ContentSource ABC for cases
    where duck typing is preferred over inheritance.
    
    Enables loading content from different backends:
    - Filesystem (default)
    - Git repositories (for versioned docs)
    - Remote APIs (headless CMS)
    - In-memory (testing)
    
    Note:
        The existing ContentSource ABC remains for implementations
        that prefer inheritance. Both satisfy this protocol.
    
    Thread Safety:
        Implementations MUST be thread-safe. fetch_all() and fetch_one()
        may be called concurrently during parallel builds.
    
    """

    @property
    def name(self) -> str:
        """Source instance name (e.g., 'api-docs', 'main-content')."""
        ...

    @property
    def source_type(self) -> str:
        """Source type identifier (e.g., 'local', 'github', 'notion')."""
        ...

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """Fetch all content entries from this source."""
        ...

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """Fetch a single content entry by ID."""
        ...
```

#### 2.3 OutputTarget Protocol

Abstract output writing:

```python
@runtime_checkable
class OutputTarget(Protocol):
    """
    Abstract interface for build output.
    
    Enables writing to different backends:
    - Filesystem (default)
    - In-memory (testing, preview)
    - S3/Cloud storage (deployment)
    - ZIP archive (distribution)
    
    Thread Safety:
        Implementations MUST be thread-safe. The write() and copy()
        methods will be called concurrently by multiple render threads
        when Bengal is configured with parallel=true.
    
    """

    @property
    def name(self) -> str:
        """Target identifier (e.g., 'filesystem', 'memory', 's3')."""
        ...

    def write(self, path: str, content: str) -> None:
        """Write string content."""
        ...

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content."""
        ...

    def copy(self, src: str, dest: str) -> None:
        """Copy file from source path to destination."""
        ...

    def mkdir(self, path: str) -> None:
        """Ensure directory exists."""
        ...

    def exists(self, path: str) -> bool:
        """Check if path exists in output."""
        ...
```

### Phase 3: Protocol Composition

#### 3.1 Split Large Protocols

Break `TemplateEngineProtocol` into composable pieces:

```python
@runtime_checkable
class TemplateRenderer(Protocol):
    """Core rendering capability - the minimum viable engine."""
    
    site: Site
    template_dirs: list[Path]

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template."""
        ...

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render an inline template string."""
        ...


@runtime_checkable  
class TemplateIntrospector(Protocol):
    """Optional introspection capabilities."""

    def template_exists(self, name: str) -> bool:
        """Check if template exists."""
        ...

    def get_template_path(self, name: str) -> Path | None:
        """Resolve template to filesystem path."""
        ...

    def list_templates(self) -> list[str]:
        """List all available templates."""
        ...


@runtime_checkable
class TemplateValidator(Protocol):
    """Optional validation capabilities."""

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """Validate templates for syntax errors."""
        ...


# Full engine is composition of all three
class TemplateEngine(TemplateRenderer, TemplateIntrospector, TemplateValidator, Protocol):
    """Full template engine with all capabilities."""
    
    @property
    def capabilities(self) -> EngineCapability:
        """Engine capability flags."""
        ...

    def has_capability(self, cap: EngineCapability) -> bool:
        """Check for specific capability."""
        ...
```

This allows:

```python
# Accept minimal renderer for simple cases
def render_page(engine: TemplateRenderer, page: Page) -> str:
    return engine.render_template("page.html", {"page": page})

# Require full engine for admin/validation
def validate_site(engine: TemplateEngine) -> list[TemplateError]:
    return engine.validate()
```

### Phase 4: Package Alignment

#### 4.1 Patitas Highlighter Alignment

Update Patitas's `Highlighter` protocol to match Bengal's expectations:

```python
# patitas/highlighting.py

@runtime_checkable
class Highlighter(Protocol):
    """
    Protocol for syntax highlighters.
    
    Aligned with Bengal's HighlightService for seamless integration.
    """

    def highlight(
        self,
        code: str,
        language: str,
        *,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """Highlight code and return HTML."""
        ...

    def supports_language(self, language: str) -> bool:
        """Check language support."""
        ...
```

#### 4.2 Rosettes Adapter

Rosettes keeps its composable `Lexer`/`Formatter` design but Bengal provides an adapter:

```python
# bengal/rendering/highlighting/rosettes.py

class RosettesHighlightService:
    """
    Adapter implementing Bengal's HighlightService using Rosettes.
    
    This bridges Rosettes' composable lexer/formatter architecture
    with Bengal's monolithic highlight interface.
    """
    
    def __init__(
        self,
        formatter: Formatter | None = None,
        *,
        css_class: str = "highlight",
        line_class: str = "line",
    ):
        self._formatter = formatter or HtmlFormatter(
            css_class=css_class,
            line_class=line_class,
        )
    
    @property
    def name(self) -> str:
        return "rosettes"
    
    def highlight(
        self,
        code: str,
        language: str,
        *,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        try:
            lexer = get_lexer(language)
        except LexerNotFoundError:
            # Fall back to plain text
            lexer = get_lexer("text")
        
        config = FormatConfig(
            hl_lines=hl_lines or [],
            linenos=show_linenos,
        )
        return self._formatter.format_string(lexer.tokenize(code), config)
    
    def supports_language(self, language: str) -> bool:
        return has_lexer(language)
```

---

## Migration Path

### Step 1: Create Protocol Package (Non-breaking)

1. Create `bengal/protocols/` with consolidated definitions
2. Re-export from original locations for compatibility
3. Add deprecation warnings to old import paths

### Step 2: Update Internal Usage

1. Update all Bengal imports to use `bengal.protocols`
2. Run tests, fix any issues
3. Document new import paths

### Step 3: Package Alignment

1. Update Patitas `Highlighter` protocol signature
2. Create Rosettes adapter in Bengal
3. Verify integration tests pass

### Step 4: Remove Deprecated Paths (Next Major)

1. Remove duplicate definitions
2. Remove re-exports from old locations
3. Update CHANGELOG

---

## Test Impact Analysis

### Affected Test Files

| Test Category | Files | Changes Needed |
|---------------|-------|----------------|
| Protocol conformance | `tests/unit/core/test_section.py` | Update import paths |
| Highlighting | `tests/unit/rendering/test_highlighting.py` | Verify adapter works |
| Template engine | `tests/unit/rendering/test_engines.py` | Update type hints |
| Integration | `tests/integration/test_build.py` | Verify end-to-end |

### New Tests Required

```python
# tests/unit/protocols/test_protocols.py

def test_section_like_compatibility():
    """Both Section implementations satisfy SectionLike protocol."""
    from bengal.protocols import SectionLike
    from bengal.core import Section
    
    assert isinstance(Section(...), SectionLike)

def test_highlight_service_adapter():
    """RosettesHighlightService satisfies HighlightService protocol."""
    from bengal.protocols import HighlightService
    from bengal.rendering.highlighting.rosettes import RosettesHighlightService
    
    adapter = RosettesHighlightService()
    assert isinstance(adapter, HighlightService)
    
def test_deprecation_warning():
    """Old import paths emit deprecation warnings."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from bengal.core.section.protocols import SectionLike
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
```

---

## File Changes

### New Files

```
bengal/protocols/
├── __init__.py          # Public API, re-exports
├── core.py              # PageLike, SectionLike, SiteLike, etc.
├── rendering.py         # TemplateRenderer, HighlightService, etc.
└── infrastructure.py    # Cacheable, OutputTarget, ContentSourceProtocol, etc.
```

### Modified Files

| File | Change |
|------|--------|
| `bengal/core/section/protocols.py` | Deprecate, re-export from `bengal.protocols` |
| `bengal/orchestration/types.py` | Remove `SectionLike`, import from `bengal.protocols` |
| `bengal/rendering/engines/protocol.py` | Split into `TemplateRenderer`/`TemplateIntrospector` |
| `bengal/rendering/highlighting/protocol.py` | Rename `HighlightBackend` → `HighlightService` |
| `bengal/rendering/highlighting/__init__.py` | Update imports |
| `bengal/rendering/highlighting/tree_sitter.py` | Update imports |

### External Package Changes

| Package | File | Change |
|---------|------|--------|
| Patitas | `src/patitas/highlighting.py` | Align `Highlighter` signature |

---

## Alternatives Considered

### 1. Shared Protocol Package

Create a separate `bengal-protocols` package that Bengal, Kida, Rosettes, and Patitas all depend on.

**Rejected because:**
- Adds deployment complexity
- Version coordination overhead
- Protocols are lightweight enough to duplicate if needed

### 2. ABC Instead of Protocol

Use Abstract Base Classes for stricter contracts.

**Rejected because:**
- Protocols enable duck typing without inheritance
- Easier testing with minimal mocks
- Better gradual adoption in extracted packages

### 3. Keep Status Quo

Leave protocols scattered across modules.

**Rejected because:**
- Duplication causes confusion
- Makes extraction harder
- Inconsistent patterns

---

## Success Criteria

- [ ] Single import path for all public protocols (`from bengal.protocols import ...`)
- [ ] No duplicate protocol definitions
- [ ] Patitas and Rosettes integrate cleanly via protocols
- [ ] All existing tests pass (~850 tests)
- [ ] Deprecation warnings guide migration
- [ ] New protocol tests added and passing

---

## Decisions

### Adapter Location: Bengal (Option A)

**Decision**: Adapters live in Bengal, not in extracted packages.

**Rationale**:
- Bengal depends on Rosettes, not vice versa
- Keeps Rosettes free of Bengal-specific code  
- Allows Rosettes to remain a general-purpose library
- Avoids circular dependency concerns

**Implementation**: `bengal/rendering/highlighting/rosettes.py`

### Deprecation Timeline: 3 Minor Versions

**Decision**: Keep deprecated paths for 3 minor versions before removal.

**Rationale**:
- Gives users time to migrate across several release cycles
- Aligns with the 1.0.0 roadmap for extracted packages
- Warnings make migration path clear

**Timeline**:
- v0.2.0: Add `bengal.protocols`, deprecation warnings on old paths
- v0.3.0: Continue warnings
- v0.4.0: Upgrade to `FutureWarning` for higher visibility
- v1.0.0: Remove deprecated paths

### Protocol vs ABC: Inheritance-based Aliasing

**Decision**: Keep existing ABCs but make them inherit from the new Protocols.

**Rationale**:
- Reduces code duplication while maintaining strict contracts
- ABCs continue to provide shared utility logic (e.g., `ContentSource.cache_key`)
- Satisfies the "Expert" and "Skeptic" personas by unifying the type hierarchy

**Implementation Example**:
```python
class ContentSource(ContentSourceProtocol, ABC):
    """ABC providing utilities while satisfying the protocol."""
    # ... utilities ...
```

---

## References

- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- `bengal/rendering/engines/protocol.py` - Current TemplateEngineProtocol
- `bengal/core/section/protocols.py` - Current SectionLike
- `bengal/content_layer/source.py` - Current ContentSource ABC
- `bengal/rendering/parsers/base.py` - Current BaseMarkdownParser ABC
- `rosettes/src/rosettes/_protocol.py` - Rosettes Lexer/Formatter
- `patitas/src/patitas/protocols.py` - Patitas LexerDelegate
- `patitas/src/patitas/highlighting.py` - Patitas Highlighter