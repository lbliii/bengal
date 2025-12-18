# RFC: Pluggable Template Engine Architecture for Bengal

**Status**: Draft
**Created**: 2025-12-18
**Author**: AI Assistant
**Subsystems**: `bengal/rendering/`, `bengal/config/`
**Depends On**: [RFC: Patitas](rfc-bengal-templates.md)

---

## Executive Summary

This RFC proposes a **pluggable template engine architecture** for Bengal that enables users to choose between Jinja2 (default) and [Patitas](rfc-bengal-templates.md) — a new Python-native templating library.

**Key Changes**:
1. Introduce `TemplateEngineProtocol` — abstract interface for template engines
2. Refactor current `TemplateEngine` → `JinjaEngine` (backward compatible)
3. Add `PatitasEngine` — adapter for the Patitas library
4. Configuration option to select engine per-site

```yaml
# bengal.yaml
site:
  template_engine: patitas  # or "jinja2" (default)
```

**Why Pluggable?**
- Users can choose the best tool for their needs
- Enables gradual migration from Jinja2 to Patitas
- Opens the door for other engines in the future

---

## Problem Statement

### Current State

Bengal's template system is **tightly coupled to Jinja2**:

```python
# bengal/rendering/template_engine/core.py
class TemplateEngine:
    def __init__(self, site):
        self.env = Environment(...)  # Hardcoded Jinja2
```

**15+ callsites** directly instantiate `TemplateEngine`:

```python
# bengal/rendering/pipeline/core.py
self.template_engine = TemplateEngine(site)

# bengal/orchestration/build/initialization.py
engine = TemplateEngine(orchestrator.site)

# bengal/postprocess/special_pages.py
template_engine = TemplateEngine(self.site)
# ... etc
```

### Problems

1. **No flexibility**: Users cannot use alternative template engines
2. **Testing difficulty**: Hard to mock template rendering in tests
3. **Innovation barrier**: Can't experiment with new templating approaches
4. **Vendor lock-in**: Jinja2 syntax baked into themes

### Desired State

Users can choose their template engine:

```yaml
# Option A: Traditional Jinja2 (default, backward compatible)
site:
  template_engine: jinja2

# Option B: Python-native with Patitas
site:
  template_engine: patitas
```

---

## Design Goals

1. **Backward Compatible**: Existing Jinja2 themes work unchanged
2. **Zero Config Default**: Jinja2 remains the default engine
3. **Clean Abstraction**: Protocol-based interface, not inheritance
4. **Incremental Adoption**: Themes can mix Jinja2 and Patitas templates
5. **SvelteKit Philosophy**: Patitas embraces "just Python" — no DSL

---

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bengal Rendering Pipeline                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TemplateEngineProtocol                          │
│  render_template(name, context) -> str                          │
│  render_string(template, context) -> str                        │
│  template_exists(name) -> bool                                  │
│  get_template_path(name) -> Path | None                         │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────┐
        │   JinjaEngine     │   │  PatitasEngine    │
        │   (default)       │   │  (opt-in)         │
        │                   │   │                   │
        │  *.html templates │   │  *.py templates   │
        │  Jinja2 syntax    │   │  Python functions │
        └───────────────────┘   └───────────────────┘
```

### 1. Template Engine Protocol

```python
# bengal/rendering/engines/protocol.py
"""Template engine protocol for pluggable rendering."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Page, Site


@runtime_checkable
class TemplateEngineProtocol(Protocol):
    """
    Abstract interface for template engines.

    All template engines must implement this protocol to be usable
    with Bengal's rendering pipeline.
    """

    site: "Site"

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a named template with the given context.

        Args:
            template_name: Template identifier (e.g., "blog/single.html" or "blog.single")
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If rendering fails
        """
        ...

    def render_page(self, page: "Page", context: dict[str, Any]) -> str:
        """
        Render a page using its configured template.

        Args:
            page: Page to render
            context: Additional context variables

        Returns:
            Rendered HTML string
        """
        ...

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        ...

    def get_template_path(self, template_name: str) -> Path | None:
        """Get the filesystem path to a template, if available."""
        ...

    def list_templates(self) -> list[str]:
        """List all available template names."""
        ...
```

### 2. Engine Factory

```python
# bengal/rendering/engines/__init__.py
"""Template engine factory and exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.engines.protocol import TemplateEngineProtocol

if TYPE_CHECKING:
    from bengal.core import Site

# Lazy imports to avoid loading unused engines
_ENGINE_REGISTRY: dict[str, type] = {}


def register_engine(name: str, engine_class: type) -> None:
    """Register a template engine implementation."""
    _ENGINE_REGISTRY[name] = engine_class


def create_template_engine(
    site: "Site",
    *,
    profile_templates: bool = False,
) -> TemplateEngineProtocol:
    """
    Create a template engine based on site configuration.

    Args:
        site: Site instance with configuration
        profile_templates: Enable template profiling (Jinja2 only)

    Returns:
        Configured template engine instance

    Raises:
        ValueError: If configured engine is unknown

    Example:
        engine = create_template_engine(site)
        html = engine.render_template("page.html", {"page": page})
    """
    engine_name = site.config.get("template_engine", "jinja2")

    # Lazy load engines
    if engine_name == "jinja2":
        from bengal.rendering.engines.jinja import JinjaEngine
        return JinjaEngine(site, profile_templates=profile_templates)

    elif engine_name == "patitas":
        from bengal.rendering.engines.patitas import PatitasEngine
        return PatitasEngine(site)

    elif engine_name in _ENGINE_REGISTRY:
        engine_class = _ENGINE_REGISTRY[engine_name]
        return engine_class(site)

    else:
        available = ["jinja2", "patitas"] + list(_ENGINE_REGISTRY.keys())
        raise ValueError(
            f"Unknown template engine: '{engine_name}'\n"
            f"Available engines: {', '.join(available)}\n"
            f"Set 'template_engine' in your bengal.yaml"
        )


__all__ = [
    "TemplateEngineProtocol",
    "create_template_engine",
    "register_engine",
]
```

### 3. Jinja Engine (Refactored)

```python
# bengal/rendering/engines/jinja.py
"""Jinja2 template engine implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from bengal.rendering.engines.protocol import TemplateEngineProtocol

if TYPE_CHECKING:
    from bengal.core import Page, Site


class JinjaEngine:
    """
    Jinja2-based template engine (default).

    This is a refactored version of the original TemplateEngine class,
    implementing the TemplateEngineProtocol for pluggability.

    Template Discovery:
        1. Site's custom templates/ directory
        2. Theme templates (child → parent chain)
        3. Default theme as fallback

    Features:
        - Template inheritance via theme chains
        - Bytecode caching for performance
        - Optional template profiling
        - Auto-reload in dev server mode
    """

    def __init__(
        self,
        site: "Site",
        profile_templates: bool = False,
    ) -> None:
        self.site = site
        self._profile_templates = profile_templates

        # Import existing setup logic
        from bengal.rendering.template_engine.environment import create_jinja_environment

        self.env, self.template_dirs = create_jinja_environment(
            site, self, profile_templates
        )

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a Jinja2 template."""
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_page(self, page: "Page", context: dict[str, Any]) -> str:
        """Render a page using its configured template."""
        from bengal.rendering.pipeline.output import determine_template

        template_name = determine_template(page)
        full_context = {
            "page": page,
            "site": self.site,
            **context,
        }
        return self.render_template(template_name, full_context)

    def template_exists(self, template_name: str) -> bool:
        """Check if template exists in any template directory."""
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False

    def get_template_path(self, template_name: str) -> Path | None:
        """Get filesystem path to template."""
        for template_dir in self.template_dirs:
            path = template_dir / template_name
            if path.exists():
                return path
        return None

    def list_templates(self) -> list[str]:
        """List all available templates."""
        return self.env.list_templates()

    # --- Backward Compatibility ---
    # Keep existing methods that other parts of Bengal use

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template string (for inline templates)."""
        template = self.env.from_string(template_str)
        return template.render(**context)


# Backward compatibility alias
TemplateEngine = JinjaEngine
```

### 4. Patitas Engine (New)

```python
# bengal/rendering/engines/patitas.py
"""
Patitas template engine — Python-native templating for Bengal.

Patitas ("little paws" 🐾) uses Python functions as templates,
powered by the patitas library. Templates are just Python modules
with a `render()` function.

Philosophy: "It's just Python"
    - Functions are templates
    - Imports are includes
    - Parameters are context
    - No DSL to learn

Template Discovery:
    Templates are Python files in the theme's templates/ directory:

    themes/mytheme/templates/
    ├── __init__.py
    ├── base.py          # Base layout
    ├── blog/
    │   ├── __init__.py
    │   ├── single.py    # Single blog post
    │   └── list.py      # Blog listing
    └── page.py          # Generic page

Each template module must have a `render()` function:

    # themes/mytheme/templates/blog/single.py
    from patitas import html, raw
    from patitas.elements import article, h1, div

    def render(page: Page, site: Site, **context) -> str:
        return str(html[
            article(class_="blog-post")[
                h1[page.title],
                div(class_="content")[raw(page.content_html)],
            ]
        ])

Requires: pip install bengal[patitas]
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from bengal.rendering.engines.protocol import TemplateEngineProtocol
from bengal.rendering.errors import TemplateNotFoundError, TemplateRenderError
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core import Page, Site

logger = get_logger(__name__)


class PatitasEngine:
    """
    Python-native template engine using patitas.

    Templates are Python modules with a render() function.
    No DSL, no special syntax — just Python.

    Attributes:
        site: Bengal Site instance
        template_dirs: List of directories to search for templates
        _templates: Cache of loaded template modules
        _render_funcs: Cache of render functions
    """

    def __init__(self, site: "Site") -> None:
        self.site = site
        self.template_dirs: list[Path] = []
        self._templates: dict[str, Any] = {}  # module cache
        self._render_funcs: dict[str, Callable[..., str]] = {}  # render function cache

        # Check patitas availability
        self._check_patitas()

        # Discover template directories
        self._discover_template_dirs()

        logger.info(
            "patitas_engine_initialized",
            template_dirs=[str(d) for d in self.template_dirs],
        )

    def _check_patitas(self) -> None:
        """Ensure patitas is installed."""
        try:
            import patitas  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Patitas requires patitas. Install with:\n"
                "  pip install bengal[patitas]\n"
                "  # or: pip install patitas"
            ) from e

    def _discover_template_dirs(self) -> None:
        """Find template directories following theme chain."""
        from bengal.utils.theme_resolution import resolve_theme_chain

        # Custom templates directory
        custom_templates = self.site.root_path / "templates"
        if custom_templates.exists():
            self.template_dirs.append(custom_templates)

        # Theme chain templates
        theme_chain = resolve_theme_chain(self.site.theme, self.site)
        for theme_name in theme_chain:
            theme_path = self._get_theme_path(theme_name)
            if theme_path:
                templates_dir = theme_path / "templates"
                if templates_dir.exists():
                    self.template_dirs.append(templates_dir)

        # Default theme fallback
        default_templates = Path(__file__).parent.parent.parent / "themes" / "default" / "templates"
        if default_templates.exists() and default_templates not in self.template_dirs:
            self.template_dirs.append(default_templates)

    def _get_theme_path(self, theme_name: str) -> Path | None:
        """Get path to a theme directory."""
        # Check site themes
        site_theme = self.site.root_path / "themes" / theme_name
        if site_theme.exists():
            return site_theme

        # Check built-in themes
        builtin_theme = Path(__file__).parent.parent.parent / "themes" / theme_name
        if builtin_theme.exists():
            return builtin_theme

        return None

    def _normalize_template_name(self, template_name: str) -> str:
        """
        Normalize template name for Python module lookup.

        "blog/single.html" → "blog.single"
        "blog/single.py" → "blog.single"
        "blog.single" → "blog.single"
        """
        # Remove file extension
        name = template_name
        for ext in (".html", ".py", ".jinja2", ".j2"):
            if name.endswith(ext):
                name = name[:-len(ext)]

        # Convert path separators to dots
        name = name.replace("/", ".").replace("\\", ".")

        return name

    def _load_template(self, template_name: str) -> Callable[..., str]:
        """
        Load a template module and return its render function.

        Args:
            template_name: Template name (e.g., "blog/single.html" or "blog.single")

        Returns:
            The template's render() function

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If template doesn't have render()
        """
        normalized = self._normalize_template_name(template_name)

        # Check cache
        if normalized in self._render_funcs:
            return self._render_funcs[normalized]

        # Find template file
        module_path = normalized.replace(".", "/") + ".py"
        template_path: Path | None = None

        for template_dir in self.template_dirs:
            candidate = template_dir / module_path
            if candidate.exists():
                template_path = candidate
                break

        if not template_path:
            raise TemplateNotFoundError(
                f"Patitas template not found: '{template_name}'\n"
                f"Looked for: {module_path}\n"
                f"In directories:\n" +
                "\n".join(f"  - {d}" for d in self.template_dirs)
            )

        # Load module dynamically
        module_name = f"patitas_template_{normalized.replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, template_path)
        if not spec or not spec.loader:
            raise TemplateRenderError(
                f"Failed to load template module: {template_path}"
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Get render function
        if not hasattr(module, "render"):
            raise TemplateRenderError(
                f"Patitas template missing render() function: {template_path}\n"
                f"Each template must have:\n"
                f"  def render(page: Page, site: Site, **context) -> str:\n"
                f"      ..."
            )

        render_func = module.render

        # Cache
        self._templates[normalized] = module
        self._render_funcs[normalized] = render_func

        logger.debug("patitas_template_loaded", template=normalized, path=str(template_path))

        return render_func

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a Patitas template.

        Args:
            template_name: Template name (e.g., "blog/single.html")
            context: Variables passed to the render() function

        Returns:
            Rendered HTML string
        """
        render_func = self._load_template(template_name)

        try:
            result = render_func(**context)
            return str(result)
        except Exception as e:
            raise TemplateRenderError(
                f"Error rendering Patitas template '{template_name}': {e}"
            ) from e

    def render_page(self, page: "Page", context: dict[str, Any]) -> str:
        """Render a page using its configured template."""
        from bengal.rendering.pipeline.output import determine_template

        template_name = determine_template(page)
        full_context = {
            "page": page,
            "site": self.site,
            **context,
        }
        return self.render_template(template_name, full_context)

    def template_exists(self, template_name: str) -> bool:
        """Check if a Patitas template exists."""
        normalized = self._normalize_template_name(template_name)
        module_path = normalized.replace(".", "/") + ".py"

        for template_dir in self.template_dirs:
            if (template_dir / module_path).exists():
                return True
        return False

    def get_template_path(self, template_name: str) -> Path | None:
        """Get filesystem path to a template."""
        normalized = self._normalize_template_name(template_name)
        module_path = normalized.replace(".", "/") + ".py"

        for template_dir in self.template_dirs:
            candidate = template_dir / module_path
            if candidate.exists():
                return candidate
        return None

    def list_templates(self) -> list[str]:
        """List all available Patitas templates."""
        templates: list[str] = []

        for template_dir in self.template_dirs:
            for py_file in template_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                rel_path = py_file.relative_to(template_dir)
                template_name = str(rel_path).replace("/", ".").replace("\\", ".")[:-3]
                if template_name not in templates:
                    templates.append(template_name)

        return sorted(templates)

    def reload_template(self, template_name: str) -> None:
        """Reload a template (for dev server hot reload)."""
        normalized = self._normalize_template_name(template_name)

        # Clear from caches
        self._templates.pop(normalized, None)
        self._render_funcs.pop(normalized, None)

        # Remove from sys.modules
        module_name = f"patitas_template_{normalized.replace('.', '_')}"
        sys.modules.pop(module_name, None)

        logger.debug("patitas_template_reloaded", template=normalized)
```

### 5. Example Patitas Template

```python
# themes/patitas-default/templates/blog/single.py
"""
Blog post template for Patitas.

This is a complete example of a Patitas template.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from patitas import html, raw, HTML
from patitas.elements import (
    article, aside, div, h1, h2, p, span, time as time_elem,
    a, ul, li, nav, header, footer, main,
)
from patitas.utils import cx

if TYPE_CHECKING:
    from bengal.core import Page, Site


# --- Helper Components (just functions!) ---

def format_date(dt) -> str:
    """Format a datetime for display."""
    return dt.strftime("%B %d, %Y") if dt else ""


def tag_list(tags: list[str], site: "Site") -> HTML:
    """Render a list of tags."""
    if not tags:
        return html[""]

    return html[
        ul(class_="tag-list")[
            [
                li[a(href=f"/tags/{tag}/")[tag]]
                for tag in tags
            ]
        ]
    ]


def author_card(author: str | None) -> HTML:
    """Render author info."""
    if not author:
        return html[""]

    return html[
        div(class_="author-card")[
            span(class_="author-name")[f"By {author}"]
        ]
    ]


def reading_time(content: str) -> str:
    """Calculate reading time."""
    words = len(content.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


# --- Layout ---

def base_layout(
    site: "Site",
    *,
    title: str,
    content: HTML,
    sidebar: HTML | None = None,
) -> HTML:
    """Base page layout."""
    from patitas.elements import (
        doctype, html as html_elem, head, body, title as title_elem,
        meta, link,
    )

    return html[
        doctype(),
        html_elem(lang=site.language or "en")[
            head[
                meta(charset="utf-8"),
                meta(name="viewport", content="width=device-width, initial-scale=1"),
                title_elem[f"{title} | {site.title}"],
                link(rel="stylesheet", href="/css/style.css"),
            ],
            body(class_="blog-post-page")[
                header(class_="site-header")[
                    nav[
                        a(href="/", class_="logo")[site.title],
                    ]
                ],
                main(class_="main-content")[
                    div(class_="container")[
                        content,
                        sidebar and aside(class_="sidebar")[sidebar],
                    ]
                ],
                footer(class_="site-footer")[
                    f"© {site.copyright_year or 2025} {site.author or site.title}"
                ],
            ],
        ],
    ]


# --- Main Template ---

def render(page: "Page", site: "Site", **context) -> str:
    """
    Render a blog post page.

    This is the main entry point called by PatitasEngine.

    Args:
        page: The Page being rendered
        site: The Site instance
        **context: Additional context variables

    Returns:
        Rendered HTML string
    """
    content = html[
        article(
            class_=cx(
                "blog-post",
                ("blog-post--featured", getattr(page, "featured", False)),
                ("blog-post--draft", getattr(page, "draft", False)),
            )
        )[
            # Header
            header(class_="post-header")[
                h1(class_="post-title")[page.title],
                div(class_="post-meta")[
                    page.date and time_elem(datetime=page.date.isoformat())[
                        format_date(page.date)
                    ],
                    span(class_="reading-time")[reading_time(page.content or "")],
                    author_card(getattr(page, "author", None)),
                ],
            ],

            # Content (markdown rendered to HTML)
            div(class_="post-content")[
                raw(page.content_html or page.rendered_html or "")
            ],

            # Tags
            footer(class_="post-footer")[
                tag_list(getattr(page, "tags", []), site),
            ],
        ]
    ]

    # Optional sidebar with table of contents
    sidebar = None
    if hasattr(page, "toc") and page.toc:
        sidebar = html[
            nav(class_="toc")[
                h2["Table of Contents"],
                raw(page.toc),
            ]
        ]

    return str(base_layout(
        site,
        title=page.title,
        content=content,
        sidebar=sidebar,
    ))
```

---

## Configuration

### Site Configuration

```yaml
# bengal.yaml
site:
  title: "My Site"
  template_engine: patitas  # "jinja2" | "patitas"
```

### Optional Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
patitas = ["patitas>=0.1.0"]
templates = ["patitas>=0.1.0"]  # Alias
```

```bash
# Installation
pip install bengal[patitas]
# or
pip install bengal[templates]
```

---

## Migration Path

### Phase 1: Abstraction Layer (No Breaking Changes)

1. Create `TemplateEngineProtocol`
2. Refactor `TemplateEngine` → `JinjaEngine`
3. Add `create_template_engine()` factory
4. Update all 15 callsites to use factory
5. Add backward compatibility alias: `TemplateEngine = JinjaEngine`

**User Impact**: None. Default behavior unchanged.

### Phase 2: Patitas Engine (Opt-in)

1. Implement `PatitasEngine`
2. Add configuration option
3. Add `bengal[patitas]` optional dependency
4. Create example Patitas theme

**User Impact**: Opt-in only. Jinja2 remains default.

### Phase 3: Hybrid Support (Future)

1. Allow mixing Jinja2 and Patitas templates
2. Fallback chain: Patitas → Jinja2 → error
3. CLI commands for template discovery

---

## Callsite Updates

All 15 callsites need updating:

```python
# Before
from bengal.rendering.template_engine import TemplateEngine
engine = TemplateEngine(site)

# After
from bengal.rendering.engines import create_template_engine
engine = create_template_engine(site)
```

### Affected Files

1. `bengal/rendering/pipeline/core.py`
2. `bengal/orchestration/build/initialization.py`
3. `bengal/postprocess/special_pages.py` (2 locations)
4. `bengal/services/validation.py`
5. `bengal/cli/commands/explain.py`
6. `bengal/cli/commands/theme.py` (2 locations)
7. `bengal/server/component_preview.py` (2 locations)
8. `bengal/health/validators/rendering.py`
9. `bengal/utils/swizzle.py`

### Backward Compatibility

```python
# bengal/rendering/template_engine/__init__.py
from bengal.rendering.engines.jinja import JinjaEngine

# Backward compatibility - deprecated alias
TemplateEngine = JinjaEngine

__all__ = ["TemplateEngine", "JinjaEngine"]
```

---

## Comparison: Jinja2 vs Patitas

| Aspect | Jinja2 | Patitas |
|--------|--------|---------|
| File extension | `.html` | `.py` |
| Syntax | `{{ var }}`, `{% for %}` | Pure Python |
| Learning curve | New DSL | None (just Python) |
| IDE support | Plugin required | Full native |
| Type checking | None | Full mypy support |
| Auto-completion | Limited | Full |
| Refactoring | Manual | IDE-assisted |
| Components | Macros, includes | Functions, imports |
| Inheritance | `{% extends %}` | Function parameters |
| Testing | Complex | Standard pytest |

### When to Use Each

**Use Jinja2 (default) when:**
- Existing theme uses Jinja2
- Designers need to edit templates
- Maximum compatibility needed
- Simple variable substitution

**Use Patitas when:**
- Type safety is important
- Complex component logic
- IDE support is valued
- Testing templates is needed
- "It's just Python" resonates

---

## Implementation Plan

### Week 1: Abstraction Layer

- [ ] Create `bengal/rendering/engines/` package
- [ ] Define `TemplateEngineProtocol`
- [ ] Create `JinjaEngine` (refactored from `TemplateEngine`)
- [ ] Implement `create_template_engine()` factory
- [ ] Add backward compatibility aliases
- [ ] Update tests

### Week 2: Callsite Migration

- [ ] Update all 15 callsites to use factory
- [ ] Add deprecation warnings for direct `TemplateEngine` usage
- [ ] Update documentation
- [ ] Integration tests

### Week 3: Patitas Engine

- [ ] Implement `PatitasEngine`
- [ ] Add configuration option
- [ ] Create `bengal[patitas]` optional dependency
- [ ] Error handling and logging

### Week 4: Polish

- [ ] Create example Patitas theme (subset of default)
- [ ] CLI support for template engine info
- [ ] Documentation and migration guide
- [ ] Performance benchmarks

---

## Open Questions

### Q1: Should Patitas templates be `.py` files?

**Options**:
- A) `.py` files (proposed) — standard Python, full tooling support
- B) `.pyt` files — distinguishable, but loses IDE support
- C) Either — detect by extension

**Recommendation**: A) `.py` files. The whole point is "just Python."

### Q2: Should we support hybrid themes?

**Options**:
- A) Single engine per site — simpler, clearer
- B) Fallback chain — more flexible, complex
- C) Explicit per-template — maximum control

**Recommendation**: A for Phase 2, consider B for Phase 3.

### Q3: How to handle template profiling for Patitas?

**Options**:
- A) Use Python's built-in profiler
- B) Manual timing decorators
- C) Skip (Patitas is already fast)

**Recommendation**: A) Standard Python profiling. It's just Python!

---

## Success Criteria

1. **Zero Breaking Changes**: All existing sites work unchanged
2. **Clean Abstraction**: Protocol-based, not inheritance
3. **Simple Config**: One line to switch engines
4. **Full Feature Parity**: Patitas can do everything Jinja2 can
5. **Documentation**: Clear migration guide and examples
6. **Performance**: Patitas should be ≥ Jinja2 speed

---

## References

- [RFC: patitas](rfc-bengal-templates.md) — Underlying templating library
- [PEP 544: Protocols](https://peps.python.org/pep-0544/) — Structural subtyping
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [SvelteKit](https://kit.svelte.dev/) — Inspiration for "use the platform" philosophy

---

## Appendix: Full File Structure

```
bengal/rendering/
├── engines/
│   ├── __init__.py          # Factory and exports
│   ├── protocol.py          # TemplateEngineProtocol
│   ├── jinja.py             # JinjaEngine (refactored)
│   └── patitas.py           # PatitasEngine (new)
├── template_engine/         # Legacy (preserved for compatibility)
│   ├── __init__.py          # Re-exports JinjaEngine as TemplateEngine
│   ├── environment.py       # Jinja2 environment setup (used by JinjaEngine)
│   └── ...                  # Other existing modules
└── ...

themes/
├── default/                 # Jinja2 theme (unchanged)
│   └── templates/
│       ├── base.html
│       └── ...
└── patitas-default/         # Patitas theme (new, optional)
    └── templates/
        ├── base.py
        ├── blog/
        │   ├── single.py
        │   └── list.py
        └── ...
```
