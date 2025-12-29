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

Kida distinguishes between template-scoped (`{% let %}`) and block-scoped (`{% set %}`) variables.

## Template Variables with `{% let %}`

Use `{% let %}` for variables available throughout the template:

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

Use `{% set %}` for variables scoped to the current block:

```kida
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>  {# Works here #}
{% end %}
{# status not accessible here #}
```

## Exporting from Inner Scope

Use `{% export %}` to make inner-scope variables accessible outside:

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

Assign multiple variables at once:

```kida
{% let (title, subtitle) = (page.title, page.subtitle) %}
{% let items = [1, 2, 3] %}
{% let config = {"key": "value"} %}
```

## Scoping Rules

| Keyword | Scope | Use Case |
|---------|-------|----------|
| `{% let %}` | Template-wide | Site config, reusable data |
| `{% set %}` | Current block | Temporary values in loops/conditionals |
| `{% export %}` | Outer scope | Promote inner values to outer scope |

## Common Patterns

### Configuration at Top of Template

```kida
{% extends "baseof.html" %}

{# Template-level configuration #}
{% let show_sidebar = page.sidebar | default(true) %}
{% let show_toc = page.toc | default(true) %}
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
{% let author = site.authors[post.author] | default({}) %}
{% let reading_time = post.content | wordcount | reading_time %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', post.tags[0])
  |> take(5) %}

<article>
  <header>
    <h1>{{ post.title }}</h1>
    <span>By {{ author.name | default('Anonymous') }}</span>
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
