---
title: Navigation Functions
description: Functions for navigating sections and checking page existence
weight: 20
tags:
- reference
- functions
- navigation
- sections
category: reference
---

# Navigation Functions

These global functions simplify common navigation patterns.

## get_section

Get a section by its path. Cleaner alternative to `site.get_section_by_path()`.

```kida
{% let docs = get_section('docs') %}
{% if docs %}
  <h2>{{ docs.title }}</h2>
  {% for page in docs.pages |> sort_by('weight') %}
    <a href="{{ page.href }}">{{ page.title }}</a>
  {% end %}
{% end %}
```

## section_pages

Get pages from a section directly. Combines `get_section()` with `.pages` access.

```kida
{# Non-recursive (direct children only) #}
{% for page in section_pages('docs') |> sort_by('weight') %}
  <a href="{{ page.href }}">{{ page.title }}</a>
{% end %}

{# Recursive (include all nested pages) #}
{% for page in section_pages('docs', recursive=true) %}
  <a href="{{ page.href }}">{{ page.title }}</a>
{% end %}
```

## page_exists

Check if a page exists without loading it. More efficient than `get_page()` for conditional rendering.

```kida
{% if page_exists('guides/advanced') %}
  <a href="/guides/advanced/">Advanced Guide Available</a>
{% end %}

{# Works with or without .md extension #}
{% if page_exists('docs/getting-started.md') %}...{% end %}
{% if page_exists('docs/getting-started') %}...{% end %}
```

## get_page

Retrieve a page object by path. Similar to `doc()` but intended for programmatic page access.

```kida
{% let page = get_page('docs/getting-started') %}
{% if page %}
  <a href="{{ page.href }}">{{ page.title }}</a>
{% end %}

{# Works with various path formats #}
{% let p1 = get_page('docs/api.md') %}       {# With extension #}
{% let p2 = get_page('docs/api') %}          {# Without extension #}
{% let p3 = get_page('/docs/api/') %}        {# Absolute path #}
```

**Parameters**:
- `path`: Page path (with or without `.md` extension)

**Returns**: `Page` object or `None`

**Use cases**:
- Track/series navigation
- Related pages lookup
- Dynamic content inclusion

Results are cached per-render for performance.
