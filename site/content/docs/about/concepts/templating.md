---
title: Use Templates
nav_title: Templates
description: Access variables and objects in Jinja2 templates
weight: 25
type: doc
draft: false
lang: en
tags:
- templating
- jinja2
- templates
- variables
keywords:
- templating
- jinja2
- templates
- variables
- context
category: documentation
---

Bengal uses Jinja2 as its template engine. This guide explains what data is available in templates and how to access site and page data.

## The Template Context

Every template in Bengal receives the following primary objects:

| Object | Description |
|--------|-------------|
| `page` | The current page being rendered |
| `site` | Global site information and collections |
| `config` | The full configuration dictionary |
| `content` | Pre-rendered HTML content (marked safe) |
| `toc` | Table of contents HTML (marked safe) |
| `toc_items` | Structured TOC data for custom rendering |
| `bengal` | Engine metadata (name, version) |

Additional globals available:

- `versioning_enabled` - Whether versioning is enabled
- `versions` - List of available versions
- `theme` - Theme configuration object

### 1. The `page` Object

The `page` object represents the current markdown file being rendered. It gives you access to content and frontmatter.

| Attribute | Description | Example |
| :--- | :--- | :--- |
| `page.title` | The page title. | `{{ page.title }}` |
| `page.nav_title` | Short title for navigation (falls back to title). | `{{ page.nav_title }}` |
| `page.content` | The raw content (rarely used directly). | `{{ page.content }}` |
| `page.metadata` | Dictionary of all frontmatter variables. | `{{ page.metadata.tags }}` |
| `page.rendered_html` | The compiled HTML of the content. | `{{ page.rendered_html }}` |
| `page.toc` | Auto-generated Table of Contents (HTML). | `{{ page.toc }}` |
| `page.toc_items` | Structured TOC data (list of dicts with id, title, level). | `{{ page.toc_items }}` |
| `page.date` | Python `datetime` object. | `{{ page.date.strftime('%Y-%m-%d') }}` |
| `page.href` | URL with baseurl applied (for display). | `{{ page.href }}` |
| `page.meta_description` | SEO description (max 160 chars, auto-generated). | `{{ page.meta_description }}` |
| `page.reading_time` | Estimated reading time in minutes. | `{{ page.reading_time }}` |
| `page.excerpt` | Content excerpt (max 200 chars). | `{{ page.excerpt }}` |

**Type Checking Properties**:

| Attribute | Description |
| :--- | :--- |
| `page.is_home` | True if this is the home page |
| `page.is_section` | True if this is a section page |
| `page.is_page` | True if this is a regular page |
| `page.kind` | Returns "home", "section", or "page" |
| `page.type` | Page type (e.g., "doc", "post") |
| `page.variant` | Visual variant for CSS customization |
| `page.draft` | True if page is a draft |
| `page.hidden` | True if page is hidden |

#### Accessing Custom Frontmatter

Any custom key you add to your YAML frontmatter is available in `page.metadata`:

```yaml
---
title: My Page
author: "Alice"
banner_image: "images/banner.jpg"
---
```

```html
<div class="author">By {{ page.metadata.author }}</div>
<img src="{{ page.metadata.banner_image }}" />
```

### 2. The `site` Object

The `site` object provides access to your entire website's content and structure.

| Attribute | Description |
| :--- | :--- |
| `site.pages` | List of all pages (includes sections and special pages). |
| `site.regular_pages` | List of standard content pages (excludes generated lists). |
| `site.sections` | List of top-level sections. |
| `site.taxonomies` | Dictionary of tags and categories. |
| `site.data` | Data loaded from the `data/` directory. |
| `site.menu` | Navigation menus defined in config. |

#### Iterating Pages

To list all blog posts:

```html
<ul>
{% for p in site.regular_pages %}
    {% if p.metadata.type == "post" %}
        <li><a href="{{ p.url }}">{{ p.title }}</a></li>
    {% endif %}
{% endfor %}
</ul>
```

#### URL Pattern Best Practices

Bengal provides URL properties with clear purposes:

**`page.href`** - **Primary property for display**

- Automatically includes baseurl (e.g., `/bengal/docs/page/`)
- Use in `<a href>`, `<link>`, `<img src>` attributes
- Works correctly for all deployment scenarios (GitHub Pages, Netlify, S3, file://, etc.)

**`page._path`** - **For internal comparisons** (internal use)

- Relative URL without baseurl (e.g., `/docs/page/`)
- Use for menu activation, filtering, and conditional logic
- Note: This is an internal property; prefer using template helpers for comparisons

**`page.absolute_href`** - **For meta tags and sitemaps**

- Fully-qualified URL when site URL is configured
- Falls back to `href` if no absolute URL configured

:::{example-label} Usage
:::

```html
{# Display URL (includes baseurl) #}
<a href="{{ page.href }}">{{ page.title }}</a>

{# For SEO meta tags #}
<meta property="og:url" content="{{ page.absolute_href }}">

{# Check page type #}
{% if page.is_section %}
  <span class="section-badge">Section</span>
{% endif %}
```

**Why This Pattern?**

- **Ergonomic**: Templates use `{{ page.href }}` for display - it "just works"
- **Clear**: Type checking properties (`is_home`, `is_section`) make logic explicit
- **No wrappers**: Page objects handle baseurl via their `_site` reference
- **Works everywhere**: Supports file://, S3, GitHub Pages, Netlify, Vercel, etc.

#### Accessing Data Files

If you have a file `data/authors.yaml`:

```yaml
alice:
  name: Alice Smith
  bio: Engineer
bob:
  name: Bob Jones
  bio: Designer
```

You can access it via `site.data`:

```html
{% set author = site.data.authors[page.metadata.author] %}
<div class="bio">{{ author.name }}: {{ author.bio }}</div>
```

## Template Inheritance

Bengal themes typically use Jinja2's inheritance model.

### Base Template (`base.html`)

Defines the common structure (HTML head, nav, footer).

```html
<!-- themes/my-theme/templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{{ site.title }}{% endblock %}</title>
</head>
<body>
    <nav>...</nav>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>...</footer>
</body>
</html>
```

### Page Template

Extends the base template and fills in the blocks.

```html
<!-- themes/my-theme/templates/page.html -->
{% extends "base.html" %}

{% block title %}{{ page.title }} - {{ site.title }}{% endblock %}

{% block content %}
    <h1>{{ page.title }}</h1>
    <div class="content">
        {{ page.rendered_html | safe }}
    </div>
{% endblock %}
```

## Template Functions

Bengal provides 80+ template functions organized into categories:

### Essential Functions

| Function | Description | Example |
|----------|-------------|---------|
| `url_for(page)` | Returns the URL for a page object | `{{ url_for(page) }}` |
| `asset_url(path)` | Returns fingerprinted asset URL | `{{ asset_url('css/style.css') }}` |
| `get_page(path)` | Get a page by path | `{% set p = get_page('/docs/intro/') %}` |
| `get_menu(name)` | Get menu items by name | `{% for item in get_menu('main') %}` |

### String Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `truncate(n)` | Truncate to n characters | `{{ text \| truncate(100) }}` |
| `slugify` | Convert to URL slug | `{{ title \| slugify }}` |
| `titlecase` | Title case text | `{{ name \| titlecase }}` |
| `markdown` | Render markdown to HTML | `{{ content \| markdown \| safe }}` |

### Collection Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `sort_by(key)` | Sort list by key | `{{ pages \| sort_by('date', reverse=True) }}` |
| `group_by(key)` | Group items by key | `{{ pages \| group_by('category') }}` |
| `where(key, val)` | Filter items | `{{ pages \| where('draft', false) }}` |

### Date Formatting

| Filter | Description | Example |
|--------|-------------|---------|
| `date_format(fmt)` | Format date | `{{ page.date \| date_format('%B %d, %Y') }}` |

### Built-in Jinja2

- **`| safe`**: Marks HTML as safe to render (prevents escaping).

## Debugging

If you are unsure what data is available, you can print objects to the console during build (using Python's `print` inside a template extension is not standard, but you can inspect variables).

A common trick is to dump data:

```html
<!-- Dump variables to HTML comments for inspection -->
<!-- {{ page.metadata }} -->
```
