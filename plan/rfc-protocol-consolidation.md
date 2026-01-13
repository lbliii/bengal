# RFC: Protocol Consolidation and Cross-Package Contracts

**Status**: Draft  
**Created**: 2026-01-12  
**Author**: Bengal Team  
**Related**: `rfc-patitas-extraction.md`, `rfc-rosettes-extraction.md`

---

## Executive Summary

As Bengal extracts core components into standalone packages (Kida, Rosettes, Patitas), the protocol system needs consolidation. This RFC proposes:

1. Removing protocol duplication
2. Creating bridge protocols for clean package boundaries
3. Aligning extracted package protocols with Bengal's expectations
4. Adding missing infrastructure protocols

---

## Problem Statement

### 1. Protocol Duplication

`SectionLike` is defined in two locations with overlapping but different purposes:

```python
# bengal/core/section/protocols.py:36
@runtime_checkable
class SectionLike(Protocol):
    """Protocol for section-like objects."""
    name: str
    title: str
    path: Path | None
    href: str
    pages: list[PageLike]
    subsections: list[SectionLike]
    parent: SectionLike | None
    index_page: PageLike | None
    is_root: bool

# bengal/orchestration/types.py:196
@runtime_checkable
class SectionLike(Protocol):
    """Protocol for section-like objects in menu building."""
    # Different subset of properties
```

This creates confusion about which to import and risks divergence.

### 2. Misaligned Package Boundaries

Extracted packages define their own protocols that don't match Bengal's interface expectations:

| Bengal Expects | Package Provides | Gap |
|----------------|------------------|-----|
| `HighlightBackend.highlight(code, lang, hl_lines, linenos)` | Rosettes: `Lexer.tokenize()` + `Formatter.format()` | Composable vs. monolithic |
| `HighlightBackend.supports_language(lang)` | Rosettes: Lexer registry lookup | OK, needs adapter |
| `LexerDelegate.tokenize_range(source, start, end, lang)` | Patitas: `Highlighter.highlight(code, lang)` | Zero-copy vs. string copy |

### 3. Missing Infrastructure Protocols

Documentation references protocols that don't exist:

- `BaseMarkdownParser` - Referenced in `HighlightBackend` docstring
- `ContentSource` - Referenced in `HighlightBackend` docstring

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
)
from bengal.protocols.infrastructure import (
    ProgressReporter,
    Cacheable,
    OutputCollector,
    ContentSource,
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
    # Infrastructure
    "ProgressReporter",
    "Cacheable",
    "OutputCollector",
    "ContentSource",
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

#### 2.2 ContentSource Protocol

Abstract content loading for future multi-source support:

```python
@runtime_checkable
class ContentSource(Protocol):
    """
    Abstract interface for content sources.
    
    Enables loading content from different backends:
    - Filesystem (default)
    - Git repositories (for versioned docs)
    - Remote APIs (headless CMS)
    - In-memory (testing)
    
    """

    @property
    def name(self) -> str:
        """Source identifier (e.g., 'filesystem', 'git', 's3')."""
        ...

    def exists(self, path: str) -> bool:
        """Check if content exists at path."""
        ...

    def read(self, path: str) -> str:
        """Read content as string."""
        ...

    def read_bytes(self, path: str) -> bytes:
        """Read content as bytes."""
        ...

    def list(self, path: str, pattern: str = "*") -> list[str]:
        """List content matching pattern."""
        ...

    def mtime(self, path: str) -> float | None:
        """Get modification time (for caching). None if unavailable."""
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

Rosettes keeps its composable `Lexer`/`Formatter` design but provides an adapter:

```python
# rosettes/adapters/bengal.py (or bengal/rendering/highlighting/rosettes.py)

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

## File Changes

### New Files

```
bengal/protocols/
├── __init__.py          # Public API, re-exports
├── core.py              # PageLike, SectionLike, SiteLike, etc.
├── rendering.py         # TemplateRenderer, HighlightService, etc.
└── infrastructure.py    # Cacheable, OutputTarget, ContentSource, etc.
```

### Modified Files

| File | Change |
|------|--------|
| `bengal/core/section/protocols.py` | Deprecate, re-export from `bengal.protocols` |
| `bengal/orchestration/types.py` | Remove `SectionLike`, import from `bengal.protocols` |
| `bengal/rendering/engines/protocol.py` | Split into `TemplateRenderer`/`TemplateIntrospector` |
| `bengal/rendering/highlighting/protocol.py` | Rename `HighlightBackend` → `HighlightService` |

### External Package Changes

| Package | File | Change |
|---------|------|--------|
| Patitas | `src/patitas/highlighting.py` | Align `Highlighter` signature |
| Rosettes | `src/rosettes/adapters/bengal.py` | Add `RosettesHighlightService` |

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
- Missing protocols leave gaps

---

## Success Criteria

- [ ] Single import path for all public protocols (`from bengal.protocols import ...`)
- [ ] No duplicate protocol definitions
- [ ] Patitas and Rosettes integrate cleanly via protocols
- [ ] All existing tests pass
- [ ] Deprecation warnings guide migration

---

## Open Questions

1. **Should we create a minimal `bengal-protocols` package?**
   - Pro: Clean dependency for extracted packages
   - Con: Version coordination, deployment complexity

2. **Where should adapters live?**
   - Option A: In Bengal (`bengal/rendering/highlighting/rosettes.py`)
   - Option B: In Rosettes (`rosettes/adapters/bengal.py`)
   - Option C: Both (Rosettes provides, Bengal re-exports)

3. **How strict should deprecation timeline be?**
   - Option A: Remove in next major (0.2.0)
   - Option B: Keep deprecated paths for 2 minors
   - Option C: Keep indefinitely with warnings

---

## References

- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- `bengal/rendering/engines/protocol.py` - Current TemplateEngineProtocol
- `bengal/core/section/protocols.py` - Current SectionLike
- `rosettes/src/rosettes/_protocol.py` - Rosettes Lexer/Formatter
- `patitas/src/patitas/protocols.py` - Patitas LexerDelegate
