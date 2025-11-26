---
title: Use Templates
description: Access variables and objects in Jinja2 templates
weight: 25
type: doc
draft: false
lang: en
tags: [templating, jinja2, templates, variables]
keywords: [templating, jinja2, templates, variables, context]
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
| `page.permalink` | The full absolute URL. | `{{ page.permalink }}` |
| `page.rel_permalink`| The relative URL path. | `{{ page.rel_permalink }}` |

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
        <li><a href="{{ p.rel_permalink }}">{{ p.title }}</a></li>
    {% endif %}
{% endfor %}
</ul>
```

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
<!-- themes/my-theme/layouts/base.html -->
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
<!-- themes/my-theme/layouts/page.html -->
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
