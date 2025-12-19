# RFC: Pluggable Template Engine Architecture

**Status**: Evaluated  
**Created**: 2025-12-18  
**Revised**: 2025-12-18 (Mako + standardization focus)  
**Subsystems**: `bengal/rendering/engines/`  
**Confidence**: 92% 🟢

---

> **Core Insight**: The value is in the **pluggable architecture**, not any specific engine.  
> Users can escape Jinja2 hell by swapping to Mako, Patitas, or any future engine.

---

## Executive Summary

This RFC proposes a **pluggable template engine architecture** that lets users escape Jinja2 by swapping to alternative engines.

**The Problem**: Jinja2 is painful. Cryptic errors, weird syntax, limited Python, awful macros.

**The Solution**: Make template engines swappable via a standardized protocol.

```yaml
# bengal.yaml - pick your poison
site:
  template_engine: jinja2  # Default (existing behavior)
  template_engine: mako    # HTML-first, real Python, better errors
  template_engine: patitas # Python-native (no HTML files)
```

**Key Changes**:
1. Define `TemplateEngine` protocol — standardized interface
2. Wrap existing code as `JinjaTemplateEngine`
3. Add `MakoTemplateEngine` — HTML + real Python (first alternative)
4. Add `PatitasTemplateEngine` — pure Python (power users)
5. Single factory: `create_engine(site)` — only way to get an engine

**Why Mako First?**
- Battle-tested (Reddit, Pyramid, Pylons)
- HTML-first (designers can still read it)
- Real Python logic (not a crippled DSL)
- Better error messages than Jinja2
- Actual ecosystem (unlike Patitas)

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

1. **Escape Hatch from Jinja2**: Users can switch engines without rewriting the SSG
2. **Standardized Protocol**: One interface, multiple implementations
3. **HTML-First Option**: Mako keeps HTML visible (unlike Patitas)
4. **Clean Break**: No backward compatibility cruft
5. **Future-Proof**: Easy to add more engines later

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

    if engine_name == "mako":
        try:
            from bengal.rendering.engines.mako import MakoTemplateEngine
        except ImportError as e:
            raise ValueError(
                "Mako engine requires mako package.\n"
                "Install with: pip install bengal[mako]"
            ) from e
        return MakoTemplateEngine(site)

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

    available = ["jinja2", "mako", "patitas", *_ENGINES.keys()]
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

### 5. Mako Engine (Recommended Alternative)

```python
# bengal/rendering/engines/mako.py
"""
Mako implementation of the standardized TemplateEngine protocol.

Philosophy: HTML-first with real Python
    - Templates are .html files (designers can read them)
    - Python blocks use % or ${...} syntax
    - Real Python logic, not a crippled DSL
    - Great error messages with line numbers
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mako.lookup import TemplateLookup
from mako.exceptions import MakoException
from mako.template import Template as MakoTemplate

from bengal.core.utils.theme_resolution import resolve_theme_chain
from bengal.utils.logging import get_logger
from .errors import TemplateNotFoundError, TemplateRenderError

if TYPE_CHECKING:
    from bengal.core import Site

logger = get_logger(__name__)


class MakoTemplateEngine:
    """
    Mako implementation of the TemplateEngine protocol.

    Provides HTML-first templating with real Python logic.
    Battle-tested: Reddit, Pyramid, Pylons.
    """

    def __init__(self, site: "Site") -> None:
        self.site = site
        self.template_dirs: list[Path] = []

        # Verify mako is installed
        try:
            import mako  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Mako engine requires mako package.\n"
                "Install with: pip install bengal[mako]"
            ) from e

        # Build template_dirs from theme chain
        self._discover_template_dirs()

        # Create Mako lookup with our directories
        self._lookup = TemplateLookup(
            directories=[str(d) for d in self.template_dirs],
            module_directory="/tmp/mako_modules",
            input_encoding="utf-8",
            output_encoding="utf-8",
            strict_undefined=True,  # Fail on undefined vars (like Jinja2)
        )

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

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a Mako template."""
        try:
            template = self._lookup.get_template(name)
            return template.render(**context)
        except MakoException as e:
            raise TemplateRenderError(name, e) from e

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """Render a template string directly."""
        try:
            template = MakoTemplate(template_string, lookup=self._lookup)
            return template.render(**context)
        except MakoException as e:
            raise TemplateRenderError("<string>", e) from e

    def validate(self) -> list[str]:
        """Validate all templates for syntax errors."""
        errors = []
        for template_dir in self.template_dirs:
            for path in template_dir.rglob("*.html"):
                try:
                    rel_path = path.relative_to(template_dir)
                    self._lookup.get_template(str(rel_path))
                except MakoException as e:
                    errors.append(f"{path}: {e}")
        return errors

    def get_template_path(self, name: str) -> Path | None:
        """Get the file path for a template."""
        for template_dir in self.template_dirs:
            path = template_dir / name
            if path.exists():
                return path
        return None

    def template_exists(self, name: str) -> bool:
        """Check if a template exists."""
        return self.get_template_path(name) is not None

    def list_templates(self, pattern: str = "*.html") -> list[str]:
        """List available templates."""
        templates = []
        for template_dir in self.template_dirs:
            for path in template_dir.rglob(pattern):
                rel_path = str(path.relative_to(template_dir))
                if rel_path not in templates:
                    templates.append(rel_path)
        return sorted(templates)

    def render_page(self, page: Any) -> str:
        """Render a page using its template."""
        template_name = page.template
        context = {"page": page, "site": self.site}
        return self.render_template(template_name, context)
```

### 6. Patitas Engine (Power Users)

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

### 7. Example Patitas Template

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

### Phase 3: Add Mako Engine (Recommended Alternative)

1. Add `mako.py` with `MakoTemplateEngine`
2. Add `bengal[mako]` optional dependency
3. Create Mako test fixtures
4. Documentation: "Escaping Jinja2: Switching to Mako"

### Phase 4: Add Patitas Engine (Power Users)

1. Add `patitas.py` with `PatitasTemplateEngine`
2. Add `bengal[patitas]` optional dependency
3. Create example Patitas theme
4. Documentation: "Power User Templates with Patitas"

### Phase 5: Delete Legacy Code

1. Delete `bengal/rendering/template_engine/core.py`
2. Update `__init__.py` to only re-export from engines
3. Update documentation

---

## Callsite Migration

### The Change

All imports and method calls change:

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BEFORE (legacy, to be deleted)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from bengal.rendering.template_engine import TemplateEngine

engine = TemplateEngine(site)
html = engine.render("page.html", context)
valid = engine.validate_templates()
path = engine._find_template_path("page.html")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AFTER (standardized)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from bengal.rendering.engines import create_engine

engine = create_engine(site)
html = engine.render_template("page.html", context)
errors = engine.validate()
path = engine.get_template_path("page.html")
```

### Method Renames

| Legacy | Standardized | Notes |
|--------|--------------|-------|
| `render()` | `render_template()` | Clearer intent |
| `render_string()` | `render_string()` | Unchanged |
| `validate_templates()` | `validate()` | Simpler |
| `_find_template_path()` | `get_template_path()` | Public API |
| `list_templates()` | `list_templates()` | Unchanged |
| `template_exists()` | `template_exists()` | Unchanged |

### Files to Update (31 total)

**Production (12 files)**:

| File | Callsites | Difficulty |
|------|-----------|------------|
| `bengal/rendering/pipeline/core.py` | 1 | Easy |
| `bengal/orchestration/build/initialization.py` | 1 | Easy |
| `bengal/postprocess/special_pages.py` | 2 | Easy |
| `bengal/services/validation.py` | 1 | Easy |
| `bengal/cli/commands/explain.py` | 1 | Easy |
| `bengal/cli/commands/theme.py` | 2 | Easy |
| `bengal/server/component_preview.py` | 2 | Medium |
| `bengal/health/validators/rendering.py` | 1 | Easy |
| `bengal/utils/swizzle.py` | 1 | Easy |
| `bengal/debug/explainer.py` | 1 | Easy |

**Tests (19 files)**: Run `grep -r "TemplateEngine" tests/` to identify all usages.

### No Backward Compatibility

The legacy `bengal/rendering/template_engine/` package will be deleted after migration.
No aliases. No deprecation warnings. Clean break.

---

## Comparison: Jinja2 vs Mako vs Patitas

| Aspect | Jinja2 | Mako | Patitas |
|--------|--------|------|---------|
| **File type** | `.html` | `.html` | `.py` |
| **HTML visible** | ✅ Yes | ✅ Yes | ❌ No |
| **Python logic** | ❌ Crippled DSL | ✅ Real Python | ✅ Real Python |
| **Error messages** | ❌ Cryptic | ✅ Clear | ✅ Clear |
| **IDE support** | ⚠️ Plugin needed | ⚠️ Plugin needed | ✅ Native |
| **Type checking** | ❌ None | ❌ None | ✅ Full mypy |
| **Ecosystem** | ✅ Huge | ✅ Good | ❌ None |
| **Designer-friendly** | ✅ Yes | ✅ Yes | ❌ No |

### Side-by-Side Syntax

**Jinja2** (the nightmare):
```jinja2
{% for post in posts | sort(attribute='date') | reverse %}
  {% if post.published and not post.draft %}
    <article>
      <h2>{{ post.title | truncate(50) }}</h2>
      <p>{{ post.date | date('%B %d, %Y') }}</p>
    </article>
  {% endif %}
{% endfor %}
```

**Mako** (HTML + real Python):
```mako
% for post in sorted(posts, key=lambda p: p.date, reverse=True):
  % if post.published and not post.draft:
    <article>
      <h2>${post.title[:50]}</h2>
      <p>${post.date.strftime('%B %d, %Y')}</p>
    </article>
  % endif
% endfor
```

**Patitas** (pure Python):
```python
for post in sorted(posts, key=lambda p: p.date, reverse=True):
    if post.published and not post.draft:
        yield article[
            h2[post.title[:50]],
            p[post.date.strftime('%B %d, %Y')],
        ]
```

### When to Use Each

**Jinja2** (default):
- Existing themes work
- Maximum ecosystem support
- Team includes non-Python designers

**Mako** (recommended alternative):
- You hate Jinja2 syntax
- Want real Python logic
- Still want HTML files
- Need better error messages

**Patitas** (power users):
- Want full type checking
- Building complex component systems
- Only developers edit templates
- Don't need existing themes

---

## Implementation Plan

### Week 1: Create Engine Package + Migrate All Code

**Single PR with breaking changes**:

- [ ] Create `bengal/rendering/engines/` package:
  - [ ] `protocol.py` - `TemplateEngine` protocol
  - [ ] `errors.py` - Standardized error types
  - [ ] `jinja.py` - `JinjaTemplateEngine`
  - [ ] `__init__.py` - `create_engine()` factory
- [ ] Update all 12 production files to use new API
- [ ] Update all 19 test files to use new API
- [ ] Delete legacy `bengal/rendering/template_engine/core.py`
- [ ] Run full test suite

**Files modified**: ~35 files  
**Estimated time**: 4-6 hours (mechanical find/replace)

### Week 2: Add Mako Engine (First Alternative)

- [ ] Add `mako.py` - `MakoTemplateEngine`
- [ ] Add `bengal[mako]` optional dependency (`mako>=1.3.0`)
- [ ] Add protocol compliance tests
- [ ] Add `test-mako` test root with Mako templates
- [ ] Convert a few default theme templates to Mako as examples

### Week 3: Add Patitas Engine (Power Users)

- [ ] Add `patitas.py` - `PatitasTemplateEngine`
- [ ] Add `bengal[patitas]` optional dependency
- [ ] Add protocol compliance tests
- [ ] Add `test-patitas` test root

### Week 4: Polish + Documentation

- [ ] Add CLI: `bengal engine list` (show available engines)
- [ ] Add CLI: `bengal engine info` (current engine details)
- [ ] Performance benchmarks (Jinja2 vs Mako vs Patitas)
- [ ] Documentation:
  - [ ] "Escaping Jinja2: Switching to Mako"
  - [ ] "Power User Templates with Patitas"
  - [ ] Update getting started guide

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

## Risk Assessment

### This is a Breaking Change

We're intentionally breaking backward compatibility to achieve standardization.

**What Breaks**:
- `from bengal.rendering.template_engine import TemplateEngine` → import error
- `engine.render()` → method not found (use `render_template()`)
- `engine.validate_templates()` → method not found (use `validate()`)
- `engine._find_template_path()` → method not found (use `get_template_path()`)

**Impact**: All Bengal users must update their code if they directly use `TemplateEngine`.

**Justification**: Clean standardization is worth the migration cost.

---

## Test Strategy

### All Tests Updated in One PR

No phased approach. Update all 19 test files in the same PR as the engine migration.

```bash
# Find all files to update
grep -rl "TemplateEngine" tests/ | wc -l  # 19 files

# Search and replace pattern
# OLD: from bengal.rendering.template_engine import TemplateEngine
# NEW: from bengal.rendering.engines import create_engine

# OLD: engine = TemplateEngine(site)
# NEW: engine = create_engine(site)

# OLD: engine.render(name, ctx)
# NEW: engine.render_template(name, ctx)
```

### Protocol Compliance Tests

New test file to verify both engines implement protocol correctly:

```python
# tests/unit/rendering/engines/test_protocol.py
import pytest
from bengal.rendering.engines import create_engine, TemplateEngine


@pytest.mark.parametrize("engine_type", ["jinja2", "patitas"])
def test_engine_implements_protocol(site_factory, engine_type):
    """All engines must implement the full protocol."""
    site = site_factory("test-basic", confoverrides={"template_engine": engine_type})
    engine = create_engine(site)

    # Verify it implements protocol
    assert isinstance(engine, TemplateEngine)

    # Verify required attributes
    assert hasattr(engine, "site")
    assert hasattr(engine, "template_dirs")

    # Verify required methods exist
    assert callable(engine.render_template)
    assert callable(engine.render_string)
    assert callable(engine.template_exists)
    assert callable(engine.get_template_path)
    assert callable(engine.list_templates)
    assert callable(engine.validate)


@pytest.mark.parametrize("engine_type", ["jinja2", "patitas"])
def test_engine_renders_basic_template(site_factory, engine_type):
    """All engines must render templates."""
    site = site_factory("test-basic", confoverrides={"template_engine": engine_type})
    engine = create_engine(site)

    # Should not raise
    templates = engine.list_templates()
    assert len(templates) > 0

    # Should return HTML
    html = engine.render_template(templates[0], {"page": mock_page})
    assert isinstance(html, str)
    assert len(html) > 0
```

---

## Success Criteria

1. **Standardized Protocol**: Single `TemplateEngine` protocol all engines implement
2. **Clean Factory**: All instantiation through `create_engine()`
3. **Consistent Methods**: Same method names across all engines
4. **Clear Errors**: Standardized `TemplateError`, `TemplateNotFoundError`, `TemplateRenderError`
5. **Full Test Coverage**: Protocol compliance tests for all engines
6. **Simple Config**: One line to switch engines (`template_engine: patitas`)
7. **No Legacy Code**: Delete `template_engine/core.py` after migration
8. **Documentation**: Migration guide for updating callsites

---

## References

- [RFC: patitas](rfc-bengal-templates.md) — Underlying templating library
- [PEP 544: Protocols](https://peps.python.org/pep-0544/) — Structural subtyping
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [SvelteKit](https://kit.svelte.dev/) — Inspiration for "use the platform" philosophy

---

## Appendix: File Structure

### After Migration

```
bengal/rendering/
├── engines/                      # NEW: Standardized engine package
│   ├── __init__.py               #   create_engine(), exports
│   ├── protocol.py               #   TemplateEngine protocol
│   ├── errors.py                 #   TemplateError, TemplateNotFoundError
│   ├── jinja.py                  #   JinjaTemplateEngine
│   ├── mako.py                   #   MakoTemplateEngine (recommended alternative)
│   └── patitas.py                #   PatitasTemplateEngine (power users)
│
├── template_engine/              # LEGACY: Kept for mixins only
│   ├── __init__.py               #   Re-exports from engines/
│   ├── asset_url.py              #   AssetURLMixin (used by JinjaEngine)
│   ├── environment.py            #   create_jinja_environment()
│   ├── manifest.py               #   ManifestHelpersMixin
│   ├── menu.py                   #   MenuHelpersMixin
│   ├── url_helpers.py            #   url_for(), with_baseurl()
│   └── core.py                   #   DELETED
│
└── ...

themes/
├── default/                      # Jinja2 theme (unchanged)
│   └── templates/*.html
│
└── patitas-minimal/              # NEW: Example Patitas theme
    └── templates/
        ├── base.py
        ├── page.py
        └── blog/
            ├── single.py
            └── list.py
```

### Deleted Files

```
bengal/rendering/template_engine/core.py  # 507 lines → DELETED
```

### New Files

```
bengal/rendering/engines/__init__.py      # ~80 lines
bengal/rendering/engines/protocol.py      # ~100 lines
bengal/rendering/engines/errors.py        # ~50 lines
bengal/rendering/engines/jinja.py         # ~200 lines
bengal/rendering/engines/mako.py          # ~130 lines
bengal/rendering/engines/patitas.py       # ~150 lines
```

---

## Evaluation Notes

**Evaluation Date**: 2025-12-18  
**Revised**: 2025-12-18 (standardization focus)  
**Confidence**: 90% 🟢

### Design Philosophy

**Standardization over backward compatibility**:
- Clean break with legacy API
- Consistent method names (`render_template`, not `render`)
- Mandatory protocol methods (no optional methods)
- Single factory function (`create_engine`)

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| `render_template()` not `render()` | Explicit > implicit. "template" clarifies what's being rendered |
| All methods required | Ensures consistent behavior, easier testing |
| No backward compat aliases | Clean break prevents tech debt accumulation |
| Single PR migration | Atomic change, easier to review/revert |
| `TemplateEngine` as protocol name | Matches the concept, not the implementation |

### Evidence Sources

- **Callsite count**: 15 instantiation sites in 12 production files
- **Test files**: 19 files need updating
- **Legacy code to delete**: `bengal/rendering/template_engine/core.py` (507 lines)
- **Prototype**: `prototypes/templit_prototype.py` validates patitas design
- **Dependency RFC**: `plan/drafted/rfc-bengal-templates.md` defines patitas library

### Migration Complexity

| Category | Files | Difficulty |
|----------|-------|------------|
| Production | 12 | Easy (mechanical) |
| Tests | 19 | Easy (find/replace) |
| Documentation | ~5 | Medium |
| **Total** | **~35** | **4-6 hours** |

### Next Steps

1. Move to `plan/ready/` when approved
2. Create single PR with all changes
3. Delete legacy code in same PR
