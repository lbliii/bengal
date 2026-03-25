---
title: Extension Points
nav_title: Extensions
description: Plugin hooks and customization points for extending Bengal
weight: 40
category: meta
tags:
- meta
- extension-points
- plugins
- customization
- hooks
- extensibility
- strategies
keywords:
- extension points
- plugins
- customization
- hooks
- extensibility
- content strategies
- validators
---

# Extension Points

Bengal is designed with multiple extension points that allow customization without modifying core code.

## 1. Custom Content Strategies

**Purpose**: Define how different content types are sorted, paginated, and rendered

**Implementation**:
```python
from bengal.content_types.base import ContentTypeStrategy
from bengal.content_types.registry import register_strategy

class NewsStrategy(ContentTypeStrategy):
    """Custom strategy for news articles."""

    default_template = "news/list.html"
    allows_pagination = True

    def sort_pages(self, pages):
        """Sort by date, newest first."""
        from datetime import datetime
        return sorted(
            pages,
            key=lambda p: p.date or datetime.min,
            reverse=True
        )

    def get_template(self, page=None, template_engine=None):
        """Custom template selection."""
        if page and page.source_path.stem == "_index":
            return "news/list.html"
        return "news/single.html"

    def detect_from_section(self, section):
        """Auto-detect news sections."""
        return section.name.lower() in ("news", "announcements")

# Register your strategy (call early in build process)
register_strategy("news", NewsStrategy())
```

**Configuration** (in section `_index.md` frontmatter):
```yaml
---
title: News
content_type: news
---
```

**Documentation**: See [Content Types](/docs/reference/architecture/core/content-types/)

## 2. Custom Markdown Parsers

**Purpose**: Add support for alternative markdown flavors or custom syntax

**Implementation**:
```python
from typing import Any
from bengal.parsing.base import BaseMarkdownParser

class CustomMarkdownParser(BaseMarkdownParser):
    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse markdown to HTML."""
        # Your parsing logic here
        html = self._convert_to_html(content)
        return html

    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """Parse markdown and extract table of contents."""
        html = self.parse(content, metadata)
        toc_html = self._extract_toc(content)
        return html, toc_html

# Register in parser factory
# (requires modification of bengal/parsing/__init__.py)
```

**Using Patitas Low-Level API** (with ContextVar configuration):

```python
from bengal.parsing.backends.patitas import (
    ParseConfig, RenderConfig,
    parse_config_context, render_config_context,
)
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer
from patitas.parser import Parser

# Configure and parse
with parse_config_context(ParseConfig(tables_enabled=True, math_enabled=True)):
    parser = Parser(source)
    ast = parser.parse()

# Configure and render
with render_config_context(RenderConfig(highlight=True)):
    renderer = HtmlRenderer(source)
    html = renderer.render(ast)
```

> **Note**: Custom parser registration currently requires modifying core code; the [plugin system](#9-plugin-system) does **not** currently expose a parser registration hook. Use the plugin system only for other kinds of extensions that do not require core modifications.

## 3. Custom Template Engines

**Purpose**: Bring your own template engine with full access to Bengal's 80+ template functions

**Implementation**:
```python
from bengal.rendering.engines import register_engine
from bengal.rendering.template_functions import register_all

class MyEngine:
    def __init__(self, site):
        self.site = site
        self.template_dirs = [site.root_path / "templates"]

        # Environment must satisfy TemplateEnvironment protocol
        # (must have globals, filters, tests as dict-like attributes)
        self._env = MyEnvironment()

        # All 80+ template functions registered automatically!
        register_all(self._env, site)

    def render_template(self, name: str, context: dict) -> str:
        ...

register_engine("myengine", MyEngine)
```

**Documentation**: See [Bring Your Own Template Engine](/docs/theming/templating/custom-engine/)

## 4. Custom Template Functions

**Purpose**: Add custom filters and functions to existing engines

**Implementation**:
```python
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry

class MyFilterPlugin(Plugin):
    name = "my-filters"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("custom", lambda value: value.upper())
```

> **Tip**: The plugin system provides a stable public API for filter registration. See [Plugin System](#9-plugin-system) for the full pattern including entry-point discovery.

**Usage in templates**:
```kida
{{ page.title | custom }}
```

**Documentation**: See [Add a Custom Filter](/docs/theming/templating/kida/add-custom-filter/)

## 5. Custom Post-Processors

**Purpose**: Add custom build steps after page rendering

**Implementation**:
```python
# In bengal/postprocess/ or custom module
class RobotsGenerator:
    def __init__(self, site):
        self.site = site

    def generate(self) -> None:
        """Generate robots.txt"""
        robots_content = self._build_robots_txt()
        output_path = self.site.output_dir / 'robots.txt'
        output_path.write_text(robots_content)

    def _build_robots_txt(self) -> str:
        # Build robots.txt content
        return "User-agent: *\nDisallow: /admin/"

# Register via plugin phase hook
# registry.on_phase("post_render", my_generator.generate)
```

**Tip**: Use the plugin system's `on_phase()` to register post-processing hooks without modifying core code

## 6. Custom Validators

**Purpose**: Add custom health checks and validation rules

**Implementation**:
```python
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus

class CustomValidator(BaseValidator):
    name = "custom"
    description = "Custom validation checks"

    def validate(self, site, build_context=None) -> list[CheckResult]:
        results = []

        # Your validation logic
        for page in site.pages:
            if not self._check_custom_requirement(page):
                results.append(CheckResult(
                    status=CheckStatus.ERROR,
                    message=f"Page {page.title} fails custom check",
                    recommendation="Fix the issue"
                ))

        return results

# Register with health system
# (requires modification of bengal/health/health_check.py)
```

**Configuration**:
```toml
[health_check.validators]
custom = true
```

**Documentation**: See [Health Checks](/docs/reference/architecture/subsystems/health/)

## 7. Custom Themes

**Purpose**: Package templates, styles, and scripts for reuse

**Structure**:
```tree
my-theme/
├── templates/
│   ├── base.html
│   ├── page.html
│   └── blog/
│       ├── post.html
│       └── list.html
├── assets/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── fonts/
└── theme.toml  # Theme metadata
```

**Configuration**:
```toml
theme = "my-theme"
```

**Documentation**: Themes automatically override default templates

## 8. Custom Shortcodes

**Purpose**: Define custom markdown syntax extensions

**Implementation** (via plugin system):
```python
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry

class AlertPlugin(Plugin):
    name = "alert-shortcode"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_shortcode(
            "alert",
            '<div class="alert alert-{{ type | default("info") }}">{{ content }}</div>',
        )
```

**Usage in markdown**:
```markdown
{{% alert type="warning" %}}
This is a warning message!
{{% /alert %}}
```

## 9. Plugin System

**Purpose**: Unified extension framework with 9 extension points and thread-safe rendering

**Protocol**: All plugins implement `Plugin` — a runtime-checkable protocol with `name`, `version`, and `register()`:

```python
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry


class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        # Directives and roles
        registry.add_directive(MyDirectiveHandler)
        registry.add_role(MyRoleHandler)

        # Template extensions
        registry.add_template_function("my_func", my_func, phase=1)
        registry.add_template_filter("my_filter", my_filter)
        registry.add_template_test("my_test", my_test)

        # Content and validation
        registry.add_content_source("my-source", MySourceClass)
        registry.add_health_validator(MyValidator())
        registry.add_shortcode("alert", '<div class="alert">{{ content }}</div>')

        # Build lifecycle
        registry.on_phase("pre_render", self.before_render)
        registry.on_phase("post_render", self.after_render)
```

**Discovery**: Plugins are auto-discovered via the `bengal.plugins` entry point group. Declare your plugin in `pyproject.toml`:

```toml
[project.entry-points."bengal.plugins"]
my-plugin = "my_package:MyPlugin"
```

**Thread Safety**: The registry uses a builder→immutable pattern. During startup, plugins register into a mutable `PluginRegistry`. Before rendering begins, `freeze()` produces a `FrozenPluginRegistry` dataclass that is safe to share across threads during parallel rendering.

**Extension Points**:

| Method | Purpose |
|--------|---------|
| `add_directive()` | Block-level content directives |
| `add_role()` | Inline markup roles |
| `add_template_function()` | Template globals (with phase ordering) |
| `add_template_filter()` | Value transformers (`{{ x \| filter }}`) |
| `add_template_test()` | Boolean predicates (`{% if x is test %}`) |
| `add_content_source()` | Content source types |
| `add_health_validator()` | Health check validators |
| `add_shortcode()` | Shortcode templates |
| `on_phase()` | Build phase lifecycle hooks |

## Future: Custom CLI Commands

**Purpose**: Add custom commands to Bengal CLI

**Planned API**:
```python
import click
from bengal.cli import cli

@cli.command()
@click.option('--verbose', is_flag=True)
def custom(verbose):
    """My custom command."""
    print("Executing custom command")

# Commands automatically discovered and registered
```

## 11. Custom Autodoc Extractors

**Purpose**: Generate documentation from other sources

**Implementation**:
```python
from typing import Any
from pathlib import Path
from bengal.autodoc.base import Extractor, DocElement

class OpenAPIExtractor(Extractor):
    """Extract docs from OpenAPI specs."""

    def extract(self, source: Any) -> list[DocElement]:
        spec = self._load_openapi_spec(source)

        elements = []
        for path, methods in spec['paths'].items():
            for method, details in methods.items():
                element = DocElement(
                    name=f"{method.upper()} {path}",
                    qualified_name=f"api.{method}.{path}",
                    element_type='endpoint',
                    description=details.get('summary', ''),
                    metadata=details
                )
                elements.append(element)

        return elements

    def get_output_path(self, element: DocElement) -> Path | None:
        """Determine output path for the endpoint."""
        return Path(f"api/{element.name.replace(' ', '-').lower()}.md")

# Register extractor
# (planned: autodoc registry system)
```

## Choosing an Extension Approach

Most extensions should use the plugin system. For simpler cases:

1. **Plugin system**: Recommended for directives, filters, content sources, validators, and build hooks
2. **Template-based**: Many customizations possible via templates alone (no code needed)
3. **Theme-based**: Package related template and asset customizations in a theme
4. **Wrapper scripts**: Write scripts that call Bengal + custom logic for CI/deployment

## Extension Best Practices

1. **Prefer Templates**: Many customizations possible without code
2. **Use Themes**: Package related customizations together
3. **Follow Conventions**: Match Bengal's patterns and style
4. **Document**: Provide clear documentation for your extensions
5. **Test**: Write tests for custom functionality
6. **Share**: Consider contributing back to Bengal

## Community Extensions (Future)

Planned extension registry at `bengal-ssg.org/extensions/`:
- Themes
- Plugins
- Template function packs
- Validators
- Content strategies
- CLI commands

## Migrating to the Plugin System

If you have existing extensions using internal APIs or fork-based patterns:

1. Create a class implementing the `Plugin` protocol (`name`, `version`, `register()`)
2. Move registration logic into `register()` using the `PluginRegistry` methods
3. Add a `bengal.plugins` entry point in your `pyproject.toml`
4. Remove any code that accesses internal attributes (e.g., `site._template_engine._env`)

## Related Documentation

- [Content Types](/docs/reference/architecture/core/content-types/) - Custom content strategies
- [Rendering](/docs/reference/architecture/rendering/) - Template and parser customization
- [Health Checks](/docs/reference/architecture/subsystems/health/) - Custom validators
- [Design Principles](/docs/reference/architecture/design-principles/) - Extension design patterns
