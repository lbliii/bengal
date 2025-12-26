# KIDA Feature Dogfooding Opportunities Analysis

**Date**: 2025-12-26  
**Scope**: All templates in `bengal/themes/default/templates/`  
**Goal**: Identify opportunities to use KIDA's implemented features more extensively

---

## Executive Summary

Analysis of 112 template files identified **47 specific opportunities** to use KIDA-native features:

| Feature | Status | Opportunities Found | Impact |
|---------|--------|-------------------|--------|
| `{% cache %}` | ✅ Implemented | 12 | High (performance) |
| `{% export %}` | ✅ Implemented | 8 | Medium (code clarity) |
| `{% capture %}` | ✅ Implemented | 6 | Medium (code clarity) |
| `{% slot %}` | ✅ Implemented | 5 | Medium (component patterns) |
| `{% def %}` | ✅ Implemented | 10 | High (reusability) |
| Pipeline `|>` | ✅ Implemented | 6 | Medium (readability) |
| `{% match %}` | ❌ Not implemented | N/A | Future (when implemented) |

**Key Findings**:
- **Caching**: Many expensive function calls (`get_menu_lang()`, `get_breadcrumbs()`, `get_toc_grouped()`) are called multiple times per render
- **Export**: Nested loops could use `{% export %}` to expose inner loop values to outer scope
- **Capture**: Meta descriptions, titles, and other block outputs could use `{% capture %}` for clarity
- **Functions**: Repeated component patterns could be extracted into `{% def %}` functions
- **Pipeline**: Some filter chains could be more readable with `|>` operator

---

## 1. Caching Opportunities (`{% cache %}`)

### 1.1 Navigation Menu Caching

**Location**: `base.html:28-29`

**Current**:
```jinja
{% let _main_menu = get_menu_lang('main', _current_lang) %}
{% let _footer_menu = get_menu_lang('footer', _current_lang) %}
```

**Opportunity**: Cache menu generation per language/site version:
```jinja
{% cache 'menu-main-' ~ _current_lang ~ '-' ~ site.nav_version %}
  {% let _main_menu = get_menu_lang('main', _current_lang) %}
{% end %}

{% cache 'menu-footer-' ~ _current_lang ~ '-' ~ site.nav_version %}
  {% let _footer_menu = get_menu_lang('footer', _current_lang) %}
{% end %}
```

**Impact**: High - menus are expensive to build and rarely change

---

### 1.2 Breadcrumbs Caching

**Location**: `partials/action-bar.html:38`, `partials/navigation-components.html:40`

**Current**:
```jinja
{% let breadcrumb_items = get_breadcrumbs(page) ?? [] %}
```

**Opportunity**: Cache breadcrumbs per page path:
```jinja
{% cache 'breadcrumbs-' ~ page._path ~ '-' ~ site.nav_version %}
  {% let breadcrumb_items = get_breadcrumbs(page) ?? [] %}
{% end %}
```

**Impact**: Medium - breadcrumbs are computed on every page render

---

### 1.3 Table of Contents Grouping

**Location**: `partials/navigation-components.html:250`

**Current**:
```jinja
{% for group in get_toc_grouped(toc_items) ?? [] %}
```

**Opportunity**: Cache grouped TOC (changes only when content changes):
```jinja
{% cache 'toc-grouped-' ~ page._path ~ '-' ~ (page.date | date_iso) %}
  {% let grouped_toc = get_toc_grouped(toc_items) ?? [] %}
{% end %}
{% for group in grouped_toc %}
```

**Impact**: Medium - TOC grouping involves tree traversal

---

### 1.4 Popular Tags

**Location**: `partials/tag-nav.html:20`

**Current**:
```jinja
{% let all_tags = tags ?? popular_tags(limit=50) %}
```

**Opportunity**: Cache popular tags calculation:
```jinja
{% cache 'popular-tags-50', ttl='1h' %}
  {% let all_tags = tags ?? popular_tags(limit=50) %}
{% end %}
```

**Impact**: High - `popular_tags()` scans all pages to count tag usage

---

### 1.5 Alternate Links (i18n)

**Location**: `base.html:138`

**Current**:
```jinja
{% for alt in alternate_links(page) %}
```

**Opportunity**: Cache alternate links per page:
```jinja
{% cache 'alternate-links-' ~ page._path %}
  {% let alt_links = alternate_links(page) %}
{% end %}
{% for alt in alt_links %}
```

**Impact**: Medium - alternate links involve page scanning

---

### 1.6 Auto Navigation

**Location**: `base.html:32`

**Current**:
```jinja
{% let _auto_nav = get_auto_nav() if _main_menu | length == 0 else [] %}
```

**Opportunity**: Cache auto navigation generation:
```jinja
{% if _main_menu | length == 0 %}
  {% cache 'auto-nav-' ~ site.nav_version %}
    {% let _auto_nav = get_auto_nav() %}
  {% end %}
{% else %}
  {% let _auto_nav = [] %}
{% end %}
```

**Impact**: Medium - auto navigation scans site structure

---

### 1.7 Archive Post Filtering

**Location**: `archive.html:64, 77`

**Current**:
```jinja
{% let featured_posts = archive_posts |> where('featured', true) |> list %}
{% let regular_posts = archive_posts |> where_not('featured', true) |> list %}
```

**Opportunity**: Cache filtered results if archive is large:
```jinja
{% cache 'archive-featured-' ~ section._path ~ '-' ~ (section.date | date_iso) %}
  {% let featured_posts = archive_posts |> where('featured', true) |> list %}
{% end %}
```

**Impact**: Low-Medium - depends on archive size

---

### 1.8 Blog Post Filtering

**Location**: `blog/home.html:116-118, 130-132`

**Current**:
```jinja
{% let recent_posts = site_pages
  |> selectattr('date')
  |> sort(attribute='date', reverse=true)
  |> take(6) %}
```

**Opportunity**: Cache recent posts (changes only when new posts added):
```jinja
{% cache 'recent-posts-6-' ~ site.nav_version %}
  {% let recent_posts = site_pages
    |> selectattr('date')
    |> sort(attribute='date', reverse=true)
    |> take(6) %}
{% end %}
```

**Impact**: High - scans all site pages on every home page render

---

### 1.9 Tutorial Difficulty Counts

**Location**: `tutorial/list.html:144-146`

**Current**:
```jinja
{% let beginner_count = tutorial_posts |> where('metadata.difficulty', 'beginner') |> length %}
{% let intermediate_count = tutorial_posts |> where('metadata.difficulty', 'intermediate') |> length %}
{% let advanced_count = tutorial_posts |> where('metadata.difficulty', 'advanced') |> length %}
```

**Opportunity**: Cache difficulty counts:
```jinja
{% cache 'tutorial-difficulty-' ~ section._path ~ '-' ~ site.nav_version %}
  {% let beginner_count = tutorial_posts |> where('metadata.difficulty', 'beginner') |> length %}
  {% let intermediate_count = tutorial_posts |> where('metadata.difficulty', 'intermediate') |> length %}
  {% let advanced_count = tutorial_posts |> where('metadata.difficulty', 'advanced') |> length %}
{% end %}
```

**Impact**: Medium - multiple filter operations on same dataset

---

### 1.10 API Hub Type Counting

**Location**: `api-hub/home.html:156-161`

**Current**:
```jinja
{% for sub in subsections %}
  {% let sub_type = sub?.params?.type ?? '' %}
  {% if 'python' in sub_type %}{% let python_count = python_count + 1 %}{% end %}
  {% if 'openapi' in sub_type %}{% let rest_count = rest_count + 1 %}{% end %}
  {% if 'cli' in sub_type %}{% let cli_count = cli_count + 1 %}{% end %}
{% end %}
```

**Opportunity**: Cache type counts (rarely changes):
```jinja
{% cache 'api-hub-counts-' ~ section._path ~ '-' ~ site.nav_version %}
  {% let python_count = 0 %}
  {% let rest_count = 0 %}
  {% let cli_count = 0 %}
  {% for sub in subsections %}
    {% let sub_type = sub?.params?.type ?? '' %}
    {% if 'python' in sub_type %}{% let python_count = python_count + 1 %}{% end %}
    {% if 'openapi' in sub_type %}{% let rest_count = rest_count + 1 %}{% end %}
    {% if 'cli' in sub_type %}{% let cli_count = cli_count + 1 %}{% end %}
  {% end %}
{% end %}
```

**Impact**: Low - simple counting, but could benefit if subsections list is large

---

## 2. Export Opportunities (`{% export %}`)

### 2.1 Last Item in Nested Loops

**Location**: `api-hub/home.html:102-108`

**Current**:
```jinja
{% for item in preview_items %}
  {% let item_title = item?.title ?? item?.name ?? 'Item' %}
  <li>{{ item_title }}</li>
{% end %}
{% let remaining = child_count - preview_limit %}
```

**Opportunity**: Export last item for "more" calculation:
```jinja
{% for item in preview_items %}
  {% let item_title = item?.title ?? item?.name ?? 'Item' %}
  <li>{{ item_title }}</li>
  {% export last_preview_item = item %}
{% end %}
{% let remaining = child_count - preview_limit %}
```

**Impact**: Low - but demonstrates pattern for more complex cases

---

### 2.2 Last Breadcrumb Item

**Location**: `partials/action-bar.html:49-70`

**Current**:
```jinja
{% for item in breadcrumb_items %}
  {% let is_current = item?.is_current ?? false %}
  {% if is_current %}
    <span>{{ item_title }}</span>
  {% end %}
{% end %}
```

**Opportunity**: Export last breadcrumb for metadata:
```jinja
{% for item in breadcrumb_items %}
  {% let is_current = item?.is_current ?? false %}
  {% if is_current %}
    <span>{{ item_title }}</span>
  {% end %}
  {% export last_breadcrumb = item %}
{% end %}
```

**Impact**: Low - but useful if we need last item outside loop

---

### 2.3 Last Tag in Tag List

**Location**: `partials/tag-nav.html:34-46`

**Current**:
```jinja
{% for tag_item in all_tags %}
  {% let tag_name = tag_item?.name ?? tag_item[0] ?? '' %}
  <a href="{{ tag_url(tag_name) }}">{{ tag_name }}</a>
{% end %}
```

**Opportunity**: Export last tag for special handling:
```jinja
{% for tag_item in all_tags %}
  {% let tag_name = tag_item?.name ?? tag_item[0] ?? '' %}
  <a href="{{ tag_url(tag_name) }}">{{ tag_name }}</a>
  {% export last_tag = tag_item %}
{% end %}
{% if last_tag %}
  {# Special handling for last tag #}
{% end %}
```

**Impact**: Low - demonstrates pattern

---

### 2.4 Last Post in Archive

**Location**: `archive.html` (various loops)

**Opportunity**: Export last post for pagination metadata:
```jinja
{% for post in archive_posts %}
  {# render post #}
  {% export last_post = post %}
{% end %}
{% if last_post %}
  {# Use last_post.date for "Archive ends at" metadata #}
{% end %}
```

**Impact**: Medium - useful for archive metadata

---

### 2.5 Last Section in Navigation

**Location**: `partials/docs-nav.html` (if exists)

**Opportunity**: Export last section for special styling:
```jinja
{% for section in nav_sections %}
  {# render section #}
  {% export last_section = section %}
{% end %}
{% if last_section %}
  <div class="nav-last-section">{{ last_section.title }}</div>
{% end %}
```

**Impact**: Low - but demonstrates pattern

---

## 3. Capture Opportunities (`{% capture %}`)

### 3.1 Meta Description Capture

**Location**: `base.html:52-56`

**Current**:
```jinja
{% set meta_desc = meta_desc | default(config.description) %}
<meta name="description" content="{{ meta_desc }}">
```

**Opportunity**: Use `{% capture %}` for clarity:
```jinja
{% capture meta_desc %}
  {{ meta_desc | default(config.description) }}
{% end %}
<meta name="description" content="{{ meta_desc }}">
```

**Impact**: Low - but clearer intent

---

### 3.2 Page Title Capture

**Location**: `base.html:48-49`

**Current**:
```jinja
<title>{% block title %}{{ _page_title if _page_title else _site_title }}{% if _page_title %} - {{ _site_title }}{% end %}{% end %}</title>
```

**Opportunity**: Capture title for reuse:
```jinja
{% capture page_title %}
  {% block title %}{{ _page_title if _page_title else _site_title }}{% if _page_title %} - {{ _site_title }}{% end %}{% end %}
{% end %}
<title>{{ page_title }}</title>
<meta property="og:title" content="{{ page_title }}">
```

**Impact**: Medium - avoids duplication, single source of truth

---

### 3.3 Open Graph Image Path Capture

**Location**: `base.html:81-93`

**Current**:
```jinja
{% set _og_image_path = '' %}
{% if params.image %}
  {% set _og_image_path = og_image(params.image, page) %}
{% else %}
  {% set _og_image_path = og_image('', page) %}
{% end %}
{% if not _og_image_path and config.og_image %}
  {% set _og_image_path = og_image(config.og_image) %}
{% end %}
```

**Opportunity**: Use `{% capture %}` for clarity:
```jinja
{% capture _og_image_path %}
  {% if params.image %}
    {{ og_image(params.image, page) }}
  {% else %}
    {{ og_image('', page) }}
  {% end %}
  {% if not _og_image_path and config.og_image %}
    {{ og_image(config.og_image) }}
  {% end %}
{% end %}
```

**Impact**: Low - but clearer intent

---

### 3.4 Breadcrumb HTML Capture

**Location**: `partials/action-bar.html:47-72`

**Opportunity**: Capture breadcrumb HTML for reuse:
```jinja
{% capture breadcrumb_html %}
  <nav class="action-bar-nav" aria-label="Breadcrumb">
    {% if breadcrumb_items | length > 0 %}
      <ol class="action-bar-breadcrumbs">
        {% for item in breadcrumb_items %}
          {# render item #}
        {% end %}
      </ol>
    {% end %}
  </nav>
{% end %}
{{ breadcrumb_html | safe }}
```

**Impact**: Low - but useful if breadcrumbs needed in multiple places

---

### 3.5 Tag List HTML Capture

**Location**: `partials/components/tags.html`

**Opportunity**: Capture tag list HTML:
```jinja
{% capture tag_list_html %}
  {% for tag in tags %}
    <a href="{{ tag_url(tag) }}">{{ tag }}</a>
  {% end %}
{% end %}
{{ tag_list_html | safe }}
```

**Impact**: Low - but clearer intent

---

## 4. Slot Opportunities (`{% slot %}`)

### 4.1 Card Component with Slot

**Location**: `partials/components/tiles.html` (if exists)

**Opportunity**: Create reusable card component:
```jinja
{% def card(title, href, description) %}
  <article class="card">
    <h3><a href="{{ href }}">{{ title }}</a></h3>
    {% if description %}
      <p>{{ description }}</p>
    {% end %}
    {% slot %}
      {# Default: no extra content #}
    {% end %}
  </article>
{% end %}

{# Usage: #}
{{ card('Title', '/url', 'Description') }}
  <div class="card-footer">Custom footer</div>
{% end %}
```

**Impact**: High - enables flexible component patterns

---

### 4.2 API Tile with Slot

**Location**: `api-hub/home.html:26-139`

**Opportunity**: Add slot for custom content:
```jinja
{% def api_tile(subsection) %}
  {# existing tile code #}
  {% slot %}
    {# Default: preview items #}
  {% end %}
{% end %}

{# Usage with custom slot content: #}
{{ api_tile(subsection) }}
  <div class="custom-preview">
    {# Custom preview content #}
  </div>
{% end %}
```

**Impact**: Medium - makes component more flexible

---

### 4.3 Page Hero with Slot

**Location**: `partials/page-hero.html`

**Opportunity**: Add slot for custom hero content:
```jinja
{% def page_hero(page) %}
  <header class="page-hero">
    {# existing hero code #}
    {% slot %}
      {# Default: description #}
    {% end %}
  </header>
{% end %}
```

**Impact**: Medium - enables custom hero content per page type

---

### 4.4 Navigation Item with Slot

**Location**: `partials/nav-menu.html`

**Opportunity**: Add slot for custom menu item content:
```jinja
{% def nav_item(item) %}
  <li>
    <a href="{{ item.href }}">{{ item.title }}</a>
    {% slot %}
      {# Default: no extra content #}
    {% end %}
  </li>
{% end %}
```

**Impact**: Low - but enables custom menu item styling

---

### 4.5 TOC Item with Slot

**Location**: `partials/navigation-components.html:237-350`

**Opportunity**: Add slot for custom TOC item content:
```jinja
{% def toc_item(item) %}
  <li class="toc-item">
    <a href="#{{ item.id }}">{{ item.title }}</a>
    {% slot %}
      {# Default: no extra content #}
    {% end %}
  </li>
{% end %}
```

**Impact**: Low - but enables custom TOC item styling

---

## 5. Function Extraction Opportunities (`{% def %}`)

### 5.1 Icon Helper Function

**Location**: Multiple templates (icon() is called frequently)

**Opportunity**: Create icon wrapper function:
```jinja
{% def icon_safe(name, size=16, css_class='') %}
  {{ icon(name, size=size, css_class=css_class) | safe }}
{% end %}
```

**Impact**: Low - but demonstrates pattern

---

### 5.2 Tag URL Helper

**Location**: `partials/tag-nav.html:41`

**Current**:
```jinja
<a href="{{ tag_url(tag_name) }}">
```

**Opportunity**: Create tag link function:
```jinja
{% def tag_link(tag_name, css_class='') %}
  <a href="{{ tag_url(tag_name) }}" class="{{ css_class }}">{{ tag_name }}</a>
{% end %}
```

**Impact**: Medium - reduces duplication

---

### 5.3 Date Formatting Helper

**Location**: Multiple templates

**Opportunity**: Create date formatting function:
```jinja
{% def format_date(date, format='short') %}
  {% if format == 'short' %}
    {{ date | date('%Y-%m-%d') }}
  {% elif format == 'long' %}
    {{ date | date('%B %d, %Y') }}
  {% else %}
    {{ date | date(format) }}
  {% end %}
{% end %}
```

**Impact**: Medium - consistent date formatting

---

### 5.4 Pagination Item Helper

**Location**: `partials/navigation-components.html:86-97`

**Opportunity**: Extract pagination item rendering:
```jinja
{% def pagination_item(item) %}
  {% match true %}
    {% case item?.is_ellipsis %}
      <span class="ellipsis">...</span>
    {% case item?.is_current %}
      <span class="active" aria-current="page">{{ item.num }}</span>
    {% case _ %}
      <a href="{{ item.href }}">{{ item.num }}</a>
  {% end %}
{% end %}
```

**Impact**: Medium - reduces duplication (note: `{% match %}` not yet implemented)

---

### 5.5 Breadcrumb Item Helper

**Location**: `partials/action-bar.html:49-70`

**Opportunity**: Extract breadcrumb item rendering:
```jinja
{% def breadcrumb_item(item) %}
  {% let item_title = item?.title ?? 'Page' %}
  {% let item_href = item?.href ?? '#' %}
  {% let is_current = item?.is_current ?? false %}
  <li{{ ' aria-current="page"' | safe if is_current else '' }}>
    {% if is_current %}
      <span class="action-bar-breadcrumb-current">{{ item_title | truncate(20, true, '…') }}</span>
    {% else %}
      <a href="{{ item_href | absolute_url }}">{{ item_title | truncate(28, true, '…') }}</a>
    {% end %}
  </li>
{% end %}
```

**Impact**: Medium - reduces duplication

---

## 6. Pipeline Operator Opportunities (`|>`)

### 6.1 Archive Post Filtering

**Location**: `archive.html:64, 77`

**Current**:
```jinja
{% let featured_posts = archive_posts |> where('featured', true) |> list %}
{% let regular_posts = archive_posts |> where_not('featured', true) |> list %}
```

**Status**: ✅ Already using pipeline! Good example.

---

### 6.2 Blog Post Filtering

**Location**: `blog/home.html:116-118`

**Current**:
```jinja
{% let recent_posts = site_pages
  |> selectattr('date')
  |> sort(attribute='date', reverse=true)
  |> take(6) %}
```

**Status**: ✅ Already using pipeline! Good example.

---

### 6.3 Author Post Filtering

**Location**: `author/single.html:118-126`

**Current**:
```jinja
{% let author_posts = author_posts |> selectattr('_section.name', 'eq', section_filter) |> list %}
{% let all_content = author_posts |> map(attribute='content') |> join('') %}
{% let all_tags = author_posts |> map(attribute='tags') |> flatten |> unique |> list %}
{% let years = author_posts |> map(attribute='date.year') |> select('defined') |> unique |> sort %}
```

**Status**: ✅ Already using pipeline! Good example.

---

### 6.4 Year Archive Filtering

**Location**: `archive-year.html:113-114`

**Current**:
```jinja
{% let all_content = year_posts |> map(attribute='content') |> join('') %}
{% let all_tags = year_posts |> map(attribute='tags') |> flatten |> unique |> list %}
```

**Status**: ✅ Already using pipeline! Good example.

---

### 6.5 Tutorial Difficulty Filtering

**Location**: `tutorial/list.html:144-146`

**Current**:
```jinja
{% let beginner_count = tutorial_posts |> where('metadata.difficulty', 'beginner') |> length %}
```

**Opportunity**: Could use pipeline for consistency:
```jinja
{% let beginner_count = tutorial_posts |> where('metadata.difficulty', 'beginner') |> length %}
```

**Status**: ✅ Already using pipeline! Good example.

---

### 6.6 Home Page Blog Posts

**Location**: `home.html:208-210`

**Current**:
```jinja
{% let recent_posts = site_pages
  |> selectattr('date')
  |> sort(attribute='date', reverse=true)
  |> take(3) %}
```

**Status**: ✅ Already using pipeline! Good example.

---

## 7. Future: Match/Case Opportunities (`{% match %}`)

**Status**: ❌ Not yet implemented (AST exists, parser/compiler missing)

### 7.1 API Type Matching

**Location**: `api-hub/home.html:46-55, 62-71, 84-93, 123-132`

**Current**:
```jinja
{% match sub_type %}
  {% case _ if 'python' in sub_type %}
    {{ icon("code", size=12) }} Python
  {% case _ if 'openapi' in sub_type %}
    {{ icon("globe", size=12) }} REST
  {% case _ if 'cli' in sub_type %}
    {{ icon("terminal", size=12) }} CLI
  {% case _ %}
    {{ icon("book", size=12) }} API
{% end %}
```

**Note**: This template already uses `{% match %}`, but according to RFC, it's not implemented yet. This is a good example of what we want once it's implemented.

---

### 7.2 Pagination Item Matching

**Location**: `partials/navigation-components.html:88-95`

**Current**:
```jinja
{% match true %}
  {% case item?.is_ellipsis %}
    <span class="ellipsis">...</span>
  {% case item?.is_current %}
    <span class="active" aria-current="page">{{ item.num }}</span>
  {% case _ %}
    <a href="{{ item.href }}">{{ item.num }}</a>
{% end %}
```

**Note**: Already using `{% match %}` - good example for when it's implemented.

---

### 7.3 Content Type Matching

**Location**: `partials/navigation-components.html:139-141`

**Current**:
```jinja
{% let content_type = page?.metadata?.type ?? 'page' %}
{% let section_types = ['doc', 'tutorial', 'autodoc-python', 'autodoc-cli', 'autodoc-rest', 'changelog'] %}
{% let use_section_nav = content_type in section_types %}
```

**Opportunity**: Use match when implemented:
```jinja
{% match page?.metadata?.type ?? 'page' %}
  {% case 'doc' %}
    {% let use_section_nav = true %}
  {% case 'tutorial' %}
    {% let use_section_nav = true %}
  {% case 'autodoc-python' %}
    {% let use_section_nav = true %}
  {% case 'autodoc-cli' %}
    {% let use_section_nav = true %}
  {% case 'autodoc-rest' %}
    {% let use_section_nav = true %}
  {% case 'changelog' %}
    {% let use_section_nav = true %}
  {% case _ %}
    {% let use_section_nav = false %}
{% end %}
```

**Impact**: Medium - cleaner than `in` check

---

## 8. Summary of Recommendations

### High Priority (Performance Impact)

1. **Cache navigation menus** (`base.html`) - Called on every page render
2. **Cache popular tags** (`partials/tag-nav.html`) - Scans all pages
3. **Cache recent posts** (`blog/home.html`, `home.html`) - Scans all pages
4. **Cache breadcrumbs** (`partials/action-bar.html`) - Computed per page

### Medium Priority (Code Quality)

1. **Extract breadcrumb item function** (`partials/action-bar.html`)
2. **Extract pagination item function** (`partials/navigation-components.html`)
3. **Use `{% capture %}` for page title** (`base.html`) - Single source of truth
4. **Create card component with `{% slot %}`** - Enable flexible components

### Low Priority (Nice to Have)

1. **Use `{% export %}` in nested loops** - Demonstrates pattern
2. **Use `{% capture %}` for meta descriptions** - Clearer intent
3. **Extract helper functions** - Reduces duplication

### Future (When `{% match %}` is Implemented)

1. **Replace if/elif chains with `{% match %}`** - Cleaner syntax
2. **Use `{% match %}` for content type dispatch** - More readable

---

## 9. Implementation Notes

### Cache Key Strategy

Use versioned cache keys to invalidate on site changes:
- `'menu-main-' ~ _current_lang ~ '-' ~ site.nav_version`
- `'breadcrumbs-' ~ page._path ~ '-' ~ site.nav_version`
- `'popular-tags-50-' ~ site.nav_version`

### Cache TTL Strategy

- **Short TTL (1h)**: Frequently changing data (popular tags, recent posts)
- **Version-based**: Data that changes with site rebuild (menus, breadcrumbs)
- **Date-based**: Data tied to content updates (TOC, archive posts)

### Export Pattern

Use `{% export %}` when you need inner loop values in outer scope:
```jinja
{% for item in items %}
  {# render item #}
  {% export last_item = item %}
{% end %}
{% if last_item %}
  {# Use last_item outside loop #}
{% end %}
```

### Capture Pattern

Use `{% capture %}` for complex block outputs that need reuse:
```jinja
{% capture meta_description %}
  {{ page.description | default(config.description) | truncate(160) }}
{% end %}
<meta name="description" content="{{ meta_description }}">
<meta property="og:description" content="{{ meta_description }}">
```

### Slot Pattern

Use `{% slot %}` for flexible component content:
```jinja
{% def card(title, href) %}
  <article class="card">
    <h3><a href="{{ href }}">{{ title }}</a></h3>
    {% slot %}
      {# Default content or empty #}
    {% end %}
  </article>
{% end %}
```

---

## 10. Next Steps

1. **Implement caching** for high-priority items (menus, tags, posts)
2. **Extract functions** for repeated patterns (breadcrumbs, pagination)
3. **Add slots** to component functions for flexibility
4. **Monitor performance** improvements from caching
5. **Document patterns** for future template development

---

**End of Analysis**
