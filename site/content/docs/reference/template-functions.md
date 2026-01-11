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
- kida
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

## Functions vs Filters: Understanding the Difference

Bengal provides two types of template capabilities: **functions** and **filters**. Understanding when to use each helps you write clearer, more efficient templates.

### Filters: Transform Values

**Filters** transform a value using the pipe operator (`|` or `|>`). The value on the left becomes the first argument to the filter.

**Syntax:**
```kida
{{ value | filter }}
{{ value | filter(arg1, arg2) }}
{{ value |> filter1 |> filter2 }}
```

**When to use:** When you have a value to transform.

**Examples:**
```kida
{# Transform text #}
{{ page.title | upper }}
{{ page.content | markdown | safe }}

{# Transform collections #}
{{ site.pages | where('draft', false) | sort_by('date') }}

{# Chain transformations #}
{{ text |> slugify |> truncate(50) }}
```

**Registered in:** `env.filters` (available via pipe operator)

### Functions: Standalone Operations

**Functions** are called directly without a value to transform. They perform operations or retrieve data.

**Syntax:**
```kida
{{ function() }}
{{ function(arg1, arg2) }}
```

**When to use:** When performing an operation that doesn't transform an existing value.

**Examples:**
```kida
{# Retrieve data #}
{{ get_page('docs/about') }}
{{ get_data('data/authors.json') }}

{# Generate references #}
{{ ref('docs/getting-started') }}
{{ get_section('blog') }}

{# Check conditions #}
{{ page_exists('path/to/page') }}
```

**Registered in:** `env.globals` (available as direct function calls)

### Quick Decision Guide

| Use Case | Type | Example |
|----------|------|---------|
| Transform text | Filter | `{{ text \| upper }}` |
| Transform a collection | Filter | `{{ pages \| where('draft', false) }}` |
| Chain transformations | Filter | `{{ data \|> filter1 \|> filter2 }}` |
| Retrieve a page | Function | `{{ get_page('path') }}` |
| Load data file | Function | `{{ get_data('file.json') }}` |
| Generate cross-reference | Function | `{{ ref('docs/page') }}` |
| Check if page exists | Function | `{{ page_exists('path') }}` |

### Why This Matters

**Filters** are designed for **data transformation pipelines**:
- Read left-to-right: `data |> transform |> format |> output`
- Chain multiple operations: `pages |> filter |> sort |> limit`
- Functional programming style

**Functions** are designed for **operations and lookups**:
- No implicit left operand
- Direct calls: `get_page('path')` not `| get_page('path')`
- Procedural style

### Common Patterns

**Pattern 1: Filter a collection, then use a function**
```kida
{% let blog_posts = site.pages |> where('type', 'blog') |> sort_by('date', reverse=true) %}
{% for post in blog_posts %}
  {# Use function to get related page #}
  {% let related = get_page(post.metadata.related) %}
  {% if related %}
    <a href="{{ related.url }}">Related: {{ related.title }}</a>
  {% end %}
{% end %}
```

**Pattern 2: Function to get data, filter to transform**
```kida
{% let authors = get_data('data/authors.json') %}
{% let active_authors = authors |> where('active', true) |> sort_by('name') %}
```

**Pattern 3: Function result used in filter chain**
```kida
{% let section = get_section('blog') %}
{% let recent = section.pages |> sort_by('date', reverse=true) |> limit(5) %}
```

:::{note}
**Can't remember which is which?** Ask: "Do I have a value to transform?"
- **Yes** → Use a filter (`|` or `|>`)
- **No** → Use a function (direct call)
:::

---

## Collection Filters

These filters work with lists of pages, dictionaries, or any iterable.

### where

Filter items where a key matches a value. Supports Hugo-like comparison operators.

:::{example-label} Basic Usage
:::

```kida
{# Filter by exact value (default) #}
{% let tutorials = site.pages |> where('category', 'tutorial') %}

{# Filter by nested attribute #}
{% let track_pages = site.pages |> where('metadata.track_id', 'getting-started') %}
```

:::{example-label} With Comparison Operators
:::

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

:::{example-label} Operator Examples
:::

```kida
{# Pages newer than a year ago #}
{% let recent = site.pages |> where('date', one_year_ago, 'gt') %}

{# Pages with priority 5 or higher #}
{% let important = site.pages |> where('metadata.priority', 5, 'gte') %}

{# Pages tagged with 'python' #}
{% let python_posts = site.pages |> where('tags', 'python', 'in') %}

{# Pages with specific statuses #}
{% let active = site.pages |> where('status', ['active', 'featured'], 'in') %}

{# Exclude archived pages #}
{% let live = site.pages |> where('status', ['archived', 'draft'], 'not_in') %}
```

### where_not

Filter items where a key does NOT equal a value. Shorthand for `where(key, value, 'ne')`.

```kida
{# Exclude drafts #}
{% let published = site.pages |> where_not('draft', true) %}

{# Exclude archived items #}
{% let active = users |> where_not('status', 'archived') %}
```

### sort_by

Sort items by a key, with optional reverse order.

```kida
{# Sort by date, newest first #}
{% let recent = site.pages |> sort_by('date', reverse=true) %}

{# Sort alphabetically by title #}
{% let alphabetical = site.pages |> sort_by('title') %}

{# Sort by weight (ascending) #}
{% let ordered = sections |> sort_by('weight') %}
```

### group_by

Group items by a key value, returning a dictionary.

```kida
{% let by_category = site.pages |> group_by('category') %}

{% for category, pages in by_category.items() %}
<h2>{{ category }}</h2>
<ul>
  {% for page in pages %}
  <li><a href="{{ page.url }}">{{ page.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

### group_by_year

Group pages by publication year. Returns dictionary sorted by year (newest first).

```kida
{% let by_year = site.pages |> group_by_year %}

{% for year, posts in by_year.items() %}
<h2>{{ year }}</h2>
<ul>
  {% for post in posts %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

**Parameters:**
- `date_attr`: Attribute containing the date (default: `'date'`)

### group_by_month

Group pages by year-month. Returns dictionary keyed by `(year, month)` tuples.

```kida
{% let by_month = site.pages |> group_by_month %}

{% for (year, month), posts in by_month.items() %}
<h2>{{ month | month_name }} {{ year }}</h2>
<ul>
  {% for post in posts %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

### archive_years

Get list of years with post counts for archive navigation.

```kida
{% let years = site.pages |> archive_years %}

<aside class="archive">
  <h3>Archive</h3>
  <ul>
    {% for item in years %}
    <li>
      <a href="/blog/{{ item.year }}/">{{ item.year }}</a>
      <span>({{ item.count }})</span>
    </li>
    {% end %}
  </ul>
</aside>
```

**Returns:** List of dicts with `year` and `count` keys, sorted newest first.

### limit

Take the first N items from a list.

```kida
{# Latest 5 posts #}
{% let latest = site.pages |> sort_by('date', reverse=true) |> limit(5) %}

{# Top 3 featured items #}
{% let featured = items |> where('featured', true) |> limit(3) %}
```

### offset

Skip the first N items from a list.

```kida
{# Skip first 10 items (pagination page 2) #}
{% let page_2 = items |> offset(10) |> limit(10) %}

{# Skip the featured post #}
{% let rest = posts |> offset(1) %}
```

### first

Get the first item from a list, or `None` if empty.

```kida
{# Get the featured post #}
{% let featured = site.pages |> where('metadata.featured', true) |> first %}

{% if featured %}
<div class="hero">
  <h1>{{ featured.title }}</h1>
</div>
{% end %}
```

### last

Get the last item from a list, or `None` if empty.

```kida
{# Get the oldest post #}
{% let oldest = site.pages |> sort_by('date') |> last %}

{# Get the final step #}
{% let final_step = steps |> last %}
```

### reverse

Reverse a list (returns a new list, original unchanged).

```kida
{# Oldest first #}
{% let chronological = site.pages |> sort_by('date') %}

{# Newest first (reversed) #}
{% let newest_first = chronological |> reverse %}
```

### uniq

Remove duplicate items while preserving order.

```kida
{# Get unique tags from all posts #}
{% let all_tags = [] %}
{% for page in site.pages %}
  {% let all_tags = all_tags + page.tags %}
{% end %}
{% let unique_tags = all_tags | uniq %}
```

### flatten

Flatten nested lists into a single list.

```kida
{# Combine all tags from all pages #}
{% let nested_tags = site.pages |> map(attribute='tags') |> list %}
{% let all_tags = nested_tags |> flatten |> uniq %}
```

## Set Operations

Perform set operations on lists of pages or items.

### union

Combine two lists, removing duplicates.

```kida
{# Combine featured and recent posts #}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let recent = site.pages |> sort_by('date', reverse=true) |> limit(5) %}
{% let combined = featured |> union(recent) %}
```

### intersect

Get items that appear in both lists.

```kida
{# Posts that are both featured AND tagged 'python' #}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let python = site.pages |> where('tags', 'python', 'in') %}
{% let featured_python = featured |> intersect(python) %}
```

### complement

Get items in the first list that are NOT in the second list.

```kida
{# All posts except featured ones #}
{% let all_posts = site.pages |> where('type', 'post') %}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let regular = all_posts |> complement(featured) %}
```

## Chaining Filters

Filters can be chained for powerful queries:

```kida
{# Recent Python tutorials, sorted by date #}
{% let result = site.pages
  |> where('category', 'tutorial')
  |> where('tags', 'python', 'in')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> limit(10) %}
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
```kida
{% let posts = site.pages |> where('section', 'blog') %}
{% let recent = site.pages |> where('date', one_year_ago, 'gt') %}
```

### Sorting

**Hugo:**
```go-html-template
{{ range .Site.RegularPages.ByDate.Reverse }}
{{ range sort .Site.RegularPages "Title" }}
```

**Bengal:**
```kida
{% for page in site.pages |> sort_by('date', reverse=true) %}
{% for page in site.pages |> sort_by('title') %}
```

### First/Last

**Hugo:**
```go-html-template
{{ $featured := (where .Site.RegularPages "Params.featured" true).First }}
{{ $oldest := .Site.RegularPages.ByDate.Last }}
```

**Bengal:**
```kida
{% let featured = site.pages |> where('metadata.featured', true) |> first %}
{% let oldest = site.pages |> sort_by('date') |> last %}
```

### Limiting

**Hugo:**
```go-html-template
{{ range first 5 .Site.RegularPages }}
```

**Bengal:**
```kida
{% for page in site.pages |> limit(5) %}
```

### Set Operations

**Hugo:**
```go-html-template
{{ $both := intersect $list1 $list2 }}
{{ $combined := union $list1 $list2 }}
{{ $diff := complement $list1 $list2 }}
```

**Bengal:**
```kida
{% let both = list1 |> intersect(list2) %}
{% let combined = list1 |> union(list2) %}
{% let diff = list1 |> complement(list2) %}
```

### Tag Filtering

**Hugo:**
```go-html-template
{{ $tagged := where .Site.RegularPages "Params.tags" "intersect" (slice "python" "web") }}
```

**Bengal:**
```kida
{# Check if page has 'python' tag #}
{% let tagged = site.pages |> where('tags', 'python', 'in') %}

{# Check if page has any of these tags #}
{% let tagged = site.pages |> where('tags', ['python', 'web'], 'in') %}
```

### Complex Queries

**Hugo:**
```go-html-template
{{ $result := where (where .Site.RegularPages "Section" "blog") ".Params.featured" true }}
```

**Bengal:**
```kida
{% let result = site.pages |> where('section', 'blog') |> where('metadata.featured', true) %}
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

```kida
{% let docs = get_section('docs') %}
{% if docs %}
  <h2>{{ docs.title }}</h2>
  {% for page in docs.pages |> sort_by('weight') %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% end %}
{% end %}
```

### section_pages

Get pages from a section directly. Combines `get_section()` with `.pages` access.

```kida
{# Non-recursive (direct children only) #}
{% for page in section_pages('docs') |> sort_by('weight') %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% end %}

{# Recursive (include all nested pages) #}
{% for page in section_pages('docs', recursive=true) %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% end %}
```

### page_exists

Check if a page exists without loading it. More efficient than `get_page()` for conditional rendering.

```kida
{% if page_exists('guides/advanced') %}
  <a href="/guides/advanced/">Advanced Guide Available</a>
{% end %}

{# Works with or without .md extension #}
{% if page_exists('docs/getting-started.md') %}...{% end %}
{% if page_exists('docs/getting-started') %}...{% end %}
```

## Linking Functions

These functions generate links to pages and headings. All use O(1) lookups from pre-built indexes.

### ref

Generate a cross-reference link to a page.

```kida
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

:::{example-label} Usage
:::

```kida
{# Link with auto-title #}
{{ ref('docs/api') }}

{# Link with custom text #}
{{ ref('docs/api', 'API Reference') }}

{# Link by custom ID #}
{{ ref('id:install-guide') }}

{# In loops #}
{% for page in related_pages %}
  <li>{{ ref(page.path) }}</li>
{% end %}
```

### doc

Get a page object for custom link generation or metadata access.

```kida
{% let page = doc('docs/getting-started') %}
{% if page %}
  <a href="{{ page.url }}">{{ page.title }}</a>
  <p>{{ page.description }}</p>
{% end %}
```

**Parameters**:
- `path`: Page path, slug, or custom ID

**Returns**: `Page` object or `None`

**Use cases**:
- Custom link formatting
- Accessing page metadata
- Conditional rendering based on page properties
- Building custom navigation structures

:::{example-label} Usage
:::

```kida
{# Custom link with metadata #}
{% let api_page = doc('docs/api') %}
{% if api_page %}
  <div class="card">
    <a href="{{ api_page.url }}">
      <h3>{{ api_page.title }}</h3>
    </a>
    <p>{{ api_page.description }}</p>
    <span class="date">{{ api_page.date | date('%Y-%m-%d') }}</span>
  </div>
{% end %}

{# Check if page exists before linking #}
{% let guide = doc('docs/advanced-guide') %}
{% if guide and not guide.draft %}
  <a href="{{ guide.url }}">Advanced Guide</a>
{% end %}
```

### anchor

Link to a heading (anchor) in a page.

```kida
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

:::{example-label} Usage
:::

```kida
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

```kida
<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>

{% let api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% end %}
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

:::{example-label} Usage
:::

```kida
{# Custom styled link #}
<a href="{{ relref('docs/api') }}" class="btn btn-primary">
  View API Documentation
</a>

{# Preload for performance #}
{% let api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% end %}

{# OpenGraph meta tag #}
<meta property="og:url" content="{{ site.baseurl }}{{ relref('docs/getting-started') }}">
```

### xref

Alias for `ref()` for compatibility with other systems.

```kida
{{ xref('docs/api') }}
{{ xref('docs/api', 'API Reference') }}
```

**Note**: `xref()` and `ref()` are identical — use whichever you prefer.

### ext

Generate a link to external documentation (Python stdlib, third-party libraries, other Bengal sites).

```kida
{{ ext('python', 'pathlib.Path') }}
{{ ext('python', 'pathlib.Path', 'Path class') }}
{{ ext('kida', 'Markup') }}
{{ ext('numpy', 'ndarray', 'NumPy Arrays') }}
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | string | Project name (must be configured in `external_refs.yaml`) |
| `target` | string | Target identifier (class, function, module, page path) |
| `text` | string | Optional custom link text |

**Returns**: Safe HTML link (`<a href="...">...</a>`)

**Resolution**: Uses three-tier strategy:
1. URL templates (instant, offline)
2. Bengal indexes (`xref.json`, cached)
3. Graceful fallback (renders as code with warning)

**Examples**:

```kida
{# Link to Python stdlib #}
{{ ext('python', 'pathlib.Path') }}

{# Link with custom text #}
{{ ext('python', 'json.dumps', 'JSON serialization') }}

{# Link to Bengal ecosystem #}
{{ ext('kida', 'Markup') }}
{{ ext('rosettes', 'PythonLexer') }}

{# In a paragraph #}
<p>
  Results are validated using {{ ext('pydantic', 'BaseModel') }}.
</p>
```

**See also**: [[docs/content/authoring/external-references|External References Guide]]

### ext_exists

Check if an external reference is resolvable before rendering.

```kida
{% if ext_exists('kida', 'Markup') %}
  See {{ ext('kida', 'Markup') }} for safe HTML handling.
{% else %}
  See the Kida documentation for Markup.
{% end %}
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | string | Project name |
| `target` | string | Target identifier |

**Returns**: `true` if resolvable via URL template or cached index, `false` otherwise

**Use cases**:

```kida
{# Conditional rendering #}
{% if ext_exists('numpy', 'ndarray') %}
  {{ ext('numpy', 'ndarray') }}
{% else %}
  <code>numpy.ndarray</code>
{% end %}

{# Build a list of available references #}
{% let refs = [('python', 'pathlib.Path'), ('numpy', 'ndarray'), ('pandas', 'DataFrame')] %}
<ul>
{% for project, target in refs %}
  {% if ext_exists(project, target) %}
    <li>{{ ext(project, target) }}</li>
  {% end %}
{% end %}
</ul>
```

**See also**: [[docs/content/authoring/external-references|External References Guide]]

## Internationalization (i18n)

These functions support multilingual sites with translations, language detection, and localized formatting.

### t

Translate UI strings using translation files.

```kida
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

```kida
<html lang="{{ current_lang() }}">

{% if current_lang() == 'fr' %}
  {# French-specific content #}
{% end %}

{# Use in conditional logic #}
{% let is_english = current_lang() == 'en' %}
```

**Returns:** Language code string (e.g., `"en"`, `"fr"`) or `None`

### languages

Get list of all configured languages.

```kida
{# Language switcher #}
<nav class="language-switcher">
  {% for lang in languages() %}
    <a href="/{{ lang.code }}/"
       {% if lang.code == current_lang() %}class="active"{% end %}>
      {{ lang.name }}
    </a>
  {% end %}
</nav>
```

**Returns:** List of language objects with:
- `code` — Language code (e.g., `"en"`)
- `name` — Display name (e.g., `"English"`)
- `hreflang` — SEO attribute value
- `weight` — Sort order

### alternate_links

Generate hreflang links for SEO.

```kida
{# In <head> #}
{% for alt in alternate_links(page) %}
  <link rel="alternate" hreflang="{{ alt.hreflang }}" href="{{ alt.href }}">
{% end %}
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

```kida
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

```kida
{{ page.content | word_count }} words

{# Combined with reading time #}
<span>{{ page.content | word_count }} words · {{ page.content | reading_time }} min read</span>
```

Also available as `wordcount` (Jinja naming convention).

---

## Date Filters

These filters help calculate and display content age and date information.

### days_ago

Calculate days since a date. Useful for freshness indicators.

```kida
{# Days since publication #}
{{ page.date | days_ago }} days old

{# Conditional styling #}
{% if page.date | days_ago < 7 %}
<span class="badge badge-new">New</span>
{% end %}
```

### months_ago

Calculate calendar months since a date.

```kida
{% if page.date | months_ago > 6 %}
<div class="notice">This content may be outdated.</div>
{% end %}
```

### month_name

Get month name from number (1-12).

```kida
{{ 3 | month_name }}         {# → "March" #}
{{ 3 | month_name(true) }}   {# → "Mar" (abbreviated) #}

{# With date #}
{{ page.date.month | month_name }}
```

### humanize_days

Convert day count to human-readable relative time.

```kida
{{ page.date | days_ago | humanize_days }}
{# → "today", "yesterday", "3 days ago", "2 weeks ago", etc. #}
```

---

## Social Sharing

Generate share URLs for social platforms.

### share_url

Generate share URL for any supported platform.

```kida
<a href="{{ share_url('twitter', page) }}">Share on Twitter</a>
<a href="{{ share_url('linkedin', page) }}">Share on LinkedIn</a>
<a href="{{ share_url('facebook', page) }}">Share on Facebook</a>
<a href="{{ share_url('reddit', page) }}">Share on Reddit</a>
<a href="{{ share_url('hackernews', page) }}">Share on HN</a>
```

**Supported Platforms:** `twitter`, `linkedin`, `facebook`, `reddit`, `hackernews` (or `hn`), `email`, `mastodon`

### Individual Share Functions

For more control, use platform-specific functions:

```kida
{# Twitter with via attribution #}
<a href="{{ twitter_share_url(page.absolute_href, page.title, via='myblog') }}">
  Tweet this
</a>

{# Reddit #}
<a href="{{ reddit_share_url(page.absolute_href, page.title) }}">
  Submit to Reddit
</a>

{# Email #}
<a href="{{ email_share_url(page.absolute_href, page.title) }}">
  Share via Email
</a>
```

---

## Page Properties

These properties are available on all page objects.

### Author Properties

Access structured author information from frontmatter.

```kida
{# Single author #}
{% if page.author %}
<div class="author">
  {% if page.author.avatar %}
  <img src="{{ page.author.avatar }}" alt="{{ page.author.name }}">
  {% end %}
  <span>{{ page.author.name }}</span>
  {% if page.author.twitter %}
  <a href="https://twitter.com/{{ page.author.twitter }}">@{{ page.author.twitter }}</a>
  {% end %}
</div>
{% end %}

{# Multiple authors #}
{% for author in page.authors %}
<span class="author">{{ author.name }}</span>
{% end %}
```

**Author fields:** `name`, `email`, `bio`, `avatar`, `url`, `twitter`, `github`, `linkedin`, `mastodon`, `social` (dict)

### Series Properties

For multi-part content like tutorials.

```kida
{% if page.series %}
<nav class="series-nav">
  <h4>{{ page.series.name }}</h4>
  <p>Part {{ page.series.part }} of {{ page.series.total }}</p>

  {% if page.prev_in_series %}
  <a href="{{ page.prev_in_series.href }}">← {{ page.prev_in_series.title }}</a>
  {% end %}

  {% if page.next_in_series %}
  <a href="{{ page.next_in_series.href }}">{{ page.next_in_series.title }} →</a>
  {% end %}
</nav>
{% end %}
```

**Series frontmatter:**
```yaml
series:
  name: "Building a Blog with Bengal"
  part: 2
  total: 5
```

### Age Properties

Content age as computed properties.

```kida
{# Days since publication #}
{% if page.age_days < 7 %}
<span class="badge">New</span>
{% elif page.age_months > 6 %}
<div class="notice">This article is {{ page.age_months }} months old.</div>
{% end %}
```

---

## Section Properties

These properties are available on section objects.

### post_count

Count of pages in a section.

```kida
<span>{{ section.post_count }} articles</span>
<span>{{ section.post_count_recursive }} total in all subsections</span>
```

### featured_posts

Get featured pages from a section.

```kida
{% for post in section.featured_posts(3) %}
<article class="featured">
  <h2>{{ post.title }}</h2>
</article>
{% end %}
```

### Section Statistics

```kida
<div class="section-stats">
  <span>{{ section.word_count | intcomma }} words</span>
  <span>{{ section.total_reading_time }} min total reading time</span>
</div>
```

---

## Math Filters

Mathematical operations for calculations in templates.

### percentage

Calculate percentage with optional decimal places.

```kida
{{ completed | percentage(total_tasks) }}      {# "75%" #}
{{ score | percentage(max_score, 2) }}         {# "87.50%" #}
```

**Parameters:**
- `part`: Part value
- `total`: Total value
- `decimals`: Number of decimal places (default: 0)

### times

Multiply value by multiplier.

```kida
{{ price | times(1.1) }}      {# Add 10% tax #}
{{ count | times(5) }}        {# Multiply by 5 #}
```

### divided_by

Divide value by divisor. Returns 0 if divisor is 0.

```kida
{{ total | divided_by(count) }}      {# Average #}
{{ seconds | divided_by(60) }}       {# Convert to minutes #}
```

### ceil

Round up to nearest integer.

```kida
{{ 4.2 | ceil }}   {# 5 #}
{{ 4.9 | ceil }}   {# 5 #}
```

### floor

Round down to nearest integer.

```kida
{{ 4.2 | floor }}  {# 4 #}
{{ 4.9 | floor }}  {# 4 #}
```

### round

Round to specified decimal places.

```kida
{{ 4.567 | round }}      {# 5 #}
{{ 4.567 | round(2) }}   {# 4.57 #}
{{ 4.567 | round(1) }}   {# 4.6 #}
```

---

## Data Functions

Functions for loading and manipulating data files.

### get_data

Load data from JSON or YAML file. Returns empty dict if file not found.

```kida
{% let authors = get_data('data/authors.json') %}
{% for author in authors %}
  {{ author.name }}
{% end %}

{% let config = get_data('data/config.yaml') %}
```

### jsonify

Convert data to JSON string.

```kida
{{ data | jsonify }}           {# Compact JSON #}
{{ data | jsonify(2) }}        {# Pretty-printed with indent #}
```

### merge

Merge two dictionaries. Second dict takes precedence.

```kida
{% let config = defaults | merge(custom_config) %}
{% let shallow = dict1 | merge(dict2, deep=false) %}
```

### has_key

Check if dictionary has a key.

```kida
{% if data | has_key('author') %}
  {{ data.author }}
{% end %}
```

### get_nested

Access nested data using dot notation.

```kida
{{ data | get_nested('user.profile.name') }}
{{ data | get_nested('user.email', 'no-email') }}   {# With default #}
```

### keys

Get dictionary keys as list.

```kida
{% for key in data | keys %}
  {{ key }}
{% end %}
```

### values

Get dictionary values as list.

```kida
{% for value in data | values %}
  {{ value }}
{% end %}
```

### items

Get dictionary items as list of (key, value) tuples.

```kida
{% for key, value in data | items %}
  {{ key }}: {{ value }}
{% end %}
```

---

## File Functions

Functions for reading files and checking file existence.

### read_file

Read file contents as string.

```kida
{% let license = read_file('LICENSE') %}
{{ license }}

{% let readme = read_file('docs/README.md') %}
```

### file_exists

Check if file exists.

```kida
{% if file_exists('custom.css') %}
  <link rel="stylesheet" href="{{ asset_url('custom.css') }}">
{% end %}
```

### file_size

Get human-readable file size.

```kida
{{ file_size('downloads/manual.pdf') }}   {# "2.3 MB" #}
{{ file_size('images/hero.png') }}        {# "145.2 KB" #}
```

---

## Content Filters

Functions for HTML and content manipulation.

### html_escape

Escape HTML entities for safe display.

```kida
{{ user_input | html_escape }}
{# "<script>" becomes "&lt;script&gt;" #}
```

### html_unescape

Convert HTML entities back to characters.

```kida
{{ escaped_text | html_unescape }}
{# "&lt;Hello&gt;" becomes "<Hello>" #}
```

### nl2br

Convert newlines to HTML `<br>` tags.

```kida
{{ text | nl2br | safe }}
{# "Line 1\nLine 2" becomes "Line 1<br>\nLine 2" #}
```

### smartquotes

Convert straight quotes to smart (curly) quotes.

```kida
{{ text | smartquotes }}
{# "Hello" becomes "Hello" #}
{# -- becomes – (en-dash) #}
{# --- becomes — (em-dash) #}
```

### emojify

Convert emoji shortcodes to Unicode emoji.

```kida
{{ text | emojify }}
{# "Hello :smile:" becomes "Hello 😊" #}
{# "I :heart: Python" becomes "I ❤️ Python" #}
```

**Supported shortcodes:** `:smile:`, `:grin:`, `:joy:`, `:heart:`, `:star:`, `:fire:`, `:rocket:`, `:check:`, `:x:`, `:warning:`, `:tada:`, `:thumbsup:`, `:thumbsdown:`, `:eyes:`, `:bulb:`, `:sparkles:`, `:zap:`, `:wave:`, `:clap:`, `:raised_hands:`, `:100:`

### extract_content

Extract main content from full rendered HTML page. Useful for embedding page content.

```kida
{{ page.rendered_html | extract_content | safe }}
```

### demote_headings

Demote HTML headings by specified levels (h1→h2, h2→h3, etc.).

```kida
{{ page.content | demote_headings | safe }}
{# <h1>Title</h1> becomes <h2>Title</h2> #}

{{ page.content | demote_headings(2) | safe }}
{# <h1>Title</h1> becomes <h3>Title</h3> #}
```

### prefix_heading_ids

Prefix heading IDs to ensure uniqueness when embedding multiple pages.

```kida
{{ page.content | prefix_heading_ids("s1-") | safe }}
{# <h2 id="quick-start"> becomes <h2 id="s1-quick-start"> #}
{# <a href="#quick-start"> becomes <a href="#s1-quick-start"> #}
```

### urlize

Convert plain URLs in text to clickable HTML links.

```kida
{{ "Check out https://example.com for more info" | urlize }}
{# "Check out <a href="https://example.com">https://example.com</a>..." #}

{{ text | urlize(target='_blank', rel='noopener') }}
{# Opens links in new tab with security attributes #}

{{ text | urlize(shorten=true, shorten_length=30) }}
{# Shortens long URLs in display text #}
```

---

## Debug Filters

Development helpers for debugging templates.

### debug

Pretty-print variable for debugging.

```kida
{{ page | debug }}
{{ config | debug(pretty=false) }}
```

### typeof

Get the type of a variable.

```kida
{{ page | typeof }}      {# "Page" #}
{{ "hello" | typeof }}   {# "str" #}
{{ 42 | typeof }}        {# "int" #}
```

### inspect

Inspect object attributes and methods.

```kida
{{ page | inspect }}
{# Properties: title, href, date, ... #}
{# Methods: get_toc(), get_siblings(), ... #}
```

---

## SEO Functions

Functions for generating SEO-friendly meta tags.

### meta_description

Generate meta description from text. Strips HTML, truncates to length, ends at sentence boundary.

```kida
<meta name="description" content="{{ page.content | meta_description }}">
<meta name="description" content="{{ page.content | meta_description(200) }}">
```

### meta_keywords

Generate meta keywords from tags list.

```kida
<meta name="keywords" content="{{ page.tags | meta_keywords }}">
<meta name="keywords" content="{{ page.tags | meta_keywords(5) }}">  {# Max 5 #}
```

### canonical_url

Generate canonical URL. For versioned docs, always points to latest version.

```kida
<link rel="canonical" href="{{ canonical_url(page.href, page=page) }}">
```

### og_image

Generate Open Graph image URL. Supports manual image, auto-generated social cards, or fallback.

```kida
<meta property="og:image" content="{{ og_image(page.metadata.get('image', ''), page) }}">
```

### get_social_card_url

Get URL to generated social card for a page (if social cards are enabled).

```kida
{% let card = get_social_card_url(page) %}
{% if card %}
  <meta property="og:image" content="{{ card }}">
{% end %}
```

---

## Image Functions

Functions for working with images in templates.

### image_url

Generate image URL with optional sizing parameters.

```kida
{{ image_url('photos/hero.jpg') }}
{{ image_url('photos/hero.jpg', width=800) }}
{{ image_url('photos/hero.jpg', width=800, height=600, quality=85) }}
```

### image_dimensions

Get image dimensions (requires Pillow).

```kida
{% let dims = image_dimensions('photo.jpg') %}
{% if dims %}
  {% let width, height = dims %}
  <img width="{{ width }}" height="{{ height }}" src="..." alt="...">
{% end %}
```

### image_srcset

Generate srcset attribute for responsive images.

```kida
<img srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}" />
{# hero.jpg?w=400 400w, hero.jpg?w=800 800w, hero.jpg?w=1200 1200w #}
```

### image_srcset_gen

Generate srcset with default sizes (400, 800, 1200, 1600).

```kida
<img srcset="{{ image_srcset_gen('hero.jpg') }}" />
```

### image_alt

Generate alt text from filename.

```kida
{{ 'mountain-sunset.jpg' | image_alt }}
{# "Mountain Sunset" #}
```

### image_data_uri

Convert image to data URI for inline embedding.

```kida
<img src="{{ image_data_uri('icons/logo.svg') }}" alt="Logo">
```

---

## Icon Function

Render SVG icons in templates.

### icon

Render an SVG icon. Uses theme-aware icon resolution with caching.

```kida
{{ icon("search") }}
{{ icon("search", size=20) }}
{{ icon("menu", size=24, css_class="nav-icon") }}
{{ icon("arrow-up", size=18, aria_label="Back to top") }}
```

**Parameters:**
- `name`: Icon name (e.g., "search", "menu", "close", "arrow-up")
- `size`: Icon size in pixels (default: 24)
- `css_class`: Additional CSS classes
- `aria_label`: Accessibility label (if empty, uses aria-hidden)

**Alias:** `render_icon` is an alias for `icon`.

---

## Theme Functions

Functions for accessing theme configuration.

### feature_enabled

Check if a theme feature is enabled.

```kida
{% if 'navigation.toc' | feature_enabled %}
  {# Render table of contents #}
{% end %}

{% if feature_enabled('search.enabled') %}
  {# Render search box #}
{% end %}
```

---

## Quick Reference Table

| Category | Filter/Function | Description |
|----------|-----------------|-------------|
| **Math** | `percentage(total)` | Calculate percentage |
| | `times(n)` | Multiply |
| | `divided_by(n)` | Divide |
| | `ceil` | Round up |
| | `floor` | Round down |
| | `round(decimals)` | Round to decimals |
| **Data** | `get_data(path)` | Load JSON/YAML file |
| | `jsonify` | Convert to JSON |
| | `merge(dict)` | Merge dictionaries |
| | `has_key(key)` | Check key exists |
| | `get_nested(path)` | Access nested data |
| | `keys` | Get dict keys |
| | `values` | Get dict values |
| | `items` | Get dict items |
| **Files** | `read_file(path)` | Read file contents |
| | `file_exists(path)` | Check file exists |
| | `file_size(path)` | Get file size |
| **Content** | `html_escape` | Escape HTML |
| | `html_unescape` | Unescape HTML |
| | `nl2br` | Newlines to `<br>` |
| | `smartquotes` | Curly quotes |
| | `emojify` | Shortcodes to emoji |
| | `demote_headings(n)` | Demote heading levels |
| | `urlize` | URLs to links |
| **Debug** | `debug` | Pretty-print |
| | `typeof` | Get type name |
| | `inspect` | List attributes |
| **SEO** | `meta_description` | Generate meta desc |
| | `meta_keywords` | Generate keywords |
| | `canonical_url(path)` | Canonical URL |
| | `og_image(path)` | OG image URL |
| **Images** | `image_url(path)` | Image URL with params |
| | `image_dimensions(path)` | Get width/height |
| | `image_srcset(sizes)` | Generate srcset |
| | `image_alt` | Alt from filename |
| | `image_data_uri(path)` | Inline data URI |
| **Icons** | `icon(name)` | Render SVG icon |
| **Theme** | `feature_enabled(key)` | Check feature flag |
