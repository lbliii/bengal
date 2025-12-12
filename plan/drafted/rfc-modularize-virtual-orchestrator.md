# RFC: Modularize VirtualAutodocOrchestrator

**Status**: Draft  
**Created**: 2025-12-11  
**Author**: AI Assistant  
**Priority**: P2 (Medium)  
**Scope**: `bengal/autodoc/virtual_orchestrator.py` → `bengal/autodoc/virtual/`

---

## Summary

Convert the monolithic `virtual_orchestrator.py` (1,393 lines) into a modular package with focused, single-responsibility modules. This improves testability, readability, and maintainability while preserving the existing public API.

---

## Problem Statement

The current `VirtualAutodocOrchestrator` class handles too many concerns in a single file:

1. **Result tracking** (`AutodocRunResult` dataclass, ~50 lines)
2. **Page context helper** (`_PageContext` class, ~45 lines)
3. **Template environment setup** (~150 lines)
4. **Python section creation** (~90 lines)
5. **CLI section creation** (~60 lines)
6. **OpenAPI section creation** (~80 lines)
7. **Page creation with two-pass approach** (~130 lines)
8. **Element rendering with fallbacks** (~150 lines)
9. **Fallback HTML rendering** (~150 lines)
10. **Index page creation and rendering** (~160 lines)
11. **Python extraction facade** (~30 lines)
12. **CLI extraction facade** (~40 lines)
13. **OpenAPI extraction facade** (~30 lines)

**Symptoms**:
- `_create_template_environment()` is 135 lines
- Multiple rendering paths with complex fallback chains
- Section creation logic is duplicated across types
- Hard to test rendering in isolation from extraction

---

## Proposed Solution

### Directory Structure

```
bengal/autodoc/virtual/
├── __init__.py              # Public API (VirtualAutodocOrchestrator, AutodocRunResult)
├── orchestrator.py          # Main orchestrator class (composition root)
├── result.py                # AutodocRunResult dataclass
├── page_context.py          # _PageContext helper class
├── template_env.py          # Template environment factory
├── section_factory.py       # Section creation for all doc types
├── page_factory.py          # Page creation logic
└── renderer.py              # Element and fallback rendering
```

### Module Responsibilities

#### `__init__.py` - Public API
```python
"""
Virtual page orchestrator for autodoc.

Public API:
    VirtualAutodocOrchestrator: Main orchestrator for virtual autodoc pages
    AutodocRunResult: Summary of an autodoc generation run
"""
from bengal.autodoc.virtual.orchestrator import VirtualAutodocOrchestrator
from bengal.autodoc.virtual.result import AutodocRunResult

__all__ = ["VirtualAutodocOrchestrator", "AutodocRunResult"]
```

#### `result.py` - Run Result (~60 lines)
```python
@dataclass
class AutodocRunResult:
    """Summary of an autodoc generation run."""

    extracted: int = 0
    rendered: int = 0
    failed_extract: int = 0
    failed_render: int = 0
    warnings: int = 0
    failed_extract_identifiers: list[str] = field(default_factory=list)
    failed_render_identifiers: list[str] = field(default_factory=list)
    fallback_pages: list[str] = field(default_factory=list)
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)

    def has_failures(self) -> bool: ...
    def has_warnings(self) -> bool: ...
    def add_dependency(self, source_file: str, page_path: str) -> None: ...
```

#### `page_context.py` - Template Context (~60 lines)
```python
class PageContext:
    """
    Lightweight page-like context for autodoc template rendering.

    Provides attributes templates expect (metadata, tags, title, relative_url)
    without requiring a full Page object.
    """

    def __init__(
        self,
        title: str,
        metadata: dict[str, Any],
        tags: list[str] | None = None,
        relative_url: str = "/",
        variant: str | None = None,
        source_path: str | None = None,
        section: Section | None = None,
    ) -> None: ...
```

#### `template_env.py` - Template Environment Factory (~180 lines)
```python
class TemplateEnvironmentFactory:
    """Creates and configures Jinja2 environment for autodoc templates."""

    def __init__(self, site: Site, config: dict[str, Any]):
        self.site = site
        self.config = config

    def create(self) -> Environment:
        """Create configured Jinja2 environment."""
        ...

    def _get_template_dirs(self) -> list[str]:
        """Get template directories in priority order."""
        ...

    def _register_globals(self, env: Environment) -> None:
        """Register global variables and functions."""
        ...

    def _register_filters(self, env: Environment) -> None:
        """Register custom filters."""
        ...

    def _get_theme_templates_dir(self) -> Path | None:
        """Get theme templates directory if available."""
        ...
```

#### `section_factory.py` - Section Creation (~250 lines)
```python
class SectionFactory:
    """Creates virtual section hierarchies for documentation types."""

    def __init__(self, site: Site):
        self.site = site

    def create_python_sections(
        self,
        elements: list[DocElement]
    ) -> dict[str, Section]:
        """Create API section hierarchy from Python modules."""
        ...

    def create_cli_sections(
        self,
        elements: list[DocElement]
    ) -> dict[str, Section]:
        """Create CLI section hierarchy from commands."""
        ...

    def create_openapi_sections(
        self,
        elements: list[DocElement],
        existing_sections: dict[str, Section] | None = None
    ) -> dict[str, Section]:
        """Create OpenAPI section hierarchy from endpoints."""
        ...

    def _create_root_section(
        self,
        name: str,
        title: str,
        doc_type: str,
        icon: str,
        description: str
    ) -> Section:
        """Create a root section with standard metadata."""
        ...
```

#### `page_factory.py` - Page Creation (~200 lines)
```python
class PageFactory:
    """Creates virtual pages for documentation elements."""

    def __init__(self, site: Site):
        self.site = site

    def create_pages(
        self,
        elements: list[DocElement],
        sections: dict[str, Section],
        doc_type: str,
        result: AutodocRunResult
    ) -> tuple[list[Page], AutodocRunResult]:
        """Create virtual pages for documentation elements."""
        ...

    def create_index_pages(
        self,
        sections: dict[str, Section]
    ) -> list[Page]:
        """Create index pages for sections that need them."""
        ...

    def _find_parent_section(
        self,
        element: DocElement,
        sections: dict[str, Section],
        doc_type: str
    ) -> Section:
        """Find appropriate parent section for an element."""
        ...

    def _get_element_metadata(
        self,
        element: DocElement,
        doc_type: str
    ) -> tuple[str, str, str]:
        """Get template name, URL path, and page type for element."""
        ...
```

#### `renderer.py` - Element Rendering (~250 lines)
```python
class AutodocRenderer:
    """Renders documentation elements to HTML."""

    def __init__(
        self,
        site: Site,
        template_env: Environment,
        config: dict[str, Any]
    ):
        self.site = site
        self.template_env = template_env
        self.config = config

    def render_element(
        self,
        element: DocElement,
        template_name: str,
        url_path: str,
        page_type: str,
        section: Section | None = None
    ) -> str:
        """Render element documentation to HTML."""
        ...

    def render_section_index(self, section: Section) -> str:
        """Render section index page HTML."""
        ...

    def render_fallback(self, element: DocElement) -> str:
        """Render minimal fallback HTML when template fails."""
        ...

    def render_section_index_fallback(self, section: Section) -> str:
        """Fallback card-based rendering for section index."""
        ...

    def _create_page_context(
        self,
        element: DocElement,
        page_type: str,
        url_path: str,
        section: Section | None
    ) -> PageContext:
        """Create page context for template rendering."""
        ...

    def _relativize_paths(self, message: str) -> str:
        """Convert absolute paths in error messages to relative."""
        ...
```

#### `orchestrator.py` - Composition Root (~200 lines)
```python
class VirtualAutodocOrchestrator:
    """
    Orchestrate API documentation generation as virtual pages.

    Composes specialized modules to:
    1. Extract DocElements from source (Python, CLI, OpenAPI)
    2. Create virtual Section hierarchy
    3. Create virtual Pages for each element
    4. Return (pages, sections, result) for site integration
    """

    def __init__(self, site: Site):
        self.site = site
        self.config = site.config.get("autodoc", {})

        # Compose modules
        self._template_env_factory = TemplateEnvironmentFactory(site, self.config)
        self._section_factory = SectionFactory(site)
        self._page_factory = PageFactory(site)
        self._renderer: AutodocRenderer | None = None  # Lazy init

    def is_enabled(self) -> bool:
        """Check if virtual autodoc is enabled for any type."""
        ...

    def generate(self) -> tuple[list[Page], list[Section], AutodocRunResult]:
        """Generate documentation as virtual pages and sections."""
        # Initialize renderer with template env
        template_env = self._template_env_factory.create()
        self._renderer = AutodocRenderer(self.site, template_env, self.config)

        result = AutodocRunResult()
        all_elements = []
        all_sections = {}
        all_pages = []

        # Extract and process each type...
        ...

    # Extraction methods stay here (they're simple facades)
    def _extract_python(self) -> list[DocElement]: ...
    def _extract_cli(self) -> list[DocElement]: ...
    def _extract_openapi(self) -> list[DocElement]: ...
```

---

## Migration Strategy

### Phase 1: Extract Data Classes

1. Move `AutodocRunResult` to `result.py`
2. Move `_PageContext` to `page_context.py` (rename to `PageContext`)
3. Update imports - public API preserved via `__init__.py`

### Phase 2: Extract Template Environment

1. Create `TemplateEnvironmentFactory` in `template_env.py`
2. Move `_create_template_environment()` logic
3. Move `_get_theme_templates_dir()` helper

### Phase 3: Extract Section Factory

1. Create `SectionFactory` in `section_factory.py`
2. Move `_create_python_sections()`, `_create_cli_sections()`, `_create_openapi_sections()`
3. Extract shared logic into helper methods

### Phase 4: Extract Page Factory

1. Create `PageFactory` in `page_factory.py`
2. Move `_create_pages()`, `_create_index_pages()`
3. Move `_find_parent_section()`, `_get_element_metadata()`

### Phase 5: Extract Renderer

1. Create `AutodocRenderer` in `renderer.py`
2. Move all `_render_*` methods
3. Move `_relativize_paths()` helper

### Phase 6: Compose in Orchestrator

1. Update `VirtualAutodocOrchestrator` to compose modules
2. Simplify `generate()` to coordinate modules
3. Keep extraction facades in orchestrator (they're simple)

---

## Backward Compatibility

**Preserved**:
- `from bengal.autodoc.virtual_orchestrator import VirtualAutodocOrchestrator`
- `from bengal.autodoc.virtual_orchestrator import AutodocRunResult`
- All public methods on `VirtualAutodocOrchestrator`

**Deprecation path**:
```python
# bengal/autodoc/virtual_orchestrator.py (compatibility shim)
"""
Backward compatibility shim. Import from bengal.autodoc.virtual instead.
"""
from bengal.autodoc.virtual import VirtualAutodocOrchestrator, AutodocRunResult

__all__ = ["VirtualAutodocOrchestrator", "AutodocRunResult"]
```

---

## Testing Strategy

| Module | Test Focus |
|--------|------------|
| `result.py` | Dataclass methods, dependency tracking |
| `page_context.py` | Attribute access, navigation attributes |
| `template_env.py` | Template loading, global registration |
| `section_factory.py` | Section hierarchy for each doc type |
| `page_factory.py` | Page creation, section assignment |
| `renderer.py` | Template rendering, fallback chains |
| `orchestrator.py` | End-to-end generation |

---

## Alternatives Considered

### Alternative 1: Keep Single File
**Rejected**: 1,393 lines is too large; multiple distinct responsibilities.

### Alternative 2: Split by Doc Type (python/, cli/, openapi/)
**Rejected**: Would duplicate shared logic; the current separation by concern is cleaner.

### Alternative 3: Merge with Extractors
**Rejected**: Extractors are already well-separated; this would increase coupling.

---

## Implementation Checklist

- [ ] Create `bengal/autodoc/virtual/` directory
- [ ] Move `AutodocRunResult` to `result.py`
- [ ] Move `_PageContext` to `page_context.py` as `PageContext`
- [ ] Extract `TemplateEnvironmentFactory` to `template_env.py`
- [ ] Extract `SectionFactory` to `section_factory.py`
- [ ] Extract `PageFactory` to `page_factory.py`
- [ ] Extract `AutodocRenderer` to `renderer.py`
- [ ] Create `orchestrator.py` as composition root
- [ ] Create `__init__.py` with public API
- [ ] Add backward compatibility shim at old location
- [ ] Update imports in consuming modules
- [ ] Add unit tests for new modules
- [ ] Verify existing tests pass
- [ ] Update autodoc documentation

---

## Success Criteria

1. ✅ All existing tests pass
2. ✅ Each module under 250 lines
3. ✅ Template rendering testable in isolation
4. ✅ Section creation testable without extraction
5. ✅ New unit tests for each module
6. ✅ No breaking changes to public API
7. ✅ Backward compatibility shim works
