---
title: Theme Variables
nav_title: Variables
description: Comprehensive reference of all variables and functions available in Jinja2
  templates.
weight: 10
type: doc
tags:
- reference
- templates
- variables
- jinja2
category: reference
---

# Theme Variables

This reference lists all variables, objects, and functions available in Bengal templates.

## Global Objects

These variables are available in **all** templates.

### `site`

The global site object.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `site.title` | `str` | Site title from config |
| `site.baseurl` | `str` | Base URL (e.g., `https://example.com`) |
| `site.author` | `str` | Site author name |
| `site.language` | `str` | Language code (e.g., `en`) |
| `site.pages` | `list[Page]` | All pages in the site |
| `site.regular_pages` | `list[Page]` | Content pages only (no list pages) |
| `site.sections` | `list[Section]` | Top-level sections |
| `site.taxonomies` | `dict` | Map of taxonomies (tags, categories) |
| `site.data` | `dict` | Data loaded from `data/` directory |
| `site.config` | `dict` | Full configuration object |

### `section`

Available on index pages (`_index.md`) and doc-type pages.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `section.name` | `str` | Directory name |
| `section.title` | `str` | Section title (from `_index.md`) |
| `section.index_page` | `Page` | The section's `_index.md` page |
| `section.pages` | `list[Page]` | Direct child pages |
| `section.sorted_pages` | `list[Page]` | Pages sorted by weight/date |
| `section.subsections` | `list[Section]` | Child sections |
| `section.metadata` | `dict` | Frontmatter from `_index.md` |

:::{example-label} Auto-Generated Child Cards
:::

```jinja2
<div class="child-cards">
  {% for subsection in section.subsections %}
    <a href="{{ subsection.index_page.url }}" class="card">
      <h3>{{ subsection.title }}</h3>
      <p>{{ subsection.metadata.description }}</p>
    </a>
  {% endfor %}
</div>
```

:::{example-label} Section Navigation
:::

```jinja2
<nav class="section-nav">
  <h4>In this section:</h4>
  <ul>
    {% for page in section.sorted_pages %}
      <li><a href="{{ page.url }}">{{ page.title }}</a></li>
    {% endfor %}
  </ul>
</nav>
```

### `page`

The current page being rendered.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `page.title` | `str` | Page title |
| `page.nav_title` | `str` | Short title for navigation (falls back to title) |
| `page.content` | `str` | Raw content |
| `page.rendered_html` | `str` | Rendered HTML content |
| `page.date` | `datetime` | Publication date |
| `page.href` | `str` | URL with baseurl applied (for display in templates) |
| `page._path` | `str` | Site-relative URL without baseurl (for comparisons) |
| `page.slug` | `str` | URL slug for the page |
| `page.metadata` | `dict` | All frontmatter keys |
| `page.toc` | `str` | Auto-generated Table of Contents HTML |
| `page.toc_items` | `list[dict]` | Structured TOC data (id, title, level) |
| `page.is_home` | `bool` | True if homepage |
| `page.is_section` | `bool` | True if section index |
| `page.is_page` | `bool` | True if regular page (not section) |
| `page.kind` | `str` | Returns 'home', 'section', or 'page' |
| `page.type` | `str` | Page type from frontmatter |
| `page.draft` | `bool` | True if page is a draft |
| `page.description` | `str` | Page description |

#### Navigation Properties

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `page._section` | `Section` | Parent section object (direct access to object tree) |
| `page.ancestors` | `list[Section]` | Parent sections from root to current (for breadcrumbs) |
| `page.prev_in_section` | `Page \| None` | Previous page in section (by weight/date) |
| `page.next_in_section` | `Page \| None` | Next page in section (by weight/date) |
| `page.related_posts` | `list[Page]` | Pages with matching tags |

:::{example-label} Custom Breadcrumbs
:::

```jinja2
<nav class="breadcrumbs">
  <a href="/">Home</a>
  {% for ancestor in page.ancestors %}
    > <a href="{{ ancestor.href }}">{{ ancestor.title }}</a>
  {% endfor %}
  > <span>{{ page.title }}</span>
</nav>
```

:::{example-label} Prev/Next Navigation
:::

```jinja2
<nav class="prev-next">
  {% if page.prev_in_section %}
    <a href="{{ page.prev_in_section.href }}">← {{ page.prev_in_section.title }}</a>
  {% endif %}
  {% if page.next_in_section %}
    <a href="{{ page.next_in_section.href }}">{{ page.next_in_section.title }} →</a>
  {% endif %}
</nav>
```

:::{example-label} Related Posts
:::

```jinja2
{% if page.related_posts %}
<aside class="related">
  <h3>Related Articles</h3>
  <ul>
    {% for post in page.related_posts[:5] %}
      <li><a href="{{ post.href }}">{{ post.title }}</a></li>
    {% endfor %}
  </ul>
</aside>
{% endif %}
```

#### URL Properties

Bengal provides two URL properties with clear purposes:

**`page.href`** - **Primary property for display**
- Automatically includes baseurl (e.g., `/bengal/docs/page/`)
- Use in `<a href>`, `<link>`, `<img src>` attributes
- Works correctly for all deployment scenarios (GitHub Pages, Netlify, S3, etc.)

**`page._path`** - **For comparisons and logic**
- Site-relative URL without baseurl (e.g., `/docs/page/`)
- Use for comparisons: `{% if page._path == '/docs/' %}`
- Use for menu activation, filtering, and conditional logic
- NEVER use in template href attributes

:::{example-label} Usage
:::

```jinja2
{# Display URL (includes baseurl) #}
<a href="{{ page.href }}">{{ page.title }}</a>

{# Comparison (without baseurl) #}
{% if page._path == '/docs/' %}
  <span class="active">Current Section</span>
{% endif %}

{# url_for() also works for URL generation #}
<a href="{{ url_for(page) }}">{{ page.title }}</a>
```

**Why This Pattern?**

- **Ergonomic**: Templates use `{{ page.href }}` for display - it "just works"
- **Clear**: `_path` makes comparisons explicit (without baseurl)
- **No wrappers**: Page objects handle baseurl via their `_site` reference
- **Works everywhere**: Supports file://, S3, GitHub Pages, Netlify, Vercel, etc.

## Global Functions

Functions available in all templates.

### `asset_url(path)`
Generates a fingerprint-aware URL for an asset.
```html
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
<!-- Outputs: /assets/css/style.a1b2c3d4.css -->
```

### `url_for(page_or_slug)`
Generates a URL for a page object or slug. Applies baseurl automatically.
```html
<a href="{{ url_for(page) }}">Link</a>
<a href="{{ url_for('/docs/getting-started/') }}">Getting Started</a>
```

### `dateformat(date, format)`
Formats a date object.
```html
{{ dateformat(page.date, "%B %d, %Y") }}
```

### `get_menu(menu_name)`
Retrieves a navigation menu.
```html
{% for item in get_menu('main') %}
  <a href="{{ item.url }}">{{ item.name }}</a>
{% endfor %}
```

## Template Helpers

Bengal includes categorized helper modules:

*   **Strings**: `truncate`, `slugify`, `markdownify`
*   **Collections**: `where`, `group_by`, `sort_by`
*   **Dates**: `time_ago`, `date_iso`
*   **Images**: `image_processed`, `image_url`
*   **Taxonomies**: `related_posts`, `popular_tags`

:::{tip}
**Debugging**
You can inspect available variables by printing them in a comment:
`<!-- {{ page.metadata }} -->`
:::
