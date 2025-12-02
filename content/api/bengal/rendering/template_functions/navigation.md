
---
title: "navigation"
type: "python-module"
source_file: "bengal/bengal/rendering/template_functions/navigation.py"
line_number: 1
description: "Navigation helper functions for templates. Provides functions for breadcrumbs, navigation trails, and hierarchical navigation."
---

# navigation
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/rendering/template_functions/navigation.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[template_functions](/api/bengal/rendering/template_functions/) ›navigation

Navigation helper functions for templates.

Provides functions for breadcrumbs, navigation trails, and hierarchical navigation.

## Functions



### `register`


```python
def register(env: Environment, site: Site) -> None
```



Register navigation functions with Jinja2 environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `env` | `Environment` | - | *No description provided.* |
| `site` | `Site` | - | *No description provided.* |







**Returns**


`None`




### `get_breadcrumbs`


```python
def get_breadcrumbs(page: Page) -> list[dict[str, Any]]
```



Get breadcrumb items for a page.

Returns a list of breadcrumb items that can be styled and rendered
however you want in your template. Each item is a dictionary with:
- title: Display text for the breadcrumb
- url: URL to link to
- is_current: True if this is the current page (should not be a link)

This function handles the logic of:
- Building the ancestor chain
- Detecting section index pages (to avoid duplication)
- Determining which item is current


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to generate breadcrumbs for |







**Returns**


`list[dict[str, Any]]` - List of breadcrumb items (dicts with title, url, is_current)

Example (basic):
    {% for item in get_breadcrumbs(page) %}
      {% if item.is_current %}
        <span>{{ item.title }}</span>
      {% else %}
        <a href="{{ item.url }}">{{ item.title }}</a>
      {% endif %}
    {% endfor %}

Example (with custom styling):
    <nav aria-label="Breadcrumb">
      <ol class="breadcrumb">
        {% for item in get_breadcrumbs(page) %}
          <li class="breadcrumb-item {{ 'active' if item.is_current else '' }}">
            {% if item.is_current %}
              {{ item.title }}
            {% else %}
              <a href="{{ item.url }}">{{ item.title }}</a>
            {% endif %}
          </li>
        {% endfor %}
      </ol>
    </nav>

Example (JSON-LD structured data):
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {% for item in get_breadcrumbs(page) %}
        {
          "@type": "ListItem",
          "position": {{ loop.index }},
          "name": "{{ item.title }}",
          "item": "{{ item.url | absolute_url }}"
        }{{ "," if not loop.last else "" }}
        {% endfor %}
      ]
    }
    </script>




### `combine_track_toc_items`


```python
def combine_track_toc_items(track_items: list[str], get_page_func: Any) -> list[dict[str, Any]]
```



Combine TOC items from all track section pages into a single TOC.

Each track section becomes a level-1 TOC item, and its headings become
nested items with incremented levels.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `track_items` | `list[str]` | - | List of page paths/slugs for track items |
| `get_page_func` | `Any` | - | Function to get page by path (from template context) |







**Returns**


`list[dict[str, Any]]` - Combined list of TOC items with section headers and nested headings




### `get_toc_grouped`


```python
def get_toc_grouped(toc_items: list[dict[str, Any]], group_by_level: int = 1) -> list[dict[str, Any]]
```



Group TOC items hierarchically for collapsible sections.

This function takes flat TOC items and groups them by a specific heading
level, making it easy to create collapsible sections. For example, grouping
by level 1 (H2 headings) creates expandable sections with H3+ as children.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `toc_items` | `list[dict[str, Any]]` | - | List of TOC items from page.toc_items |
| `group_by_level` | `int` | `1` | Level to group by (1 = H2 sections, default) |







**Returns**


`list[dict[str, Any]]` - List of groups, each with:
    - header: The group header item (dict with id, title, level)
    - children: List of child items (empty list if standalone)
    - is_group: True if has children, False for standalone items

Example (basic):
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

Example (with custom styling):
    {% for group in get_toc_grouped(page.toc_items) %}
      <div class="toc-group">
        <div class="toc-header">
          <button class="toggle" aria-expanded="false">▶</button>
          <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
        </div>
        {% if group.children %}
          <ul class="toc-children">
            {% for child in group.children %}
              <li class="level-{{ child.level }}">
                <a href="#{{ child.id }}">{{ child.title }}</a>
              </li>
            {% endfor %}
          </ul>
        {% endif %}
      </div>
    {% endfor %}




### `get_pagination_items`


```python
def get_pagination_items(current_page: int, total_pages: int, base_url: str, window: int = 2) -> dict[str, Any]
```



Generate pagination data structure with URLs and ellipsis markers.

This function handles all pagination logic including:
- Page number range calculation with window
- Ellipsis placement (represented as None)
- URL generation (special case for page 1)
- Previous/next links


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_page` | `int` | - | Current page number (1-indexed) |
| `total_pages` | `int` | - | Total number of pages |
| `base_url` | `str` | - | Base URL for pagination (e.g., '/blog/') |
| `window` | `int` | `2` | Number of pages to show around current (default: 2) |







**Returns**


`dict[str, Any]` - Dictionary with:
    - pages: List of page items (num, url, is_current, is_ellipsis)
    - prev: Previous page info (num, url) or None
    - next: Next page info (num, url) or None
    - first: First page info (num, url)
    - last: Last page info (num, url)

Example (basic):
    {% set pagination = get_pagination_items(current_page, total_pages, base_url) %}

    <nav class="pagination">
      {% if pagination.prev %}
        <a href="{{ pagination.prev.url }}">← Prev</a>
      {% endif %}

      {% for item in pagination.pages %}
        {% if item.is_ellipsis %}
          <span>...</span>
        {% elif item.is_current %}
          <strong>{{ item.num }}</strong>
        {% else %}
          <a href="{{ item.url }}">{{ item.num }}</a>
        {% endif %}
      {% endfor %}

      {% if pagination.next %}
        <a href="{{ pagination.next.url }}">Next →</a>
      {% endif %}
    </nav>

Example (Bootstrap):
    {% set p = get_pagination_items(current_page, total_pages, base_url) %}

    <ul class="pagination">
      {% if p.prev %}
        <li class="page-item">
          <a class="page-link" href="{{ p.prev.url }}">Previous</a>
        </li>
      {% endif %}

      {% for item in p.pages %}
        <li class="page-item {{ 'active' if item.is_current }}">
          {% if item.is_ellipsis %}
            <span class="page-link">...</span>
          {% else %}
            <a class="page-link" href="{{ item.url }}">{{ item.num }}</a>
          {% endif %}
        </li>
      {% endfor %}

      {% if p.next %}
        <li class="page-item">
          <a class="page-link" href="{{ p.next.url }}">Next</a>
        </li>
      {% endif %}
    </ul>




### `get_nav_tree`


```python
def get_nav_tree(page: Page, root_section: Any | None = None, mark_active_trail: bool = True) -> list[dict[str, Any]]
```



Build navigation tree with active trail marking.

This function builds a hierarchical navigation tree from sections and pages,
automatically detecting which items are in the active trail (path to current
page). Returns a flat list with depth information, making it easy to render
with indentation or as nested structures.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Current page for active trail detection |
| `root_section` | `Any \| None` | - | Section to build tree from (defaults to page's root section) |
| `mark_active_trail` | `bool` | `True` | Whether to mark active trail (default: True) |







**Returns**


`list[dict[str, Any]]` - List of navigation items, each with:
    - title: Display title
    - url: Link URL
    - is_current: True if this is the current page
    - is_in_active_trail: True if in path to current page
    - is_section: True if this is a section (vs regular page)
    - depth: Nesting level (0 = top level)
    - children: List of child items (for nested rendering)
    - has_children: Boolean shortcut

Example (flat rendering with indentation):
    {% for item in get_nav_tree(page) %}
      <a href="{{ item.url }}"
         class="nav-link depth-{{ item.depth }}
                {{ 'active' if item.is_current }}
                {{ 'in-trail' if item.is_in_active_trail }}"
         style="padding-left: {{ item.depth * 20 }}px">
        {{ item.title }}
        {% if item.has_children %}
          <span class="has-children">▶</span>
        {% endif %}
      </a>
    {% endfor %}

Example (nested rendering with macro):
    {% macro render_nav_item(item) %}
      <li class="{{ 'active' if item.is_current }}
                 {{ 'in-trail' if item.is_in_active_trail }}">
        <a href="{{ item.url }}">
          {% if item.is_section %}📁{% endif %}
          {{ item.title }}
        </a>
        {% if item.children %}
          <ul class="nav-children">
            {% for child in item.children %}
              {{ render_nav_item(child) }}
            {% endfor %}
          </ul>
        {% endif %}
      </li>
    {% endmacro %}

    <ul class="nav-tree">
      {% for item in get_nav_tree(page) %}
        {{ render_nav_item(item) }}
      {% endfor %}
    </ul>




### `get_auto_nav`


```python
def get_auto_nav(site: Site) -> list[dict[str, Any]]
```



Auto-discover hierarchical navigation from site sections.

This function provides automatic navigation discovery similar to how
sidebars and TOC work. It discovers sections and creates nav items
automatically, respecting the section hierarchy.

Features:
- Auto-discovers all sections in content/ (not just top-level)
- Builds hierarchical menu based on section.parent relationships
- Respects section weight for ordering
- Respects 'menu: false' in section _index.md to hide from nav
- Returns empty list if manual [[menu.main]] config exists (hybrid mode)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | *No description provided.* |







**Returns**


`list[dict[str, Any]]` - List of navigation items with name, url, weight, parent (for hierarchy)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{# In nav template #}
    {% set auto_items = get_auto_nav() %}
    {% if auto_items %}
      {% for item in auto_items %}
        <a href="{{ item.url }}">{{ item.name }}</a>
      {% endfor %}
    {% endif %}

Section _index.md frontmatter can control visibility:
    ---
    title: Secret Section
    menu: false  # Won't appear in auto-nav
    weight: 10   # Controls ordering
    ---
```



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/template_functions/navigation.py`*

