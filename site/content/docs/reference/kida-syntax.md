---
title: KIDA Syntax Reference
nav_title: KIDA Syntax
description: Complete reference for KIDA template syntax, operators, and features
weight: 60
type: doc
draft: false
lang: en
tags:
- reference
- templates
- kida
- syntax
keywords:
- kida syntax
- template syntax
- unified endings
- pattern matching
- pipeline operator
category: reference
---

# KIDA Syntax Reference

Complete reference for KIDA template syntax, operators, and features. KIDA is Bengal's **default template engine**, optimized for performance and free-threaded Python.

:::{tip}
**New to KIDA?** Start with the [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) for a guided introduction. KIDA is Jinja2-compatible, so existing Jinja2 templates work without changes.
:::

## Quick Comparison: KIDA vs Jinja2

| Feature | KIDA | Jinja2 |
|---------|------|--------|
| Block endings | `{% end %}` (unified) | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let %}` (template-scoped) | `{% set %}` (block-scoped) |
| Block variables | `{% set %}` (block-scoped) | `{% set %}` (block-scoped) |
| Pattern matching | `{% match %}...{% case %}...{% end %}` | `{% if %}...{% elif %}...{% endif %}` |
| Pipeline operator | `|>` | `\|` (filter chain) |
| Fragment caching | `{% cache key %}...{% end %}` | Requires extension |
| Functions | `{% def %}` (lexical scope) | `{% macro %}` (no scope) |

## Basic Syntax

### Variables

Output a variable:

```kida
{{ page.title }}
{{ site.config.title }}
{{ page.content | safe }}
```

### Comments

```kida
{# This is a comment #}
{# Multi-line
   comments work too #}
```

### Escaping

```kida
{# HTML is escaped by default #}
{{ user_input }}  {# Escaped #}
{{ user_input | safe }}  {# Raw HTML #}
{{ user_input | e }}  {# Explicit escape #}
```

## Control Flow

### Conditionals

```kida
{% if page.draft %}
  <span class="draft">Draft</span>
{% end %}

{% if page.published %}
  Published
{% elif page.scheduled %}
  Scheduled
{% else %}
  Unpublished
{% end %}
```

### Loops

```kida
{% for post in site.pages | where('type', 'blog') %}
  <article>
    <h2>{{ post.title }}</h2>
    {{ post.content | safe }}
  </article>
{% end %}
```

**Loop variables**:

```kida
{% for item in items %}
  {% if loop.first %}First item{% end %}
  {% if loop.last %}Last item{% end %}
  Item {{ loop.index }} of {{ loop.length }}
{% end %}
```

### Pattern Matching

KIDA's native pattern matching replaces long `if/elif` chains:

```kida
{% match page.type %}
  {% case "blog" %}
    <i class="icon-pen"></i> Blog Post
  {% case "doc" %}
    <i class="icon-book"></i> Documentation
  {% case "tutorial" %}
    <i class="icon-graduation-cap"></i> Tutorial
  {% case _ %}
    <i class="icon-file"></i> Page
{% end %}
```

**With expressions**:

```kida
{% match page.status %}
  {% case "published" %}
    <span class="status-published">Published</span>
  {% case "draft" %}
    <span class="status-draft">Draft</span>
  {% case _ %}
    <span class="status-unknown">Unknown</span>
{% end %}
```

## Variables and Scoping

### Template-Scoped Variables (`{% let %}`)

Variables available throughout the entire template:

```kida
{% let site_title = site.config.title %}
{% let nav_items = site.menus.main %}

{# Available anywhere in template #}
<h1>{{ site_title }}</h1>
```

### Block-Scoped Variables (`{% set %}`)

Variables scoped to the current block:

```kida
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>
{% end %}
{# status not available here #}
```

### Exporting from Inner Scope (`{% export %}`)

Make a variable from an inner scope available to the outer scope:

```kida
{% for post in posts %}
  {% if post.featured %}
    {% export featured_post = post %}
  {% end %}
{% end %}

{# featured_post available here #}
{{ featured_post.title }}
```

## Template Structure

### Extends

```kida
{% extends "baseof.html" %}
```

### Blocks

```kida
{% block content %}
  <article>
    {{ page.content | safe }}
  </article>
{% endblock %}
```

**Note**: KIDA uses `{% endblock %}` for blocks (Jinja2 compatibility), but `{% end %}` works too.

### Includes

```kida
{% include "partials/header.html" %}
{% include "partials/footer.html" with context %}
```

### Imports

```kida
{% import "macros.html" as macros %}
{{ macros.card(page) }}

{% from "macros.html" import card %}
{{ card(page) }}
```

## Functions

### Defining Functions (`{% def %}`)

KIDA functions have true lexical scoping (unlike Jinja2 macros):

```kida
{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <span>From: {{ site.title }}</span>  {# Access outer scope #}
  </div>
{% end %}

{# Usage #}
{{ card(page) }}
```

**With parameters**:

```kida
{% def button(text, href, class="btn") %}
  <a href="{{ href }}" class="{{ class }}">{{ text }}</a>
{% end %}

{{ button("Click me", "/page", "btn-primary") }}
{{ button("Default", "/page") }}
```

### Calling Functions with Blocks

```kida
{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    {% slot %}
      {# Content passed via call block #}
    {% endslot %}
  </div>
{% end %}

{% call card(page) %}
  <p>Custom content here</p>
{% endcall %}
```

## Filters and Pipeline

### Filter Syntax

```kida
{{ text | upper }}
{{ text | truncate(100) }}
{{ text | default("N/A") }}
```

### Pipeline Operator (`|>`)

KIDA's pipeline operator provides left-to-right readability:

```kida
{# KIDA: Read left-to-right #}
{{ items |> where('published', true) |> sort_by('date') |> take(5) }}

{# Jinja2: Read inside-out #}
{{ items | selectattr('published') | sort(attribute='date') | first(5) }}
```

**Chaining filters**:

```kida
{{ page.content
   |> markdownify
   |> truncate(200)
   |> strip_tags }}
```

## Built-in Filters

### String Filters

```kida
{{ text | upper }}
{{ text | lower }}
{{ text | capitalize }}
{{ text | title }}
{{ text | trim }}
{{ text | truncate(100) }}
{{ text | truncatewords(20) }}
{{ text | replace('old', 'new') }}
{{ text | slugify }}
```

### Collection Filters

```kida
{{ items | first }}
{{ items | last }}
{{ items | length }}
{{ items | sort }}
{{ items | reverse }}
{{ items | unique }}
{{ items | join(', ') }}
{{ items | group_by('category') }}
```

### Type Conversion

```kida
{{ value | string }}
{{ value | int }}
{{ value | float }}
{{ value | bool }}
{{ value | list }}
{{ value | dict }}
{{ value | tojson }}
```

### HTML/Security

```kida
{{ html | safe }}      {# Render raw HTML #}
{{ html | escape }}    {# Escape HTML #}
{{ html | e }}         {# Short form #}
{{ html | striptags }} {# Remove HTML tags #}
```

### Validation

```kida
{{ value | default('fallback') }}
{{ value | d('fallback') }}      {# Short form #}
{{ value | require }}            {# Raise if None #}
```

## Fragment Caching

KIDA provides built-in fragment caching:

```kida
{% cache "sidebar-nav" %}
  {{ build_nav_tree(site.pages) }}
{% end %}

{% cache "weather", ttl="5m" %}
  {{ fetch_weather() }}
{% end %}

{% cache "posts-" ~ site.nav_version %}
  {% for post in recent_posts %}
    {{ post.title }}
  {% end %}
{% end %}
```

**Cache keys** can be:
- Static strings: `"sidebar"`
- Expressions: `"posts-" ~ page.id`
- Variables: `cache_key`

**TTL (Time To Live)**:
- `ttl="5m"` - 5 minutes
- `ttl="1h"` - 1 hour
- `ttl="30s"` - 30 seconds

## Automatic Block Caching

KIDA automatically caches site-scoped template blocks for optimal build performance. This happens automatically—no template syntax changes required.

**How it works**:

1. **Analysis**: KIDA analyzes your templates to identify blocks that only depend on site-wide context (not page-specific data)
2. **Pre-rendering**: These blocks are rendered once at build start
3. **Automatic reuse**: During page rendering, cached blocks are used automatically instead of re-rendering

**Example**:

```kida
{# base.html #}
{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% end %}

{% block content %}
  {{ page.content | safe }}
{% end %}
```

The `nav` block depends only on `site.pages` (site-wide), so it's automatically cached and reused for all pages. The `content` block depends on `page.content` (page-specific), so it renders per page.

**Benefits**:
- **10-100x faster builds** for navigation-heavy sites
- **Zero template changes** — works automatically
- **Transparent** — templates render normally, caching is invisible

**Cache scope detection**:
- **Site-scoped**: Blocks that only access `site.*`, `config.*`, or no page-specific variables
- **Page-scoped**: Blocks that access `page.*` or other page-specific data
- **Not cacheable**: Blocks with non-deterministic behavior (random, shuffle, etc.)

:::{tip}
**Performance tip**: Structure your templates so site-wide blocks (nav, footer, sidebar) are separate from page-specific blocks (content). KIDA will automatically optimize them.
:::

## Modern Syntax Features

### Optional Chaining (`?.`)

Safe attribute access:

```kida
{{ user?.profile?.name | default('Anonymous') }}
{{ page?.metadata?.author | default('Unknown') }}
```

### Null Coalescing (`??`)

Fallback for None values:

```kida
{{ page.subtitle ?? page.title }}
{{ user.name ?? 'Guest' }}
```

:::{warning}
**Precedence gotcha**: The `??` operator has lower precedence than `|` (pipe). This means filters bind to the fallback value, not the result:

```kida
{# ❌ Wrong: parses as items ?? ([] | length) #}
{{ items ?? [] | length }}

{# ✅ Correct: use default filter for filter chains #}
{{ items | default([]) | length }}

{# ✅ Also works: explicit parentheses #}
{{ (items ?? []) | length }}
```
:::

#### When to Use Each Pattern

| Pattern | Use When | Example |
|---------|----------|---------|
| `??` | Simple fallback, no further filtering | `{{ user.name ?? 'Anonymous' }}` |
| `\| default()` | Fallback followed by filters | `{{ items \| default([]) \| length }}` |

**Rule of thumb**: If you need to apply filters after the fallback, use `| default()`. Otherwise, `??` is fine.

### Range Literals

```kida
{% for i in 1..10 %}
  {{ i }}  {# 1, 2, 3, ..., 10 #}
{% end %}

{% for i in 1...11 %}
  {{ i }}  {# 1, 2, 3, ..., 10 (exclusive end) #}
{% end %}

{% for i in 1..10 by 2 %}
  {{ i }}  {# 1, 3, 5, 7, 9 #}
{% end %}
```

### Break and Continue

```kida
{% for item in items %}
  {% if item.hidden %}
    {% continue %}
  {% end %}
  {% if item.stop %}
    {% break %}
  {% end %}
  {{ item.title }}
{% end %}
```

### Spaceless

Remove whitespace between HTML tags:

```kida
{% spaceless %}
  <div>
    <span>Hello</span>
    <span>World</span>
  </div>
{% endspaceless %}
{# Output: <div><span>Hello</span><span>World</span></div> #}
```

## Operators

### Arithmetic

```kida
{{ 10 + 5 }}    {# 15 #}
{{ 10 - 5 }}    {# 5 #}
{{ 10 * 5 }}    {# 50 #}
{{ 10 / 5 }}    {# 2.0 #}
{{ 10 // 5 }}   {# 2 #}
{{ 10 % 3 }}    {# 1 #}
{{ 2 ** 3 }}    {# 8 #}
```

### Comparison

```kida
{{ a == b }}     {# Equal #}
{{ a != b }}     {# Not equal #}
{{ a < b }}      {# Less than #}
{{ a > b }}      {# Greater than #}
{{ a <= b }}     {# Less than or equal #}
{{ a >= b }}     {# Greater than or equal #}
{{ a in b }}     {# Membership #}
{{ a not in b }} {# Not in #}
```

### Logical

```kida
{{ a and b }}
{{ a or b }}
{{ not a }}
```

### String Concatenation

```kida
{{ "Hello" ~ " " ~ "World" }}  {# "Hello World" #}
{{ name ~ "-" ~ id }}           {# "john-123" #}
```

## Tests

```kida
{% if value is defined %}
  {{ value }}
{% end %}

{% if value is none %}
  Default value
{% end %}

{% if value is even %}
  Even number
{% end %}

{% if value is odd %}
  Odd number
{% end %}

{% if value is divisibleby(3) %}
  Divisible by 3
{% end %}
```

## Error Handling

### Strict Mode (Default)

KIDA raises `UndefinedError` for undefined variables:

```kida
{{ missing_var }}  {# Raises UndefinedError #}
{{ missing_var | default('N/A') }}  {# Safe: 'N/A' #}
```

### Disabling Strict Mode

Configure in `bengal.yaml`:

```yaml
kida:
  strict: false  # Return None for undefined variables
```

## Configuration

KIDA is the default template engine. Configure KIDA options in `bengal.yaml`:

```yaml
kida:
  strict: true              # Raise on undefined (default)
  bytecode_cache: true      # Cache compiled templates (default)
  autoescape: true          # HTML escape by default (default)
```

To use a different engine instead:

```yaml
site:
  template_engine: jinja2   # or mako, patitas, or custom
```

## Migration from Jinja2

KIDA can parse Jinja2 syntax via compatibility mode. Most Jinja2 templates work without changes, but consider migrating to KIDA syntax for better performance:

:::{seealso}
[How to Migrate from Jinja2 to KIDA](/docs/theming/templating/kida/migrate-jinja-to-kida/) — Step-by-step migration guide
:::

**Key differences**:

1. **Block endings**: Replace `{% endif %}`, `{% endfor %}` with `{% end %}`
2. **Template variables**: Use `{% let %}` instead of `{% set %}` for template-wide scope
3. **Pattern matching**: Replace long `if/elif` chains with `{% match %}...{% case %}`
4. **Pipeline**: Use `|>` for better readability

## Complete Example

```kida
{% extends "baseof.html" %}

{% let site_title = site.config.title %}
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{% block content %}
  <h1>{{ site_title }}</h1>

  {% match page.type %}
    {% case "blog" %}
      <article class="blog-post">
        <h2>{{ page.title }}</h2>
        <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
        {{ page.content | safe }}
      </article>
    {% case "list" %}
      <ul>
        {% for post in recent_posts %}
          <li>
            <a href="{{ post.url }}">{{ post.title }}</a>
            <span>{{ post.date | days_ago }} days ago</span>
          </li>
        {% end %}
      </ul>
    {% case _ %}
      <div>{{ page.content | safe }}</div>
  {% end %}

  {% cache "sidebar-" ~ site.nav_version %}
    <aside>
      {{ build_sidebar(site.pages) }}
    </aside>
  {% end %}
{% endblock %}
```

## See Also

- [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn KIDA step-by-step
- [Template Functions Reference](/docs/reference/template-functions/) — Available filters and functions
- [Theming Guide](/docs/theming/templating/) — Template organization and inheritance
- [KIDA How-Tos](/docs/theming/templating/kida/) — Common tasks and patterns
