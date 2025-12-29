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

**Purpose**: Define how different content types are organized and rendered

**Implementation**:
```python
from bengal.content_types import ContentStrategy, ContentTypeRegistry

class CustomStrategy(ContentStrategy):
    def get_template(self, page):
        # Custom template selection logic
        return 'custom/template.html'

    def get_url_pattern(self, page):
        # Custom URL structure
        return f"custom/{page.slug}/"

    def get_sorting_key(self, pages):
        # Custom page sorting
        return lambda p: p.title

    def should_generate_index(self, section):
        return True

# Register your strategy
ContentTypeRegistry.register('custom', CustomStrategy)
```

**Configuration**:
```toml
[content_type]
strategy = "custom"
```

**Documentation**: Refer to [[docs/reference/architecture/core/content-types|Content Types]]

## 2. Custom Markdown Parsers

**Purpose**: Add support for alternative markdown flavors or custom syntax

**Implementation**:
```python
from bengal.rendering.parsers.base import BaseMarkdownParser

class CustomMarkdownParser(BaseMarkdownParser):
    def parse(self, content: str) -> str:
        # Parse markdown to HTML
        return html

    def parse_with_toc(self, content: str) -> tuple[str, list]:
        # Parse with TOC extraction
        return html, toc_items

# Register in parser factory
# (requires modification of bengal/rendering/parsers/__init__.py)
```

**Configuration**:
```toml
[build]
markdown_engine = "custom"
```

## 3. Custom Template Functions

**Purpose**: Add custom filters and functions for Jinja2 templates

**Implementation**:
```python
# In your site's custom module
from bengal.rendering.template_engine import TemplateEngine

def my_custom_filter(value):
    """Custom filter implementation."""
    return value.upper()

# Register with template engine (requires hook - see below)
def register_custom_functions(engine: TemplateEngine):
    engine.env.filters['custom'] = my_custom_filter
```

**Usage in templates**:
```kida
{{ page.title | custom }}
```

**Examples**: See [`example_templates/filters/safe_filters.py`](../example_templates/filters/safe_filters.py) for real-world custom filter implementations.

**Future**: Plugin system will formalize this

## 4. Custom Post-Processors

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

# Add to PostprocessOrchestrator
# (requires modification or plugin hook)
```

**Future**: Plugin system will provide hooks

## 5. Custom Validators

**Purpose**: Add custom health checks and validation rules

**Implementation**:
```python
from bengal.health.base import BaseValidator, CheckResult, CheckStatus

class CustomValidator(BaseValidator):
    name = "custom"
    description = "Custom validation checks"

    def validate(self, site) -> list[CheckResult]:
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

**Documentation**: Refer to [[docs/reference/architecture/subsystems/health|Health Checks]]

## 6. Custom Themes

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

## 7. Custom Shortcodes (Planned)

**Purpose**: Define custom markdown syntax extensions

**Planned API**:
```python
from bengal.rendering.plugins import ShortcodePlugin

class AlertShortcode(ShortcodePlugin):
    name = "alert"

    def render(self, content, **kwargs):
        alert_type = kwargs.get('type', 'info')
        return f'<div class="alert alert-{alert_type}">{content}</div>'

# Register shortcode
# (requires plugin system)
```

**Usage in markdown**:
```markdown
{{% alert type="warning" %}}
This is a warning message!
{{% /alert %}}
```

## 8. Plugin System (Planned v0.4.0)

**Purpose**: Formal plugin architecture with lifecycle hooks

**Planned API**:
```python
from bengal.plugins import Plugin, hook

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"

    @hook('pre_build')
    def before_build(self, site):
        """Called before build starts"""
        print(f"Building {len(site.pages)} pages")

    @hook('post_page_render')
    def after_page_render(self, page, html):
        """Called after each page renders"""
        return self._modify_html(html)

    @hook('post_build')
    def after_build(self, site, stats):
        """Called after build completes"""
        print(f"Built in {stats.duration}s")

# Register plugin
# bengal.toml:
# [plugins]
# my-plugin = true
```

**Planned Hooks**:
- `pre_build` - Before build starts
- `post_content_discovery` - After content discovered
- `pre_page_render` - Before page renders
- `post_page_render` - After page renders
- `post_build` - After build completes
- `template_context` - Modify template context
- `pre_asset_process` - Before asset processing
- `post_asset_process` - After asset processing

## 9. Custom CLI Commands (Future)

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

## 10. Custom Autodoc Extractors

**Purpose**: Generate documentation from other sources

**Implementation**:
```python
from bengal.autodoc.base import Extractor, DocElement

class OpenAPIExtractor(Extractor):
    """Extract docs from OpenAPI specs."""

    def extract(self, source_path):
        spec = self._load_openapi_spec(source_path)

        elements = []
        for path, methods in spec['paths'].items():
            for method, details in methods.items():
                element = DocElement(
                    name=f"{method.upper()} {path}",
                    element_type='endpoint',
                    description=details.get('summary', ''),
                    metadata=details
                )
                elements.append(element)

        return elements

# Register extractor
# (planned: autodoc registry system)
```

## Current Workarounds

Until the plugin system is implemented, some extensions require:

1. **Fork and modify**: Make changes in your own fork
2. **Wrapper scripts**: Write scripts that call Bengal + custom logic
3. **Template-based**: Many customizations possible via templates alone
4. **Theme-based**: Package customizations in a theme

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

## Migration Path

When plugin system arrives:
1. Existing extensions can be migrated incrementally
2. Old patterns will continue working (backward compatibility)
3. New APIs will be opt-in
4. Migration guides will be provided

## Related Documentation

- [[docs/reference/architecture/core/content-types|Content Types]] - Custom content strategies
- [[docs/reference/architecture/rendering|Rendering]] - Template and parser customization
- [[docs/reference/architecture/subsystems/health|Health Checks]] - Custom validators
- [[docs/reference/architecture/design-principles|Design Principles]] - Extension design patterns
