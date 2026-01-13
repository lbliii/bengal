---
title: Linking Functions
description: Generate links to pages, headings, and external documentation
weight: 30
type: doc
tags:
- reference
- functions
- linking
- cross-references
category: reference
---

# Linking Functions

These functions generate links to pages and headings. All use O(1) lookups from pre-built indexes.

## ref

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

## doc

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

## anchor

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

## relref

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

## xref

Alias for `ref()` for compatibility with other systems.

```kida
{{ xref('docs/api') }}
{{ xref('docs/api', 'API Reference') }}
```

**Note**: `xref()` and `ref()` are identical — use whichever you prefer.

## ext

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

## ext_exists

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
