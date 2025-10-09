# Template Functions Guide

Bengal provides 80+ template functions for use in Jinja2 templates. This guide explains how to use them and the patterns they follow.

## Quick Start

Template functions come in two flavors:

### Filters (Transform Values)
```jinja2
{{ "hello world" | upper }}           → "HELLO WORLD"
{{ post.content | reading_time }}     → 5 (minutes)
{{ text | truncate(100) }}            → "First 100 chars..."
```

### Global Functions (Compute or Build Data)
```jinja2
{{ url_for(page) }}                   → "/docs/getting-started/"
{{ get_breadcrumbs(page) }}           → [{'title': 'Home', ...}, ...]
```

---

## The Data Provider Pattern ⭐

Some template functions return **structured data** (lists of dicts) designed for iteration. These move complex logic from templates to Python while giving you full control over HTML and styling.

### Pattern Recognition

Functions that return structured data typically:
- Start with `get_*` (convention, not required)
- Return lists of dictionaries with consistent keys
- Handle complex logic (grouping, filtering, calculations)
- Let you control presentation completely

### Example: Breadcrumbs

**❌ Without data provider (complex template logic):**
```jinja2
{% if page.ancestors %}
  {# Complex logic to detect section indexes, build URLs, etc. #}
  {% for ancestor in page.ancestors | reverse %}
    {# Check if this is a section index page #}
    {# Build URLs with fallbacks #}
    {# Determine which item is current #}
  {% endfor %}
{% endif %}
```

**✅ With data provider (clean separation):**
```jinja2
{% for item in get_breadcrumbs(page) %}
  {% if item.is_current %}
    <span>{{ item.title }}</span>
  {% else %}
    <a href="{{ item.url }}">{{ item.title }}</a>
  {% endif %}
{% endfor %}
```

The function handles all the complex logic. You just iterate and style.

### Key Benefits

1. **Logic in Python** - Testable, maintainable, debuggable
2. **Data in Templates** - Clean, predictable structures
3. **Full Style Control** - Works with any CSS framework
4. **Consistent APIs** - Predictable dict keys and patterns

---

## Data Provider Functions

These functions build structured data from your content:

### Navigation

#### `get_breadcrumbs(page)`

Returns list of breadcrumb items with automatic section index detection.

**Returns:** `List[Dict]`
```python
[
    {'title': 'Home', 'url': '/', 'is_current': False},
    {'title': 'Docs', 'url': '/docs/', 'is_current': False},
    {'title': 'Getting Started', 'url': '/docs/getting-started/', 'is_current': True},
]
```

**Usage:**
```jinja2
{# Basic #}
{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.url }}">{{ item.title }}</a> /
{% endfor %}

{# Bootstrap #}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    {% for item in get_breadcrumbs(page) %}
      <li class="breadcrumb-item {{ 'active' if item.is_current }}">
        {% if item.is_current %}
          {{ item.title }}
        {% else %}
          <a href="{{ item.url }}">{{ item.title }}</a>
        {% endif %}
      </li>
    {% endfor %}
  </ol>
</nav>

{# Tailwind #}
<nav class="flex">
  {% for item in get_breadcrumbs(page) %}
    <a href="{{ item.url }}" class="text-gray-600 hover:text-gray-900">
      {{ item.title }}
    </a>
    {% if not loop.last %}<span class="mx-2">/</span>{% endif %}
  {% endfor %}
</nav>
```

**See also:** [Complete Breadcrumbs Guide](BREADCRUMBS.md)

---

#### `get_toc_grouped(toc_items, group_by_level=1)`

Groups table of contents items hierarchically for collapsible sections.

**Parameters:**
- `toc_items`: List from `page.toc_items`
- `group_by_level`: Level to group by (1 = H2, default)

**Returns:** `List[Dict]`
```python
[
    {
        'header': {'id': 'intro', 'title': 'Introduction', 'level': 1},
        'children': [
            {'id': 'overview', 'title': 'Overview', 'level': 2},
            {'id': 'features', 'title': 'Features', 'level': 2}
        ],
        'is_group': True  # Has children
    },
    {
        'header': {'id': 'standalone', 'title': 'Standalone', 'level': 1},
        'children': [],
        'is_group': False  # No children
    }
]
```

**Usage:**
```jinja2
{# Basic collapsible TOC #}
{% for group in get_toc_grouped(page.toc_items) %}
  {% if group.is_group %}
    <details>
      <summary>
        <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
        <span class="count">{{ group.children|length }}</span>
      </summary>
      <ul>
        {% for child in group.children %}
          <li><a href="#{{ child.id }}">{{ child.title }}</a></li>
        {% endfor %}
      </ul>
    </details>
  {% else %}
    <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
  {% endif %}
{% endfor %}

{# With custom styling #}
{% for group in get_toc_grouped(page.toc_items) %}
  <div class="toc-section">
    <button class="toc-toggle" aria-expanded="false">
      {{ '▶' if group.is_group else '' }}
    </button>
    <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
    {% if group.children %}
      <ul class="toc-children">
        {% for child in group.children %}
          <li><a href="#{{ child.id }}">{{ child.title }}</a></li>
        {% endfor %}
      </ul>
    {% endif %}
  </div>
{% endfor %}
```

**Replaces:** 80+ lines of complex template logic with namespace hacks

---

#### `get_pagination_items(current_page, total_pages, base_url, window=2)`

Generates complete pagination data with URLs and ellipsis markers.

**Parameters:**
- `current_page`: Current page number (1-indexed)
- `total_pages`: Total number of pages
- `base_url`: Base URL (e.g., `/blog/`)
- `window`: Pages to show around current (default: 2)

**Returns:** `Dict`
```python
{
    'pages': [
        {'num': 1, 'url': '/blog/', 'is_current': False, 'is_ellipsis': False},
        {'num': None, 'url': None, 'is_current': False, 'is_ellipsis': True},  # ...
        {'num': 5, 'url': '/blog/page/5/', 'is_current': True, 'is_ellipsis': False},
        ...
    ],
    'prev': {'num': 4, 'url': '/blog/page/4/'},
    'next': {'num': 6, 'url': '/blog/page/6/'},
    'first': {'num': 1, 'url': '/blog/'},
    'last': {'num': 10, 'url': '/blog/page/10/'}
}
```

**Usage:**
```jinja2
{# Basic pagination #}
{% set p = get_pagination_items(current_page, total_pages, base_url) %}

<nav class="pagination">
  {% if p.prev %}<a href="{{ p.prev.url }}">← Prev</a>{% endif %}
  
  {% for item in p.pages %}
    {% if item.is_ellipsis %}
      <span>...</span>
    {% elif item.is_current %}
      <strong>{{ item.num }}</strong>
    {% else %}
      <a href="{{ item.url }}">{{ item.num }}</a>
    {% endif %}
  {% endfor %}
  
  {% if p.next %}<a href="{{ p.next.url }}">Next →</a>{% endif %}
</nav>

{# Bootstrap pagination #}
{% set p = get_pagination_items(current_page, total_pages, base_url) %}

<ul class="pagination">
  {% for item in p.pages %}
    <li class="page-item {{ 'active' if item.is_current }}">
      {% if item.is_ellipsis %}
        <span class="page-link">...</span>
      {% else %}
        <a class="page-link" href="{{ item.url }}">{{ item.num }}</a>
      {% endif %}
    </li>
  {% endfor %}
</ul>

{# Tailwind pagination #}
<div class="flex gap-2">
  {% for item in p.pages %}
    {% if item.is_ellipsis %}
      <span class="px-3 py-2">...</span>
    {% else %}
      <a href="{{ item.url }}" 
         class="px-4 py-2 rounded 
                {{ 'bg-blue-500 text-white' if item.is_current else 'bg-gray-200' }}">
        {{ item.num }}
      </a>
    {% endif %}
  {% endfor %}
</div>
```

**Replaces:** 50+ lines of complex range calculation and URL logic

---

#### `get_nav_tree(page, root_section=None, mark_active_trail=True)`

Builds hierarchical navigation tree with automatic active trail detection.

**Parameters:**
- `page`: Current page for active trail
- `root_section`: Section to build from (auto-detected if None)
- `mark_active_trail`: Mark active path (default: True)

**Returns:** `List[Dict]`
```python
[
    {
        'title': 'Getting Started',
        'url': '/docs/getting-started/',
        'is_current': False,
        'is_in_active_trail': True,
        'is_section': False,
        'depth': 0,
        'children': [],
        'has_children': False
    },
    {
        'title': 'Advanced',
        'url': '/docs/advanced/',
        'is_current': False,
        'is_in_active_trail': True,
        'is_section': True,
        'depth': 0,
        'children': [
            {
                'title': 'Caching',
                'url': '/docs/advanced/caching/',
                'is_current': True,
                'depth': 1,
                ...
            }
        ],
        'has_children': True
    }
]
```

**Usage:**
```jinja2
{# Flat navigation with indentation #}
{% for item in get_nav_tree(page) %}
  <a href="{{ item.url }}" 
     class="nav-link {{ 'active' if item.is_current }}
                      {{ 'in-trail' if item.is_in_active_trail }}"
     style="padding-left: {{ item.depth * 20 }}px">
    {{ '📁' if item.is_section else '📄' }}
    {{ item.title }}
  </a>
{% endfor %}

{# Nested navigation with macro #}
{% macro render_nav(item) %}
  <li class="{{ 'active' if item.is_current }}">
    <a href="{{ item.url }}">{{ item.title }}</a>
    {% if item.children %}
      <ul>
        {% for child in item.children %}
          {{ render_nav(child) }}
        {% endfor %}
      </ul>
    {% endif %}
  </li>
{% endmacro %}

<ul class="nav-tree">
  {% for item in get_nav_tree(page) %}
    {{ render_nav(item) }}
  {% endfor %}
</ul>

{# Collapsible sections #}
{% for item in get_nav_tree(page) %}
  <div class="nav-item depth-{{ item.depth }}">
    {% if item.has_children %}
      <button class="nav-toggle" 
              aria-expanded="{{ 'true' if item.is_in_active_trail else 'false' }}">
        ▶
      </button>
    {% endif %}
    <a href="{{ item.url }}" 
       class="{{ 'active' if item.is_current }}">
      {{ item.title }}
    </a>
    {% if item.children %}
      <div class="nav-children" 
           hidden="{{ 'false' if item.is_in_active_trail else 'true' }}">
        {# Render children recursively #}
      </div>
    {% endif %}
  </div>
{% endfor %}
```

**Replaces:** 127 lines across 2 files with recursive template includes

---

## All Template Functions

### Strings

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `truncate` | Filter | Truncate text | `{{ text \| truncate(100) }}` |
| `truncatewords` | Filter | Truncate by words | `{{ text \| truncatewords(20) }}` |
| `slugify` | Filter | Convert to URL slug | `{{ "Hello World" \| slugify }}` → `hello-world` |
| `markdownify` | Filter | Render Markdown | `{{ text \| markdownify }}` |
| `strip_html` | Filter | Remove HTML tags | `{{ content \| strip_html }}` |
| `reading_time` | Filter | Calculate reading time | `{{ content \| reading_time }}` → `5` |
| `excerpt` | Filter | Extract excerpt | `{{ content \| excerpt(150) }}` |
| `pluralize` | Filter | Pluralize word | `{{ count }} item{{ count \| pluralize }}` |
| `camelize` | Filter | Convert to camelCase | `{{ "hello_world" \| camelize }}` |
| `pascalize` | Filter | Convert to PascalCase | `{{ "hello_world" \| pascalize }}` |

### Collections

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `where` | Filter | Filter by key/value | `{{ posts \| where('featured', true) }}` |
| `limit` | Filter | Limit items | `{{ posts \| limit(5) }}` |
| `sample` | Filter | Random sample | `{{ posts \| sample(3) }}` |
| `group_by` | Filter | Group by key | `{{ posts \| group_by('category') }}` |
| `sort_by` | Filter | Sort by key | `{{ posts \| sort_by('date') }}` |
| `unique` | Filter | Remove duplicates | `{{ tags \| unique }}` |

### Dates

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `dateformat` | Filter | Format date | `{{ date \| dateformat('%Y-%m-%d') }}` |
| `time_ago` | Filter | Relative time | `{{ date \| time_ago }}` → "2 days ago" |
| `date_iso` | Filter | ISO 8601 format | `{{ date \| date_iso }}` |

### URLs

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `url_for` | Function | Generate page URL | `{{ url_for(page) }}` |
| `absolute_url` | Filter | Make URL absolute | `{{ url \| absolute_url }}` |
| `url_encode` | Filter | URL encode | `{{ query \| url_encode }}` |

### Content

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `html_escape` | Filter | Escape HTML | `{{ text \| html_escape }}` |
| `html_unescape` | Filter | Unescape HTML | `{{ text \| html_unescape }}` |
| `nl2br` | Filter | Newlines to `<br>` | `{{ text \| nl2br }}` |
| `smartquotes` | Filter | Smart quotes | `{{ text \| smartquotes }}` |
| `emojify` | Filter | Convert emoji codes | `{{ ":smile:" \| emojify }}` → 😊 |

### Images

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `image_url` | Filter | Generate image URL | `{{ path \| image_url(width=800) }}` |
| `image_srcset` | Filter | Generate srcset | `{{ img \| image_srcset([400, 800]) }}` |
| `image_alt` | Filter | Extract alt text | `{{ img \| image_alt }}` |

### Data

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `jsonify` | Filter | Convert to JSON | `{{ data \| jsonify }}` |
| `get_data` | Function | Load data file | `{{ get_data('authors.yaml') }}` |
| `get_nested` | Filter | Get nested value | `{{ obj \| get_nested('a.b.c') }}` |

### Pagination

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `paginate` | Filter | Paginate items | `{{ posts \| paginate(10, page) }}` |
| `page_url` | Function | Pagination URL | `{{ page_url('/blog/', 2) }}` |
| `page_range` | Function | Page range | `{{ page_range(5, 20) }}` |

### Taxonomies

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `has_tag` | Filter | Check for tag | `{{ page \| has_tag('featured') }}` |
| `related_posts` | Filter | Find related pages | `{{ page \| related_posts(limit=5) }}` |
| `taxonomy_cloud` | Function | Tag cloud data | `{{ taxonomy_cloud('tags') }}` |

### Debug

| Function | Type | Description | Example |
|----------|------|-------------|---------|
| `debug` | Filter | Debug output | `{{ page \| debug }}` |
| `typeof` | Filter | Get type | `{{ value \| typeof }}` |

---

## Writing Custom Functions

You can add your own template functions:

```python
# my_site/template_functions.py
def my_custom_filter(text: str) -> str:
    """My custom text transformation."""
    return text.upper() + "!"

def register(env, site):
    """Register with Jinja2."""
    env.filters['my_filter'] = my_custom_filter
```

Then in your config:
```toml
[build]
custom_template_functions = "my_site.template_functions"
```

---

## Best Practices

### 1. Use Data Providers for Complex Logic

**Don't do this:**
```jinja2
{# 50 lines of complex grouping, filtering, calculation logic #}
```

**Do this:**
```python
# In template_functions/navigation.py
def get_my_data(page):
    # Complex logic here
    return structured_data
```

```jinja2
{# In template #}
{% for item in get_my_data(page) %}
  {# Clean iteration #}
{% endfor %}
```

### 2. Return Predictable Structures

Good - consistent dict keys:
```python
[
    {'title': '...', 'url': '...', 'is_current': bool},
    {'title': '...', 'url': '...', 'is_current': bool},
]
```

Bad - inconsistent structure:
```python
[
    {'name': '...', 'link': '...'},
    {'title': '...', 'url': '...', 'active': True},
]
```

### 3. Use Boolean Flags for State

Use `is_*`, `has_*` prefixes for clarity:
```python
{
    'is_current': True,
    'is_featured': False,
    'has_children': True,
}
```

### 4. Pre-compute Values

Don't make templates do work:
```python
# Good - pre-formatted
{'date_formatted': 'January 1, 2025', 'reading_time': 5}

# Bad - requires template logic
{'date': datetime_object}  # Template must format
```

---

## Related Guides

- [Breadcrumbs Guide](BREADCRUMBS.md) - Complete breadcrumb documentation
- [Templates Overview](../TEMPLATES.md) - Template system architecture
- [Content Types](CONTENT_TYPES.md) - Understanding pages and sections


