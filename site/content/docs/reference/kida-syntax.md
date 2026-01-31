---
title: Kida Syntax Reference
nav_title: Kida Syntax
description: Complete reference for Kida template syntax, operators, and features
weight: 60
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

# Kida Syntax Reference

Complete reference for Kida template syntax, operators, and features. Kida is Bengal's **default template engine**, optimized for performance and free-threaded Python.

:::{tip}
**New to Kida?** Start with the [Kida Tutorial](/docs/tutorials/theming/getting-started-with-kida/) for a guided introduction. Most Jinja2 templates work without changes, but Kida does not support all Jinja2 features (notably `{% macro %}`—use `{% def %}` instead). If you need full Jinja2 compatibility, use the Jinja2 engine by setting `template_engine: jinja2` in your config.
:::

## Quick Comparison: Kida vs Jinja2

| Feature            | Kida                           | Jinja2                              |
|--------------------|--------------------------------|-------------------------------------|
| Block endings      | `{% end %}` (unified)          | `{% endif %}`, `{% endfor %}`, etc. |
| Template variables | `{% let %}` (template-scoped)  | `{% set %}` (block-scoped only)     |
| Block variables    | `{% set %}` (block-scoped)     | `{% set %}` (block-scoped)          |
| Pattern matching   | `{% match %}...{% case %}`     | `{% if %}...{% elif %}` chains      |
| While loops        | `{% while cond %}...{% end %}` | ❌ Not available                    |
| Pipeline operator  | `\|>` (left-to-right)          | `\|` (right-to-left)                |
| Optional chaining  | `obj?.attr`, `obj?['key']`     | ❌ Not available                    |
| Null coalescing    | `value ?? default`             | `value \| default(...)`             |
| Fragment caching   | `{% cache key %}...{% end %}`  | Requires extension                  |
| Functions          | `{% def %}` (lexical scope)    | `{% macro %}` (isolated scope)      |

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
{% for post in site.pages |> where('type', 'blog') %}
  <article>
    <h2>{{ post.title }}</h2>
    {{ post.content | safe }}
  </article>
{% end %}
```

**Loop variables**:

| Variable          | Description                     |
|-------------------|---------------------------------|
| `loop.index`      | Current iteration (1-indexed)   |
| `loop.index0`     | Current iteration (0-indexed)   |
| `loop.length`     | Total number of items           |
| `loop.first`      | True on first iteration         |
| `loop.last`       | True on last iteration          |
| `loop.revindex`   | Iterations remaining (1-indexed)|
| `loop.cycle(...)` | Cycle through values            |

```kida
{% for item in items %}
  {% if loop.first %}First item{% end %}
  {% if loop.last %}Last item{% end %}
  Item {{ loop.index }} of {{ loop.length }}
  <tr class="{{ loop.cycle('odd', 'even') }}">
{% end %}
```

### Pattern Matching

Kida's native pattern matching replaces long `if/elif` chains:

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

**Scoping**: `{% let %}` is template-scoped, `{% set %}` is block-scoped, and `{% export %}` promotes variables to template scope. See the [Variables documentation](../theming/templating/kida/syntax/variables.md) for details.

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

### Multi-let (Comma-Separated)

Assign multiple variables in a single `{% let %}` block:

```kida
{# Single-line multi-let #}
{% let a = 1, b = 2, c = 3 %}

{# Multi-line multi-let (recommended for readability) #}
{% let
    _site_title = config?.title ?? 'Untitled Site',
    _page_title = page?.title ?? config?.title ?? 'Page',
    _description = page?.description ?? '' %}
```

**Recommended pattern** for template setup:

```kida
{% extends "base.html" %}

{# Group related configuration at template start #}
{% let
    _show_sidebar = page?.sidebar ?? true,
    _show_toc = page?.toc ?? true,
    _prev = get_prev_page(page),
    _next = get_next_page(page) %}

{% block content %}
  {# Variables available throughout #}
  {% if _show_sidebar %}...{% end %}
{% end %}
```

### Tuple Unpacking

Destructure tuples into separate variables:

```kida
{% let (title, subtitle) = (page.title, page.subtitle) %}
{% let (first, second) = get_pair() %}
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

**Note**: Kida uses `{% endblock %}` for blocks (Jinja2 compatibility), but `{% end %}` works too.

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

Kida functions can access variables from their surrounding context automatically—no need to pass site config, theme settings, or other shared values as parameters:

```kida
{% let site_name = site.config.title %}

{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
    <span>From: {{ site_name }}</span>  {# ✅ Accesses outer variable #}
  </div>
{% end %}

{# Just pass the item—site_name is available automatically #}
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

### Functions vs Filters

Kida templates support both **filters** (transform values) and **functions** (standalone operations).

**Filters** transform a value using `|` or `|>`:
```kida
{{ page.title | upper }}                    {# Transform text #}
{{ site.pages |> where('draft', false) }}  {# Transform collection #}
```

**Functions** are called directly without a value:
```kida
{{ get_page('docs/about') }}               {# Retrieve page #}
{{ get_data('data/authors.json') }}        {# Load data #}
{{ ref('docs/getting-started') }}          {# Generate link #}
```

**When to use which:**
- **Filter**: You have a value to transform (`{{ value | filter }}`)
- **Function**: You're performing an operation (`{{ function() }}`)

See [Template Functions Reference](/docs/reference/template-functions/#functions-vs-filters-understanding-the-difference) for details.

### Filter Syntax

```kida
{{ text | upper }}
{{ text | truncate(100) }}
{{ text | default("N/A") }}
```

### Pipeline Operator (`|>`)

Kida's pipeline operator provides left-to-right readability for complex filter chains:

```kida
{# Kida: Read left-to-right #}
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

:::{tip}
Use `|>` for chains of 3+ filters. For simple single-filter cases, `|` is fine:

```kida
{{ text | upper }}           {# Simple: use | #}
{{ data |> filter |> sort |> take(5) }}  {# Complex: use |> #}
```

:::

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

{# Prefix/Suffix Operations #}
{{ url | trim_prefix("https://") }}    {# Remove prefix #}
{{ file | trim_suffix(".txt") }}       {# Remove suffix #}
{{ url | has_prefix("https://") }}     {# Check prefix (bool) #}
{{ file | has_suffix(".md") }}         {# Check suffix (bool) #}
{{ text | contains("error") }}         {# Check substring (bool) #}

{# Regex Extraction #}
{{ "Price: $99.99" | regex_search(r'\$[\d.]+') }}  {# "$99.99" #}
{{ "v2.3.1" | regex_search(r'v(\d+)', group=1) }} {# "2" #}
{{ "a1 b2 c3" | regex_findall(r'\d+') }}           {# ["1", "2", "3"] #}

{# Natural Language #}
{{ ["Alice", "Bob", "Charlie"] | to_sentence }}    {# "Alice, Bob, and Charlie" #}
{{ items | to_sentence(connector='or') }}          {# "A, B, or C" #}

{# Base64 Encoding #}
{{ "hello" | base64_encode }}     {# "aGVsbG8=" #}
{{ encoded | base64_decode }}     {# Decode Base64 #}
```

### Collection Filters

```kida
{{ items |> first }}
{{ items |> last }}
{{ items | length }}
{{ items |> sort }}
{{ items |> reverse }}
{{ items |> unique }}
{{ items | join(', ') }}
{{ items |> group_by('category') }}
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
{{ html | plainify }}  {# Alias for striptags (Hugo compat) #}

{# Auto-link URLs #}
{{ "Visit https://example.com" | urlize }}
{# Output: Visit <a href="https://example.com">https://example.com</a> #}

{{ text | urlize(target='_blank', rel='noopener') }}  {# Open in new tab #}
```

### Validation

```kida
{{ value | default('fallback') }}
{{ value | d('fallback') }}      {# Short form #}
{{ value | require }}            {# Raise if None #}
```

### URL Manipulation

```kida
{# Parse URL into components #}
{% let parts = url | url_parse %}
{{ parts.scheme }}     {# "https" #}
{{ parts.host }}       {# "example.com" #}
{{ parts.path }}       {# "/docs/api" #}
{{ parts.query }}      {# "version=2" #}
{{ parts.fragment }}   {# "section" #}
{{ parts.params.q }}   {# ["search term"] #}

{# Extract query parameter #}
{{ "https://x.com?page=2" | url_param('page') }}        {# "2" #}
{{ url | url_param('missing', 'default') }}             {# "default" #}

{# Build query string from dict #}
{{ {'q': 'test', 'page': 1} | url_query }}              {# "q=test&page=1" #}
```

### Date Filters

```kida
{# Format dates #}
{{ page.date | dateformat('%B %d, %Y') }}  {# "January 15, 2026" #}
{{ page.date | dateformat('%Y-%m-%d') }}   {# "2026-01-15" (default) #}
{{ page.date | date_iso }}                 {# ISO 8601 format #}
{{ page.date | date_rfc822 }}              {# RFC 822 for RSS feeds #}

{# Relative time #}
{{ post.date | time_ago }}    {# "2 days ago", "5 hours ago" #}
{{ post.date | days_ago }}    {# 14 (integer) #}
{{ post.date | months_ago }}  {# 3 (integer) #}
{% if post.date | days_ago < 7 %}NEW{% end %}

{# Add/subtract time #}
{{ page.date | date_add(days=7) }}               {# One week later #}
{{ now | date_add(days=-30) }}                   {# 30 days ago #}
{{ event.start | date_add(hours=2, minutes=30) }} {# 2.5 hours later #}
{{ page.date | date_add(weeks=2) }}              {# Two weeks later #}

{# Calculate difference #}
{{ end_date | date_diff(start_date) }}               {# Days between #}
{{ end_date | date_diff(start_date, unit='hours') }} {# Hours between #}
{{ end_date | date_diff(start_date, unit='all') }}   {# Dict with all units #}
```

## Fragment Caching

Kida provides built-in fragment caching:

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

Kida automatically caches site-scoped template blocks for optimal build performance. This happens automatically—no template syntax changes required.

**How it works**:

1. **Analysis**: Kida analyzes your templates to identify blocks that only depend on site-wide context (not page-specific data)
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

- **Significantly faster builds** for navigation-heavy sites (benchmarks show 10x+ improvement for large sites)
- **Zero template changes** — works automatically
- **Transparent** — templates render normally, caching is invisible

**Cache scope detection**:

- **Site-scoped**: Blocks that only access `site.*`, `config.*`, or no page-specific variables
- **Page-scoped**: Blocks that access `page.*` or other page-specific data
- **Not cacheable**: Blocks with non-deterministic behavior (random, shuffle, etc.)

:::{tip}
**Performance tip**: Structure your templates so site-wide blocks (nav, footer, sidebar) are separate from page-specific blocks (content). Kida will automatically optimize them.
:::

## Kida-Only Features

These features are unique to Kida and not available in Jinja2:

| Feature           | Syntax                          | Purpose                     |
|-------------------|---------------------------------|-----------------------------|
| Optional chaining | `?.`, `?[`                      | Safe access without errors  |
| Null coalescing   | `??`                            | Fallback for None values    |
| Range literals    | `1..10`, `1...11`               | Concise iteration ranges    |
| While loops       | `{% while %}`                   | Condition-based iteration   |
| Break/Continue    | `{% break %}`, `{% continue %}` | Loop control                |

### Optional Chaining

Safe navigation operators return `None` instead of raising errors when accessing missing attributes or keys.

#### Optional Attribute Access (`?.`)

Safe attribute access—returns `None` if the object is `None`:

```kida
{{ user?.profile?.name }}           {# None if user or profile is None #}
{{ page?.metadata?.author }}        {# None if page or metadata is None #}
{{ config?.theme?.colors?.primary }} {# Deep safe access #}
```

#### Optional Subscript Access (`?[`)

Safe key/index access—returns `None` if the object is `None`:

```kida
{{ data?['key'] }}                  {# None if data is None #}
{{ schema?['in'] }}                 {# Access reserved word keys safely #}
{{ items?[0] }}                     {# Safe index access #}
{{ config?['settings']?['theme'] }} {# Chained safe subscript #}
```

**Combining with attribute access**:

```kida
{{ api?.response?['data']?['items'] }}  {# Mix both operators #}
{{ user?.preferences?['theme'] ?? 'light' }}
```

:::{tip}
**Kida uses `?[` not `?.[]`**: Unlike JavaScript which uses `?.['key']`, Kida uses the more concise `?['key']`. The pattern is simple: prefix `?` makes any accessor optional.

| Accessor  | Regular   | Optional   |
|-----------|-----------|------------|
| Attribute | `.attr`   | `?.attr`   |
| Subscript | `['key']` | `?['key']` |

:::

#### Common Use Cases

**Accessing reserved word keys** (common in OpenAPI, JSON Schema):

```kida
{# OpenAPI security schemes use 'in' as a field name #}
{% let location = scheme?['in'] ?? 'header' %}
{% let api_type = spec?['type'] ?? 'apiKey' %}
```

**Safe array access**:

```kida
{% let first = items?[0] %}
{% let last = items?[-1] %}
{{ results?[0]?.name ?? 'No results' }}
```

**Nested data structures**:

```kida
{% let value = response?['data']?['users']?[0]?['email'] %}
{{ value ?? 'Not found' }}
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

| Pattern        | Use When                         | Example                                 |
|----------------|----------------------------------|-----------------------------------------|
| `??`           | Simple fallback, no filtering    | `{{ user.name ?? 'Anonymous' }}`        |
| `\| default()` | Fallback followed by filters     | `{{ items \| default([]) \| length }}`  |

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

### While Loops

Condition-based loops for scenarios where the iteration count isn't known upfront:

```kida
{% let counter = 0 %}
{% while counter < 5 %}
  {{ counter }}
  {% set counter = counter + 1 %}
{% end %}
```

**With break and continue**:

```kida
{% let i = 0 %}
{% while true %}
  {% if i >= 10 %}{% break %}{% end %}
  {% set i = i + 1 %}
  {% if i % 2 == 0 %}{% continue %}{% end %}
  {{ i }}  {# Prints odd numbers: 1, 3, 5, 7, 9 #}
{% end %}
```

:::{tip}
While loops are useful for:

- Processing data until a condition is met
- Implementing search algorithms in templates
- Building countdown/countup displays
:::

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

Kida raises `UndefinedError` for undefined variables:

```kida
{{ missing_var }}  {# Raises UndefinedError #}
{{ missing_var | default('N/A') }}  {# Safe: 'N/A' #}
```

### Disabling Strict Mode

Configure in `bengal.yaml`:

## Configuration

Kida is Bengal's default template engine. Configure in `bengal.yaml`:

```yaml
kida:
  bytecode_cache: true      # Persistent compiled template cache (default)
```

**Note**: Strict mode (raising `UndefinedError` for undefined variables) is always enabled in Kida and cannot be disabled. This helps catch typos and missing context variables at render time.

| Option            | Default | Description                         |
|-------------------|---------|-------------------------------------|
| `bytecode_cache`  | `true`  | Cache compiled templates to disk    |

**Switching template engines**:

```yaml
site:
  template_engine: jinja2   # Options: kida (default), jinja2, mako
```

## Migration from Jinja2

Kida can parse Jinja2 syntax via compatibility mode. Most Jinja2 templates work without changes, but consider migrating to Kida syntax for pattern matching, pipeline operators, and unified block endings:

:::{seealso}
[How to Migrate from Jinja2 to Kida](/docs/theming/templating/kida/migration/from-jinja/) — Step-by-step migration guide
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

- [Kida Tutorial](/docs/tutorials/theming/getting-started-with-kida/) — Learn Kida step-by-step
- [Template Functions Reference](/docs/reference/template-functions/) — Available filters and functions
- [Theming Guide](/docs/theming/templating/) — Template organization and inheritance
- [Kida How-Tos](/docs/theming/templating/kida/) — Common tasks and patterns
