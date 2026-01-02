---
title: Variables and Scoping
nav_title: Variables
description: Template variables, scoping rules, and exports
weight: 20
type: doc
tags:
- reference
- kida
- syntax
---

# Variables and Scoping

Kida provides three variable assignment keywords with distinct scoping behaviors:

- **`{% let %}`**: Template-scoped variables available throughout the template
- **`{% set %}`**: Block-scoped variables limited to the current block (if/for/while)
- **`{% export %}`**: Variables promoted from inner scopes to template scope

This explicit scoping model prevents variable leakage, enables safer refactoring, and eliminates the need for Jinja2's `namespace()` workarounds.

## Template Variables with `{% let %}`

Use `{% let %}` for variables available throughout the template. Variables assigned with `{% let %}` persist across all blocks and can be accessed anywhere in the template.

```kida
{# Template-scoped: available everywhere #}
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}

{# Use anywhere in template #}
<title>{{ page.title }} - {{ site_title }}</title>

<nav>
  {% for item in nav_items %}
    <a href="{{ item.url }}">{{ item.title }}</a>
  {% end %}
</nav>
```

## Block Variables with `{% set %}`

Use `{% set %}` for variables scoped to the current block. Variables assigned with `{% set %}` are only accessible within the block where they're defined (if/for/while blocks). Once the block ends, the variable is no longer accessible.

This prevents variable leakage and allows you to safely reuse variable names in different blocks without conflicts.

```kida
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>  {# Works here #}
{% end %}
{# status not accessible here #}
```

## Exporting from Inner Scope

Use `{% export %}` to promote variables from inner scopes (loops, conditionals) to template scope. Variables assigned with `{% export %}` are always assigned to template scope, making them available after the block ends.

This is particularly useful for loop aggregation, finding values in loops, and extracting matched values from pattern matching blocks.

```kida
{% for post in posts %}
  {% if post.featured %}
    {% export featured_post = post %}
  {% end %}
{% end %}

{# featured_post available here #}
<div class="featured">{{ featured_post.title }}</div>
```

Compare to Jinja2's namespace workaround:

```jinja2
{# Jinja2 workaround: use namespace #}
{% set ns = namespace(featured_post=none) %}
{% for post in posts %}
  {% if post.featured %}
    {% set ns.featured_post = post %}
  {% endif %}
{% endfor %}
{{ ns.featured_post.title }}
```

## Multiple Assignment

### Multi-let (Comma-Separated)

Assign multiple independent variables in a single `{% let %}` block:

```kida
{# Single-line multi-let #}
{% let a = 1, b = 2, c = 3 %}

{# Multi-line multi-let (recommended for readability) #}
{% let
    _site_title = config?.title ?? 'Untitled Site',
    _page_title = page?.title ?? config?.title ?? 'Page',
    _description = page?.description ?? config?.description ?? '' %}
```

This is the **recommended pattern** for template setup sections:

```kida
{% extends "base.html" %}

{# Group related configuration variables #}
{% let
    _show_sidebar = page?.sidebar ?? true,
    _show_toc = page?.toc ?? true,
    _show_reading_time = theme?.features?.content?.reading_time ?? false %}

{# Group navigation variables #}
{% let
    _prev = get_prev_page(page),
    _next = get_next_page(page),
    _has_nav = _prev is defined or _next is defined %}

{% block content %}
  {# Variables are available throughout the template #}
{% end %}
```

### Tuple Unpacking

Destructure tuples or pairs into separate variables:

```kida
{% let (title, subtitle) = (page.title, page.subtitle) %}
{% let (first, second, third) = get_top_three() %}
```

### Literal Assignment

Assign array and dict literals directly:

```kida
{% let items = [1, 2, 3] %}
{% let config = {"key": "value", "enabled": true} %}
```

## Scoping Rules

| Keyword | Scope | Use Case |
|---------|-------|----------|
| `{% let %}` | Template-wide | Site config, reusable data, template setup |
| `{% set %}` | Current block | Temporary values in loops/conditionals, block-local state |
| `{% export %}` | Template-wide (promoted) | Loop aggregation, extracting values from blocks |

**Scoping Rules**:
- `{% let %}`: Available throughout the entire template
- `{% set %}`: Only available within the block where it's defined
- `{% export %}`: Promoted to template scope, available after the block ends

## Common Patterns

### Configuration at Top of Template

```kida
{% extends "baseof.html" %}

{# Template-level configuration #}
{% let show_sidebar = page.sidebar ?? true %}
{% let show_toc = page.toc ?? true %}
{% let theme_color = config.theme.primary_color %}

{% block content %}
  <main class="{% if show_sidebar %}with-sidebar{% end %}">
    {{ page.content | safe }}
  </main>
{% endblock %}
```

### Computed Values

```kida
{% let post = page %}
{% let author = site.authors[post.author] ?? {} %}
{% let reading_time = post.content | wordcount | reading_time %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', post.tags[0])
  |> take(5) %}

<article>
  <header>
    <h1>{{ post.title }}</h1>
    <span>By {{ author.name ?? 'Anonymous' }}</span>
    <span>{{ reading_time }} min read</span>
  </header>
  {{ post.content | safe }}
</article>
```

### Loop Aggregation

```kida
{% export total = 0 %}
{% for item in items %}
  {% export total = total + item.count %}
{% end %}

<p>Total: {{ total }}</p>
```

**How it works**: `{% export %}` assigns to template scope, so `total` persists after the loop ends and is available for use.
