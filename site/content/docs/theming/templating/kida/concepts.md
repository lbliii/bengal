---
title: Template Engine Concepts
nav_title: Concepts
description: Foundational concepts for understanding Kida and template engines
weight: 3
type: doc
draft: false
lang: en
tags:
- explanation
- kida
- templates
- concepts
keywords:
- template engine
- filters
- tags
- expressions
- scope
- template inheritance
category: explanation
---

# Template Engine Concepts

A crash course in template engine terminology and mental models. Whether you're coming from Hugo, Django, PHP, or have never used a template engine—this page gives you the foundation to understand Kida.

## What is a Template Engine?

A template engine combines **static markup** (HTML) with **dynamic data** (your content). Instead of writing HTML files by hand for every page, you write a template once and the engine fills in the data.

```
Template + Data = Output HTML
```

**Example**:

```kida
{# Template #}
<h1>{{ page.title }}</h1>
<p>Published: {{ page.date | dateformat('%B %d, %Y') }}</p>

{# Data: { page: { title: "My Post", date: 2024-01-15 } } #}

{# Output #}
<h1>My Post</h1>
<p>Published: January 15, 2024</p>
```

The template engine (Kida) takes your template, injects the data, and produces HTML.

---

## The Three Delimiters

Kida uses three types of delimiters. Understanding these is fundamental:

### 1. Expressions: `{{ }}`

**Purpose**: Output a value.

```kida
{{ page.title }}
{{ site.config.title }}
{{ 1 + 1 }}
```

Think of `{{ }}` as "print this value here."

### 2. Statements: `{% %}`

**Purpose**: Control flow, logic, and structure. Does not output anything directly.

```kida
{% if page.draft %}
  <span>Draft</span>
{% end %}

{% for post in site.pages %}
  <li>{{ post.title }}</li>
{% end %}
```

Statements control *what* gets rendered and *how*, but don't output text themselves.

### 3. Comments: `{# #}`

**Purpose**: Notes for developers. Completely ignored in output.

```kida
{# TODO: Add featured image support #}
{# This comment won't appear in HTML #}
```

### Quick Reference

| Delimiter | Name | Purpose | Output? |
|-----------|------|---------|---------|
| `{{ }}` | Expression | Print a value | Yes |
| `{% %}` | Statement | Logic and control | No |
| `{# #}` | Comment | Developer notes | No |

---

## Filters: Transforming Data

A **filter** transforms a value. Think of it like a Unix pipe—data flows through, gets modified, comes out the other side.

```kida
{{ "hello world" | upper }}
{# Output: HELLO WORLD #}

{{ page.title | slugify }}
{# "My Great Post" → "my-great-post" #}

{{ page.content | truncate(100) }}
{# Cuts text to 100 characters #}
```

### Syntax

```kida
{{ value | filter_name }}
{{ value | filter_name(argument) }}
{{ value | filter_name(arg1, arg2) }}
```

### Chaining Filters

Filters can be chained. Data flows left-to-right:

```kida
{{ page.title | lower | slugify }}
{# "My Post" → "my post" → "my-post" #}
```

**Kida's Pipeline Operator** (`|>`) makes chains more readable:

```kida
{# Traditional: inner-to-outer reading #}
{{ site.pages | where('type', 'blog') | sort_by('date') | take(5) }}

{# Pipeline: left-to-right reading #}
{{ site.pages |> where('type', 'blog') |> sort_by('date') |> take(5) }}
```

Both produce the same result. Pipeline is just easier to read.

### Common Filters

| Filter | Purpose | Example |
|--------|---------|---------|
| `upper` | Uppercase | `{{ "hello" \| upper }}` → `HELLO` |
| `lower` | Lowercase | `{{ "HELLO" \| lower }}` → `hello` |
| `truncate(n)` | Limit characters | `{{ text \| truncate(100) }}` |
| `default(val)` | Fallback if empty | `{{ x \| default("N/A") }}` |
| `safe` | Don't escape HTML | `{{ page.content \| safe }}` |
| `slugify` | URL-safe string | `{{ title \| slugify }}` |
| `length` | Count items | `{{ items \| length }}` |
| `first` | First item | `{{ items \| first }}` |
| `join(sep)` | Combine list | `{{ tags \| join(", ") }}` |

See [Template Functions Reference](/docs/reference/template-functions/) for all 80+ filters.

---

## Tests: Checking Conditions

A **test** is a boolean check used in conditionals. Tests use the `is` keyword:

```kida
{% if page.draft is defined %}
  {# page.draft exists #}
{% end %}

{% if count is even %}
  {# count is an even number #}
{% end %}

{% if value is none %}
  {# value is None/null #}
{% end %}
```

### Common Tests

| Test | Purpose | Example |
|------|---------|---------|
| `defined` | Variable exists | `{% if x is defined %}` |
| `none` | Value is None | `{% if x is none %}` |
| `even` | Even number | `{% if n is even %}` |
| `odd` | Odd number | `{% if n is odd %}` |
| `divisibleby(n)` | Divisible by n | `{% if x is divisibleby(3) %}` |

### Filters vs Tests

| Concept | Syntax | Purpose | Example |
|---------|--------|---------|---------|
| **Filter** | `value \| filter` | Transform data | `{{ text \| upper }}` |
| **Test** | `value is test` | Check condition | `{% if x is defined %}` |

---

## Functions (Global and Local)

### Global Functions

Functions provided by Bengal that you call directly:

```kida
{{ url_for(page) }}
{{ asset_url('css/style.css') }}
{% set p = get_page('/docs/intro/') %}
```

### Template Functions (`{% def %}`)

Functions you define in your template:

```kida
{% def card(item) %}
  <div class="card">
    <h3>{{ item.title }}</h3>
    <p>{{ item.description }}</p>
  </div>
{% end %}

{# Usage #}
{{ card(page) }}
{{ card(another_page) }}
```

Functions are reusable blocks of template code. Kida's `{% def %}` has **lexical scoping**, meaning it can access variables from where it was defined (unlike Jinja2's `{% macro %}`).

---

## Scope: Where Variables Live

**Scope** determines where a variable is accessible.

### Template Scope (`{% let %}`)

Variables available throughout the entire template:

```kida
{% let site_title = site.config.title %}

{# Available everywhere below #}
<h1>{{ site_title }}</h1>

{% if page.draft %}
  <span>{{ site_title }} - Draft</span>  {# Still accessible #}
{% end %}
```

### Block Scope (`{% set %}`)

Variables available only within the current block:

```kida
{% if page.published %}
  {% set status = "Published" %}
  <span>{{ status }}</span>  {# Works #}
{% end %}

{{ status }}  {# ERROR: status is not defined here #}
```

### Quick Reference

| Keyword | Scope | Use When |
|---------|-------|----------|
| `{% let %}` | Entire template | Shared values, computed once |
| `{% set %}` | Current block only | Temporary values in loops/conditionals |

### Exporting from Inner Scope (`{% export %}`)

Sometimes you need to pull a value *out* of a block:

```kida
{% for post in posts %}
  {% if post.featured %}
    {% export featured = post %}
  {% end %}
{% end %}

{# featured is now available here #}
<h2>Featured: {{ featured.title }}</h2>
```

---

## Template Inheritance: extends and blocks

Template inheritance lets you define a base layout and override parts of it.

### Base Template (`base.html`)

```kida
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}{{ site.config.title }}{% endblock %}</title>
</head>
<body>
  <header>{% include "partials/nav.html" %}</header>

  <main>
    {% block content %}{% endblock %}
  </main>

  <footer>{% include "partials/footer.html" %}</footer>
</body>
</html>
```

### Child Template (`page.html`)

```kida
{% extends "base.html" %}

{% block title %}{{ page.title }} - {{ site.config.title }}{% endblock %}

{% block content %}
  <article>
    <h1>{{ page.title }}</h1>
    {{ page.content | safe }}
  </article>
{% endblock %}
```

**Result**: The child template "fills in" the blocks defined by the parent. Everything else comes from the base.

### Vocabulary

| Term | Meaning |
|------|---------|
| `{% extends %}` | This template inherits from another |
| `{% block %}` | Defines a replaceable section |
| `{% include %}` | Insert another template inline |

---

## Context: What Data is Available

When a template renders, it receives a **context**—a dictionary of available data.

Bengal provides:

| Variable | Contains |
|----------|----------|
| `page` | Current page being rendered |
| `site` | Global site data (all pages, config, menus) |
| `config` | Site configuration |
| `content` | Pre-rendered HTML (marked safe) |
| `toc` | Table of contents HTML |

**Example**:

```kida
{# Page data #}
{{ page.title }}
{{ page.date }}
{{ page.metadata.author }}

{# Site data #}
{{ site.config.title }}
{% for p in site.pages %}
  {{ p.title }}
{% end %}
```

See [Template Context](/docs/about/concepts/templating/#the-template-context) for the complete list.

---

## Coming from Hugo?

If you're familiar with Hugo's Go templates, here's a mental model translation:

| Hugo | Kida | Notes |
|------|------|-------|
| `{{ .Title }}` | `{{ page.title }}` | Dot notation → named object |
| `{{ .Date \| dateFormat "Jan 2006" }}` | `{{ page.date \| dateformat('%b %Y') }}` | Python strftime format |
| `{{ range .Pages }}` | `{% for p in site.pages %}` | Range → for loop |
| `{{ if .Draft }}` | `{% if page.draft %}` | Same concept |
| `{{ with .Params.author }}` | `{% if page.metadata.author %}` | With → if + variable access |
| `{{ partial "header.html" . }}` | `{% include "partials/header.html" %}` | Partials → includes |
| `{{ .Permalink }}` | `{{ page.href }}` | URL access |
| `{{ .Site.Title }}` | `{{ site.config.title }}` | Site config access |
| `{{ urlize .Title }}` | `{{ page.title \| slugify }}` | Similar filter concept |

**Key differences**:

1. **No dot context**: Hugo's `.` changes meaning in different scopes. Kida uses explicit names (`page`, `site`).
2. **Python syntax**: Filters use Python conventions (e.g., strftime for dates).
3. **Explicit delimiters**: Hugo uses `{{ }}` for everything. Kida separates `{{ }}` (output) from `{% %}` (logic).

---

## Coming from Jinja2?

Kida is Jinja2-compatible. Your templates work without changes. Key improvements:

| Jinja2 | Kida | Benefit |
|--------|------|---------|
| `{% endif %}`, `{% endfor %}`, etc. | `{% end %}` | Unified endings |
| `{% set %}` (block-scoped) | `{% let %}` (template-scoped) | Clear scope distinction |
| `{% macro %}` (no closure) | `{% def %}` (lexical scope) | Access outer variables |
| `{% if %}...{% elif %}...{% endif %}` | `{% match %}...{% case %}` | Cleaner pattern matching |
| `\| filter(arg)` | `\|> filter(arg)` | Left-to-right pipelines |
| `x \| default(y)` | `x ?? y` | Null coalescing shorthand |
| N/A | `x?.y?.z` | Optional chaining |

See [Migrate from Jinja2](/docs/theming/templating/kida/migrate-jinja-to-kida/) for a step-by-step guide.

---

## Putting It Together

Here's a complete example using multiple concepts:

```kida
{# 1. Template-scoped variables #}
{% let recent_posts = site.pages
  |> where('type', 'blog')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> take(5) %}

{# 2. Define a reusable function #}
{% def post_card(post) %}
  <article class="card">
    <h3>{{ post.title }}</h3>
    <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    <p>{{ post.content | truncate(100) | striptags }}</p>
  </article>
{% end %}

{# 3. Conditional rendering with pattern matching #}
{% match page.type %}
  {% case "home" %}
    <h1>Welcome to {{ site.config.title }}</h1>

    {# 4. Loop with the function #}
    {% for post in recent_posts %}
      {{ post_card(post) }}
    {% end %}

  {% case "blog" %}
    <h1>{{ page.title }}</h1>
    <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
    {{ page.content | safe }}

  {% case _ %}
    <h1>{{ page.title }}</h1>
    {{ page.content | safe }}
{% end %}
```

**Concepts used**:
1. `{% let %}` for template-scoped variables
2. `|>` pipeline for readable filter chains  
3. `{% def %}` for reusable template functions
4. `{% match %}` for clean conditional branching
5. `{{ }}` for outputting values
6. Filters for transforming data (`dateformat`, `truncate`, `striptags`, `safe`)
7. `{% for %}` for iteration

---

## Next Steps

Now that you understand the fundamentals:

- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [Template Functions Reference](/docs/reference/template-functions/) — All 80+ filters and functions
- [Getting Started with Kida](/docs/tutorials/getting-started-with-kida/) — Hands-on tutorial
- [Kida vs Jinja2](/docs/theming/templating/kida/comparison/) — Feature comparison
