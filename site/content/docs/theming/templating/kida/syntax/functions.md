---
title: Functions
nav_title: Functions
description: Reusable template components that automatically access outer variables
weight: 40
tags:
- reference
- kida
- syntax
---

# Functions

Kida's `{% def %}` creates reusable template components that can automatically access variables from their surrounding context—no need to pass everything as parameters.

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

## Automatic Access to Outer Variables

Kida functions can "see" variables defined outside them. This is called **lexical scoping**—functions inherit the context where they're defined.

**Why this matters**: You don't need to pass site configuration, theme settings, or other shared values as parameters. Define them once at the top of your template, and all your functions can use them.

```kida
{% let site_name = site.config.title %}
{% let theme_color = config.theme.primary_color %}

{% def card(item) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <small>From: {{ site_name }}</small>  {# ✅ Works! Accesses outer scope #}
  </div>
{% end %}

{# Just pass the item—site_name and theme_color are available automatically #}
{{ card(page) }}
```

**Compare to Jinja2**, where macros are isolated and require passing every variable explicitly:

```jinja2
{# Jinja2: Must pass ALL needed variables as parameters #}
{% def card(item, site_name, theme_color) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <small>From: {{ site_name }}</small>
  </div>
{% end %}

{# Caller must remember to pass everything #}
{{ card(page, site.config.title, config.theme.primary_color) }}
```

**Benefits of Kida's approach**:
- **Less boilerplate**: No need to thread variables through every function call
- **Easier refactoring**: Add a new shared variable once, use it everywhere
- **Cleaner function signatures**: Parameters reflect what's unique to each call, not shared context

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

Add custom filters using a build hook:

```python
# python/build_hooks.py
from bengal.core import Site

def reading_time(content: str, wpm: int = 200) -> int:
    """Calculate reading time in minutes."""
    words = len(content.split())
    return max(1, round(words / wpm))

def format_number(value: int) -> str:
    """Format number with commas."""
    return f"{value:,}"

def register_filters(site: Site) -> None:
    """Register custom Kida filters."""
    # Get the Kida environment from the template engine
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("reading_time", reading_time)
        env.add_filter("format_number", format_number)
```

Add the build hook to `bengal.yaml`:

```yaml
build_hooks:
  - python.build_hooks.register_filters
```

Use in templates:

```kida
<span>{{ page.content | reading_time }} min read</span>
<span>{{ view_count | format_number }} views</span>
```

**Note**: `page.reading_time` is already available as a built-in Page property, so you may not need a custom filter for reading time. See [Add a Custom Filter](/docs/theming/templating/kida/add-custom-filter/) for more details.

## Functions vs Partials

| Feature | Functions | Partials |
|---------|-----------|----------|
| Definition | In template | Separate file |
| Parameters | Explicit | Via `{% let %}` before include |
| Scope access | Sees outer variables automatically | Only sees passed context |
| Cacheability | Part of template (cached with template) | Separate file (can be cached independently) |
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
        {% for tag in post.tags |> take(3) %}
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
