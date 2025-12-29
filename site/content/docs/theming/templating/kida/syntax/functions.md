---
title: Functions
nav_title: Functions
description: Template functions with lexical scoping and slots
weight: 40
type: doc
tags:
- reference
- kida
- syntax
---

# Functions

Kida's `{% def %}` provides true lexical scoping, unlike Jinja2 macros.

## Defining Functions

```kida
{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
  </div>
{% end %}

{# Call the function #}
{{ card(page) }}
```

## Lexical Scoping

Kida functions can access variables from their outer scope:

```kida
{% let site_name = site.config.title %}
{% let theme_color = config.theme.primary_color %}

{% def card(item) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <small>From: {{ site_name }}</small>  {# Accesses outer scope #}
  </div>
{% end %}
```

Jinja2 macros require passing all variables explicitly:

```jinja2
{# Jinja2: Must pass all needed variables #}
{% macro card(item, site_name, theme_color) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <small>From: {{ site_name }}</small>
  </div>
{% endmacro %}
```

## Default Parameters

```kida
{% def button(text, href, variant="primary", size="md") %}
  <a href="{{ href }}" class="btn btn-{{ variant }} btn-{{ size }}">
    {{ text }}
  </a>
{% end %}

{{ button("Get Started", "/docs", variant="success", size="lg") }}
{{ button("Learn More", "/about") }}
```

## Slots (Block Content)

Functions can accept block content using `{% slot %}`:

```kida
{% def modal(title, size="md") %}
  <div class="modal modal-{{ size }}">
    <div class="modal-header">
      <h2>{{ title }}</h2>
    </div>
    <div class="modal-body">
      {% slot %}
        {# Default content if no call block #}
        <p>Modal content goes here</p>
      {% endslot %}
    </div>
  </div>
{% end %}
```

Use with `{% call %}` to pass content:

```kida
{% call modal("Confirm Action", size="sm") %}
  <p>Are you sure you want to delete this item?</p>
  <div class="modal-actions">
    <button class="btn btn-danger">Delete</button>
    <button class="btn btn-secondary">Cancel</button>
  </div>
{% endcall %}
```

## Common Patterns

### Reusable UI Components

```kida
{% def tag_badge(tag) %}
  <a href="/tags/{{ tag | slugify }}" class="tag">{{ tag }}</a>
{% end %}

{% def author_card(author) %}
  <div class="author-card">
    {% if author.avatar %}
      <img src="{{ author.avatar }}" alt="{{ author.name }}">
    {% end %}
    <span>{{ author.name }}</span>
  </div>
{% end %}
```

### Conditional Rendering

```kida
{% def status_badge(status) %}
  {% match status %}
    {% case "published" %}
      <span class="badge badge-success">Published</span>
    {% case "draft" %}
      <span class="badge badge-warning">Draft</span>
    {% case "archived" %}
      <span class="badge badge-secondary">Archived</span>
    {% case _ %}
      <span class="badge badge-muted">Unknown</span>
  {% end %}
{% end %}

{{ status_badge(page.status) }}
```

### Navigation Items

```kida
{% def nav_item(item, current_path) %}
  {% let is_active = current_path == item.url or current_path | startswith(item.url ~ '/') %}
  <li class="nav-item{% if is_active %} active{% end %}">
    <a href="{{ item.url }}"
       {% if is_active %}aria-current="page"{% end %}>
      {{ item.title }}
    </a>
  </li>
{% end %}
```

## Custom Filters

Add custom filters in Python:

```python
# bengal.py or hooks/filters.py
from bengal import Site

def reading_time(content: str, wpm: int = 200) -> int:
    """Calculate reading time in minutes."""
    words = len(content.split())
    return max(1, round(words / wpm))

def format_number(value: int) -> str:
    """Format number with commas."""
    return f"{value:,}"

site = Site()
site.add_filter("reading_time", reading_time)
site.add_filter("format_number", format_number)
```

Use in templates:

```kida
<span>{{ page.content | reading_time }} min read</span>
<span>{{ view_count | format_number }} views</span>
```

## Functions vs Partials

| Feature | Functions | Partials |
|---------|-----------|----------|
| Definition | In template | Separate file |
| Parameters | Explicit | Via `{% let %}` before include |
| Scope access | Lexical | Template context |
| Cacheability | Cannot be cached | Can be cached |
| Use case | Reusable within template | Shared across templates |

**Use functions** for components reused within a single template.

**Use partials** for components shared across multiple templates.

## Complete Example

```kida
{% extends "baseof.html" %}

{# Template-level configuration #}
{% let theme_accent = config.theme.accent_color %}

{# Reusable function with access to outer scope #}
{% def post_card(post) %}
  <article class="post-card" style="border-color: {{ theme_accent }}">
    <h2><a href="{{ post.url }}">{{ post.title }}</a></h2>
    <div class="meta">
      <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
      <span>{{ post.content | reading_time }} min</span>
    </div>
    {% if post.tags %}
      <div class="tags">
        {% for tag in post.tags | take(3) %}
          {{ tag_badge(tag) }}
        {% end %}
      </div>
    {% end %}
  </article>
{% end %}

{% def tag_badge(tag) %}
  <a href="/tags/{{ tag | slugify }}" class="tag">{{ tag }}</a>
{% end %}

{% block content %}
  <section class="posts">
    {% for post in site.pages |> where('type', 'blog') |> take(10) %}
      {{ post_card(post) }}
    {% end %}
  </section>
{% endblock %}
```
