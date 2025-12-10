---
title: Use Templates
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

Every template in Bengal receives three primary objects:

1.  **`page`**: The current page being rendered.
2.  **`site`**: Global site information and collections.
3.  **`config`**: The full configuration dictionary.

### 1. The `page` Object

The `page` object represents the current markdown file being rendered. It gives you access to content and frontmatter.

| Attribute | Description | Example |
| :--- | :--- | :--- |
| `page.title` | The page title. | `{{ page.title }}` |
| `page.content` | The raw content (rarely used directly). | `{{ page.content }}` |
| `page.metadata` | Dictionary of all frontmatter variables. | `{{ page.metadata.tags }}` |
| `page.rendered_html` | The compiled HTML of the content. | `{{ page.rendered_html }}` |
| `page.toc` | Auto-generated Table of Contents (HTML). | `{{ page.toc }}` |
| `page.date` | Python `datetime` object. | `{{ page.date.strftime('%Y-%m-%d') }}` |
| `page.url` | URL with baseurl applied (for display). | `{{ page.url }}` |
| `page.relative_url` | Relative URL without baseurl (for comparisons). | `{{ page.relative_url }}` |
| `page.permalink` | Alias for `url` (backward compatibility). | `{{ page.permalink }}` |

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

Bengal provides three URL properties with clear purposes:

**`page.url`** - **Primary property for display**
- Automatically includes baseurl (e.g., `/bengal/docs/page/`)
- Use in `<a href>`, `<link>`, `<img src>` attributes
- Works correctly for all deployment scenarios (GitHub Pages, Netlify, S3, file://, etc.)

**`page.relative_url`** - **For comparisons and logic**
- Relative URL without baseurl (e.g., `/docs/page/`)
- Use for comparisons: `{% if page.relative_url == '/docs/' %}`
- Use for menu activation, filtering, and conditional logic

**`page.permalink`** - **Backward compatibility**
- Alias for `url` (same value)
- Maintained for compatibility with existing themes

:::{example-label} Usage
:::

```html
{# Display URL (includes baseurl) #}
<a href="{{ page.url }}">{{ page.title }}</a>

{# Comparison (without baseurl) #}
{% if page.relative_url == '/docs/' %}
  <span class="active">Current Section</span>
{% endif %}

{# Both work the same #}
<a href="{{ page.url }}">Link 1</a>
<a href="{{ page.permalink }}">Link 2</a>  {# Same as page.url #}
```

**Why This Pattern?**

- **Ergonomic**: Templates use `{{ page.url }}` for display - it "just works"
- **Clear**: `relative_url` makes comparisons explicit
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

## Common Helpers

Bengal provides several Jinja2 filters and functions.

*   **`url_for(page)`**: Returns the relative URL for a page object.
*   **`date_format(date, format)`**: Formats a date object.
*   **`| safe`**: Marks HTML as safe to render (prevents escaping).

## Debugging

If you are unsure what data is available, you can print objects to the console during build (using Python's `print` inside a template extension is not standard, but you can inspect variables).

A common trick is to dump data:

```html
<!-- Dump variables to HTML comments for inspection -->
<!-- {{ page.metadata }} -->
```
