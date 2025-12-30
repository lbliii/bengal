---
title: Templating
description: Kida template engine, layouts, inheritance, and partials
weight: 10
category: guide
icon: code
card_color: blue
---
# Templating

Bengal's template system uses **Kida** as the default engine, with support for Jinja2 and custom engines.

## Template Engines

- **[Kida](/docs/reference/kida-syntax/)** — Bengal's native template engine (default). Unified `{% end %}` blocks, pattern matching, pipeline operators
- **[Jinja2](https://jinja.palletsprojects.com/)** — Industry-standard engine with excellent documentation and tooling
- **Custom engines** — Bring your own via the plugin API

:::{tip}
**Kida is Jinja2-compatible**: Your existing Jinja2 templates work without changes. Use Kida-specific features incrementally.
:::

## Template Lookup Order

```mermaid
flowchart LR
    A[Page Request] --> B{templates/ ?}
    B -->|Found| C[Use Your Template]
    B -->|Not Found| D{Theme templates/ ?}
    D -->|Found| E[Use Theme Template]
    D -->|Not Found| F[Use Bengal Default]
```

Bengal searches: **Your project** → **Theme** → **Bengal defaults**

## Quick Start

:::{tab-set}
:::{tab-item} Basic Template
```kida
{# templates/layouts/single.html #}
{% extends "baseof.html" %}

{% block content %}
<article>
  <h1>{{ page.title }}</h1>
  {{ page.content | safe }}
</article>
{% endblock %}
```
:::

:::{tab-item} Base Layout
```kida
{# templates/baseof.html #}
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}{{ page.title }}{% endblock %}</title>
</head>
<body>
  {% block header %}{% include "partials/header.html" %}{% endblock %}
  {% block content %}{% endblock %}
  {% block footer %}{% include "partials/footer.html" %}{% endblock %}
</body>
</html>
```
:::

:::{tab-item} Partial
```kida
{# templates/partials/header.html #}
<header>
  <nav>
    {% for item in site.menus.main %}
      <a href="{{ item.href }}">{{ item.title }}</a>
    {% end %}
  </nav>
</header>
```
:::
:::{/tab-set}

## Key Concepts

| Concept | Syntax | Purpose |
|---------|--------|---------|
| **Extends** | `{% extends "base.html" %}` | Inherit from parent template |
| **Block** | `{% block name %}...{% endblock %}` | Replaceable section |
| **Include** | `{% include "partial.html" %}` | Insert another template |
| **Variable** | `{{ page.title }}` | Output a value |
| **Filter** | `{{ text \| truncate(100) }}` | Transform a value |

## Template Inheritance

```mermaid
flowchart TB
    A["baseof.html<br/>(blocks: head, content, footer)"]
    B["single.html<br/>(extends baseof)"]
    C["list.html<br/>(extends baseof)"]
    D["doc.html<br/>(extends single)"]

    A --> B
    A --> C
    B --> D
```

## Kida Features

Kida is Bengal's default template engine:

- **Unified syntax**: `{% end %}` closes all blocks (no more `{% end %}`, `{% end %}`)
- **Pattern matching**: `{% match %}...{% case %}` for cleaner conditionals
- **Pipeline operator**: `|>` for readable filter chains
- **Fragment caching**: Built-in `{% cache %}` directive
- **Jinja2 compatible**: Existing Jinja2 templates work without changes

:::{cards}
:columns: 2
:gap: small

:::{card} Kida Syntax Reference
:icon: book
:link: /docs/reference/kida-syntax/
:description: Complete Kida syntax documentation
:::{/card}

:::{card} Kida Tutorial
:icon: notepad
:link: /docs/tutorials/getting-started-with-kida/
:description: Learn Kida from scratch
:::{/card}

:::{card} Kida How-Tos
:icon: code
:link: /docs/theming/templating/kida/
:description: Common Kida tasks and patterns
:::{/card}

:::{card} Migrate from Jinja2
:icon: arrow-right
:link: /docs/theming/templating/kida/migrate-jinja-to-kida/
:description: Convert Jinja2 templates to Kida
:::{/card}
:::{/cards}

## Choose Your Engine

Kida is the default. To use a different engine, configure `bengal.yaml`:

```yaml
site:
  template_engine: jinja2  # Options: kida (default), jinja2, mako, patitas
```

### Custom Engines (BYOR)

Register custom template engines via the plugin API:

```python
from bengal.rendering.engines import register_engine

class MyTemplateEngine:
    """Implement TemplateEngineProtocol."""
    def render_template(self, name: str, context: dict) -> str:
        # Your implementation
        ...

register_engine("myengine", MyTemplateEngine)
```

Then configure:

```yaml
site:
  template_engine: myengine
```

:::{tip}
**Override sparingly**: You only need to create templates you want to customize. Use `bengal utils theme swizzle <template>` to copy a template for customization. Let the rest fall through to theme defaults.
:::
