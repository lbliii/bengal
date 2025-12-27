---
title: KIDA vs Jinja2 Comparison (Legacy)
nav_title: KIDA vs Jinja2 (Legacy)
description: Legacy comparison document - see new modular comparison structure
weight: 100
type: doc
draft: true
lang: en
tags:
- reference
- templates
- kida
- jinja
- comparison
- legacy
keywords:
- kida vs jinja
- template comparison
- syntax comparison
- migration
category: reference
---

# KIDA vs Jinja2 Comparison (Legacy)

:::{warning}
**This is a legacy document**. The comparison has been restructured into focused, modular articles. See the [new Comparison Guide](/docs/theming/templating/kida/comparison/) for the updated structure.
:::

This document contains a comprehensive side-by-side comparison of KIDA and Jinja2. For better organization, this content has been split into focused articles:

- **[Comparison Overview](/docs/theming/templating/kida/comparison/)** — Feature-by-feature comparison index
- **[Syntax Comparison](/docs/theming/templating/kida/comparison/syntax)** — Side-by-side syntax examples
- **[Control Flow](/docs/theming/templating/kida/comparison/control-flow)** — Conditionals, loops, pattern matching
- **[Variables and Scoping](/docs/theming/templating/kida/comparison/variables)** — Variable scoping patterns
- **[Functions and Macros](/docs/theming/templating/kida/comparison/functions)** — Functions vs macros
- **[Filters and Pipelines](/docs/theming/templating/kida/comparison/filters)** — Filter syntax and pipelines
- **[Caching](/docs/theming/templating/kida/comparison/caching)** — Fragment caching and optimization
- **[Modern Features](/docs/theming/templating/kida/comparison/modern-features)** — Optional chaining, null coalescing, etc.
- **[Performance](/docs/theming/templating/kida/comparison/performance)** — Benchmarks and optimization

---

# KIDA vs Jinja2 Comparison (Legacy Content)

Side-by-side comparison of common template patterns in KIDA (Bengal's default engine) and Jinja2. Use this reference when migrating templates or learning KIDA syntax.

:::{tip}
**KIDA is Jinja2-compatible**: Your Jinja2 templates work without changes. KIDA is the default engine, so you can migrate incrementally to unlock performance benefits.
:::

## Quick Reference

| Feature | KIDA | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` (unified) | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let %}` (template-scoped) | `{% set %}` (block-scoped) |
| Pattern matching | `{% match %}...{% case %}` | `{% if %}...{% elif %}` chains |
| Pipeline operator | `\|>` (left-to-right) | `\|` (filter chain) |
| Optional chaining | `?.` | Not available |
| Null coalescing | `??` (simple) or `\| default()` (filter chains) | `\| default()` |
| Fragment caching | `{% cache %}` (built-in) | Requires extension |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (no closure) |
| Range literals | `1..10`, `1...11`, `1..10 by 2` | `range(1, 11)` |
| Loop control | `{% break %}`, `{% continue %}` | Limited support |

---

## Block Endings

KIDA uses `{% end %}` for all block endings, eliminating the need to remember specific closing tags.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% if page.draft %}
  <span class="draft">Draft</span>
{% end %}

{% for post in posts %}
  <article>{{ post.title }}</article>
{% end %}

{% block content %}
  {{ page.content | safe }}
{% endblock %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{% if page.draft %}
  <span class="draft">Draft</span>
{% endif %}

{% for post in posts %}
  <article>{{ post.title }}</article>
{% endfor %}

{% block content %}
  {{ page.content | safe }}
{% endblock %}
```
:::{/tab-item}

:::{/tab-set}

:::{note}
KIDA also accepts `{% endblock %}` for block endings (Jinja2 compatibility), but `{% end %}` works everywhere.
:::

---

## Variables and Scoping

KIDA distinguishes between template-scoped (`{% let %}`) and block-scoped (`{% set %}`) variables.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Template-scoped: available everywhere in template #}
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}

{# Block-scoped: only available in current block #}
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>  {# Works here #}
{% end %}
{# status not accessible here #}

{# Use site_title anywhere #}
<title>{{ page.title }} - {{ site_title }}</title>
```
:::

:::{tab-item} Jinja2
```jinja2
{# Block-scoped only: may not be accessible outside block #}
{% set site_title = site.config.title %}
{% set nav_items = site.menus.main %}

{# Block-scoped: only available in current block #}
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>  {# Works here #}
{% endif %}
{# status may or may not be accessible depending on context #}

{# Variables at template level work, but scoping is confusing #}
<title>{{ page.title }} - {{ site_title }}</title>
```
:::

:::

### Exporting from Inner Scope

KIDA provides `{% export %}` to make inner-scope variables accessible outside:

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% for post in posts %}
  {% if post.featured %}
    {% export featured_post = post %}
  {% end %}
{% end %}

{# featured_post available here #}
<div class="featured">{{ featured_post.title }}</div>
```
:::

:::{tab-item} Jinja2
```jinja2
{# Jinja2 workaround: use namespace #}
{% set ns = namespace(featured_post=none) %}
{% for post in posts %}
  {% if post.featured %}
    {% set ns.featured_post = post %}
  {% endif %}
{% endfor %}

{# Access via namespace #}
<div class="featured">{{ ns.featured_post.title }}</div>
```
:::

:::

---

## Pattern Matching

KIDA's `{% match %}` replaces verbose `if/elif` chains with clean pattern matching.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% match page.type %}
  {% case "blog" %}
    <i class="icon-pen"></i> Blog Post
  {% case "doc" %}
    <i class="icon-book"></i> Documentation
  {% case "tutorial" %}
    <i class="icon-graduation-cap"></i> Tutorial
  {% case "api" %}
    <i class="icon-code"></i> API Reference
  {% case _ %}
    <i class="icon-file"></i> Page
{% end %}
```
:::

:::{tab-item} Jinja2
```jinja2
{% if page.type == "blog" %}
  <i class="icon-pen"></i> Blog Post
{% elif page.type == "doc" %}
  <i class="icon-book"></i> Documentation
{% elif page.type == "tutorial" %}
  <i class="icon-graduation-cap"></i> Tutorial
{% elif page.type == "api" %}
  <i class="icon-code"></i> API Reference
{% else %}
  <i class="icon-file"></i> Page
{% endif %}
```
:::

:::

### Pattern Matching with Complex Conditions

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% match page.status %}
  {% case "published" %}
    <span class="badge badge-success">Published</span>
  {% case "draft" %}
    <span class="badge badge-warning">Draft</span>
  {% case "scheduled" %}
    <span class="badge badge-info">Scheduled: {{ page.publish_date }}</span>
  {% case "archived" %}
    <span class="badge badge-secondary">Archived</span>
  {% case _ %}
    <span class="badge badge-muted">Unknown</span>
{% end %}
```
:::

:::{tab-item} Jinja2
```jinja2
{% if page.status == "published" %}
  <span class="badge badge-success">Published</span>
{% elif page.status == "draft" %}
  <span class="badge badge-warning">Draft</span>
{% elif page.status == "scheduled" %}
  <span class="badge badge-info">Scheduled: {{ page.publish_date }}</span>
{% elif page.status == "archived" %}
  <span class="badge badge-secondary">Archived</span>
{% else %}
  <span class="badge badge-muted">Unknown</span>
{% endif %}
```
:::

:::

---

## Pipeline Operator

KIDA's `|>` pipeline reads left-to-right, matching natural reading order.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Left-to-right: Read naturally as a data pipeline #}
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{# Single line #}
{{ items |> where('published', true) |> sort_by('date') |> first }}

{# Text processing pipeline #}
{{ page.content |> markdownify |> truncate(200) |> striptags }}
```
:::

:::{tab-item} Jinja2
```jinja2
{# Inside-out: Must read from inner to outer #}
{% set recent_posts = site.pages
  | selectattr('type', 'eq', 'blog')
  | selectattr('draft', 'eq', false)
  | sort(attribute='date', reverse=true)
  | list | batch(5) | first %}

{# Single line - harder to read #}
{{ items | selectattr('published') | sort(attribute='date') | first }}

{# Text processing - read order differs from execution order #}
{{ page.content | markdownify | truncate(200) | striptags }}
```
:::

:::

### Filter Name Differences

| Jinja2 Filter | KIDA Filter | Description |
|--------------|-------------|-------------|
| `selectattr('key')` | `where('key', true)` | Boolean filter |
| `selectattr('key', 'eq', val)` | `where('key', val)` | Equality filter |
| `rejectattr('key')` | `where_not('key', true)` | Inverse boolean |
| `sort(attribute='key')` | `sort_by('key')` | Sort by attribute |
| `first` (single item) | `first` | Get first item |
| `batch(n) \| first` | `take(n)` | Get first n items |
| `groupby('key')` | `group_by('key')` | Group by attribute |

---

## Optional Chaining and Null Coalescing

KIDA provides modern JavaScript-like operators for null-safe access.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Optional chaining: Safe navigation through potentially null values #}
{{ user?.profile?.name | default('Anonymous') }}
{{ page?.metadata?.author?.avatar }}
{{ config?.social?.twitter?.handle }}

{# Null coalescing: Concise fallback for simple output #}
{{ page.subtitle ?? page.title }}
{{ user.nickname ?? user.name ?? 'Guest' }}
{{ config.theme ?? 'default' }}

{# Use | default() when applying filters after fallback #}
{{ items | default([]) | length }}
{{ description | default('') | truncate(100) }}

{# Combined usage #}
{{ page?.metadata?.image ?? site?.config?.default_image ?? '/images/placeholder.png' }}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# Defensive coding required: verbose and error-prone #}
{{ user.profile.name if user and user.profile and user.profile.name else 'Anonymous' }}
{{ page.metadata.author.avatar if page and page.metadata and page.metadata.author else '' }}

{# Default filter for fallbacks #}
{{ page.subtitle | default(page.title) }}
{{ user.nickname | default(user.name) | default('Guest') }}
{{ config.theme | default('default') }}

{# Combined: Very verbose #}
{% if page and page.metadata and page.metadata.image %}
  {{ page.metadata.image }}
{% elif site and site.config and site.config.default_image %}
  {{ site.config.default_image }}
{% else %}
  /images/placeholder.png
{% endif %}
```
:::{/tab-item}

:::{/tab-set}

---

## Functions vs Macros

KIDA's `{% def %}` provides true lexical scoping, unlike Jinja2 macros.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# KIDA functions have access to outer scope #}
{% let site_name = site.config.title %}
{% let theme_color = config.theme.primary_color %}

{% def card(item) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <small>From: {{ site_name }}</small>  {# Accesses outer scope! #}
  </div>
{% end %}

{# Default parameters work naturally #}
{% def button(text, href, variant="primary", size="md") %}
  <a href="{{ href }}" class="btn btn-{{ variant }} btn-{{ size }}">
    {{ text }}
  </a>
{% end %}

{{ button("Get Started", "/docs", variant="success", size="lg") }}
{{ button("Learn More", "/about") }}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# Jinja2 macros don't have access to outer scope by default #}
{% set site_name = site.config.title %}
{% set theme_color = config.theme.primary_color %}

{# Must pass all needed variables explicitly #}
{% macro card(item, site_name, theme_color) %}
  <div class="card" style="border-color: {{ theme_color }}">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <small>From: {{ site_name }}</small>
  </div>
{% endmacro %}

{# Or use caller() pattern for some access #}
{% macro button(text, href, variant="primary", size="md") %}
  <a href="{{ href }}" class="btn btn-{{ variant }} btn-{{ size }}">
    {{ text }}
  </a>
{% endmacro %}

{{ button("Get Started", "/docs", variant="success", size="lg") }}
{{ button("Learn More", "/about") }}
```
:::{/tab-item}

:::{/tab-set}

### Functions with Block Content (Slots)

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% def modal(title, size="md") %}
  <div class="modal modal-{{ size }}">
    <div class="modal-header">
      <h2>{{ title }}</h2>
    </div>
    <div class="modal-body">
      {% slot %}
        {# Default content if no call block provided #}
        <p>Modal content goes here</p>
      {% endslot %}
    </div>
  </div>
{% end %}

{# Use with custom content #}
{% call modal("Confirm Action", size="sm") %}
  <p>Are you sure you want to delete this item?</p>
  <div class="modal-actions">
    <button class="btn btn-danger">Delete</button>
    <button class="btn btn-secondary">Cancel</button>
  </div>
{% endcall %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{% macro modal(title, size="md") %}
  <div class="modal modal-{{ size }}">
    <div class="modal-header">
      <h2>{{ title }}</h2>
    </div>
    <div class="modal-body">
      {{ caller() }}
    </div>
  </div>
{% endmacro %}

{# Use with custom content #}
{% call modal("Confirm Action", size="sm") %}
  <p>Are you sure you want to delete this item?</p>
  <div class="modal-actions">
    <button class="btn btn-danger">Delete</button>
    <button class="btn btn-secondary">Cancel</button>
  </div>
{% endcall %}
```
:::{/tab-item}

:::{/tab-set}

---

## Fragment Caching

KIDA has built-in fragment caching; Jinja2 requires an extension.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Simple cache #}
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}

{# Cache with TTL (Time To Live) #}
{% cache "weather-widget", ttl="5m" %}
  {{ fetch_weather_data() }}
{% end %}

{# Dynamic cache key #}
{% cache "user-profile-" ~ user.id %}
  {{ render_user_profile(user) }}
{% end %}

{# Version-based invalidation #}
{% cache "posts-" ~ site.nav_version %}
  {% for post in recent_posts %}
    <article>{{ post.title }}</article>
  {% end %}
{% end %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# Requires jinja2-fragment-cache extension #}
{# Not available by default #}

{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% endcache %}

{# TTL support depends on extension #}
{% cache "weather-widget" 300 %}
  {{ fetch_weather_data() }}
{% endcache %}

{# Dynamic key #}
{% cache "user-profile-" ~ user.id %}
  {{ render_user_profile(user) }}
{% endcache %}

{# Or manual caching in Python code #}
{# Most Jinja2 users don't have template-level caching #}
```
:::{/tab-item}

:::{/tab-set}

---

## Range Literals and Loop Control

KIDA provides modern range syntax and full loop control.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Inclusive range #}
{% for i in 1..5 %}
  {{ i }}  {# 1, 2, 3, 4, 5 #}
{% end %}

{# Exclusive range #}
{% for i in 1...5 %}
  {{ i }}  {# 1, 2, 3, 4 #}
{% end %}

{# Range with step #}
{% for i in 0..10 by 2 %}
  {{ i }}  {# 0, 2, 4, 6, 8, 10 #}
{% end %}

{# Break and continue #}
{% for item in items %}
  {% if item.hidden %}
    {% continue %}
  {% end %}
  {% if item.is_final %}
    {{ item.title }}
    {% break %}
  {% end %}
  {{ item.title }}
{% end %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# range() function required #}
{% for i in range(1, 6) %}
  {{ i }}  {# 1, 2, 3, 4, 5 #}
{% endfor %}

{# Exclusive range (default) #}
{% for i in range(1, 5) %}
  {{ i }}  {# 1, 2, 3, 4 #}
{% endfor %}

{# Range with step #}
{% for i in range(0, 11, 2) %}
  {{ i }}  {# 0, 2, 4, 6, 8, 10 #}
{% endfor %}

{# No break/continue - must use workarounds #}
{% for item in items if not item.hidden %}
  {# No break available - must process all items #}
  {{ item.title }}
{% endfor %}
```
:::{/tab-item}

:::{/tab-set}

---

## Collection Filtering

Real-world comparison of filtering blog posts.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Get published blog posts, sorted by date, limited to 10 #}
{% let posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> where('published', true)
  |> sort_by('date', reverse=true)
  |> take(10) %}

{# Get featured posts from a specific category #}
{% let featured = site.pages
  |> where('featured', true)
  |> where('category', 'tutorials')
  |> sort_by('weight') %}

{# Filter by multiple conditions with grouping #}
{% let grouped_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> group_by('category') %}

{% for category, posts in grouped_posts %}
  <h2>{{ category }}</h2>
  {% for post in posts |> take(5) %}
    <a href="{{ post.url }}">{{ post.title }}</a>
  {% end %}
{% end %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# Get published blog posts, sorted by date, limited to 10 #}
{% set posts = site.pages
  | selectattr('type', 'eq', 'blog')
  | selectattr('draft', 'eq', false)
  | selectattr('published')
  | sort(attribute='date', reverse=true)
  | list %}
{% set posts = posts[:10] %}

{# Get featured posts from a specific category #}
{% set featured = site.pages
  | selectattr('featured')
  | selectattr('category', 'eq', 'tutorials')
  | sort(attribute='weight')
  | list %}

{# Filter by multiple conditions with grouping #}
{% set filtered = site.pages
  | selectattr('type', 'eq', 'blog')
  | selectattr('draft', 'eq', false)
  | list %}
{% set grouped_posts = filtered | groupby('category') %}

{% for category, posts in grouped_posts %}
  <h2>{{ category }}</h2>
  {% for post in posts[:5] %}
    <a href="{{ post.url }}">{{ post.title }}</a>
  {% endfor %}
{% endfor %}
```
:::{/tab-item}

:::{/tab-set}

---

## Complete Template Example

A blog post template showing multiple KIDA features together.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{% extends "baseof.html" %}

{# Template-scoped variables #}
{% let site_title = site.config.title %}
{% let author = page?.metadata?.author ?? site?.config?.default_author ?? 'Anonymous' %}
{% let post_image = page?.metadata?.image ?? page?.metadata?.cover %}
{% let related_posts = site.pages
  |> where('type', 'blog')
  |> where('tags', page.tags | first)
  |> where_not('_path', page._path)
  |> sort_by('date', reverse=true)
  |> take(3) %}

{# Reusable tag component #}
{% def tag_badge(tag) %}
  <a href="/tags/{{ tag | slugify }}" class="tag">{{ tag }}</a>
{% end %}

{% block content %}
<article class="blog-post">
  {# Hero section with optional image #}
  {% if post_image %}
  <div class="post-hero">
    <img src="{{ post_image }}" alt="{{ page.title }}" loading="eager">
  </div>
  {% end %}

  <header class="post-header">
    <h1>{{ page.title }}</h1>

    <div class="post-meta">
      <span class="author">By {{ author }}</span>
      <time datetime="{{ page.date | date_iso }}">
        {{ page.date | dateformat('%B %d, %Y') }}
      </time>
      <span class="reading-time">
        {{ page.content | wordcount | reading_time }} min read
      </span>
    </div>

    {% if page.tags | length > 0 %}
    <div class="post-tags">
      {% for tag in page.tags %}
        {{ tag_badge(tag) }}
      {% end %}
    </div>
    {% end %}
  </header>

  <div class="post-content">
    {{ page.content | safe }}
  </div>

  {# Author bio with pattern matching #}
  {% match page.metadata.show_author %}
    {% case true %}
      {% include "partials/author-bio.html" %}
    {% case "compact" %}
      {% include "partials/author-compact.html" %}
    {% case _ %}
      {# No author box #}
  {% end %}

  {# Related posts with caching #}
  {% if related_posts | length > 0 %}
  {% cache "related-" ~ page._path %}
  <aside class="related-posts">
    <h2>Related Posts</h2>
    <div class="related-grid">
      {% for post in related_posts %}
      <a href="{{ post.url }}" class="related-card">
        <h3>{{ post.title }}</h3>
        <time>{{ post.date | time_ago }}</time>
      </a>
      {% end %}
    </div>
  </aside>
  {% end %}
  {% end %}
</article>
{% endblock %}
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{% extends "baseof.html" %}

{# Block-scoped variables #}
{% set site_title = site.config.title %}
{% set author = page.metadata.author if page and page.metadata and page.metadata.author else (site.config.default_author if site and site.config else 'Anonymous') %}
{% set post_image = page.metadata.image if page and page.metadata and page.metadata.image else (page.metadata.cover if page and page.metadata else none) %}
{% set related_posts = site.pages
  | selectattr('type', 'eq', 'blog')
  | selectattr('tags', 'contains', page.tags[0] if page.tags else '')
  | rejectattr('_path', 'eq', page._path)
  | sort(attribute='date', reverse=true)
  | list %}
{% set related_posts = related_posts[:3] %}

{# Macro for tag badge #}
{% macro tag_badge(tag) %}
  <a href="/tags/{{ tag | slugify }}" class="tag">{{ tag }}</a>
{% endmacro %}

{% block content %}
<article class="blog-post">
  {# Hero section with optional image #}
  {% if post_image %}
  <div class="post-hero">
    <img src="{{ post_image }}" alt="{{ page.title }}" loading="eager">
  </div>
  {% endif %}

  <header class="post-header">
    <h1>{{ page.title }}</h1>

    <div class="post-meta">
      <span class="author">By {{ author }}</span>
      <time datetime="{{ page.date | date('%Y-%m-%d') }}">
        {{ page.date | date('%B %d, %Y') }}
      </time>
      <span class="reading-time">
        {{ page.content | wordcount | reading_time }} min read
      </span>
    </div>

    {% if page.tags and page.tags | length > 0 %}
    <div class="post-tags">
      {% for tag in page.tags %}
        {{ tag_badge(tag) }}
      {% endfor %}
    </div>
    {% endif %}
  </header>

  <div class="post-content">
    {{ page.content | safe }}
  </div>

  {# Author bio - verbose conditional #}
  {% if page.metadata.show_author == true %}
    {% include "partials/author-bio.html" %}
  {% elif page.metadata.show_author == "compact" %}
    {% include "partials/author-compact.html" %}
  {% endif %}

  {# Related posts - no built-in caching #}
  {% if related_posts | length > 0 %}
  <aside class="related-posts">
    <h2>Related Posts</h2>
    <div class="related-grid">
      {% for post in related_posts %}
      <a href="{{ post.url }}" class="related-card">
        <h3>{{ post.title }}</h3>
        <time>{{ post.date | time_ago }}</time>
      </a>
      {% endfor %}
    </div>
  </aside>
  {% endif %}
</article>
{% endblock %}
```
:::{/tab-item}

:::{/tab-set}

---

## Navigation Template Example

A common navigation template pattern.

:::{tab-set}

:::{tab-item} KIDA
```jinja
{# Navigation with automatic caching (site-scoped blocks are cached automatically) #}
{% let main_menu = get_menu('main') %}
{% let current_path = page._path %}

<nav class="main-nav">
  <ul class="nav-list">
    {% for item in main_menu %}
      {% let is_active = current_path == item.url or current_path | startswith(item.url ~ '/') %}
      {% let has_children = item.children | length > 0 %}

      <li class="nav-item{% if is_active %} active{% end %}{% if has_children %} has-dropdown{% end %}">
        <a href="{{ item.url }}"
           {% if is_active %}aria-current="page"{% end %}>
          {% if item.icon %}
            <i class="icon-{{ item.icon }}"></i>
          {% end %}
          {{ item.title }}
        </a>

        {% if has_children %}
        <ul class="nav-dropdown">
          {% for child in item.children %}
            {% let child_active = current_path == child.url %}
            <li{% if child_active %} class="active"{% end %}>
              <a href="{{ child.url }}">{{ child.title }}</a>
            </li>
          {% end %}
        </ul>
        {% end %}
      </li>
    {% end %}
  </ul>
</nav>
```
:::{/tab-item}

:::{tab-item} Jinja2
```jinja2
{# Navigation - no automatic caching #}
{% set main_menu = get_menu('main') %}
{% set current_path = page._path %}

<nav class="main-nav">
  <ul class="nav-list">
    {% for item in main_menu %}
      {% set is_active = current_path == item.url or current_path.startswith(item.url ~ '/') %}
      {% set has_children = item.children | length > 0 %}

      <li class="nav-item{% if is_active %} active{% endif %}{% if has_children %} has-dropdown{% endif %}">
        <a href="{{ item.url }}"
           {% if is_active %}aria-current="page"{% endif %}>
          {% if item.icon %}
            <i class="icon-{{ item.icon }}"></i>
          {% endif %}
          {{ item.title }}
        </a>

        {% if has_children %}
        <ul class="nav-dropdown">
          {% for child in item.children %}
            {% set child_active = current_path == child.url %}
            <li{% if child_active %} class="active"{% endif %}>
              <a href="{{ child.url }}">{{ child.title }}</a>
            </li>
          {% endfor %}
        </ul>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
</nav>
```
:::{/tab-item}

:::{/tab-set}

---

## Performance Comparison

| Metric | KIDA | Jinja2 |
|--------|------|--------|
| Render speed | **5.6x faster** | Baseline |
| Site-scoped block caching | Automatic | Manual/None |
| Fragment caching | Built-in | Extension required |
| Free-threaded Python | Optimized | GIL-bound |
| Bytecode caching | Yes | Yes |

### Automatic Block Caching

KIDA automatically detects and caches site-scoped blocks (navigation, footer, sidebar) that don't depend on page-specific data. This provides **10-100x faster builds** for navigation-heavy sites with no template changes required.

```jinja
{# KIDA automatically caches this block #}
{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% endblock %}

{# This block renders per-page (page-specific data) #}
{% block content %}
  {{ page.content | safe }}
{% endblock %}
```

---

## Migration Checklist

When migrating from Jinja2 to KIDA:

- [ ] Enable KIDA in `bengal.yaml`: `template_engine: kida`
- [ ] Replace block endings (`{% endif %}` → `{% end %}`)
- [ ] Replace template-wide `{% set %}` with `{% let %}`
- [ ] Convert long `if/elif` chains to `{% match %}`
- [ ] Update filter chains to use `|>` and KIDA filter names
- [ ] Add `{% cache %}` for expensive operations
- [ ] Use `?.` for null-safe access
- [ ] Use `??` for default values

:::{seealso}
- [Migrate from Jinja2 to KIDA](/docs/theming/templating/kida/migrate-jinja-to-kida/) — Step-by-step migration guide
- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [KIDA How-Tos](/docs/theming/templating/kida/) — Common tasks and patterns
:::
