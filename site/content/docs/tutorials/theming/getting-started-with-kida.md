---
title: Getting Started with Kida
nav_title: Kida Tutorial
description: Learn Kida template syntax from scratch with hands-on examples
weight: 25
draft: false
lang: en
tags:
- tutorial
- kida
- templates
- beginner
keywords:
- kida tutorial
- template engine
- kida syntax
category: tutorial
---

# Getting Started with Kida

Learn Kida, Bengal's native template engine, from scratch. This tutorial teaches you Kida syntax through hands-on examples, building up to a complete blog template.

## Goal

By the end of this tutorial, you will:
1. Understand Kida syntax basics
2. Know how to use pattern matching and pipelines
3. Create a custom blog template
4. Use fragment caching for performance

## Prerequisites

- Bengal installed (`pip install bengal`)
- Python 3.14+ (3.14t recommended)
- Basic understanding of HTML
- Familiarity with terminal/command line

## What is Kida?

Kida is Bengal's **default template engine**, designed for:
- **Free-threading**: GIL-free rendering on Python 3.14t+ (parallel template rendering)
- **Cleaner syntax**: Unified `{% end %}` for all blocks, pattern matching, pipelines
- **Performance**: 2-5x faster than Jinja2 with automatic caching
- **Jinja2 compatible**: Existing Jinja2 templates work without changes

:::{tip}
**Coming from Jinja2?** Kida can parse Jinja2 syntax, so your existing templates work. This tutorial focuses on Kida-native features.
:::

## Step 1: Set Up Your Project

### Initialize Bengal Site

```bash
# Create a new Bengal site
bengal new site my-kida-site

# Enter the directory
cd my-kida-site
```

### Configure Kida (Optional)

Kida is the default engine. Optionally configure Kida options in `bengal.yaml`:

```yaml
kida:
  bytecode_cache: true       # Cache compiled templates (default)
```

**Note**: Strict mode (raising errors for undefined variables) is always enabled in Kida and cannot be disabled. This helps catch typos and missing variables early.

### Create Test Template

Create your first Kida template:

```bash
mkdir -p templates
touch templates/test.html
```

## Step 2: Basic Syntax

### Variables

Output a variable:

```kida
{# templates/test.html #}
<h1>{{ site.config.title }}</h1>
<p>Welcome to {{ site.config.title }}!</p>
```

### Conditionals

Use `{% if %}` with unified `{% end %}`:

```kida
{% if page.published %}
  <article>
    <h1>{{ page.title }}</h1>
    {{ page.content | safe }}
  </article>
{% end %}
```

### Loops

Iterate over collections:

```kida
<ul>
  {% for post in site.pages %}
    <li>{{ post.title }}</li>
  {% end %}
</ul>
```

**Loop variables**:

```kida
{% for item in items %}
  {% if loop.first %}First item{% end %}
  Item {{ loop.index }} of {{ loop.length }}
{% end %}
```

### Template Variables

Use `{% let %}` for template-wide variables (available throughout the entire template):

```kida
{% let site_title = site.config.title %}
{% let recent_posts = site.pages |> where('type', 'blog') |> take(5) %}

<h1>{{ site_title }}</h1>
<ul>
  {% for post in recent_posts %}
    <li>{{ post.title }}</li>
  {% end %}
</ul>
```

**Variable Scoping**:

- `{% let %}` — Template-scoped (available everywhere in the template)
- `{% set %}` — Block-scoped (only within the current block)
- `{% export %}` — Export from inner scope to outer scope

## Step 3: Pattern Matching

Replace long `if/elif` chains with pattern matching:

```kida
{% match page.type %}
  {% case "blog" %}
    <article class="blog-post">
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% case "doc" %}
    <article class="doc">
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
  {% case _ %}
    <article>
      <h1>{{ page.title }}</h1>
      {{ page.content | safe }}
    </article>
{% end %}
```

**Practice**: Create a template that shows different icons based on page type. Use pattern matching to handle `blog`, `doc`, and `gallery` page types, with a default case for other types.

## Step 4: Pipeline Operator

Use `|>` for readable filter chains:

```kida
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}
```

**Practice**: Filter posts by tag, sort by date, and limit to 5. Use the pipeline operator to chain these operations together.

## Step 5: Template Inheritance

### Base Layout

Create `templates/baseof.html`:

```kida
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{{ site.config.title }}{% endblock %}</title>
</head>
<body>
  <header>
    <h1>{{ site.config.title }}</h1>
    <nav>
      {% for item in site.menus.main %}
        <a href="{{ item.href }}">{{ item.title }}</a>
      {% end %}
    </nav>
  </header>

  <main>
    {% block content %}{% endblock %}
  </main>

  <footer>
    <p>&copy; {{ site.config.title }}</p>
  </footer>
</body>
</html>
```

### Extend Base

Create `templates/blog/single.html`:

```kida
{% extends "baseof.html" %}

{% block title %}{{ page.title }} - {{ site.config.title }}{% endblock %}

{% block content %}
  <article class="blog-post">
    <header>
      <h1>{{ page.title }}</h1>
      <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
    </header>
    <div class="content">
      {{ page.content | safe }}
    </div>
  </article>
{% endblock %}
```

## Step 6: Build a Complete Blog Template

Create a full-featured blog template:

```kida
{# templates/blog/single.html #}
{% extends "baseof.html" %}

{% let post = page %}
{% let reading_time = post.content | reading_time %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', post.tags[0] ?? '')
  |> where('id', '!=', post.id)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{% block title %}{{ post.title }} - {{ site.config.title }}{% endblock %}

{% block content %}
  <article class="blog-post">
    <header>
      <h1>{{ post.title }}</h1>

      <div class="post-meta">
        <time datetime="{{ post.date | dateformat('%Y-%m-%d') }}">
          {{ post.date | dateformat('%B %d, %Y') }}
        </time>
        <span class="reading-time">{{ reading_time }} min read</span>
      </div>
    </header>

    <div class="post-content">
      {{ post.content | safe }}
    </div>

    {% if post.tags %}
      <footer class="post-footer">
        <div class="tags">
          {% for tag in post.tags %}
            <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
          {% end %}
        </div>
      </footer>
    {% end %}
  </article>

  {% cache "related-posts-" ~ post.id %}
    {% if related_posts %}
      <aside class="related-posts">
        <h2>Related Posts</h2>
        <ul>
          {% for related in related_posts %}
            <li>
              <a href="{{ related.url }}">{{ related.title }}</a>
              <span>{{ related.date | days_ago }} days ago</span>
            </li>
          {% end %}
        </ul>
      </aside>
    {% end %}
  {% end %}
{% endblock %}
```

## Step 7: Fragment Caching

Cache expensive operations:

```kida
{% cache "sidebar-nav" %}
  {% let nav = get_nav_tree(page) %}
  <nav>
    {% for item in nav %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% end %}
  </nav>
{% end %}

{% cache "recent-posts" %}
  {% let recent = site.pages
    |> where('type', 'blog')
    |> sort_by('date', reverse=true)
    |> take(10) %}
  <ul>
    {% for post in recent %}
      <li><a href="{{ post.url }}">{{ post.title }}</a></li>
    {% end %}
  </ul>
{% end %}
```

:::{note}
**Cache TTL**: Fragment cache uses a global TTL configured in `bengal.yaml`. All cached fragments share the same expiration time. Per-key TTL is not currently supported. See [Fragment Caching](/docs/theming/templating/kida/caching/fragments/) for configuration details.
:::

## Step 8: Create Content

Create a blog post:

```bash
bengal new page "My First Post" --section blog
```

Edit `content/blog/my-first-post.md`:

```markdown
---
title: My First Post
date: 2024-01-15
tags:
  - kida
  - tutorial
---

This is my first blog post using Kida templates!
```

## Step 9: Build and Test

```bash
# Build the site
bengal build

# Or run dev server
bengal serve
```

Visit `http://localhost:5173/blog/my-first-post/` to see your template.

## Step 10: Advanced Features

### Functions

Define reusable functions that can access outer scope variables:

```kida
{% let site_title = site.config.title %}

{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <span>From: {{ site_title }}</span>  {# Accesses outer variable #}
  </div>
{% end %}

{{ card(page) }}
```

:::{tip}
Kida functions automatically access variables from their surrounding context. You don't need to pass `site`, `config`, or other shared values as parameters.
:::

### Optional Chaining

Safe attribute access:

```kida
{{ user?.profile?.name ?? 'Anonymous' }}
{{ page?.metadata?.author ?? 'Unknown' }}
```

### Null Coalescing

Fallback for None:

```kida
{{ page.subtitle ?? page.title }}
{{ user.name ?? 'Guest' }}
```

## Common Patterns

### Blog Post List

```kida
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(10) %}

<ul>
  {% for post in posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    </li>
  {% end %}
</ul>
```

### Tag Cloud

```kida
{% let tags = site.tags
  |> items()
  |> sort_by('count', reverse=true)
  |> take(20) %}

<div class="tag-cloud">
  {% for tag in tags %}
    <a href="{{ tag_url(tag.name) }}" class="tag">
      {{ tag.name }} ({{ tag.count }})
    </a>
  {% end %}
</div>
```

## Troubleshooting

### Undefined Variable Error

Kida raises errors for undefined variables by default (strict mode). This helps catch typos and missing variables early:

```kida
{# ❌ Raises UndefinedError if 'missing_var' doesn't exist #}
{{ missing_var }}

{# ✅ Safe with default filter #}
{{ missing_var | default('N/A') }}

{# ✅ Safe with null coalescing operator #}
{{ missing_var ?? 'N/A' }}
```

**Note**: Strict mode cannot be disabled in Kida. Undefined variables will always raise `UndefinedError`. Use the `default` filter or null coalescing operator (`??`) to provide fallback values.

### Template Not Found

Check template lookup order:
1. `templates/` (your project)
2. Theme templates
3. Bengal defaults

See [Template Lookup Order](/docs/theming/templating/#template-lookup-order) for details.

### Syntax Errors

Common issues:
- Missing `{% end %}` for blocks
- Incorrect filter names
- Undefined variables

Check build output for detailed error messages.

## Next Steps

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Kida How-Tos](/docs/theming/templating/kida/) — Common tasks and patterns
- [Fragment Caching](/docs/theming/templating/kida/caching/fragments/) — Manual caching for expensive operations
- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build advanced templates
- [Add Custom Filters](/docs/theming/templating/kida/add-custom-filter/) — Extend Kida functionality

## Summary

You've learned:
- ✅ Basic Kida syntax (variables, conditionals, loops)
- ✅ Pattern matching for cleaner conditionals
- ✅ Pipeline operator for readable filter chains
- ✅ Template inheritance and blocks
- ✅ Fragment caching for performance
- ✅ Common patterns and best practices

**Practice**: Build a complete blog with list pages, single posts, and tag pages using Kida syntax.

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Available filters and functions
- [Theming Guide](/docs/theming/templating/) — Template organization
- [Performance Guide](/docs/building/performance/) — Optimization tips
:::
