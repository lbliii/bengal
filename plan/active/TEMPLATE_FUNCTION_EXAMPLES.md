# Template Function Quick Reference

Visual before/after examples for proposed template functions.

## 1. TOC Grouping: `get_toc_grouped()`

### ❌ BEFORE (80 lines of template logic)

```jinja2
{% set current_h2 = namespace(item=none, children=[]) %}
{% for item in toc_items %}
  {% if item.level == 1 %}
    {% if current_h2.item %}
      <li class="toc-item toc-group">
        <div class="toc-group-header">
          <button class="toc-group-toggle">...</button>
          <a href="#{{ current_h2.item.id }}">{{ current_h2.item.title }}</a>
          {% if current_h2.children|length > 0 %}
            <span class="toc-count">{{ current_h2.children|length }}</span>
          {% endif %}
        </div>
        {% if current_h2.children|length > 0 %}
          <ul class="toc-subitems">
            {% for child in current_h2.children %}
              <li><a href="#{{ child.id }}">{{ child.title }}</a></li>
            {% endfor %}
          </ul>
        {% endif %}
      </li>
    {% endif %}
    {% set current_h2.item = item %}
    {% set current_h2.children = [] %}
  {% elif item.level > 1 %}
    {% set _ = current_h2.children.append(item) %}
  {% endif %}
{% endfor %}
{# Then repeat all the rendering logic again for the last group! #}
```

### ✅ AFTER (20 lines, clean separation)

```jinja2
{% for group in get_toc_grouped(page.toc_items) %}
  {% if group.is_group %}
    <li class="toc-item toc-group">
      <div class="toc-group-header">
        <button class="toc-group-toggle">...</button>
        <a href="#{{ group.header.id }}">{{ group.header.title }}</a>
        <span class="toc-count">{{ group.children|length }}</span>
      </div>
      <ul class="toc-subitems">
        {% for child in group.children %}
          <li><a href="#{{ child.id }}">{{ child.title }}</a></li>
        {% endfor %}
      </ul>
    </li>
  {% else %}
    <li><a href="#{{ group.header.id }}">{{ group.header.title }}</a></li>
  {% endif %}
{% endfor %}
```

**Reduction: 80 lines → 20 lines (75% reduction)**

---

## 2. Pagination: `get_pagination_items()`

### ❌ BEFORE (50+ lines with scattered logic)

```jinja2
{% set start_page = [current_page - 2, 1] | max %}
{% set end_page = [current_page + 2, total_pages] | min %}

{% if start_page > 1 %}
  <li><a href="{{ base_url }}">1</a></li>
  {% if start_page > 2 %}
    <li><span class="ellipsis">...</span></li>
  {% endif %}
{% endif %}

{% for page_num in range(start_page, end_page + 1) %}
  <li>
    {% if page_num == current_page %}
      <span class="active">{{ page_num }}</span>
    {% elif page_num == 1 %}
      <a href="{{ base_url }}">{{ page_num }}</a>
    {% else %}
      <a href="{{ base_url }}page/{{ page_num }}/">{{ page_num }}</a>
    {% endif %}
  </li>
{% endfor %}

{% if end_page < total_pages %}
  {% if end_page < total_pages - 1 %}
    <li><span class="ellipsis">...</span></li>
  {% endif %}
  <li><a href="{{ base_url }}page/{{ total_pages }}/">{{ total_pages }}</a></li>
{% endif %}
```

### ✅ AFTER (15 lines, any style)

```jinja2
{% set pagination = get_pagination_items(current_page, total_pages, base_url) %}

<ul class="pagination">
  {% if pagination.prev %}
    <li><a href="{{ pagination.prev.url }}">← Prev</a></li>
  {% endif %}
  
  {% for item in pagination.pages %}
    <li class="{{ 'active' if item.is_current }}">
      {% if item.is_ellipsis %}
        <span>...</span>
      {% else %}
        <a href="{{ item.url }}">{{ item.num }}</a>
      {% endif %}
    </li>
  {% endfor %}
  
  {% if pagination.next %}
    <li><a href="{{ pagination.next.url }}">Next →</a></li>
  {% endif %}
</ul>
```

**Bonus: Works with any CSS framework**

```jinja2
{# Bootstrap #}
<nav>
  <ul class="pagination">
    {% for item in pagination.pages %}
      <li class="page-item {{ 'active' if item.is_current }}">
        <a class="page-link" href="{{ item.url }}">{{ item.num }}</a>
      </li>
    {% endfor %}
  </ul>
</nav>

{# Tailwind #}
<div class="flex space-x-2">
  {% for item in pagination.pages %}
    <a href="{{ item.url }}" 
       class="px-4 py-2 {{ 'bg-blue-500 text-white' if item.is_current else 'bg-gray-200' }}">
      {{ item.num }}
    </a>
  {% endfor %}
</div>
```

**Reduction: 50+ lines → 15 lines (70% reduction)**

---

## 3. Navigation Tree: `get_nav_tree()`

### ❌ BEFORE (2 files, 127 lines total)

**File 1: docs-nav.html (73 lines)**
```jinja2
{% set root_section = page._section.root if page._section else none %}

{% if root_section %}
  {% if root_section.index_page %}
    <a href="{{ url_for(root_section.index_page) }}" 
       class="docs-nav-link {% if page.url == root_section.index_page.url %}active{% endif %}">
      {{ root_section.index_page.title }}
    </a>
  {% endif %}
  
  {% for p in root_section.regular_pages %}
    {% if p.url != root_section.index_page.url %}
      <a href="{{ url_for(p) }}" 
         class="docs-nav-link {% if page.url == p.url %}active{% endif %}">
        {{ p.title }}
      </a>
    {% endif %}
  {% endfor %}
  
  {% for section in root_section.sections %}
    {% set depth = 0 %}
    {% include 'partials/docs-nav-section.html' %}  {# Recursive! #}
  {% endfor %}
{% else %}
  {# Fallback logic... another 20 lines #}
{% endif %}
```

**File 2: docs-nav-section.html (54 lines, recursive)**
```jinja2
<div class="docs-nav-group" data-depth="{{ depth }}">
  <button class="docs-nav-group-toggle">
    {{ section.title }}
  </button>
  
  <div class="docs-nav-group-items">
    {% if section.index_page %}
      <a href="{{ url_for(section.index_page) }}" 
         class="{% if page.url == section.index_page.url %}active{% endif %}">
        {{ section.index_page.title }}
      </a>
    {% endif %}
    
    {% for p in section.regular_pages %}
      {% if p.url != section.index_page.url %}
        <a href="{{ url_for(p) }}" 
           class="{% if page.url == p.url %}active{% endif %}">
          {{ p.title }}
        </a>
      {% endif %}
    {% endfor %}
    
    {% for subsection in section.sections %}
      {% set section = subsection %}
      {% set depth = depth + 1 %}
      {% include 'partials/docs-nav-section.html' %}  {# Recursion! #}
    {% endfor %}
  </div>
</div>
```

### ✅ AFTER (1 file, 30 lines, no recursion)

```jinja2
{% set nav_items = get_nav_tree(page) %}

{# Flat rendering with indentation #}
<nav class="docs-nav">
  {% for item in nav_items %}
    <a href="{{ item.url }}" 
       class="docs-nav-link depth-{{ item.depth }}
              {{ 'active' if item.is_current }}
              {{ 'in-trail' if item.is_in_active_trail }}"
       style="padding-left: {{ item.depth * 20 }}px">
      {{ item.title }}
    </a>
  {% endfor %}
</nav>

{# OR nested rendering with macro #}
{% macro render_item(item) %}
  <li class="{{ 'active' if item.is_current }}">
    <a href="{{ item.url }}">{{ item.title }}</a>
    {% if item.children %}
      <ul>
        {% for child in item.children %}
          {{ render_item(child) }}
        {% endfor %}
      </ul>
    {% endif %}
  </li>
{% endmacro %}

<ul class="docs-nav">
  {% for item in nav_items %}
    {{ render_item(item) }}
  {% endfor %}
</ul>
```

**Reduction: 127 lines (2 files) → 30 lines (1 file) (76% reduction)**  
**Bonus: Active trail automatically calculated, no recursion needed**

---

## 4. Card Data: `get_card_data()`

### ❌ BEFORE (scattered across 85 lines)

```jinja2
<article class="article-card {% if article | has_tag('featured') %}featured-card{% endif %}">
  {# Badge logic scattered #}
  <div class="article-card-badges">
    {% if article | has_tag('featured') %}
      <span class="badge badge-featured">⭐ Featured</span>
    {% endif %}
    {% if article | has_tag('tutorial') %}
      <span class="badge badge-tutorial">📚 Tutorial</span>
    {% endif %}
    {% if article | has_tag('new') %}
      <span class="badge badge-new">✨ New</span>
    {% endif %}
  </div>
  
  <h2><a href="{{ url_for(article) }}">{{ article.title }}</a></h2>
  
  {# Meta logic scattered #}
  <div class="article-card-meta">
    {% if article.date %}
      <time datetime="{{ article.date | date_iso }}">{{ article.date | time_ago }}</time>
    {% endif %}
    {% if article.metadata.author %}
      <span class="author">{{ article.metadata.author }}</span>
    {% endif %}
    {% if article.content %}
      <span class="reading-time">{{ article.content | reading_time }} min read</span>
    {% endif %}
  </div>
  
  {# Excerpt logic with fallbacks #}
  <p class="article-card-excerpt">
    {% if article.metadata.description %}
      {{ article.metadata.description }}
    {% elif article.content %}
      {{ article.content | strip_html | excerpt(150) }}
    {% endif %}
  </p>
  
  {# More scattered logic... #}
</article>
```

### ✅ AFTER (35 lines, consistent)

```jinja2
{% set card = get_card_data(article, excerpt_length=150) %}

<article class="article-card {{ 'featured' if card.is_featured }}">
  {# All badge logic handled by function #}
  {% if card.badges %}
    <div class="article-card-badges">
      {% for badge in card.badges %}
        <span class="badge badge-{{ badge.type }}">{{ badge.icon }} {{ badge.label }}</span>
      {% endfor %}
    </div>
  {% endif %}
  
  <h2><a href="{{ card.url }}">{{ card.title }}</a></h2>
  
  {# All meta logic handled by function #}
  <div class="article-card-meta">
    {% if card.author %}<span>{{ card.author }}</span>{% endif %}
    {% if card.date_formatted %}<time>{{ card.date_formatted }}</time>{% endif %}
    {% if card.reading_time %}<span>{{ card.reading_time }} min read</span>{% endif %}
  </div>
  
  {# Smart excerpt with fallbacks handled #}
  <p>{{ card.excerpt }}</p>
  
  {# Tags if present #}
  {% if card.tags %}
    <div class="tags">
      {% for tag in card.tags %}
        <a href="/tags/{{ tag | slugify }}/">#{{ tag }}</a>
      {% endfor %}
    </div>
  {% endif %}
</article>
```

**Reduction: 85 lines → 35 lines (59% reduction)**  
**Bonus: Consistent excerpt logic across all card types**

---

## 5. Section Stats: `get_section_stats()`

### ❌ BEFORE (inconsistent across templates)

```jinja2
{# In api-reference/list.html #}
{% set module_count = (posts | length) + (subsections | length) %}
{% set all_pages = section.regular_pages_recursive %}

{# In section-navigation.html #}
{% set content_pages = subsection.regular_pages | rejectattr('url', 'equalto', subsection.index_page.url if subsection.index_page else '') | list %}

{# In another template... different logic again #}
{% set total = section.regular_pages | length %}
```

### ✅ AFTER (consistent everywhere)

```jinja2
{% set stats = get_section_stats(section) %}

<div class="section-overview">
  <div class="stat">
    <strong>{{ stats.content_pages }}</strong>
    <span>pages</span>
  </div>
  
  {% if stats.has_subsections %}
    <div class="stat">
      <strong>{{ stats.subsections }}</strong>
      <span>subsections</span>
    </div>
    <div class="stat">
      <strong>{{ stats.total_pages_recursive }}</strong>
      <span>total pages</span>
    </div>
  {% endif %}
</div>
```

**Benefit: One source of truth for all statistics**

---

## Summary: Real-World Impact

| Function | Lines Saved | Complexity Reduction | Files Consolidated |
|----------|-------------|---------------------|-------------------|
| `get_toc_grouped()` | 60 lines | 75% | 1 file |
| `get_pagination_items()` | 35 lines | 70% | 1 file |
| `get_nav_tree()` | 97 lines | 76% | 2 files → 1 |
| `get_card_data()` | 50 lines | 59% | Consistent across 5+ files |
| `get_section_stats()` | N/A | Consistency | Standardizes 8+ locations |

**Total: ~240 lines of template code eliminated**  
**Average: ~70% complexity reduction**  
**Bonus: Full styling flexibility maintained**

---

## Migration Path

All proposed functions are **non-breaking additions**:

1. **Add new functions** to `bengal/rendering/template_functions/navigation.py`
2. **Update default theme** to use new functions
3. **Users with custom themes** can:
   - Continue using old approach (works fine)
   - Gradually adopt new functions (better experience)
   - Mix and match as needed

**Zero breaking changes, 100% opt-in improvement!**

