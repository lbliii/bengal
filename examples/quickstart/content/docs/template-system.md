---
title: "Template System Reference"
date: 2025-10-03
tags: ["templates", "jinja2", "customization", "reference"]
categories: ["Documentation", "Reference"]
type: "reference"
description: "Complete reference for Bengal's Jinja2-based template system"
author: "Bengal Documentation Team"
preprocess: false  # Disable Jinja2 preprocessing (this page documents Jinja2 syntax)
---

# Template System Reference

Complete reference for Bengal's powerful Jinja2-based template system.

## Overview

Bengal uses [Jinja2](https://jinja.palletsprojects.com/) for templating, providing:

- ✅ Template inheritance
- ✅ Reusable partials/includes
- ✅ Custom filters and functions
- ✅ Conditional rendering
- ✅ Loops and iteration
- ✅ Safe HTML escaping

> **📝 Writing Template Documentation?** If you need to show Jinja2 syntax literally (like `{{ '{{ toc }}' }}` or `{{ '{% for %}' }}`), use **string literals** instead of `{{ '{% raw %}' }}` blocks. See [Escaping Template Syntax](#escaping-template-syntax) below for details.

## Available Templates

Bengal's default theme includes these templates:

| Template | Purpose | Use Case |
|----------|---------|----------|
| `base.html` | Master layout | All templates extend this |
| `index.html` | Homepage | Site homepage/landing page |
| `page.html` | Static pages | About, contact, etc. |
| `post.html` | Blog posts | Blog posts with dates/tags |
| `archive.html` | Section lists | Category/section archives |
| `tags.html` | Tag index | All tags overview |
| `tag.html` | Single tag | Posts for one tag |
| `404.html` | Error page | Not found errors |

### Partials (Reusable Components)

| Partial | Purpose |
|---------|---------|
| `partials/article-card.html` | Blog post preview card |
| `partials/tag-list.html` | Tag display component |
| `partials/pagination.html` | Pagination controls |
| `partials/breadcrumbs.html` | Breadcrumb navigation |

## Template Context

Every template receives these context variables:

### Page Object

```jinja2
{{ page.title }}           # Page title (string)
{{ page.date }}            # Publication date (datetime object)
{{ page.tags }}            # List of tags (list of strings)
{{ page.url }}             # Clean URL path (string, e.g., /posts/my-post/)
{{ page.slug }}            # URL slug (string, e.g., my-post)
{{ page.metadata }}        # All frontmatter (dict)
{{ page.content }}         # Raw content (string)
{{ page.source_path }}     # Source file path (Path object)
```

**Example usage**:

```jinja2
<article>
  <h1>{{ page.title }}</h1>
  {% if page.date %}
    <time datetime="{{ page.date | dateformat('%Y-%m-%d') }}">
      {{ page.date | dateformat('%B %d, %Y') }}
    </time>
  {% endif %}
</article>
```

### Site Object

```jinja2
{{ site.title }}           # Site title
{{ site.baseurl }}         # Base URL (e.g., https://example.com)
{{ site.description }}     # Site description
{{ site.theme }}           # Current theme name
{{ site.pages }}           # All site pages (list)
{{ site.taxonomies }}      # Tags and categories (dict)
```

**Example usage**:

```jinja2
<header>
  <h1>{{ site.title }}</h1>
  <p>{{ site.description }}</p>
</header>
```

### Config Object

```jinja2
{{ config.output_dir }}    # Output directory
{{ config.parallel }}      # Parallel processing enabled
{{ config.incremental }}   # Incremental builds enabled
{{ config.theme }}         # Theme name
```

### Content Variable

```jinja2
{{ content }}              # Rendered HTML content
```

This contains the parsed and rendered Markdown content.

### Additional Context (Page-Specific)

**For Archive Pages**:

```jinja2
{{ pages }}                # List of pages in archive
{{ section }}              # Section name
{{ pagination }}           # Pagination object (if paginated)
```

**For Tag Pages**:

```jinja2
{{ tag }}                  # Tag name
{{ pages }}                # Pages with this tag
{{ pagination }}           # Pagination object (if paginated)
```

**For Tag Index**:

```jinja2
{{ tags }}                 # Dict of all tags with counts
```

## Custom Filters

### dateformat

Format dates with strftime syntax:

```jinja2
{{ page.date | dateformat('%B %d, %Y') }}
# Output: October 03, 2025

{{ page.date | dateformat('%Y-%m-%d') }}
# Output: 2025-10-03

{{ page.date | dateformat('%A, %B %d') }}
# Output: Friday, October 03

{{ page.date | dateformat('%b %d, %Y') }}
# Output: Oct 03, 2025
```

**Common Format Codes**:

| Code | Meaning | Example |
|------|---------|---------|
| `%Y` | Year (4 digits) | 2025 |
| `%y` | Year (2 digits) | 25 |
| `%m` | Month (numeric) | 10 |
| `%B` | Month (full name) | October |
| `%b` | Month (abbreviated) | Oct |
| `%d` | Day of month | 03 |
| `%A` | Weekday (full) | Friday |
| `%a` | Weekday (abbreviated) | Fri |

### Built-in Jinja2 Filters

Bengal includes all standard Jinja2 filters:

```jinja2
{{ page.title | upper }}           # UPPERCASE
{{ page.title | lower }}           # lowercase
{{ page.title | capitalize }}      # Capitalize first word
{{ page.title | title }}           # Title Case Each Word

{{ page.content | length }}        # String length
{{ page.content | truncate(100) }} # Truncate to 100 chars

{{ page.tags | join(', ') }}       # Join list with separator
{{ page.tags | first }}            # First item
{{ page.tags | last }}             # Last item
```

## Global Functions

### url_for(page)

Generate clean URLs for pages:

```jinja2
<a href="{{ url_for(page) }}">{{ page.title }}</a>
# Output: <a href="/posts/my-post/">My Post</a>

<link rel="canonical" href="{{ site.baseurl }}{{ url_for(page) }}">
# Output: <link rel="canonical" href="https://example.com/posts/my-post/">
```

### asset_url(path)

Generate asset URLs:

```jinja2
<img src="{{ asset_url('images/logo.png') }}" alt="Logo">
# Output: <img src="/assets/images/logo.png" alt="Logo">

<link rel="stylesheet" href="{{ asset_url('css/custom.css') }}">
# Output: <link rel="stylesheet" href="/assets/css/custom.css">

<script src="{{ asset_url('js/app.js') }}"></script>
# Output: <script src="/assets/js/app.js"></script>
```

## Template Inheritance

### Extending the Base Template

All templates should extend `base.html`:

```jinja2
{% extends "base.html" %}

{% block title %}{{ page.title }} - {{ site.title }}{% endblock %}

{% block content %}
  <article>
    <h1>{{ page.title }}</h1>
    <div class="content">
      {{ content }}
    </div>
  </article>
{% endblock %}
```

### Available Blocks

The `base.html` template provides these blocks:

```jinja2
{% block title %}
  <!-- Page title for <title> tag -->
{% endblock %}

{% block head %}
  <!-- Additional <head> content -->
  <!-- Meta tags, extra CSS, etc. -->
{% endblock %}

{% block header %}
  <!-- Header content -->
  <!-- Navigation, site title -->
{% endblock %}

{% block content %}
  <!-- Main page content -->
  <!-- Your page HTML goes here -->
{% endblock %}

{% block sidebar %}
  <!-- Sidebar content (if theme supports) -->
{% endblock %}

{% block footer %}
  <!-- Footer content -->
{% endblock %}

{% block scripts %}
  <!-- Additional JavaScript -->
{% endblock %}
```

### Multi-Level Inheritance

You can create intermediate templates:

```jinja2
{# templates/blog-base.html #}
{% extends "base.html" %}

{% block content %}
<div class="blog-layout">
  <article class="blog-post">
    {% block article %}{% endblock %}
  </article>
  
  <aside class="blog-sidebar">
    {% block sidebar %}
      {# Default sidebar content #}
    {% endblock %}
  </aside>
</div>
{% endblock %}
```

Then extend it:

```jinja2
{# templates/post.html #}
{% extends "blog-base.html" %}

{% block article %}
  <h1>{{ page.title }}</h1>
  {{ content }}
{% endblock %}
```

## Including Partials

### Basic Include

```jinja2
{% include "partials/article-card.html" %}
```

### Include with Context

```jinja2
{% include "partials/article-card.html" %}
{# Automatically receives all template context #}
```

### Include with Specific Variables

```jinja2
{% for post in recent_posts %}
  {% include "partials/article-card.html" with context %}
{% endfor %}
```

### Common Partials

**Article Card**:

```jinja2
{% for post in pages %}
  {% include "partials/article-card.html" %}
{% endfor %}
```

**Tag List**:

```jinja2
{% if page.tags %}
  {% include "partials/tag-list.html" %}
{% endif %}
```

**Pagination**:

```jinja2
{% if pagination %}
  {% include "partials/pagination.html" %}
{% endif %}
```

**Breadcrumbs**:

```jinja2
{% include "partials/breadcrumbs.html" %}
```

## Conditional Rendering

### If Statements

```jinja2
{% if page.date %}
  <time>{{ page.date | dateformat('%B %d, %Y') }}</time>
{% endif %}

{% if page.tags and page.tags|length > 0 %}
  <div class="tags">
    {% for tag in page.tags %}
      <span class="tag">{{ tag }}</span>
    {% endfor %}
  </div>
{% endif %}
```

### If-Else

```jinja2
{% if page.metadata.author %}
  <p>By {{ page.metadata.author }}</p>
{% else %}
  <p>By Anonymous</p>
{% endif %}
```

### If-Elif-Else

```jinja2
{% if page.metadata.type == 'post' %}
  <article class="blog-post">
{% elif page.metadata.type == 'tutorial' %}
  <article class="tutorial">
{% elif page.metadata.type == 'guide' %}
  <article class="guide">
{% else %}
  <article class="generic-page">
{% endif %}
  {{ content }}
</article>
```

### Inline If (Ternary)

```jinja2
<p class="{{ 'featured' if page.metadata.featured else 'regular' }}">

{{ page.metadata.author or 'Anonymous' }}
```

## Loops

### Basic For Loop

```jinja2
{% for post in site.pages %}
  <article>
    <h2>{{ post.title }}</h2>
  </article>
{% endfor %}
```

### For Loop with Filter

```jinja2
{% for post in site.pages %}
  {% if post.metadata.type == 'post' %}
    <article>
      <h2><a href="{{ url_for(post) }}">{{ post.title }}</a></h2>
      <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    </article>
  {% endif %}
{% endfor %}
```

### For Loop with Else

```jinja2
{% for post in recent_posts %}
  <article>{{ post.title }}</article>
{% else %}
  <p>No posts found.</p>
{% endfor %}
```

### Loop Variables

```jinja2
{% for post in posts %}
  <article class="{{ 'first' if loop.first else '' }} {{ 'last' if loop.last else '' }}">
    <span>{{ loop.index }}. {{ post.title }}</span>
    <small>({{ loop.index }} of {{ loop.length }})</small>
  </article>
{% endfor %}
```

**Available loop variables**:

| Variable | Description |
|----------|-------------|
| `loop.index` | Current iteration (1-indexed) |
| `loop.index0` | Current iteration (0-indexed) |
| `loop.first` | True if first iteration |
| `loop.last` | True if last iteration |
| `loop.length` | Number of items |
| `loop.revindex` | Reverse index (from end) |
| `loop.revindex0` | Reverse index (0-indexed) |

## Macros (Reusable Functions)

Define reusable template functions:

```jinja2
{# templates/macros.html #}
{% macro render_post(post) %}
  <article>
    <h2><a href="{{ url_for(post) }}">{{ post.title }}</a></h2>
    {% if post.date %}
      <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
    {% endif %}
    {% if post.tags %}
      <div class="tags">
        {% for tag in post.tags %}
          <span class="tag">{{ tag }}</span>
        {% endfor %}
      </div>
    {% endif %}
  </article>
{% endmacro %}
```

Use the macro:

```jinja2
{% from "macros.html" import render_post %}

{% for post in posts %}
  {{ render_post(post) }}
{% endfor %}
```

## Custom Templates

### Creating a Custom Template

Create `templates/tutorial.html`:

```jinja2
{% extends "base.html" %}

{% block title %}{{ page.title }} - Tutorial - {{ site.title }}{% endblock %}

{% block content %}
<article class="tutorial">
  <header class="tutorial-header">
    <h1>{{ page.title }}</h1>
    
    {% if page.metadata.difficulty %}
      <span class="badge difficulty-{{ page.metadata.difficulty | lower }}">
        {{ page.metadata.difficulty }}
      </span>
    {% endif %}
    
    {% if page.metadata.duration %}
      <span class="duration">⏱️ {{ page.metadata.duration }}</span>
    {% endif %}
  </header>

  {% if page.metadata.prerequisites %}
    <aside class="prerequisites">
      <h2>Prerequisites</h2>
      <ul>
        {% for prereq in page.metadata.prerequisites %}
          <li>{{ prereq }}</li>
        {% endfor %}
      </ul>
    </aside>
  {% endif %}

  <div class="tutorial-content">
    {{ content }}
  </div>

  <footer class="tutorial-footer">
    {% if page.metadata.next_tutorial %}
      <a href="{{ url_for(page.metadata.next_tutorial) }}" class="btn-next">
        Next Tutorial →
      </a>
    {% endif %}
  </footer>
</article>
{% endblock %}
```

### Using the Custom Template

In your content file:

```markdown
---
title: "My Tutorial"
type: tutorial
template: tutorial.html
difficulty: "Intermediate"
duration: "30 minutes"
prerequisites:
  - "Basic Python knowledge"
  - "Bengal installed"
---

# Tutorial content here...
```

## Template Lookup Order

Bengal searches for templates in this order:

1. **Custom templates**: `<site>/templates/`
2. **Theme templates**: `<site>/themes/<theme>/templates/`
3. **Default templates**: `<bengal>/themes/default/templates/`

This allows you to override any template by creating it in your custom templates directory.

### Template Selection Logic

For a page, Bengal determines the template in this order:

1. **Explicit template**: If `template: custom.html` in frontmatter
2. **Type-based**: If `type: post`, use `post.html`
3. **Default**: Use `page.html`

## Best Practices

### ✅ Do

- **Use template inheritance** for consistent layouts
- **Create partials** for reusable components
- **Add comments** to complex template logic
- **Use semantic HTML** elements
- **Escape user content** (Jinja2 does this by default)
- **Keep logic simple** in templates

### ❌ Don't

- **Don't put business logic** in templates
- **Don't create deeply nested** template hierarchies
- **Don't forget** to handle missing data
- **Don't duplicate** code (use partials/macros)

## Advanced Techniques

### Dynamic CSS Classes

```jinja2
<article class="
  post
  {{ 'featured' if page.metadata.featured }}
  {{ 'has-image' if page.metadata.image }}
  type-{{ page.metadata.type or 'default' }}
">
```

### Safe HTML

```jinja2
{# Escape HTML by default #}
{{ page.user_content }}

{# Mark as safe (dangerous!) #}
{{ page.trusted_html | safe }}

{# Better: use markdown rendering #}
{{ content }}
```

### Escaping Template Syntax

When writing documentation about Bengal's templates, you need to show Jinja2 syntax literally without it being processed. **Use string literals** for this:

#### Basic Escaping

```jinja2
{# Show template variables as text #}
Use {{ '{{ page.title }}' }} to display the page title.
Use {{ '{{ toc }}' }} for table of contents.
Use {{ '{{ site.pages | length }}' }} to show page count.

{# Show template tags #}
{{ '{% for item in items %}' }}
{{ '{% if condition %}' }}
{{ '{% endfor %}' }}
{{ '{% endif %}' }}
```

**How it works**: The outer `{{ '{{ }}' }}` evaluates the inner string literal, outputting the Jinja2 syntax as plain text.

#### In Code Blocks

String literals work perfectly in fenced code blocks:

````markdown
Example template code:

```jinja2
{{ '{{ toc }}' }}
{{ '{{ page.metadata.author }}' }}
{{ '{% for post in site.pages %}' }}
  <h2>{{ '{{ post.title }}' }}</h2>
{{ '{% endfor %}' }}
```
````

#### Common Use Cases

**Documenting template variables**:
```markdown
To display the page title, use {{ '{{ page.title }}' }}.
To show the table of contents, use {{ '{{ toc }}' }}.
```

**Showing filter usage**:
```markdown
Format dates with {{ '{{ page.date | dateformat("%Y-%m-%d") }}' }}.
```

**Explaining conditionals**:
```markdown
Use {{ '{% if page.featured %}' }} to check if a page is featured.
```

#### Why Not `{{ '{% raw %}' }}`?

**Don't use** `{{ '{% raw %}...{% endraw %}' }}` in Bengal markdown files! Here's why:

Bengal has a **two-stage rendering process**:
1. **Stage 1**: Markdown content is preprocessed through Jinja2 (allows variables in markdown)
2. **Stage 2**: Final HTML is wrapped in templates (base.html with CSS, navigation, etc.)

`{{ '{% raw %}' }}` blocks can span between these stages, causing:
- ❌ Template rendering errors
- ❌ Broken CSS and styling
- ❌ Missing navigation/page structure
- ❌ Incomplete output

String literals work because they're evaluated in Stage 1, becoming plain text before Stage 2 runs.

#### Quick Reference

| Need to Show | Use This |
|--------------|----------|
| `{{ toc }}` | `{{ '{{' }} toc {{ '}}' }}` or `{{ '{{ toc }}' }}` |
| `{% for x in y %}` | `{{ '{% for x in y %}' }}` |
| `{{ page.title }}` | `{{ '{{ page.title }}' }}` |
| Multiple lines | Use string literal for each line |

> **Pro Tip**: This only applies to **markdown content files**. In actual `.html` template files, you can use `{{ '{% raw %}' }}` normally since they're only processed once.

### Whitespace Control

```jinja2
{# Remove whitespace before #}
{{ '{%- if condition %}' }}

{# Remove whitespace after #}
{{ '{% if condition -%}' }}

{# Remove both #}
{{ '{%- if condition -%}' }}
```

### Set Variables

```jinja2
{% set post_count = site.pages | length %}
<p>Total posts: {{ post_count }}</p>

{% set author_name = page.metadata.author or 'Anonymous' %}
<p>By {{ author_name }}</p>
```

## Debugging Templates

### Print Variables

```jinja2
{# Development only #}
<pre>{{ page | pprint }}</pre>
<pre>{{ site | pprint }}</pre>
```

### Check Variable Types

```jinja2
{% if page.date is defined %}
  {# date exists #}
{% endif %}

{% if page.tags is iterable %}
  {# tags is a list #}
{% endif %}

{% if page.metadata.author is string %}
  {# author is a string #}
{% endif %}
```

## Examples

### Blog Post List

```jinja2
<div class="blog-posts">
  {% for post in site.pages %}
    {% if post.metadata.type == 'post' %}
      <article class="post-preview">
        <h2><a href="{{ url_for(post) }}">{{ post.title }}</a></h2>
        <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
        <p>{{ post.metadata.description }}</p>
        {% if post.tags %}
          <div class="tags">
            {% for tag in post.tags %}
              <a href="/tags/{{ tag }}/" class="tag">{{ tag }}</a>
            {% endfor %}
          </div>
        {% endif %}
      </article>
    {% endif %}
  {% endfor %}
</div>
```

### Recent Posts Sidebar

```jinja2
<aside class="sidebar">
  <h3>Recent Posts</h3>
  <ul>
    {% for post in site.pages[:5] %}
      {% if post.metadata.type == 'post' %}
        <li>
          <a href="{{ url_for(post) }}">{{ post.title }}</a>
          <small>{{ post.date | dateformat('%b %d') }}</small>
        </li>
      {% endif %}
    {% endfor %}
  </ul>
</aside>
```

## Learn More

- [Custom Templates Guide](/posts/custom-templates/)
- [Understanding Themes](/posts/understanding-themes/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Configuration Reference](/docs/configuration-reference/)

## Reference

Full Jinja2 documentation: [https://jinja.palletsprojects.com/](https://jinja.palletsprojects.com/)

Bengal template source: [GitHub](https://github.com/bengal-ssg/bengal/tree/main/bengal/themes/default/templates)

