# Bengal Default Theme - Templates

**Template Engine:** Jinja2  
**Version:** 2.0  
**Documentation:** https://jinja.palletsprojects.com/

---

## Overview

Bengal templates use Jinja2, a powerful and flexible template engine for Python. Templates combine HTML structure with template logic to generate dynamic pages.

## Template Hierarchy

### Resolution Order

Bengal searches for templates in this order:

1. **Project templates** (`your-project/templates/`)
2. **Theme templates** (`bengal/themes/default/templates/`)

This allows you to override any theme template by creating a file with the same name in your project.

### Inheritance Chain

```
base.html                 # Base layout
  ├── home.html          # Homepage (extends base)
  ├── page.html          # Generic page (extends base)
  ├── doc/single.html    # Documentation page (extends base)
  ├── blog/list.html     # Blog index (extends base)
  └── ...
```

---

## File Structure

```
templates/
├── base.html                    # Base layout (header, footer, scripts)
│
├── Core Pages
├── home.html                    # Homepage
├── page.html                    # Generic page
├── index.html                   # Site index
├── 404.html                     # Error page
│
├── Content Types
├── doc/
│   ├── list.html               # Documentation section list
│   └── single.html             # Documentation page
├── blog/
│   ├── list.html               # Blog index
│   └── single.html             # Blog post
├── post.html                   # Simple blog post
│
├── Reference Documentation
├── api-reference/
│   ├── list.html               # API reference index
│   └── single.html             # API documentation page
├── api/
│   └── single.html             # API page (legacy)
├── cli-reference/
│   ├── list.html               # CLI reference index
│   └── single.html             # CLI command page
├── cli/
│   └── single.html             # CLI page (legacy)
├── tutorial/
│   ├── list.html               # Tutorial list
│   └── single.html             # Tutorial page
│
├── Special Pages
├── archive.html                 # Archive pages
├── search.html                  # Search results page
├── tag.html                     # Single tag page
├── tags.html                    # All tags index
│
└── partials/
    ├── breadcrumbs.html         # Breadcrumb navigation
    ├── pagination.html          # Page number navigation
    ├── page-navigation.html     # Prev/Next links
    ├── toc-sidebar.html         # Table of contents
    ├── docs-nav.html            # Documentation sidebar
    ├── docs-nav-section.html    # Docs nav section (recursive)
    ├── docs-meta.html           # Documentation metadata
    ├── article-card.html        # Article preview card
    ├── tag-list.html            # Tag cloud
    ├── popular-tags.html        # Popular tags widget
    ├── random-posts.html        # Random posts widget
    ├── section-navigation.html  # Section navigation
    └── search.html              # Search input
```

---

## Core Templates

### `base.html`

**Purpose:** Base layout with header, footer, and scripts

**Blocks:**
```jinja
{% block title %}              # Page title
{% block meta %}               # Meta tags
{% block styles %}             # Extra CSS
{% block header %}             # Header content
{% block main %}               # Main content area (required)
{% block footer %}             # Footer content
{% block scripts %}            # Extra JavaScript
```

**Usage:**
```jinja
{% extends "base.html" %}

{% block title %}My Page{% endblock %}

{% block main %}
  <article class="prose">
    {{ content }}
  </article>
{% endblock %}
```

---

### `home.html`

**Purpose:** Homepage with hero section

**Features:**
- Hero section with title, subtitle, CTAs
- Featured posts/docs
- Recent posts
- Custom sections

**Variables:**
```jinja
{{ site.title }}           # Site title
{{ site.description }}     # Site description
{{ site.hero }}           # Hero configuration
{{ recent_posts }}        # Recent posts (custom)
```

**Example:**
```jinja
{% extends "base.html" %}

{% block main %}
  <section class="hero">
    <h1>{{ site.title }}</h1>
    <p>{{ site.description }}</p>
    <a href="/docs/" class="button-primary">Get Started</a>
  </section>
  
  <!-- Featured posts -->
  <section class="featured">
    {% for post in featured_posts %}
      {% include "partials/article-card.html" %}
    {% endfor %}
  </section>
{% endblock %}
```

---

### `page.html`

**Purpose:** Generic content page

**Features:**
- Simple prose content
- Optional TOC
- Page metadata
- Breadcrumbs

**Layout:**
```html
<div class="page-layout">
  <article class="prose">
    <!-- Breadcrumbs -->
    <!-- Page title -->
    <!-- Content -->
    <!-- Page navigation -->
  </article>
  
  <!-- Optional sidebar with TOC -->
</div>
```

---

## Content Type Templates

### Documentation (`doc/`)

#### `doc/single.html`

**Purpose:** Documentation page with full features

**Features:**
- Docs navigation sidebar
- Table of contents sidebar
- Breadcrumbs
- Edit on GitHub link
- Last updated info
- Prev/Next navigation

**Layout:**
```html
<div class="docs-layout">
  <aside class="docs-sidebar">
    <!-- Docs navigation -->
  </aside>
  
  <main class="docs-main">
    <article class="prose">
      <!-- Content -->
    </article>
  </main>
  
  <aside class="docs-toc">
    <!-- Table of contents -->
  </aside>
</div>
```

#### `doc/list.html`

**Purpose:** Documentation section listing

**Features:**
- Section description
- Subsection cards
- Page list

---

### Blog (`blog/`)

#### `blog/single.html`

**Purpose:** Blog post with rich features

**Features:**
- Hero image
- Author info with avatar
- Reading time
- Tags
- Social sharing buttons
- Author bio box
- Related posts
- Comments section placeholder

**Variables:**
```jinja
{{ page.title }}          # Post title
{{ page.author }}         # Author name
{{ page.date }}           # Publication date
{{ page.updated }}        # Last updated
{{ page.tags }}           # Post tags
{{ page.hero_image }}     # Hero image URL
{{ page.reading_time }}   # Estimated reading time
```

#### `blog/list.html`

**Purpose:** Blog index with post grid

**Features:**
- Featured posts section
- Post cards with images
- Pagination
- Tag cloud
- Search

---

### API Reference (`api-reference/`)

#### `api-reference/single.html`

**Purpose:** API documentation page

**Features:**
- API-specific styling (`.prose.api-content`)
- Syntax highlighting
- Parameter tables
- Examples sections
- Source code links

**Special Classes:**
```html
<article class="prose api-content">
  <!-- Enhanced API documentation styling -->
</article>
```

#### `api-reference/list.html`

**Purpose:** API reference index

**Features:**
- Module/class cards
- Statistics (modules, classes, functions)
- Search filter
- Grouped by type

---

### CLI Reference (`cli-reference/`)

#### `cli-reference/single.html`

**Purpose:** CLI command documentation

**Features:**
- Command syntax highlighting
- Arguments/options tables
- Usage examples
- Related commands

#### `cli-reference/list.html`

**Purpose:** CLI commands index

**Features:**
- Command cards
- Usage patterns
- Quick reference

---

### Tutorials (`tutorial/`)

#### `tutorial/single.html`

**Purpose:** Step-by-step tutorial page

**Features:**
- Prerequisites section
- Numbered steps
- Code examples
- Next steps section

#### `tutorial/list.html`

**Purpose:** Tutorial listing

**Features:**
- Difficulty badges (beginner/intermediate/advanced)
- Duration estimates
- Prerequisites
- Tutorial categories

---

## Partials

### `partials/breadcrumbs.html`

**Purpose:** Breadcrumb navigation

**Usage:**
```jinja
{% include "partials/breadcrumbs.html" %}
```

**Output:**
```html
<nav class="breadcrumbs" aria-label="Breadcrumb">
  <ol>
    <li><a href="/">Home</a></li>
    <li><a href="/docs/">Docs</a></li>
    <li aria-current="page">Current Page</li>
  </ol>
</nav>
```

---

### `partials/pagination.html`

**Purpose:** Page number navigation

**Usage:**
```jinja
{% include "partials/pagination.html" with context %}
```

**Variables Required:**
```python
pagination = {
    'current_page': 2,
    'total_pages': 10,
    'per_page': 10,
    'total_items': 95,
    'has_prev': True,
    'has_next': True,
    'prev_url': '/blog/page/1/',
    'next_url': '/blog/page/3/'
}
```

---

### `partials/page-navigation.html`

**Purpose:** Previous/Next page links

**Usage:**
```jinja
{% include "partials/page-navigation.html" %}
```

**Variables:**
```jinja
{{ page.prev }}   # Previous page object
{{ page.next }}   # Next page object
```

---

### `partials/toc-sidebar.html`

**Purpose:** Table of contents sidebar

**Usage:**
```jinja
{% if page.toc %}
  {% include "partials/toc-sidebar.html" %}
{% endif %}
```

**Features:**
- Nested heading hierarchy (h2, h3, h4)
- Active section highlighting
- Reading progress bar
- Collapse/expand groups
- Smooth scroll

---

### `partials/docs-nav.html`

**Purpose:** Documentation sidebar navigation

**Usage:**
```jinja
{% include "partials/docs-nav.html" %}
```

**Features:**
- Hierarchical section tree
- Active page highlighting
- Expand/collapse sections
- Recursive rendering

---

### `partials/article-card.html`

**Purpose:** Article preview card

**Usage:**
```jinja
{% for post in posts %}
  {% include "partials/article-card.html" with post=post %}
{% endfor %}
```

**Variables:**
```jinja
{{ post.title }}
{{ post.excerpt }}
{{ post.date }}
{{ post.author }}
{{ post.url }}
{{ post.hero_image }}
{{ post.tags }}
```

---

## Template Variables

### Global Variables

Available in all templates:

```jinja
{{ site }}         # Site configuration
{{ config }}       # Full configuration
{{ page }}         # Current page object
{{ pages }}        # All pages list
{{ sections }}     # All sections list
{{ menu }}         # Navigation menu
{{ request }}      # Request context (dev server)
```

### Site Object

```jinja
{{ site.title }}              # Site title
{{ site.description }}        # Site description
{{ site.baseurl }}            # Base URL
{{ site.author }}            # Default author
{{ site.language }}          # Site language (e.g., 'en')
{{ site.theme }}             # Theme name
{{ site.build_time }}        # Last build timestamp
```

### Page Object

```jinja
{{ page.title }}             # Page title
{{ page.url }}               # Page URL
{{ page.content }}           # Rendered content (HTML)
{{ page.excerpt }}           # Excerpt/summary
{{ page.date }}              # Publication date
{{ page.updated }}           # Last updated date
{{ page.author }}            # Author name
{{ page.tags }}              # List of tags
{{ page.section }}           # Section path
{{ page.draft }}             # Draft status
{{ page.weight }}            # Sort weight
{{ page.toc }}               # Table of contents
{{ page.prev }}              # Previous page
{{ page.next }}              # Next page
{{ page.word_count }}        # Word count
{{ page.reading_time }}      # Estimated reading time
{{ page.hero_image }}        # Hero image URL
{{ page.kind }}              # Page kind (page, doc, blog, etc.)
```

### Section Object

```jinja
{{ section.title }}          # Section title
{{ section.path }}           # Section path
{{ section.pages }}          # Pages in section
{{ section.subsections }}    # Child sections
{{ section.parent }}         # Parent section
```

---

## Filters

### Built-in Jinja2 Filters

```jinja
{{ text|upper }}             # UPPERCASE
{{ text|lower }}             # lowercase
{{ text|title }}             # Title Case
{{ text|capitalize }}        # Capitalize first letter
{{ text|trim }}              # Remove whitespace
{{ text|truncate(100) }}     # Truncate to 100 chars
{{ text|wordcount }}         # Count words
{{ list|length }}            # List/string length
{{ list|first }}             # First item
{{ list|last }}              # Last item
{{ list|sort }}              # Sort list
{{ list|reverse }}           # Reverse list
{{ list|join(', ') }}        # Join with separator
{{ date|default('N/A') }}    # Default value
```

### Custom Bengal Filters

```jinja
{{ date|date_format('%Y-%m-%d') }}     # Format date
{{ text|markdown }}                     # Render markdown
{{ url|url_for }}                       # Generate URL
{{ text|slugify }}                      # Create slug
{{ pages|by_date }}                     # Sort by date
{{ pages|by_weight }}                   # Sort by weight
{{ pages|limit(10) }}                   # Limit items
```

---

## Functions

### `url_for()`

Generate URLs for assets and pages:

```jinja
<link rel="stylesheet" href="{{ url_for('assets/css/style.css') }}">
<script src="{{ url_for('assets/js/main.js') }}"></script>
<a href="{{ url_for(page.url) }}">{{ page.title }}</a>
```

### `get_page()`

Get page by URL:

```jinja
{% set about_page = get_page('/about/') %}
<a href="{{ about_page.url }}">{{ about_page.title }}</a>
```

### `get_section()`

Get section by path:

```jinja
{% set docs = get_section('docs') %}
<h2>{{ docs.title }}</h2>
```

---

## Control Structures

### Conditionals

```jinja
{% if page.draft %}
  <div class="alert-warning">This is a draft</div>
{% endif %}

{% if page.hero_image %}
  <img src="{{ page.hero_image }}" alt="{{ page.title }}">
{% else %}
  <!-- No image -->
{% endif %}
```

### Loops

```jinja
{% for post in posts %}
  <article>
    <h2>{{ post.title }}</h2>
    <p>{{ post.excerpt }}</p>
  </article>
{% endfor %}

{% for tag in page.tags %}
  <a href="/tags/{{ tag|slugify }}/">{{ tag }}</a>
  {% if not loop.last %}, {% endif %}
{% endfor %}
```

### Loop Variables

```jinja
{% for item in items %}
  {{ loop.index }}       # 1, 2, 3, ...
  {{ loop.index0 }}      # 0, 1, 2, ...
  {{ loop.first }}       # True on first iteration
  {{ loop.last }}        # True on last iteration
  {{ loop.length }}      # Total iterations
{% endfor %}
```

---

## Macros

### Creating Macros

```jinja
{% macro card(title, content, url) %}
  <div class="card">
    <h3><a href="{{ url }}">{{ title }}</a></h3>
    <p>{{ content }}</p>
  </div>
{% endmacro %}
```

### Using Macros

```jinja
{% from "macros/cards.html" import card %}

{{ card(page.title, page.excerpt, page.url) }}
```

---

## Best Practices

### ✅ Do

**1. Use semantic HTML**
```jinja
<article>
  <header>
    <h1>{{ page.title }}</h1>
  </header>
  <main>
    {{ content }}
  </main>
</article>
```

**2. Provide fallbacks**
```jinja
{{ page.title|default('Untitled') }}
{{ page.author|default(site.author) }}
```

**3. Check before using**
```jinja
{% if page.toc %}
  {% include "partials/toc-sidebar.html" %}
{% endif %}
```

**4. Use descriptive variable names**
```jinja
{% set featured_posts = posts|filter(featured=True)|limit(3) %}
```

**5. Comment complex logic**
```jinja
{# Sort posts by date, newest first, limit to 10 #}
{% set recent_posts = posts|by_date|reverse|limit(10) %}
```

---

### ❌ Don't

**1. Don't use bare CSS classes**
```jinja
<!-- ❌ Bad -->
<div class="box">{{ content }}</div>

<!-- ✅ Good -->
<div class="prose has-prose-content">{{ content }}</div>
```

**2. Don't assume variables exist**
```jinja
<!-- ❌ Bad -->
<img src="{{ page.image }}">

<!-- ✅ Good -->
{% if page.image %}
  <img src="{{ page.image }}" alt="{{ page.title }}">
{% endif %}
```

**3. Don't repeat code**
```jinja
<!-- ❌ Bad -->
{% for post in posts %}
  <div class="card">
    <h3>{{ post.title }}</h3>
    <!-- 20 lines of card HTML -->
  </div>
{% endfor %}

<!-- ✅ Good -->
{% for post in posts %}
  {% include "partials/article-card.html" with post=post %}
{% endfor %}
```

**4. Don't use inline styles**
```jinja
<!-- ❌ Bad -->
<div style="color: red;">{{ content }}</div>

<!-- ✅ Good -->
<div class="alert-error">{{ content }}</div>
```

---

## Customization

### Overriding Templates

Create a template with the same path in your project:

```
your-project/
└── templates/
    └── doc/
        └── single.html     # Overrides theme template
```

### Extending Templates

```jinja
{% extends "bengal://doc/single.html" %}

{% block main %}
  <div class="custom-header">Custom content</div>
  {{ super() }}
{% endblock %}
```

### Adding New Blocks

```jinja
{# In base.html #}
{% block custom_sidebar %}
{% endblock %}

{# In your template #}
{% extends "base.html" %}

{% block custom_sidebar %}
  <aside>Custom sidebar</aside>
{% endblock %}
```

---

## Debugging

### Template Debugging

```jinja
{# Print variable #}
{{ page|pprint }}

{# Check if variable exists #}
{% if page is defined %}
  Page exists
{% endif %}

{# Show all available variables #}
{{ vars()|pprint }}

{# Raise error for debugging #}
{% if not page.title %}
  {{ raise('Page title is required') }}
{% endif %}
```

### Error Messages

```jinja
{# Custom error messages #}
{% if not page %}
  {# This will show in build output #}
  {{ log('Warning: Page not found') }}
{% endif %}
```

---

## Performance

### Optimization Tips

**1. Cache expensive operations**
```jinja
{% set sorted_posts = posts|by_date %}
{% for post in sorted_posts %}
  <!-- Use sorted_posts multiple times -->
{% endfor %}
```

**2. Limit loops**
```jinja
{% for post in posts|limit(10) %}
  <!-- Only process first 10 -->
{% endfor %}
```

**3. Use includes sparingly**
```jinja
<!-- ❌ Bad: Include in loop -->
{% for item in items %}
  {% include "partial.html" %}
{% endfor %}

<!-- ✅ Good: Loop inside partial -->
{% include "partial-list.html" with items=items %}
```

**4. Avoid nested loops**
```jinja
<!-- ❌ Bad: O(n²) complexity -->
{% for post in posts %}
  {% for tag in all_tags %}
    {% if tag in post.tags %}...{% endif %}
  {% endfor %}
{% endfor %}

<!-- ✅ Good: Pre-filter -->
{% set post_tags = post.tags %}
```

---

## Resources

### Documentation
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Bengal Template Guide](https://bengal-ssg.org/docs/templates/)
- [HTML Best Practices](https://github.com/hail2u/html-best-practices)

### Tools
- [Jinja2 Live Parser](https://cryptic-cliffs-32040.herokuapp.com/)
- [HTML Validator](https://validator.w3.org/)
- [Accessibility Checker](https://wave.webaim.org/)

---

## License

MIT License - See [LICENSE](../../../../../LICENSE) for details

