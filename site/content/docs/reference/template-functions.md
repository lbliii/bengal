---
title: Template Functions Reference
nav_title: Functions
description: Complete reference for Bengal's template filters and functions
weight: 50
type: doc
draft: false
lang: en
tags:
- reference
- templates
- filters
- jinja2
- hugo
keywords:
- template functions
- filters
- where
- sort
- collections
- hugo migration
category: reference
---

Bengal provides powerful template filters for querying, filtering, and transforming content collections. Many filters are inspired by Hugo for easy migration.

## Collection Filters

These filters work with lists of pages, dictionaries, or any iterable.

### where

Filter items where a key matches a value. Supports Hugo-like comparison operators.

**Basic Usage:**

```jinja2
{# Filter by exact value (default) #}
{% set tutorials = site.pages | where('category', 'tutorial') %}

{# Filter by nested attribute #}
{% set track_pages = site.pages | where('metadata.track_id', 'getting-started') %}
```

**With Comparison Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal (default) | `where('status', 'published', 'eq')` |
| `ne` | Not equal | `where('status', 'draft', 'ne')` |
| `gt` | Greater than | `where('date', one_year_ago, 'gt')` |
| `gte` | Greater than or equal | `where('priority', 5, 'gte')` |
| `lt` | Less than | `where('weight', 100, 'lt')` |
| `lte` | Less than or equal | `where('order', 10, 'lte')` |
| `in` | Value in list | `where('tags', 'python', 'in')` |
| `not_in` | Value not in list | `where('status', ['archived'], 'not_in')` |

**Operator Examples:**

```jinja2
{# Pages newer than a year ago #}
{% set recent = site.pages | where('date', one_year_ago, 'gt') %}

{# Pages with priority 5 or higher #}
{% set important = site.pages | where('metadata.priority', 5, 'gte') %}

{# Pages tagged with 'python' #}
{% set python_posts = site.pages | where('tags', 'python', 'in') %}

{# Pages with specific statuses #}
{% set active = site.pages | where('status', ['active', 'featured'], 'in') %}

{# Exclude archived pages #}
{% set live = site.pages | where('status', ['archived', 'draft'], 'not_in') %}
```

### where_not

Filter items where a key does NOT equal a value. Shorthand for `where(key, value, 'ne')`.

```jinja2
{# Exclude drafts #}
{% set published = site.pages | where_not('draft', true) %}

{# Exclude archived items #}
{% set active = users | where_not('status', 'archived') %}
```

### sort_by

Sort items by a key, with optional reverse order.

```jinja2
{# Sort by date, newest first #}
{% set recent = site.pages | sort_by('date', reverse=true) %}

{# Sort alphabetically by title #}
{% set alphabetical = site.pages | sort_by('title') %}

{# Sort by weight (ascending) #}
{% set ordered = sections | sort_by('weight') %}
```

### group_by

Group items by a key value, returning a dictionary.

```jinja2
{% set by_category = site.pages | group_by('category') %}

{% for category, pages in by_category.items() %}
<h2>{{ category }}</h2>
<ul>
  {% for page in pages %}
  <li><a href="{{ page.url }}">{{ page.title }}</a></li>
  {% endfor %}
</ul>
{% endfor %}
```

### limit

Take the first N items from a list.

```jinja2
{# Latest 5 posts #}
{% set latest = site.pages | sort_by('date', reverse=true) | limit(5) %}

{# Top 3 featured items #}
{% set featured = items | where('featured', true) | limit(3) %}
```

### offset

Skip the first N items from a list.

```jinja2
{# Skip first 10 items (pagination page 2) #}
{% set page_2 = items | offset(10) | limit(10) %}

{# Skip the featured post #}
{% set rest = posts | offset(1) %}
```

### first

Get the first item from a list, or `None` if empty.

```jinja2
{# Get the featured post #}
{% set featured = site.pages | where('metadata.featured', true) | first %}

{% if featured %}
<div class="hero">
  <h1>{{ featured.title }}</h1>
</div>
{% endif %}
```

### last

Get the last item from a list, or `None` if empty.

```jinja2
{# Get the oldest post #}
{% set oldest = site.pages | sort_by('date') | last %}

{# Get the final step #}
{% set final_step = steps | last %}
```

### reverse

Reverse a list (returns a new list, original unchanged).

```jinja2
{# Oldest first #}
{% set chronological = site.pages | sort_by('date') %}

{# Newest first (reversed) #}
{% set newest_first = chronological | reverse %}
```

### uniq

Remove duplicate items while preserving order.

```jinja2
{# Get unique tags from all posts #}
{% set all_tags = [] %}
{% for page in site.pages %}
  {% set all_tags = all_tags + page.tags %}
{% endfor %}
{% set unique_tags = all_tags | uniq %}
```

### flatten

Flatten nested lists into a single list.

```jinja2
{# Combine all tags from all pages #}
{% set nested_tags = site.pages | map(attribute='tags') | list %}
{% set all_tags = nested_tags | flatten | uniq %}
```

## Set Operations

Perform set operations on lists of pages or items.

### union

Combine two lists, removing duplicates.

```jinja2
{# Combine featured and recent posts #}
{% set featured = site.pages | where('metadata.featured', true) %}
{% set recent = site.pages | sort_by('date', reverse=true) | limit(5) %}
{% set combined = featured | union(recent) %}
```

### intersect

Get items that appear in both lists.

```jinja2
{# Posts that are both featured AND tagged 'python' #}
{% set featured = site.pages | where('metadata.featured', true) %}
{% set python = site.pages | where('tags', 'python', 'in') %}
{% set featured_python = featured | intersect(python) %}
```

### complement

Get items in the first list that are NOT in the second list.

```jinja2
{# All posts except featured ones #}
{% set all_posts = site.pages | where('type', 'post') %}
{% set featured = site.pages | where('metadata.featured', true) %}
{% set regular = all_posts | complement(featured) %}
```

## Chaining Filters

Filters can be chained for powerful queries:

```jinja2
{# Recent Python tutorials, sorted by date #}
{% set result = site.pages
  | where('category', 'tutorial')
  | where('tags', 'python', 'in')
  | where('draft', false)
  | sort_by('date', reverse=true)
  | limit(10) %}
```

## Hugo Migration Guide

Bengal's template functions are designed for easy migration from Hugo. Here's how common Hugo patterns translate:

### Filtering Pages

**Hugo:**
```go-html-template
{{ $posts := where .Site.RegularPages "Section" "blog" }}
{{ $recent := where .Site.RegularPages ".Date" ">" (now.AddDate -1 0 0) }}
```

**Bengal:**
```jinja2
{% set posts = site.pages | where('section', 'blog') %}
{% set recent = site.pages | where('date', one_year_ago, 'gt') %}
```

### Sorting

**Hugo:**
```go-html-template
{{ range .Site.RegularPages.ByDate.Reverse }}
{{ range sort .Site.RegularPages "Title" }}
```

**Bengal:**
```jinja2
{% for page in site.pages | sort_by('date', reverse=true) %}
{% for page in site.pages | sort_by('title') %}
```

### First/Last

**Hugo:**
```go-html-template
{{ $featured := (where .Site.RegularPages "Params.featured" true).First }}
{{ $oldest := .Site.RegularPages.ByDate.Last }}
```

**Bengal:**
```jinja2
{% set featured = site.pages | where('metadata.featured', true) | first %}
{% set oldest = site.pages | sort_by('date') | last %}
```

### Limiting

**Hugo:**
```go-html-template
{{ range first 5 .Site.RegularPages }}
```

**Bengal:**
```jinja2
{% for page in site.pages | limit(5) %}
```

### Set Operations

**Hugo:**
```go-html-template
{{ $both := intersect $list1 $list2 }}
{{ $combined := union $list1 $list2 }}
{{ $diff := complement $list1 $list2 }}
```

**Bengal:**
```jinja2
{% set both = list1 | intersect(list2) %}
{% set combined = list1 | union(list2) %}
{% set diff = list1 | complement(list2) %}
```

### Tag Filtering

**Hugo:**
```go-html-template
{{ $tagged := where .Site.RegularPages "Params.tags" "intersect" (slice "python" "web") }}
```

**Bengal:**
```jinja2
{# Check if page has 'python' tag #}
{% set tagged = site.pages | where('tags', 'python', 'in') %}

{# Check if page has any of these tags #}
{% set tagged = site.pages | where('tags', ['python', 'web'], 'in') %}
```

### Complex Queries

**Hugo:**
```go-html-template
{{ $result := where (where .Site.RegularPages "Section" "blog") ".Params.featured" true }}
```

**Bengal:**
```jinja2
{% set result = site.pages | where('section', 'blog') | where('metadata.featured', true) %}
```

## Quick Reference

| Filter | Purpose | Example |
|--------|---------|---------|
| `where(key, val)` | Filter by value | `pages \| where('type', 'post')` |
| `where(key, val, 'gt')` | Greater than | `pages \| where('date', cutoff, 'gt')` |
| `where(key, val, 'in')` | Value in list | `pages \| where('tags', 'python', 'in')` |
| `where_not(key, val)` | Exclude value | `pages \| where_not('draft', true)` |
| `sort_by(key)` | Sort ascending | `pages \| sort_by('title')` |
| `sort_by(key, reverse=true)` | Sort descending | `pages \| sort_by('date', reverse=true)` |
| `group_by(key)` | Group by value | `pages \| group_by('category')` |
| `limit(n)` | Take first N | `pages \| limit(5)` |
| `offset(n)` | Skip first N | `pages \| offset(10)` |
| `first` | First item | `pages \| first` |
| `last` | Last item | `pages \| last` |
| `reverse` | Reverse order | `pages \| reverse` |
| `uniq` | Remove duplicates | `tags \| uniq` |
| `flatten` | Flatten nested lists | `nested \| flatten` |
| `union(list2)` | Combine lists | `list1 \| union(list2)` |
| `intersect(list2)` | Common items | `list1 \| intersect(list2)` |
| `complement(list2)` | Difference | `list1 \| complement(list2)` |

## Navigation Functions

These global functions simplify common navigation patterns.

### get_section

Get a section by its path. Cleaner alternative to `site.get_section_by_path()`.

```jinja2
{% set docs = get_section('docs') %}
{% if docs %}
  <h2>{{ docs.title }}</h2>
  {% for page in docs.pages | sort_by('weight') %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% endfor %}
{% endif %}
```

### section_pages

Get pages from a section directly. Combines `get_section()` with `.pages` access.

```jinja2
{# Non-recursive (direct children only) #}
{% for page in section_pages('docs') | sort_by('weight') %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% endfor %}

{# Recursive (include all nested pages) #}
{% for page in section_pages('docs', recursive=true) %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% endfor %}
```

### page_exists

Check if a page exists without loading it. More efficient than `get_page()` for conditional rendering.

```jinja2
{% if page_exists('guides/advanced') %}
  <a href="/guides/advanced/">Advanced Guide Available</a>
{% endif %}

{# Works with or without .md extension #}
{% if page_exists('docs/getting-started.md') %}...{% endif %}
{% if page_exists('docs/getting-started') %}...{% endif %}
```

## Linking Functions

These functions generate links to pages and headings. All use O(1) lookups from pre-built indexes.

### ref

Generate a cross-reference link to a page.

```jinja2
{{ ref('docs/getting-started') }}
{{ ref('docs/getting-started', 'Get Started') }}
{{ ref('id:install-guide') }}
{{ ref('id:install-guide', 'Installation') }}
```

**Parameters**:
- `path`: Page path (`docs/page`), slug (`page-name`), or custom ID (`id:xxx`)
- `text`: Optional custom link text (defaults to page title)

**Returns**: Safe HTML link (`<a href="...">...</a>`) or broken reference indicator

**Use cases**:
- Dynamic navigation menus
- Related pages sections
- Breadcrumbs
- Conditional links

**Examples**:

```jinja2
{# Link with auto-title #}
{{ ref('docs/api') }}

{# Link with custom text #}
{{ ref('docs/api', 'API Reference') }}

{# Link by custom ID #}
{{ ref('id:install-guide') }}

{# In loops #}
{% for page in related_pages %}
  <li>{{ ref(page.path) }}</li>
{% endfor %}
```

### doc

Get a page object for custom link generation or metadata access.

```jinja2
{% set page = doc('docs/getting-started') %}
{% if page %}
  <a href="{{ page.url }}">{{ page.title }}</a>
  <p>{{ page.description }}</p>
{% endif %}
```

**Parameters**:
- `path`: Page path, slug, or custom ID

**Returns**: `Page` object or `None`

**Use cases**:
- Custom link formatting
- Accessing page metadata
- Conditional rendering based on page properties
- Building custom navigation structures

**Examples**:

```jinja2
{# Custom link with metadata #}
{% set api_page = doc('docs/api') %}
{% if api_page %}
  <div class="card">
    <a href="{{ api_page.url }}">
      <h3>{{ api_page.title }}</h3>
    </a>
    <p>{{ api_page.description }}</p>
    <span class="date">{{ api_page.date | date('%Y-%m-%d') }}</span>
  </div>
{% endif %}

{# Check if page exists before linking #}
{% set guide = doc('docs/advanced-guide') %}
{% if guide and not guide.draft %}
  <a href="{{ guide.url }}">Advanced Guide</a>
{% endif %}
```

### anchor

Link to a heading (anchor) in a page.

```jinja2
{{ anchor('Installation') }}
{{ anchor('Configuration', 'docs/getting-started') }}
```

**Parameters**:
- `heading`: Heading text to find (case-insensitive)
- `page_path`: Optional page path to restrict search (default: search all pages)

**Returns**: Safe HTML link with anchor fragment (`<a href="page#anchor">...</a>`)

**Use cases**:
- Table of contents
- "Jump to" links
- Cross-page heading references
- Section navigation

**Examples**:

```jinja2
{# Link to any heading with this text #}
{{ anchor('Installation') }}

{# Link to heading in specific page #}
{{ anchor('Configuration', 'docs/getting-started') }}

{# Build table of contents #}
<ul>
  <li>{{ anchor('Introduction') }}</li>
  <li>{{ anchor('Installation') }}</li>
  <li>{{ anchor('Configuration') }}</li>
</ul>
```

### relref

Get relative URL for a page without generating a full link.

```jinja2
<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>

{% set api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% endif %}
```

**Parameters**:
- `path`: Page path, slug, or custom ID

**Returns**: URL string or empty string if not found

**Use cases**:
- Custom link HTML
- Meta tags (`<link rel="preload">`)
- Prefetch links
- OpenGraph URLs
- Custom button styling

**Examples**:

```jinja2
{# Custom styled link #}
<a href="{{ relref('docs/api') }}" class="btn btn-primary">
  View API Documentation
</a>

{# Preload for performance #}
{% set api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% endif %}

{# OpenGraph meta tag #}
<meta property="og:url" content="{{ site.baseurl }}{{ relref('docs/getting-started') }}">
```

### xref

Alias for `ref()` for compatibility with other systems.

```jinja2
{{ xref('docs/api') }}
{{ xref('docs/api', 'API Reference') }}
```

**Note**: `xref()` and `ref()` are identical — use whichever you prefer.

## Internationalization (i18n)

These functions support multilingual sites with translations, language detection, and localized formatting.

### t

Translate UI strings using translation files.

```jinja2
{# Basic translation #}
{{ t('nav.home') }}

{# With interpolation parameters #}
{{ t('content.minutes_read', {'minutes': page.reading_time}) }}

{# Force specific language #}
{{ t('nav.home', lang='fr') }}
```

**Parameters:**
- `key`: Dot-notation path to translation (e.g., `'nav.home'`, `'errors.404.title'`)
- `params`: Optional dictionary for string interpolation
- `lang`: Optional language code override

**Translation Files:**

Place translation files in `i18n/` directory:

```yaml
# i18n/en.yaml
nav:
  home: "Home"
  docs: "Documentation"

content:
  minutes_read: "{minutes} min read"
```

```yaml
# i18n/fr.yaml
nav:
  home: "Accueil"
  docs: "Documentation"

content:
  minutes_read: "{minutes} min de lecture"
```

### current_lang

Get the current page's language code.

```jinja2
<html lang="{{ current_lang() }}">

{% if current_lang() == 'fr' %}
  {# French-specific content #}
{% endif %}

{# Use in conditional logic #}
{% set is_english = current_lang() == 'en' %}
```

**Returns:** Language code string (e.g., `"en"`, `"fr"`) or `None`

### languages

Get list of all configured languages.

```jinja2
{# Language switcher #}
<nav class="language-switcher">
  {% for lang in languages() %}
    <a href="/{{ lang.code }}/"
       {% if lang.code == current_lang() %}class="active"{% endif %}>
      {{ lang.name }}
    </a>
  {% endfor %}
</nav>
```

**Returns:** List of language objects with:
- `code` — Language code (e.g., `"en"`)
- `name` — Display name (e.g., `"English"`)
- `hreflang` — SEO attribute value
- `weight` — Sort order

### alternate_links

Generate hreflang links for SEO.

```jinja2
{# In <head> #}
{% for alt in alternate_links(page) %}
  <link rel="alternate" hreflang="{{ alt.hreflang }}" href="{{ alt.href }}">
{% endfor %}
```

**Output:**
```html
<link rel="alternate" hreflang="en" href="/docs/getting-started/">
<link rel="alternate" hreflang="fr" href="/fr/docs/getting-started/">
<link rel="alternate" hreflang="x-default" href="/docs/getting-started/">
```

**Returns:** List of dictionaries with:
- `hreflang` — Language code for SEO
- `href` — Full URL to alternate version

### locale_date

Format dates according to locale.

```jinja2
{# Format with current locale #}
{{ locale_date(page.date, 'medium') }}
{# → "Dec 19, 2025" (English) or "19 déc. 2025" (French) #}

{{ locale_date(page.date, 'long') }}
{# → "December 19, 2025" or "19 décembre 2025" #}

{# Force specific locale #}
{{ locale_date(page.date, 'medium', lang='fr') }}
```

**Parameters:**
- `date`: Date object or string
- `format`: Format style (`'short'`, `'medium'`, `'long'`)
- `lang`: Optional language code override

:::{tip}
For full locale date formatting, install Babel: `pip install babel`
:::

### i18n Configuration

Configure languages in your site config:

```yaml
# config/_default/i18n.yaml
i18n:
  strategy: "prefix"           # URL prefix strategy (/en/, /fr/)
  default_language: "en"
  default_in_subdir: false     # Default lang at root
  languages:
    - code: "en"
      name: "English"
      weight: 1
    - code: "fr"
      name: "Français"
      weight: 2
```

:::{seealso}
See [[docs/content/i18n|Multilingual Sites Guide]] for complete i18n setup.
:::

---

## String Filters

### word_count

Count words in text, stripping HTML first. Uses same logic as `reading_time`.

```jinja2
{{ page.content | word_count }} words

{# Combined with reading time #}
<span>{{ page.content | word_count }} words · {{ page.content | reading_time }} min read</span>
```

Also available as `wordcount` (Jinja naming convention).
