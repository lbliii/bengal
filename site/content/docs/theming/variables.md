---
title: Theme Variables Reference
nav_title: Variables
description: Complete reference of all variables available in Jinja2 templates
weight: 40
draft: false
lang: en
tags:
- reference
- templates
- variables
- jinja2
keywords:
- theme variables
- templates
- jinja2
- site
- page
- context
category: reference
---

# Theme Variables Reference

Complete reference for all variables, objects, and context available in Bengal templates.

## Quick Reference

```jinja2
{# Core objects - always available #}
{{ page }}          {# Current page #}
{{ site }}          {# Site object #}
{{ config }}        {# Site config (alias for site.config) #}
{{ params }}        {# Page metadata (alias for page.metadata) #}
{{ section }}       {# Current section #}

{# Pre-computed values - cached for performance #}
{{ content }}       {# Rendered page content (safe HTML) #}
{{ title }}         {# Page title #}
{{ toc }}           {# Table of contents HTML #}
{{ toc_items }}     {# Structured TOC data #}
{{ meta_desc }}     {# Pre-computed meta description #}
{{ reading_time }}  {# Pre-computed reading time #}
{{ excerpt }}       {# Pre-computed excerpt #}
```

---

## Template Tests

Clean conditional checks using `is` operator:

```jinja2
{% if page is draft %}
  <span class="badge badge-draft">Draft</span>
{% endif %}

{% if page is featured %}
  <article class="featured">...</article>
{% endif %}

{% if page is outdated(180) %}
  <div class="warning">This page may be outdated.</div>
{% endif %}
```

| Test | Usage | Description |
|------|-------|-------------|
| `is draft` | `{% if page is draft %}` | Check if page is a draft |
| `is featured` | `{% if page is featured %}` | Check if page has 'featured' tag |
| `is outdated` | `{% if page is outdated %}` | Check if page is older than 90 days |
| `is outdated(N)` | `{% if page is outdated(30) %}` | Check if page is older than N days |
| `is match` | `{% if value is match('pattern') %}` | Regex pattern matching |
| `is section` | `{% if obj is section %}` | Check if object is a Section |
| `is translated` | `{% if page is translated %}` | Check if page has translations |

---

## Global Objects

### `page`

The current page being rendered.

#### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `page.title` | `str` | Page title |
| `page.content` | `str` | Raw markdown content |
| `page.date` | `datetime` | Publication date |
| `page.metadata` | `dict` | All frontmatter keys |
| `page.kind` | `str` | Page kind (page, section, etc.) |
| `page.type` | `str` | Content type |
| `page.draft` | `bool` | Is draft? |
| `page.hidden` | `bool` | Is hidden? |
| `page.tags` | `list` | List of tags |

#### URL Properties

| Property | Description |
|----------|-------------|
| `page.href` | Full URL with baseurl (use in `<a href>`) |
| `page._path` | Site-relative URL without baseurl (use for comparisons) |
| `page.source_path` | Source file path |

```jinja2
{# Display URL (includes baseurl) #}
<a href="{{ page.href }}">{{ page.title }}</a>

{# Comparison (without baseurl) #}
{% if page._path == '/docs/' %}
  <span class="active">Current Section</span>
{% endif %}
```

#### Relationships

| Property | Type | Description |
|----------|------|-------------|
| `page.section` | `Section` | Parent section |
| `page.translations` | `list` | Available translations |
| `page.prev_in_series` | `Page` | Previous page in series |
| `page.next_in_series` | `Page` | Next page in series |

#### Computed Properties

| Property | Type | Description |
|----------|------|-------------|
| `page.reading_time` | `int` | Estimated reading time in minutes |
| `page.age_days` | `int` | Days since publication |
| `page.age_months` | `int` | Months since publication |
| `page.author` | `Author` | Structured author info |
| `page.authors` | `list` | Multiple authors |
| `page.series` | `dict` | Series metadata |

---

### `site`

The global site object.

| Property | Type | Description |
|----------|------|-------------|
| `site.title` | `str` | Site title from config |
| `site.baseurl` | `str` | Base URL |
| `site.author` | `str` | Site author name |
| `site.language` | `str` | Language code |
| `site.pages` | `list[Page]` | All pages |
| `site.regular_pages` | `list[Page]` | Content pages only |
| `site.sections` | `list[Section]` | Top-level sections |
| `site.taxonomies` | `dict` | Tags, categories |
| `site.data` | `dict` | Data from `data/` directory |
| `site.config` | `dict` | Full configuration |
| `site.params` | `dict` | Site-level custom parameters |
| `site.logo` | `str` | Logo URL from config |
| `site.versioning_enabled` | `bool` | Is versioning on? |
| `site.versions` | `list` | Available versions |
| `site.theme_config` | `dict` | Theme configuration |

---

### `section`

The current section (parent of the page).

| Property | Type | Description |
|----------|------|-------------|
| `section.title` | `str` | Section title |
| `section.href` | `str` | Section URL |
| `section.pages` | `list[Page]` | Pages in section |
| `section.subsections` | `list[Section]` | Child sections |
| `section.metadata` | `dict` | Section frontmatter |
| `section.post_count` | `int` | Number of pages |
| `section.post_count_recursive` | `int` | Including subsections |
| `section.word_count` | `int` | Total words |
| `section.total_reading_time` | `int` | Total reading time |

---

## Context Shortcuts

Bengal provides shortcuts for common patterns:

| Shortcut | Equivalent To | Description |
|----------|---------------|-------------|
| `params` | `page.metadata` | Page frontmatter |
| `meta` | `page.metadata` | Alias for params |
| `config` | `site.config` | Site configuration |
| `theme` | `site.theme_config` | Theme configuration |

```jinja2
{# Instead of #}
{{ page.metadata.get('author') }}
{{ site.config.get('baseurl') }}

{# Use #}
{{ params.author }}
{{ config.baseurl }}
```

---

## Pre-computed Context

These values are computed once and cached in the template context:

| Variable | Description |
|----------|-------------|
| `content` | Rendered page content (safe HTML) |
| `title` | Page title |
| `toc` | Table of contents HTML |
| `toc_items` | Structured TOC data (for custom rendering) |
| `meta_desc` | Meta description for SEO |
| `reading_time` | Reading time in minutes |
| `excerpt` | Page excerpt/summary |

```jinja2
{# Use pre-computed values #}
<h1>{{ title }}</h1>
<p class="meta">{{ reading_time }} min read</p>
<article>{{ content }}</article>

{# TOC in sidebar #}
<nav class="toc">{{ toc | safe }}</nav>
```

---

## Theme Configuration Access

Access theme features and settings:

```jinja2
{# Check if feature is enabled #}
{% if 'navigation.back_to_top' in theme.features %}
  <button class="back-to-top">↑</button>
{% endif %}

{# Get theme defaults #}
{{ theme.default_appearance }}  {# light, dark, system #}
{{ theme.default_palette }}     {# color palette name #}
```

---

## Best Practices

### 1. Use Template Tests

```jinja2
{# ✅ Preferred #}
{% if page is draft %}
{% if page is featured %}
{% if page is outdated(90) %}

{# ❌ Verbose #}
{% if page.draft is defined and page.draft %}
{% if page.tags is defined and (page | has_tag('featured')) %}
```

### 2. Use Shortcuts

```jinja2
{# ✅ Preferred #}
{{ params.author }}
{{ config.baseurl }}

{# ❌ Verbose #}
{{ page.metadata.get('author') }}
{{ site.config.get('baseurl') }}
```

### 3. Cache Function Calls

```jinja2
{# ✅ Cache at top of template #}
{% set _breadcrumbs = breadcrumbs(page) %}
{% set _menu = get_menu_lang('main', current_lang()) %}

{# Then use cached values #}
{% for item in _breadcrumbs %}...{% endfor %}
{% for item in _menu %}...{% endfor %}
```

### 4. Use Pre-computed Values

```jinja2
{# ✅ Use pre-computed #}
{{ content }}
{{ meta_desc }}
{{ reading_time }}

{# ❌ Recompute each time #}
{{ page.content | markdownify | safe }}
{{ page.content | truncate(160) }}
{{ page.content | reading_time }}
```

---

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Complete function and filter documentation
- [Template Functions Overview](/docs/theming/templating/functions/) — Quick function reference
- [Templating Basics](/docs/theming/templating/) — Template inheritance and syntax
:::
