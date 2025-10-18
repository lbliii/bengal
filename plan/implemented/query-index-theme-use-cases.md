# Query Index Use Cases for Default Theme & Bengal Docs Site

**Status:** Analysis & Recommendations  
**Date:** 2025-10-18  
**Context:** Practical applications of the new query index system

---

## Current Patterns That Can Be Optimized

### 1. **Home Template - Recent Posts** (line 91)

**Current Code:**
```jinja2
{% set recent = pages | where('section', 'blog') | sort_by('date', reverse=true) | first(3) %}
```

**Problem:** O(n) scan through ALL pages to find blog posts

**With Indexes:**
```jinja2
{% set blog_posts = site.indexes.section.get('blog') | resolve_pages %}
{% set recent = blog_posts | sort_by('date', reverse=true) | limit(3) %}
```

**Benefit:** O(1) lookup + O(k log k) sort where k=blog posts only

---

### 2. **Docs Navigation - Top-Level Pages** (line 82)

**Current Code:**
```jinja2
{% set top_pages = site.pages | selectattr('_section', 'none') | rejectattr('metadata._generated', 'defined') | list %}
```

**Problem:** Filters through all pages

**With Indexes:**
```jinja2
{# Could add a RootPagesIndex #}
{% set top_pages = site.indexes.root_pages.get('no_section') | resolve_pages %}
```

---

### 3. **Blog List - Featured Posts** (line 51)

**Current Code:**
```jinja2
{% set featured_posts = posts | where('featured', true) | limit(3) %}
```

**Already Optimal!** This filters an already-scoped `posts` list (from section), not all site.pages.

**But could be even better with FeaturedIndex:**
```jinja2
{# Get all featured posts from any section #}
{% set all_featured = site.indexes.featured.get('true') | resolve_pages %}
```

---

## New Opportunities for Bengal Docs Site

### 4. **Author Archive Pages**

For the docs site, multiple authors contribute. Create author pages:

**Structure:**
```
site/content/
  authors/
    jane-smith.md    # Author bio + automatically shows their posts
    bob-jones.md
```

**Template: `templates/author.html`**
```jinja2
{% extends "base.html" %}

{% block content %}
<div class="author-page">
  <header class="author-header">
    {% if page.metadata.avatar %}
    <img src="{{ page.metadata.avatar }}" alt="{{ page.title }}" class="author-avatar">
    {% endif %}
    <h1>{{ page.title }}</h1>
    {% if page.metadata.bio %}
    <p class="author-bio">{{ page.metadata.bio }}</p>
    {% endif %}
  </header>

  {# O(1) lookup of all posts by this author #}
  {% set author_posts = site.indexes.author.get(page.title) | resolve_pages %}

  <section class="author-posts">
    <h2>Posts by {{ page.title }} ({{ author_posts | length }})</h2>

    {% for post in author_posts | sort_by('date', reverse=true) %}
      <article class="post-card">
        <h3><a href="{{ url_for(post) }}">{{ post.title }}</a></h3>
        <time>{{ post.date | dateformat('%B %d, %Y') }}</time>
        {% if post.metadata.description %}
          <p>{{ post.metadata.description }}</p>
        {% endif %}
      </article>
    {% endfor %}
  </section>

  {# Show contribution stats #}
  <aside class="author-stats">
    <h3>Contribution Stats</h3>
    <ul>
      <li><strong>{{ author_posts | length }}</strong> posts</li>
      <li><strong>{{ author_posts | sum(attribute='content') | wordcount }}</strong> words written</li>
      {% set years = author_posts | map(attribute='date.year') | unique | sort %}
      <li>Active since <strong>{{ years | first }}</strong></li>
    </ul>
  </aside>
</div>
{% endblock %}
```

---

### 5. **Docs Site: "What's New" Page**

Show recent additions across ALL sections:

**Template: `content/whats-new.md`**
```yaml
---
title: What's New
type: page
---
```

**Template enhancement:**
```jinja2
{# Last 30 days #}
{% set thirty_days_ago = now() | add_days(-30) %}

<section class="whats-new">
  <h2>New Documentation (Last 30 Days)</h2>

  {# Get docs by category #}
  {% set guides = site.indexes.category.get('guide') | resolve_pages %}
  {% set tutorials = site.indexes.category.get('tutorial') | resolve_pages %}
  {% set references = site.indexes.category.get('reference') | resolve_pages %}

  {# Combine and filter by date #}
  {% set all_docs = (guides + tutorials + references)
     | where_gt('date', thirty_days_ago)
     | sort_by('date', reverse=true) %}

  {% for doc in all_docs %}
    <article>
      <span class="badge">{{ doc.metadata.category }}</span>
      <h3><a href="{{ url_for(doc) }}">{{ doc.title }}</a></h3>
      <time>{{ doc.date | time_ago }}</time>
    </article>
  {% endfor %}
</section>
```

---

### 6. **Year/Month Archives**

**Template: `templates/archive-year.html`**
```jinja2
{% extends "base.html" %}

{% block content %}
<div class="year-archive">
  <h1>{{ year }} Archive</h1>

  {# O(1) lookup for the year #}
  {% set year_posts = site.indexes.date_range.get(year) | resolve_pages %}

  <p>{{ year_posts | length }} posts in {{ year }}</p>

  {# Group by month #}
  {% for month_num in range(1, 13) %}
    {% set month_key = year ~ '-' ~ '%02d' | format(month_num) %}
    {% set month_posts = site.indexes.date_range.get(month_key) | resolve_pages %}

    {% if month_posts %}
      <section class="month-group">
        <h2>{{ month_key | strftime('%B %Y') }}</h2>
        <ul class="post-list">
          {% for post in month_posts | sort_by('date', reverse=true) %}
            <li>
              <time>{{ post.date | dateformat('%d') }}</time>
              <a href="{{ url_for(post) }}">{{ post.title }}</a>
            </li>
          {% endfor %}
        </ul>
      </section>
    {% endif %}
  {% endfor %}
</div>
{% endblock %}
```

**Sidebar Widget:**
```jinja2
<aside class="archive-widget">
  <h3>Browse by Date</h3>
  <ul class="archive-list">
    {# Get all year keys and sort #}
    {% for year in site.indexes.date_range.keys()
       | select('match', '^\\d{4}$')  {# Only 4-digit years #}
       | sort(reverse=true) %}

      {% set count = site.indexes.date_range.get(year) | length %}
      <li>
        <a href="/archive/{{ year }}/">{{ year }}</a>
        <span class="count">({{ count }})</span>
      </li>
    {% endfor %}
  </ul>
</aside>
```

---

### 7. **Docs Site: Category Browser**

**Template: `templates/category-browser.html`**
```jinja2
<div class="category-browser">
  <h2>Browse Documentation</h2>

  <div class="category-grid">
    {# Get all categories with counts #}
    {% for category in site.indexes.category.keys() | sort %}
      {% set category_pages = site.indexes.category.get(category) | resolve_pages %}

      <div class="category-card">
        <h3>
          <a href="/docs/category/{{ category }}/">
            {{ category | title }}
          </a>
        </h3>
        <p class="count">{{ category_pages | length }} pages</p>

        {# Show 3 most recent #}
        <ul class="recent-in-category">
          {% for page in category_pages | sort_by('date', reverse=true) | limit(3) %}
            <li><a href="{{ url_for(page) }}">{{ page.title }}</a></li>
          {% endfor %}
        </ul>
      </div>
    {% endfor %}
  </div>
</div>
```

---

### 8. **API Docs: Group by Module**

For Bengal's autodoc-generated API docs:

**Custom Index:**
```python
# site/indexes/module_index.py
from bengal.cache.query_index import QueryIndex

class ModuleIndex(QueryIndex):
    """Index API pages by Python module."""

    def extract_keys(self, page):
        # Check if this is an API doc page
        if 'api' in str(page.source_path):
            module = page.metadata.get('module')
            if module:
                # Extract top-level module
                top_module = module.split('.')[0]
                return [
                    (module, {'type': 'full'}),
                    (top_module, {'type': 'top_level'}),
                ]
        return []
```

**Usage in template:**
```jinja2
{# API docs navigation #}
<nav class="api-nav">
  <h3>API Modules</h3>
  {% for module in site.indexes.module.keys() | sort %}
    {% set module_pages = site.indexes.module.get(module) | resolve_pages %}
    <details>
      <summary>
        {{ module }} <span class="count">({{ module_pages | length }})</span>
      </summary>
      <ul>
        {% for page in module_pages | sort_by('title') %}
          <li><a href="{{ url_for(page) }}">{{ page.title }}</a></li>
        {% endfor %}
      </ul>
    </details>
  {% endfor %}
</nav>
```

---

### 9. **Changelog Grouping**

For Bengal's changelog:

**Custom Index:**
```python
class VersionIndex(QueryIndex):
    """Index changelog entries by version."""

    def extract_keys(self, page):
        if page.metadata.get('type') == 'changelog':
            version = page.metadata.get('version', 'unreleased')
            return [(version, {})]
        return []
```

**Template:**
```jinja2
<div class="changelog">
  <h1>Changelog</h1>

  {# Get all versions in reverse order #}
  {% for version in site.indexes.version.keys() | sort(reverse=true) %}
    {% set changes = site.indexes.version.get(version) | resolve_pages %}

    <section class="version-block">
      <h2>Version {{ version }}</h2>
      <ul>
        {% for change in changes | sort_by('date', reverse=true) %}
          <li>
            <span class="change-type">{{ change.metadata.type }}</span>
            {{ change.title }}
          </li>
        {% endfor %}
      </ul>
    </section>
  {% endfor %}
</div>
```

---

### 10. **Tutorial Series Navigation**

For multi-part tutorials:

**Custom Index:**
```python
class SeriesIndex(QueryIndex):
    """Index pages by tutorial series."""

    def extract_keys(self, page):
        series = page.metadata.get('series')
        if series:
            order = page.metadata.get('series_order', 0)
            return [(series, {'order': order, 'title': page.title})]
        return []
```

**In tutorial template:**
```jinja2
{% if page.metadata.series %}
  {% set series_name = page.metadata.series %}
  {% set series_pages = site.indexes.series.get(series_name) | resolve_pages %}
  {% set series_pages = series_pages | sort_by('metadata.series_order') %}

  <aside class="series-nav">
    <h3>{{ series_name | title }} Series</h3>
    <ol>
      {% for part in series_pages %}
        <li {% if part.url == page.url %}class="current"{% endif %}>
          <a href="{{ url_for(part) }}">{{ part.title }}</a>
        </li>
      {% endfor %}
    </ol>

    {# Previous/Next navigation #}
    {% set current_idx = series_pages.index(page) %}
    <nav class="series-prevnext">
      {% if current_idx > 0 %}
        {% set prev = series_pages[current_idx - 1] %}
        <a href="{{ url_for(prev) }}" class="prev">← {{ prev.title }}</a>
      {% endif %}

      {% if current_idx < series_pages | length - 1 %}
        {% set next = series_pages[current_idx + 1] %}
        <a href="{{ url_for(next) }}" class="next">{{ next.title }} →</a>
      {% endif %}
    </nav>
  </aside>
{% endif %}
```

---

### 11. **Docs Site: Search Filters**

Enhance the search page with category filters:

**Template: `templates/search.html`**
```jinja2
<div class="search-page">
  <div class="search-filters">
    <h3>Filter by Category</h3>
    <ul>
      <li>
        <button data-filter="all" class="active">
          All Results
        </button>
      </li>
      {% for category in site.indexes.category.keys() | sort %}
        {% set count = site.indexes.category.get(category) | length %}
        <li>
          <button data-filter="{{ category }}">
            {{ category | title }} ({{ count }})
          </button>
        </li>
      {% endfor %}
    </ul>
  </div>

  <div class="search-results" id="search-results">
    {# JavaScript will populate this #}
  </div>
</div>

<script>
// Pass category mappings to JavaScript for client-side filtering
const categoryIndex = {
  {% for category in site.indexes.category.keys() %}
    '{{ category }}': {{ site.indexes.category.get(category) | map(attribute='url') | jsonify }},
  {% endfor %}
};
</script>
```

---

### 12. **Related Docs (Cross-Reference)**

Instead of just related posts by tags, show related docs by category:

**In doc template:**
```jinja2
<aside class="related-docs">
  <h3>Related Documentation</h3>

  {# Get docs in same category #}
  {% set category = page.metadata.category %}
  {% if category %}
    {% set related = site.indexes.category.get(category) | resolve_pages %}
    {% set related = related | reject('eq', page) | limit(5) %}

    <ul>
      {% for doc in related %}
        <li><a href="{{ url_for(doc) }}">{{ doc.title }}</a></li>
      {% endfor %}
    </ul>
  {% endif %}

  {# Also show docs by same author #}
  {% set author = page.metadata.author %}
  {% if author %}
    {% set author_docs = site.indexes.author.get(author) | resolve_pages %}
    {% set author_docs = author_docs | reject('eq', page) | limit(3) %}

    {% if author_docs %}
      <h4>More from {{ author }}</h4>
      <ul>
        {% for doc in author_docs %}
          <li><a href="{{ url_for(doc) }}">{{ doc.title }}</a></li>
        {% endfor %}
      </ul>
    {% endif %}
  {% endif %}
</aside>
```

---

## Performance Comparison

### Before (O(n) filtering)

```jinja2
{# Scans ALL 5000 docs pages #}
{% set guides = site.pages | where('category', 'guide') %}  {# 5000 ops #}
{% set by_jane = site.pages | where('author', 'Jane') %}    {# 5000 ops #}
{% set recent = site.pages | where_gt('date', cutoff) %}    {# 5000 ops #}

{# Total: 15,000 operations for 3 queries #}
```

### After (O(1) lookups)

```jinja2
{# O(1) hash lookups #}
{% set guides = site.indexes.category.get('guide') | resolve_pages %}     {# 1 op #}
{% set by_jane = site.indexes.author.get('Jane') | resolve_pages %}       {# 1 op #}
{% set recent_2024 = site.indexes.date_range.get('2024') | resolve_pages %} {# 1 op #}

{# Total: 3 operations + O(k) resolve where k = result size #}
```

**Speedup:** 5000x for each query!

---

## Recommended Custom Indexes for Bengal Docs Site

### 1. **StatusIndex** (for docs workflow)
```python
class StatusIndex(QueryIndex):
    def extract_keys(self, page):
        status = page.metadata.get('status', 'published')
        # 'draft', 'review', 'published', 'outdated'
        return [(status, {})]
```

### 2. **DifficultyIndex** (for tutorials)
```python
class DifficultyIndex(QueryIndex):
    def extract_keys(self, page):
        difficulty = page.metadata.get('difficulty')
        if difficulty:
            # 'beginner', 'intermediate', 'advanced'
            return [(difficulty, {})]
        return []
```

### 3. **PlatformIndex** (for platform-specific docs)
```python
class PlatformIndex(QueryIndex):
    def extract_keys(self, page):
        platforms = page.metadata.get('platforms', [])
        # ['linux', 'macos', 'windows']
        return [(platform, {}) for platform in platforms]
```

---

## Implementation Priority

### Phase 1: Built-in Indexes (✅ Done!)
- Section
- Author
- Category  
- DateRange

### Phase 2: Theme Enhancements (Week 1)
1. Update `home.html` to use section index
2. Add year/month archive templates
3. Add author archive pages
4. Update sidebar widgets

### Phase 3: Docs Site Custom Indexes (Week 2)
1. SeriesIndex for tutorial navigation
2. StatusIndex for workflow
3. DifficultyIndex for filtering
4. ModuleIndex for API docs

### Phase 4: Advanced Features (Week 3)
1. Search page filters
2. "What's New" page
3. Category browser
4. Enhanced related docs

---

## Migration Notes

Most templates will work without changes! Indexes are additive.

**Gradual migration path:**
1. Keep existing `where()` filters for now
2. Add new features using indexes
3. Gradually replace O(n) patterns with O(1) lookups
4. Document both patterns in theme docs

---

## Conclusion

The query index system will be **incredibly useful** for:

1. **Default theme:** Faster home pages, better archives, author pages
2. **Bengal docs site:** Category browsing, tutorial series, API navigation
3. **Theme developers:** Scalable patterns that work from 10 to 10,000 pages

**Next steps:**
1. Start with home page optimization (easy win)
2. Add year/month archive templates
3. Build custom indexes for docs site workflow
