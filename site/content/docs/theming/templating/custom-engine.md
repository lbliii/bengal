---
title: Bring Your Own Template Engine
nav_title: Custom Engine
description: Implement a custom template engine with full access to Bengal's 200+ template functions, filters, and tests
weight: 50
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- advanced
- extension
keywords:
- custom template engine
- bring your own engine
- template protocol
- TemplateEnvironment
category: guide
---

# Bring Your Own Template Engine

Bengal supports custom template engines through a protocol-based interface. Your engine automatically gets access to all 200+ template functions, filters, and tests (74 global functions, 135 filters, and 6 tests).

## Required Protocols

Bengal defines two protocols for template engines:

### TemplateEnvironment Protocol

Your engine's environment object must satisfy this protocol for template function registration:

```python
from typing import Protocol, MutableMapping, Callable, Any

class TemplateEnvironment(Protocol):
    """Minimal interface for template function registration."""
    globals: MutableMapping[str, Any]           # Global variables
    filters: MutableMapping[str, Callable]      # Filter functions
    tests: MutableMapping[str, Callable]        # Test functions
```

If your environment has `globals`, `filters`, and `tests` as dict-like attributes, Bengal automatically registers:
- **200+ template functions, filters, and tests** (74 globals, 135 filters, 6 tests)
- **String functions** (truncate, slugify, markdownify, strip_html, etc.)
- **Collection functions** (sort_by, group_by, where, first, last, etc.)
- **Date/time filters** (strftime, relative_date, days_ago, etc.)
- **Navigation helpers** (breadcrumbs, toc, auto_nav, etc.)
- **SEO/sharing functions** (meta tags, Open Graph, social sharing URLs)
- **And much more...**

### TemplateEngine Protocol

For a complete engine implementation:

```python
from bengal.protocols import TemplateEngine, EngineCapability

class MyEngine:
    """Custom template engine implementation."""

    site: Site
    template_dirs: list[Path]

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template."""
        ...

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render an inline template string."""
        ...

    def template_exists(self, name: str) -> bool:
        """Check if template exists."""
        ...

    def get_template_path(self, name: str) -> Path | None:
        """Resolve template to filesystem path."""
        ...

    def list_templates(self) -> list[str]:
        """List all available templates."""
        ...

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """Validate templates for syntax errors."""
        ...

    @property
    def capabilities(self) -> EngineCapability:
        """Return supported capabilities."""
        return EngineCapability.NONE

    def has_capability(self, cap: EngineCapability) -> bool:
        return cap in self.capabilities
```

## Step-by-Step Implementation

### Step 1: Create Your Environment Class

```python
# my_engine/environment.py
from collections.abc import MutableMapping
from typing import Any, Callable

class MyEnvironment:
    """Template environment that satisfies TemplateEnvironment protocol."""

    def __init__(self):
        # These three attributes are REQUIRED for protocol compliance
        self.globals: dict[str, Any] = {}
        self.filters: dict[str, Callable[..., Any]] = {}
        self.tests: dict[str, Callable[..., bool]] = {}

        # Your engine-specific setup
        self._templates: dict[str, str] = {}

    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable."""
        self.globals[name] = value

    def add_filter(self, name: str, func: Callable) -> None:
        """Add a filter function."""
        self.filters[name] = func

    def add_test(self, name: str, func: Callable) -> None:
        """Add a test function."""
        self.tests[name] = func
```

### Step 2: Create Your Engine Class

```python
# my_engine/engine.py
from pathlib import Path
from typing import Any

from bengal.core import Site
from bengal.protocols import EngineCapability
from bengal.rendering.engines.errors import TemplateError, TemplateNotFoundError
from bengal.rendering.template_functions import register_all

from .environment import MyEnvironment

class MyEngine:
    """Custom template engine implementation."""

    def __init__(self, site: Site):
        self.site = site
        self.template_dirs = self._build_template_dirs()

        # Create environment that satisfies TemplateEnvironment protocol
        self._env = MyEnvironment()

        # Register all 200+ Bengal template functions, filters, and tests automatically!
        register_all(self._env, site, engine_type="generic")

    def _build_template_dirs(self) -> list[Path]:
        """Build ordered list of template directories."""
        dirs = []

        # Project templates (highest priority)
        project_templates = self.site.root_path / "templates"
        if project_templates.exists():
            dirs.append(project_templates)

        # Theme templates (simplified - for theme inheritance, see Kida engine)
        # For basic cases, this works. For parent/child theme support, use
        # resolve_theme_chain() as shown in bengal.rendering.engines.kida
        if hasattr(self.site, 'theme_path') and self.site.theme_path:
            theme_templates = self.site.theme_path / "templates"
            if theme_templates.exists():
                dirs.append(theme_templates)

        return dirs

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a named template with context."""
        template_path = self.get_template_path(name)
        if not template_path:
            raise TemplateNotFoundError(f"Template not found: {name}")

        source = template_path.read_text()
        return self._render(source, context)

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render an inline template string."""
        return self._render(template, context)

    def _render(self, source: str, context: dict[str, Any]) -> str:
        """Core rendering logic - implement for your engine."""
        # Merge globals into context
        full_context = {**self._env.globals, **context}

        # Your rendering implementation here
        # Access filters via self._env.filters
        # Access tests via self._env.tests
        ...

    def template_exists(self, name: str) -> bool:
        """Check if template exists."""
        return self.get_template_path(name) is not None

    def get_template_path(self, name: str) -> Path | None:
        """Find template in search directories."""
        for dir in self.template_dirs:
            path = dir / name
            if path.exists():
                return path
        return None

    def list_templates(self) -> list[str]:
        """List all available templates."""
        templates = set()
        for dir in self.template_dirs:
            for path in dir.rglob("*.html"):
                templates.add(str(path.relative_to(dir)))
        return sorted(templates)

    def validate(self, patterns: list[str] | None = None) -> list[TemplateError]:
        """Validate templates for syntax errors."""
        errors = []
        for name in self.list_templates():
            try:
                path = self.get_template_path(name)
                if path:
                    source = path.read_text()
                    self._validate_syntax(source)
            except Exception as e:
                errors.append(TemplateError(name=name, message=str(e)))
        return errors

    @property
    def capabilities(self) -> EngineCapability:
        """Declare engine capabilities."""
        return EngineCapability.NONE

    def has_capability(self, cap: EngineCapability) -> bool:
        return cap in self.capabilities
```

### Step 3: Register Your Engine

```python
# my_engine/__init__.py
from bengal.rendering.engines import register_engine
from .engine import MyEngine

# Register with Bengal
register_engine("myengine", MyEngine)
```

### Step 4: Configure Bengal

```yaml
# bengal.yaml
site:
  template_engine: myengine
```

## Verification

Verify your environment satisfies the protocol:

```python
from bengal.protocols import TemplateEnvironment

env = MyEnvironment()

# Runtime check (protocol is @runtime_checkable)
assert isinstance(env, TemplateEnvironment), "Environment doesn't satisfy protocol"

# Check required attributes exist
assert hasattr(env, 'globals') and hasattr(env.globals, 'update')
assert hasattr(env, 'filters') and hasattr(env.filters, 'update')  
assert hasattr(env, 'tests') and hasattr(env.tests, 'update')

print("✓ Environment satisfies TemplateEnvironment protocol")
```

## What You Get Automatically

Once your environment satisfies `TemplateEnvironment`, `register_all()` provides:

| Category | Functions | Examples |
|----------|-----------|----------|
| **Strings** | 15+ | `truncate`, `slugify`, `markdownify`, `strip_html` |
| **Collections** | 15+ | `sort_by`, `group_by`, `where`, `first`, `last` |
| **Dates** | 10+ | `strftime`, `days_ago`, `relative_date` |
| **URLs** | 5+ | `absurl`, `relurl`, `url_encode` |
| **Content** | 10+ | `markdown`, `highlight`, `excerpt` |
| **Navigation** | 10+ | `breadcrumbs`, `toc`, `auto_nav`, `pagination` |
| **SEO** | 5+ | `meta_tags`, `og_tags`, `schema_org` |
| **i18n** | 5+ | `t`, `current_lang`, `available_langs` |
| **Debug** | 5+ | `dump`, `inspect`, `type_of` |

## Engine Capabilities

Declare optional capabilities your engine supports:

```python
from bengal.protocols import EngineCapability

@property
def capabilities(self) -> EngineCapability:
    return (
        EngineCapability.BLOCK_CACHING |      # {% cache %} support
        EngineCapability.INTROSPECTION        # Template analysis
    )
```

Available capabilities:
- `BLOCK_CACHING` — Supports `{% cache %}` blocks
- `BLOCK_LEVEL_DETECTION` — Can detect block-level changes
- `INTROSPECTION` — Can analyze template structure
- `PIPELINE_OPERATORS` — Supports `|>` operator
- `PATTERN_MATCHING` — Supports `{% match %}` syntax

## Examples

### Minimal Engine (Dict-Based)

```python
class DictEngine:
    """Minimal engine using Python string formatting."""

    def __init__(self, site):
        self.site = site
        self.template_dirs = [site.root_path / "templates"]

        # Minimal environment
        self._env = type('Env', (), {
            'globals': {},
            'filters': {},
            'tests': {}
        })()

        register_all(self._env, site)

    def render_template(self, name: str, context: dict) -> str:
        path = self.template_dirs[0] / name
        template = path.read_text()
        return template.format(**{**self._env.globals, **context})
```

### Wrapping an Existing Engine

```python
class MakoEngine:
    """Wrap Mako template engine."""

    def __init__(self, site):
        from mako.lookup import TemplateLookup

        self.site = site
        self.template_dirs = [site.root_path / "templates"]

        self._lookup = TemplateLookup(directories=self.template_dirs)

        # Create protocol-compatible wrapper
        self._env = MakoEnvironmentWrapper(self._lookup)
        register_all(self._env, site)

class MakoEnvironmentWrapper:
    """Make Mako compatible with TemplateEnvironment protocol."""

    def __init__(self, lookup):
        self._lookup = lookup
        self.globals = {}
        self.filters = {}
        self.tests = {}
```

## Next Steps

- [Template Functions Reference](/docs/reference/template-functions/) — All available functions
- [Engine Protocol Reference](/docs/reference/architecture/rendering/) — Full protocol details
- [Kida Source Code](https://github.com/lbliii/bengal/tree/main/bengal/rendering/kida/) — Reference implementation

:::{seealso}
- [Add Custom Filter](/docs/theming/templating/kida/add-custom-filter/) — Add functions to existing engines
- [Extension Points](/docs/reference/architecture/meta/extension-points/) — Other customization options
:::
