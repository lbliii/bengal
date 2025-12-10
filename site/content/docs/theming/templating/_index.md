---
title: Templating
description: Jinja2 layouts, inheritance, and partials
weight: 10
category: guide
icon: code
card_color: blue
---
# Jinja2 Templating

Bengal uses [Jinja2](https://jinja.palletsprojects.com/) for all templates. If you know Python, you'll feel at home.

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
```jinja
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
```jinja
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
```jinja
{# templates/partials/header.html #}
<header>
  <nav>
    {% for item in site.menus.main %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% endfor %}
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

:::{tip}
**Override sparingly**: You only need to create templates you want to customize. Start by copying one template from your theme, modify it, and let the rest fall through to defaults.
:::
