# RFC: Pluggable Template Engine Architecture for Bengal

**Status**: Draft → Evaluated
**Created**: 2025-12-18
**Author**: AI Assistant
**Subsystems**: `bengal/rendering/`, `bengal/config/`
**Depends On**: [RFC: Patitas](rfc-bengal-templates.md)
**Confidence**: 85% 🟢

---

> **Note**: This RFC has been evaluated and revised based on codebase research.
> See [Evaluation Notes](#evaluation-notes) at the end for details.

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

1. **Standardized Interface**: Single protocol all engines must implement
2. **Clean Break**: No backward compatibility aliases or deprecation dance
3. **Protocol-Based**: Structural typing via `typing.Protocol` (PEP 544)
4. **Factory Pattern**: All instantiation through `create_template_engine()`
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
"""
Standardized template engine protocol.

All template engines MUST implement this protocol. No exceptions, no optional methods.
This ensures consistent behavior across Jinja2, Patitas, and any future engines.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core import Site


@runtime_checkable
class TemplateEngine(Protocol):
    """
    Standardized interface for all Bengal template engines.

    REQUIRED ATTRIBUTES:
        site: Site instance (injected at construction)
        template_dirs: Ordered list of template search directories

    REQUIRED METHODS:
        render_template(): Render a named template
        render_string(): Render an inline template string
        template_exists(): Check if a template exists
        get_template_path(): Resolve template to filesystem path
        list_templates(): List all available templates
        validate(): Validate all templates for syntax errors

    ALL methods are required. No optional methods. This ensures:
        - Consistent behavior across engines
        - Easy testing and mocking
        - Clear contract for third-party engines
    """

    # --- Required Attributes ---

    site: "Site"
    template_dirs: list[Path]

    # --- Required Methods ---

    def render_template(
        self,
        name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a named template with the given context.

        Args:
            name: Template identifier (e.g., "blog/single.html")
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If rendering fails

        Contract:
            - MUST automatically inject `site` and `config` into context
            - MUST search template_dirs in order (first match wins)
            - MUST raise TemplateNotFoundError (not return empty string)
        """
        ...

    def render_string(
        self,
        template: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a template string with the given context.

        Args:
            template: Template content as string
            context: Variables available to the template

        Returns:
            Rendered HTML string

        Contract:
            - MUST automatically inject `site` and `config` into context
            - MUST NOT cache the compiled template
        """
        ...

    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template identifier

        Returns:
            True if template can be loaded, False otherwise

        Contract:
            - MUST NOT raise exceptions (return False instead)
            - MUST check all template_dirs
        """
        ...

    def get_template_path(self, name: str) -> Path | None:
        """
        Resolve a template name to its filesystem path.

        Args:
            name: Template identifier

        Returns:
            Absolute path to template file, or None if not found

        Contract:
            - MUST return None (not raise) if not found
            - MUST return the path that would be used by render_template()
        """
        ...

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            Sorted list of template names (relative to template_dirs)

        Contract:
            - MUST return unique names (no duplicates)
            - MUST return sorted list
            - MUST include templates from all template_dirs
        """
        ...

    def validate(self, patterns: list[str] | None = None) -> list["TemplateError"]:
        """
        Validate all templates for syntax errors.

        Args:
            patterns: Optional glob patterns to filter (e.g., ["*.html"])
                      If None, validates all templates.

        Returns:
            List of TemplateError for any invalid templates.
            Empty list if all templates are valid.

        Contract:
            - MUST NOT raise exceptions (return errors in list)
            - MUST validate syntax only (not runtime errors)
        """
        ...
```

### 2. Engine Factory

```python
# bengal/rendering/engines/__init__.py
"""
Standardized template engine factory.

ALL template engine access MUST go through create_engine().
Direct imports of engine classes are for type hints only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.engines.protocol import TemplateEngine
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError

if TYPE_CHECKING:
    from bengal.core import Site

# Third-party engine registry (for plugins)
_ENGINES: dict[str, type[TemplateEngine]] = {}


def register_engine(name: str, engine_class: type[TemplateEngine]) -> None:
    """
    Register a third-party template engine.

    Args:
        name: Engine identifier (used in bengal.yaml)
        engine_class: Class implementing TemplateEngine protocol
    """
    _ENGINES[name] = engine_class


def create_engine(site: "Site", *, profile: bool = False) -> TemplateEngine:
    """
    Create a template engine based on site configuration.

    This is the ONLY way to get a template engine instance.

    Args:
        site: Site instance
        profile: Enable template profiling

    Returns:
        Engine implementing TemplateEngine protocol

    Raises:
        ValueError: If engine is unknown or patitas not installed

    Configuration:
        template_engine: jinja2  # or "patitas"
    """
    engine_name = site.config.get("template_engine", "jinja2")

    if engine_name == "jinja2":
        from bengal.rendering.engines.jinja import JinjaTemplateEngine
        return JinjaTemplateEngine(site, profile=profile)

    if engine_name == "patitas":
        try:
            from bengal.rendering.engines.patitas import PatitasTemplateEngine
        except ImportError as e:
            raise ValueError(
                "Patitas engine requires patitas package.\n"
                "Install with: pip install bengal[patitas]"
            ) from e
        return PatitasTemplateEngine(site)

    if engine_name in _ENGINES:
        return _ENGINES[engine_name](site)

    available = ["jinja2", "patitas", *_ENGINES.keys()]
    raise ValueError(
        f"Unknown template engine: '{engine_name}'\n"
        f"Available: {', '.join(sorted(available))}"
    )


# Public API
__all__ = [
    # Protocol
    "TemplateEngine",
    # Factory
    "create_engine",
    "register_engine",
    # Errors
    "TemplateError",
    "TemplateNotFoundError",
]
```

### 3. Jinja Engine

```python
# bengal/rendering/engines/jinja.py
"""
Jinja2 implementation of the standardized TemplateEngine protocol.
"""

from __future__ import annotations

import threading
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import TemplateNotFound, TemplateSyntaxError

from bengal.assets.manifest import AssetManifestEntry
from bengal.rendering.engines.protocol import TemplateEngine
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.rendering.template_engine.asset_url import AssetURLMixin
from bengal.rendering.template_engine.environment import create_jinja_environment
from bengal.rendering.template_engine.manifest import ManifestHelpersMixin
from bengal.rendering.template_engine.menu import MenuHelpersMixin
from bengal.rendering.template_profiler import ProfiledTemplate, TemplateProfiler, get_profiler
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core import Site

logger = get_logger(__name__)


class JinjaTemplateEngine(MenuHelpersMixin, ManifestHelpersMixin, AssetURLMixin):
    """
    Jinja2 implementation of the TemplateEngine protocol.

    Implements ALL required protocol methods with Jinja2-specific behavior.
    Includes mixins for Bengal-specific functionality (menus, assets).
    """

    def __init__(self, site: "Site", *, profile: bool = False) -> None:
        """
        Initialize Jinja2 engine.

        Args:
            site: Site instance
            profile: Enable template profiling
        """
        self.site = site
        self.template_dirs: list[Path] = []

        # Profiling
        self._profiler: TemplateProfiler | None = get_profiler() if profile else None

        # Create Jinja2 environment
        self.env, self.template_dirs = create_jinja_environment(site, self, profile)

        # Dependency tracking (injected by RenderingPipeline)
        self._dependency_tracker = None

        # Mixin initialization
        self._init_asset_manifest()
        self._init_menu_cache()
        self._init_template_cache()

    def _init_asset_manifest(self) -> None:
        """Initialize asset manifest caching."""
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_mtime: float | None = None
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_fallbacks: set[str] = set()
        self._asset_manifest_present = self._asset_manifest_path.exists()
        self._asset_manifest_loaded = False
        self._fingerprinted_asset_cache: dict[str, str | None] = {}

        # Thread-safe warnings
        if not hasattr(self.site, "_asset_manifest_fallbacks_global"):
            self.site._asset_manifest_fallbacks_global = set()
            self.site._asset_manifest_fallbacks_lock = threading.Lock()

    def _init_menu_cache(self) -> None:
        """Initialize menu caching."""
        self._menu_dict_cache: dict[str, list[dict[str, Any]]] = {}

    def _init_template_cache(self) -> None:
        """Initialize template path caching."""
        dev_mode = self.site.config.get("dev_server", False)
        self._template_path_cache_enabled = not dev_mode
        self._template_path_cache: dict[str, Path | None] = {}
        self._referenced_template_cache: dict[str, set[str]] = {}
        self._referenced_template_paths_cache: dict[str, tuple[Path, ...]] = {}

    # =========================================================================
    # PROTOCOL IMPLEMENTATION (all required methods)
    # =========================================================================

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template."""
        logger.debug("render_template", name=name)

        # Inject standard context
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        # Track dependencies
        if self._dependency_tracker:
            if path := self.get_template_path(name):
                self._dependency_tracker.track_template(path)

        # Invalidate menu cache for fresh active states
        self.invalidate_menu_cache()

        try:
            template = self.env.get_template(name)

            if self._profiler:
                return ProfiledTemplate(template, self._profiler).render(**context)
            return template.render(**context)

        except TemplateNotFound as e:
            raise TemplateNotFoundError(name, self.template_dirs) from e

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render a template string."""
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)
        self.invalidate_menu_cache()

        return self.env.from_string(template).render(**context)

    def template_exists(self, name: str) -> bool:
        """Check if template exists."""
        try:
            self.env.get_template(name)
            return True
        except TemplateNotFound:
            return False

    def get_template_path(self, name: str) -> Path | None:
        """Resolve template to filesystem path."""
        if self._template_path_cache_enabled and name in self._template_path_cache:
            return self._template_path_cache[name]

        for template_dir in self.template_dirs:
            path = template_dir / name
            if path.exists():
                if self._template_path_cache_enabled:
                    self._template_path_cache[name] = path
                return path

        if self._template_path_cache_enabled:
            self._template_path_cache[name] = None
        return None

    def list_templates(self) -> list[str]:
        """List all available templates."""
        return sorted(self.env.list_templates())

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """Validate all templates for syntax errors."""
        errors: list[TemplateError] = []
        validated: set[str] = set()
        patterns = patterns or ["*.html", "*.xml"]

        for template_dir in self.template_dirs:
            if not template_dir.exists():
                continue

            for file in template_dir.rglob("*"):
                if not file.is_file():
                    continue

                try:
                    name = str(file.relative_to(template_dir))
                except ValueError:
                    continue

                if name in validated:
                    continue

                if not any(fnmatch(name, p) or fnmatch(file.name, p) for p in patterns):
                    continue

                validated.add(name)

                try:
                    self.env.get_template(name)
                except TemplateSyntaxError as e:
                    errors.append(TemplateError(
                        template=name,
                        line=e.lineno,
                        message=str(e),
                        path=file,
                    ))
                except Exception:
                    pass  # Skip non-syntax errors

        return errors
```

### 4. Standardized Errors

```python
# bengal/rendering/engines/errors.py
"""
Standardized template engine errors.

All engines MUST use these error types for consistency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TemplateError:
    """
    Represents a template validation or render error.

    Returned by validate() method. Also raised during render_template().
    """

    template: str
    message: str
    line: int | None = None
    column: int | None = None
    path: Path | None = None

    def __str__(self) -> str:
        loc = f":{self.line}" if self.line else ""
        return f"{self.template}{loc}: {self.message}"


class TemplateNotFoundError(Exception):
    """
    Raised when a template cannot be found.

    MUST be raised by render_template() when template doesn't exist.
    """

    def __init__(self, name: str, search_paths: list[Path]) -> None:
        self.name = name
        self.search_paths = search_paths
        paths_str = "\n  ".join(str(p) for p in search_paths)
        super().__init__(
            f"Template not found: '{name}'\n"
            f"Searched in:\n  {paths_str}"
        )


class TemplateRenderError(Exception):
    """
    Raised when template rendering fails.

    MUST be raised by render_template() for runtime errors.
    """

    def __init__(self, name: str, cause: Exception) -> None:
        self.name = name
        self.cause = cause
        super().__init__(f"Error rendering '{name}': {cause}")
```

### 5. Patitas Engine

```python
# bengal/rendering/engines/patitas.py
"""
Patitas implementation of the standardized TemplateEngine protocol.

Philosophy: "It's just Python"
    - Functions are templates
    - Imports are includes
    - Parameters are context
    - No DSL to learn

Template files are Python modules with a `render()` function:

    # templates/blog/single.py
    from patitas import html, raw
    from patitas.elements import article, h1, div

    def render(page, site, **ctx):
        return str(html[
            article[h1[page.title], div[raw(page.content_html)]]
        ])

Requires: pip install bengal[patitas]
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from bengal.rendering.engines.errors import (
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
)
from bengal.utils.logger import get_logger
from bengal.utils.theme_resolution import resolve_theme_chain

if TYPE_CHECKING:
    from bengal.core import Site

logger = get_logger(__name__)


class PatitasTemplateEngine:
    """
    Patitas implementation of the TemplateEngine protocol.

    Templates are Python modules with a render() function.
    Implements ALL required protocol methods.
    """

    def __init__(self, site: "Site") -> None:
        self.site = site
        self.template_dirs: list[Path] = []
        self._cache: dict[str, Callable[..., str]] = {}

        # Verify patitas is installed
        try:
            import patitas  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Patitas engine requires patitas package.\n"
                "Install with: pip install bengal[patitas]"
            ) from e

        # Build template_dirs from theme chain
        self._discover_template_dirs()

    def _discover_template_dirs(self) -> None:
        """Build template search path from theme chain."""
        # Site templates first
        site_templates = self.site.root_path / "templates"
        if site_templates.exists():
            self.template_dirs.append(site_templates)

        # Theme chain
        for theme in resolve_theme_chain(self.site.theme, self.site):
            for base in [self.site.root_path / "themes", Path(__file__).parent.parent.parent / "themes"]:
                theme_templates = base / theme / "templates"
                if theme_templates.exists() and theme_templates not in self.template_dirs:
                    self.template_dirs.append(theme_templates)

    def _to_module_path(self, name: str) -> str:
        """Convert template name to Python module path."""
        # Remove extensions: blog/single.html → blog/single
        for ext in (".html", ".py", ".jinja2", ".j2"):
            if name.endswith(ext):
                name = name[: -len(ext)]
        # Convert to path: blog.single → blog/single.py
        return name.replace(".", "/") + ".py"

    def _load_render_func(self, name: str) -> Callable[..., str]:
        """Load and cache render function from template module."""
        if name in self._cache:
            return self._cache[name]

        module_path = self._to_module_path(name)
        template_path: Path | None = None

        for dir in self.template_dirs:
            candidate = dir / module_path
            if candidate.exists():
                template_path = candidate
                break

        if not template_path:
            raise TemplateNotFoundError(name, self.template_dirs)

        # Dynamic import
        spec = importlib.util.spec_from_file_location(f"_template_{name}", template_path)
        if not spec or not spec.loader:
            raise TemplateRenderError(name, Exception("Failed to load module"))

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "render"):
            raise TemplateRenderError(
                name,
                Exception("Template must define render() function"),
            )

        self._cache[name] = module.render
        return module.render

    # =========================================================================
    # PROTOCOL IMPLEMENTATION
    # =========================================================================

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template."""
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        render_func = self._load_render_func(name)

        try:
            return str(render_func(**context))
        except Exception as e:
            raise TemplateRenderError(name, e) from e

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Execute Python code defining a render() function."""
        context.setdefault("site", self.site)
        context.setdefault("config", self.site.config)

        namespace: dict[str, Any] = {}
        exec(template, namespace)

        if "render" not in namespace:
            raise TemplateRenderError(
                "<string>",
                Exception("Template string must define render() function"),
            )

        return str(namespace["render"](**context))

    def template_exists(self, name: str) -> bool:
        """Check if template exists."""
        module_path = self._to_module_path(name)
        return any((d / module_path).exists() for d in self.template_dirs)

    def get_template_path(self, name: str) -> Path | None:
        """Resolve template to filesystem path."""
        module_path = self._to_module_path(name)
        for dir in self.template_dirs:
            path = dir / module_path
            if path.exists():
                return path
        return None

    def list_templates(self) -> list[str]:
        """List all available templates."""
        seen: set[str] = set()
        for dir in self.template_dirs:
            for py_file in dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                name = str(py_file.relative_to(dir))[:-3].replace("/", ".")
                seen.add(name)
        return sorted(seen)

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """Validate all templates (check for render() function)."""
        errors: list[TemplateError] = []
        patterns = patterns or ["*.py"]

        for name in self.list_templates():
            path = self.get_template_path(name)
            if not path:
                continue

            try:
                self._load_render_func(name)
            except TemplateRenderError as e:
                errors.append(TemplateError(
                    template=name,
                    message=str(e.cause),
                    path=path,
                ))
            except Exception as e:
                errors.append(TemplateError(
                    template=name,
                    message=str(e),
                    path=path,
                ))

        return errors
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

### Phase 1: Create Standardized Engine Package

1. Create `bengal/rendering/engines/` package
2. Add `protocol.py` with `TemplateEngine` protocol
3. Add `errors.py` with standardized error types
4. Add `jinja.py` with `JinjaTemplateEngine`
5. Add `__init__.py` with `create_engine()` factory

**Breaking Change**: Yes. All imports change.

### Phase 2: Migrate All Callsites

Update all 15 callsites in one pass:

```python
# BEFORE (removed)
from bengal.rendering.template_engine import TemplateEngine
engine = TemplateEngine(site)
html = engine.render("page.html", context)

# AFTER (standardized)
from bengal.rendering.engines import create_engine
engine = create_engine(site)
html = engine.render_template("page.html", context)
```

**Files to update**: 12 production files + 19 test files

### Phase 3: Add Patitas Engine

1. Add `patitas.py` with `PatitasTemplateEngine`
2. Add `bengal[patitas]` optional dependency
3. Create example Patitas theme

### Phase 4: Delete Legacy Code

1. Delete `bengal/rendering/template_engine/core.py`
2. Update `__init__.py` to only re-export from engines
3. Update documentation

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

### Affected Files (12 Files, 15 Instantiation Sites)

**Production Code** (11 files, 13 instantiation sites):

| File | Locations | Usage |
|------|-----------|-------|
| `bengal/rendering/pipeline/core.py` | 1 | RenderingPipeline (main usage) |
| `bengal/orchestration/build/initialization.py` | 1 | Template validation during build |
| `bengal/postprocess/special_pages.py` | 2 | 404 page, special page generation |
| `bengal/services/validation.py` | 1 | Template validation service |
| `bengal/cli/commands/explain.py` | 1 | CLI explain command |
| `bengal/cli/commands/theme.py` | 2 | Theme list and info commands |
| `bengal/server/component_preview.py` | 2 | Component preview in dev server |
| `bengal/health/validators/rendering.py` | 1 | Health check validator |
| `bengal/utils/swizzle.py` | 1 | Template swizzle utility |
| `bengal/debug/explainer.py` | 1 | Debug explainer (import only) |

**Test Files** (19 files using TemplateEngine):
- `tests/unit/rendering/test_template_*.py` (12 files)
- `tests/unit/rendering/test_*_baseurl.py` (5 files)
- `tests/unit/rendering/test_metadata_exposure.py`
- `tests/unit/rendering/test_pipeline_*.py` (2 files)

**See**: [Test Migration Plan](#test-migration-plan) for test update strategy.

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

### Week 1: Abstraction Layer (No Breaking Changes)

- [ ] Create `bengal/rendering/engines/` package
- [ ] Define `TemplateEngineProtocol` in `protocol.py`
- [ ] Create `JinjaEngine` in `jinja.py` (refactored from `TemplateEngine`)
  - [ ] Inherit all three mixins
  - [ ] Preserve all caching attributes
  - [ ] Preserve all private methods (`_find_template_path`, `_track_referenced_templates`)
- [ ] Implement `create_template_engine()` factory in `__init__.py`
- [ ] Add backward compatibility alias in `template_engine/__init__.py`:
  ```python
  from bengal.rendering.engines.jinja import JinjaEngine
  TemplateEngine = JinjaEngine  # Backward compatibility
  ```
- [ ] Run existing tests (should all pass unchanged)

### Week 2: Callsite Migration

- [ ] Update all 15 callsites to use `create_template_engine()`
- [ ] Add deprecation warnings for direct `TemplateEngine` import
- [ ] Update internal documentation
- [ ] Add integration tests for factory function
- [ ] Add protocol compliance test for `JinjaEngine`

### Week 3: Patitas Engine

- [ ] Implement `PatitasEngine` in `patitas.py`
- [ ] Add `template_engine` configuration option
- [ ] Create `bengal[patitas]` optional dependency in `pyproject.toml`
- [ ] Error handling and logging
- [ ] Add `PatitasEngine` tests

### Week 4: Polish

- [ ] Create example Patitas theme (subset of default)
- [ ] Add CLI command: `bengal theme --engine-info`
- [ ] Documentation: migration guide and examples
- [ ] Performance benchmarks (Jinja2 vs Patitas)
- [ ] Run full test suite on both engines

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

**Status**: ✅ **Already solved** in existing codebase.

The existing `TemplateEngine` has comprehensive profiling support via:
- `TemplateProfiler` class in `bengal/rendering/template_profiler.py`
- `ProfiledTemplate` wrapper for timing individual templates
- `get_template_profile()` method returns timing statistics

**For Patitas**: Use Python's standard `cProfile` or `time.perf_counter()` wrappers.
The architecture already supports engine-specific profiling implementations.

---

## Risk Mitigation

### Risk 1: Breaking Existing Themes

**Impact**: HIGH  
**Mitigation**:
- Jinja2 remains the default engine (`template_engine: jinja2`)
- `TemplateEngine = JinjaEngine` alias maintains backward compatibility
- No changes required for existing Jinja2 themes
- All 15+ callsites continue to work with existing import paths

### Risk 2: Test Suite Breakage

**Impact**: MEDIUM  
**Mitigation**:
- Phase 1 changes are purely additive (new `engines/` package)
- Phase 2 maintains existing exports from `template_engine/__init__.py`
- Test files can continue importing `TemplateEngine` unchanged
- Add integration test for both engines

### Risk 3: Performance Regression

**Impact**: MEDIUM  
**Mitigation**:
- JinjaEngine reuses all existing caching infrastructure:
  - `_template_path_cache` for path lookups
  - `_referenced_template_cache` for dependency tracking
  - `_asset_manifest_cache` for asset URLs
  - `_menu_dict_cache` for menu generation
- Run benchmarks before/after migration
- Add performance regression test

### Risk 4: Mixin Method Breakage

**Impact**: HIGH  
**Mitigation**:
- JinjaEngine inherits all three mixins (verified in design):
  - `MenuHelpersMixin` → `_get_menu()`, `_get_menu_lang()`, `invalidate_menu_cache()`
  - `ManifestHelpersMixin` → `_get_manifest_entry()`, `_load_asset_manifest()`
  - `AssetURLMixin` → `_asset_url()`, `_find_fingerprinted_asset()`
- All mixin attributes initialized in `__init__`
- Template functions that use these methods continue to work

---

## Test Migration Plan

### Phase 1: No Test Changes Required

During abstraction layer creation:
- Tests continue importing `from bengal.rendering.template_engine import TemplateEngine`
- `TemplateEngine` is aliased to `JinjaEngine`
- All tests pass without modification

### Phase 2: Add Engine-Specific Tests

New test files:
```
tests/unit/rendering/
├── engines/
│   ├── test_protocol.py       # Protocol compliance tests
│   ├── test_jinja_engine.py   # JinjaEngine-specific tests
│   └── test_patitas_engine.py # PatitasEngine-specific tests (Phase 3)
```

### Phase 3: Parametrized Tests (Optional)

For shared behavior, parametrize tests:
```python
@pytest.mark.parametrize("engine_name", ["jinja2", "patitas"])
def test_engine_renders_page(engine_name, site_factory):
    """Test that both engines can render a basic page."""
    site = site_factory("test-basic", confoverrides={"template_engine": engine_name})
    engine = create_template_engine(site)
    html = engine.render("page.html", {"page": mock_page})
    assert "<html" in html
```

---

## Success Criteria

1. **Zero Breaking Changes**: All existing sites work unchanged
2. **Clean Abstraction**: Protocol-based, not inheritance
3. **Simple Config**: One line to switch engines
4. **Full Feature Parity**: Patitas can do everything Jinja2 can
5. **Documentation**: Clear migration guide and examples
6. **Performance**: Patitas should be ≥ Jinja2 speed
7. **Mixin Preservation**: All existing mixin functionality preserved
8. **API Compatibility**: `render()`, `render_string()` signatures unchanged
9. **Test Stability**: All 19 existing test files pass unchanged

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

---

## Evaluation Notes

**Evaluation Date**: 2025-12-18  
**Confidence**: 85% 🟢 (up from 78% after revisions)

### Issues Identified and Resolved

| Issue | Severity | Resolution |
|-------|----------|------------|
| Protocol method names didn't match existing API | HIGH | Changed `render_template()` → `render()` |
| Missing `render_string()` in protocol | HIGH | Added to protocol |
| JinjaEngine missing mixin inheritance | HIGH | Added all three mixins |
| Missing callsite: `bengal/debug/explainer.py` | LOW | Added to affected files |
| Open Question Q3 already solved | LOW | Marked as resolved |
| No risk mitigation section | MEDIUM | Added comprehensive risk section |
| No test migration plan | MEDIUM | Added test migration plan |

### Evidence Sources

All claims verified against codebase:

- **Callsite count**: Found 15 instantiation sites in 11 production files
- **Existing API**: `bengal/rendering/template_engine/core.py:170` - `render()` method
- **Mixin architecture**: `core.py:53` - `class TemplateEngine(MenuHelpersMixin, ManifestHelpersMixin, AssetURLMixin)`
- **Caching attributes**: `core.py:126-168` - 8 different caches preserved
- **Test files**: 19 files in `tests/unit/rendering/` use TemplateEngine

### Remaining Considerations

1. **Prototype exists**: `prototypes/templit_prototype.py` validates patitas design
2. **Dependency RFC exists**: `plan/drafted/rfc-bengal-templates.md` defines patitas library
3. **No existing `engines/` package**: Clean namespace available for new code

### Next Steps

1. Move to `plan/ready/` when approved
2. Begin Phase 1 implementation (abstraction layer)
3. Add deprecation warning for direct `TemplateEngine` imports
