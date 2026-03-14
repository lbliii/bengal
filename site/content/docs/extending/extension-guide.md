---
title: Extension Guide
description: Accurate walkthrough for custom directives, filters, and shortcodes with working examples
weight: 30
---

This guide walks through the three main extension mechanisms in Bengal: **shortcodes** (template-only), **custom filters** (template functions), and **custom directives** (Markdown blocks). Each section includes working examples you can copy and run.

## Choose Your Extension Type

| Extension | When to Use | Effort |
|-----------|-------------|--------|
| **Shortcode** | Simple HTML from args, no validation, template authors can add | Easy |
| **Custom Filter** | Transform values in templates (`{{ x \| my_filter }}`) | Easy |
| **Custom Directive** | Validation, nesting, structured Markdown blocks | Advanced |

:::{tip}
Start with shortcodes for content embeds. Add filters when you need value transforms. Use directives only when you need validation or parent-child nesting.
:::

---

## 1. Shortcodes (Template-Only)

Shortcodes require **no Python**. Create a Kida template in `templates/shortcodes/<name>.html` and use it in Markdown.

### Self-Closing Shortcode

**Create** `templates/shortcodes/audio.html`:

```html
{% set src = shortcode.Get("src") %}
{% if src %}<audio controls preload="auto" src="{{ src }}"></audio>{% end %}
```

**Use in Markdown:**

```markdown
{{< audio src=/audio/test.mp3 >}}
```

### Paired Shortcode (with inner content)

**Create** `templates/shortcodes/blockquote.html`:

```html
<blockquote class="blockquote">
  {{- shortcode.Inner -}}
  {% set author = shortcode.Get("author") %}
  {% if author %}<footer>— {{ author }}</footer>{% end %}
</blockquote>
```

**Use in Markdown** (use `{{% %}}` for Markdown in inner content):

```markdown
{{% blockquote author="Jane Doe" %}}
The only way to do great work is to **love** what you do.
{{% /blockquote %}}
```

### Shortcode API

| Method | Description |
|--------|-------------|
| `shortcode.Get("key")` | Named argument |
| `shortcode.Get(0)` | Positional argument (0-indexed) |
| `shortcode.GetInt("key", 0)` | Argument as int |
| `shortcode.GetBool("key", false)` | Argument as bool |
| `shortcode.Inner` | Inner content (paired only) |
| `shortcode.InnerDeindent` | Inner with leading indentation stripped |
| `shortcode.Ref("path")` | Resolve content path to absolute URL |
| `shortcode.RelRef("path")` | Resolve to relative URL |
| `shortcode.Parent` | Parent shortcode when nested (or None) |

### List Available Shortcodes

```bash
bengal shortcodes list
```

### Strict Mode

Configure in `bengal.toml` or `config/_default/site.yaml`:

```toml
[shortcodes]
strict = true
```

When enabled, the build fails if an unknown shortcode is used or a shortcode template fails.

See [Template Shortcodes](/docs/extending/shortcodes/) for the full reference.

---

## 2. Custom Filters

Custom filters transform values in templates: `{{ value | currency }}` or `{{ value |> currency }}`.

### Recommended: Custom Engine Wrapper

The cleanest approach is to register a custom engine that extends Kida and adds your filters after Bengal's built-in functions are registered:

**Create** `python/my_engine.py`:

```python
"""Custom Kida engine with additional filters."""
from bengal.rendering.engines import register_engine
from bengal.rendering.engines.kida import KidaTemplateEngine


def currency(value: float | None, symbol: str = "$") -> str:
    """Format a number as currency."""
    if value is None:
        return f"{symbol}0.00"
    return f"{symbol}{value:,.2f}"


def truncate_words(value: str | None, length: int = 50, suffix: str = "...") -> str:
    """Truncate text to a specific word count."""
    if not value:
        return ""
    words = value.split()
    length = int(length) if length is not None else 50
    if len(words) <= length:
        return value
    return " ".join(words[:length]) + suffix


class MyKidaEngine(KidaTemplateEngine):
    """Kida engine with custom filters."""

    def _register_bengal_template_functions(self) -> None:
        super()._register_bengal_template_functions()
        self._env.filters["currency"] = currency
        self._env.filters["truncate_words"] = truncate_words


register_engine("mykida", MyKidaEngine)
```

**Load the module and configure.** Use a small build script so the engine is registered before Bengal runs:

```python
# build.py
import python.my_engine  # Registers MyKidaEngine as "mykida"
from pathlib import Path
from bengal.core import Site
from bengal.orchestration.build import BuildOptions

site = Site.from_config(Path("."))
site.build(BuildOptions())
```

Or run with `PYTHONPATH=.:python python build.py`. Ensure `bengal.toml` has:

```toml
[site]
template_engine = "mykida"
```

**Use in templates:**

```kida
{{ 1234.56 | currency }}
{{ 1234.56 | currency("€") }}
{{ page.excerpt | truncate_words(20) }}
```

:::{note}
**Type coercion**: Values from YAML or config can arrive as strings. Coerce numeric params in your filter: `length = int(length) if length is not None else 50`.
:::

See [Add a Custom Filter](/docs/theming/templating/kida/add-custom-filter/) for more examples and the programmatic build script approach.

---

## 3. Custom Directives

Custom directives add new MyST-style block syntax to Markdown. Implement the `DirectiveHandler` protocol (or use the `BengalDirective` alias).

### Minimal Alert Directive

```python
from html import escape as html_escape

from patitas.nodes import Directive

from bengal.directives import DirectiveHandler


class AlertDirective:
    """Custom alert box directive."""

    names = ("alert", "callout")
    token_type = "alert"

    def parse(self, name, title, options, content, children, location):
        level = title.strip() if title else "info"
        return Directive(
            location=location,
            name=name,
            title=title,
            options={"level": level, "class": getattr(options, "class_", "") or ""},
            children=children,
        )

    def render(self, node, rendered_children, sb):
        level = node.options.get("level", "info")
        css_class = node.options.get("class", "")
        classes = f"alert alert-{level} {css_class}".strip()
        sb.append(f'<div class="{html_escape(classes)}">{rendered_children}</div>')
```

**Usage in Markdown:**

```markdown
:::{alert} warning
:class: my-custom-class

This is a warning message.
:::
```

### Registration

Custom directives must be registered in the directive registry. Currently this requires modifying the Bengal codebase or using a fork. Add your handler in `bengal/parsing/backends/patitas/directives/registry.py` inside `create_default_registry()`:

```python
from your_module import AlertDirective

builder.register(AlertDirective())
```

:::{note}
A plugin system for external directive registration is on the roadmap. Until then, custom directives require a fork or patch.
:::

### Typed Options

Use a dataclass for typed directive options:

```python
from dataclasses import dataclass

from bengal.directives import DirectiveOptions


@dataclass(frozen=True, slots=True)
class EmbedOptions(DirectiveOptions):
    width: str = "100%"
    height: str = "400px"
    title: str = ""


class EmbedDirective:
    names = ("embed", "iframe")
    token_type = "embed"
    options_class = EmbedOptions

    def parse(self, name, title, options, content, children, location):
        url = title.strip() if title else ""
        return Directive(
            location=location,
            name=name,
            title=url,
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        opts = node.options
        url = html_escape(node.title or "", quote=True)
        width = html_escape(opts.width or "100%", quote=True)
        height = html_escape(opts.height or "400px", quote=True)
        sb.append(f'<iframe src="{url}" width="{width}" height="{height}" loading="lazy"></iframe>')
```

See [Custom Directives](/docs/extending/custom-directives/) for the full reference including `contract`, testing, and HTML escaping.

---

## Quick Reference

| Extension | Location | Registration |
|-----------|----------|--------------|
| Shortcode | `templates/shortcodes/<name>.html` | None (auto-discovered) |
| Filter | Custom engine or `env.filters["name"] = func` | `register_engine` or build script |
| Directive | Python class | `create_default_registry()` (codebase) |

## Related

- [Template Shortcodes](/docs/extending/shortcodes/) — Full shortcode reference
- [Add a Custom Filter](/docs/theming/templating/kida/add-custom-filter/) — Filter details and programmatic build
- [Custom Directives](/docs/extending/custom-directives/) — Directive protocol, options, testing
- [Extension Points](/docs/reference/architecture/meta/extension-points/) — All extension mechanisms
