# Bengal Template Context Reference

**Audience:** Theme developers  
**Purpose:** Reference for all available template variables, functions, filters, and tests  
**Last Updated:** 2025-12-23

---

## Quick Reference

```jinja2
{# Core objects - always available #}
{{ page }}          {# Current page #}
{{ site }}          {# Site object #}
{{ config }}        {# Site config (alias for site.config) #}
{{ params }}        {# Page metadata (alias for page.metadata) #}
{{ section }}       {# Current section #}

{# Pre-computed values - cached for performance #}
{{ content }}       {# Rendered page content (safe HTML) #}
{{ title }}         {# Page title #}
{{ toc }}           {# Table of contents HTML #}
{{ toc_items }}     {# Structured TOC data #}
{{ meta_desc }}     {# Pre-computed meta description #}
{{ reading_time }}  {# Pre-computed reading time #}
{{ excerpt }}       {# Pre-computed excerpt #}
```

---

## Template Tests

Clean conditional checks using `is` operator:

| Test | Usage | Description |
|------|-------|-------------|
| `is draft` | `{% if page is draft %}` | Check if page is a draft |
| `is featured` | `{% if page is featured %}` | Check if page has 'featured' tag |
| `is outdated` | `{% if page is outdated %}` | Check if page is older than 90 days |
| `is outdated(N)` | `{% if page is outdated(30) %}` | Check if page is older than N days |
| `is match` | `{% if value is match('pattern') %}` | Regex pattern matching |
| `is section` | `{% if obj is section %}` | Check if object is a Section |
| `is translated` | `{% if page is translated %}` | Check if page has translations |

### Examples

```jinja2
{# Draft indicator #}
{% if page is draft %}
  <span class="badge badge-draft">Draft</span>
{% endif %}

{# Featured content styling #}
<article class="{% if page is featured %}featured{% endif %}">

{# Stale content warning #}
{% if page is outdated(180) %}
  <div class="warning">This page may be outdated.</div>
{% endif %}

{# Pattern matching #}
{% if page.source_path is match('.*_index.*') %}
  {# This is an index page #}
{% endif %}
```

---

## Global Functions

Functions available directly in templates:

### Navigation

| Function | Description |
|----------|-------------|
| `breadcrumbs(page)` | Generate breadcrumb trail |
| `page_navigation(page)` | Prev/next page navigation |
| `toc(toc_items, toc, page)` | Render table of contents |
| `get_auto_nav()` | Auto-discovered navigation tree |
| `get_menu('name')` | Get named menu items |
| `get_menu_lang('name', 'en')` | Get menu for specific language |

### Content

| Function | Description |
|----------|-------------|
| `icon('name', size=16)` | Render icon |
| `tag_list(tags)` | Render tag pills |
| `tag_url(tag)` | Get URL for tag page |
| `get_page('/path')` | Lookup page by path |
| `page_exists('/path')` | Check if page exists |

### URLs

| Function | Description |
|----------|-------------|
| `asset_url('path')` | Get versioned asset URL |
| `url_for('path')` | Build URL with baseurl |
| `canonical_url(path, page)` | Get canonical URL |
| `og_image(path, page)` | Get Open Graph image URL |

### SEO & Sharing

| Function | Description |
|----------|-------------|
| `share_url('twitter', page)` | Generate social share URL |
| `twitter_share_url(url, text)` | Twitter share URL |
| `linkedin_share_url(url, text)` | LinkedIn share URL |
| `facebook_share_url(url)` | Facebook share URL |
| `reddit_share_url(url, title)` | Reddit share URL |
| `email_share_url(url, subject, body)` | Email share URL |

### i18n

| Function | Description |
|----------|-------------|
| `t('key')` | Translate UI string |
| `t('key', {'name': 'value'})` | Translate with params |
| `current_lang()` | Get current language code |
| `languages()` | Get configured languages |
| `locale_date(date, 'medium')` | Localized date formatting |

---

## Filters

Apply to values with `|` operator:

### Text

| Filter | Description |
|--------|-------------|
| `truncate(N)` | Truncate to N characters |
| `truncatewords(N)` | Truncate to N words |
| `first_sentence` | Extract first sentence |
| `slugify` | Convert to URL-safe slug |
| `markdownify` | Render markdown to HTML |
| `strip_html` | Remove HTML tags |
| `reading_time` | Estimate reading time (minutes) |
| `wordcount` | Count words |

### Collections

| Filter | Description |
|--------|-------------|
| `where('key', value)` | Filter by attribute |
| `where_not('key', value)` | Exclude by attribute |
| `sort_by('key')` | Sort by attribute |
| `sort_by('key', reverse=True)` | Sort descending |
| `limit(N)` | Take first N items |
| `offset(N)` | Skip first N items |
| `group_by('key')` | Group by attribute |
| `first` | Get first item |
| `last` | Get last item |
| `flatten` | Flatten nested lists |
| `resolve_pages` | Convert paths to Page objects |

### Dates

| Filter | Description |
|--------|-------------|
| `dateformat('%Y-%m-%d')` | Format date |
| `date_iso` | ISO 8601 format |
| `time_ago` | "2 days ago" format |
| `days_ago` | Days since date |

### URLs

| Filter | Description |
|--------|-------------|
| `absolute_url` | Add baseurl |
| `url` | Alias for absolute_url |
| `href` | Apply baseurl to path |
| `url_encode` | URL encode |

### Logic

| Filter | Description |
|--------|-------------|
| `has_tag('name')` | Check if has tag |
| `default(value)` | Fallback value |
| `safe_access` | Wrap dict for safe dot-notation access |

---

## Page Object Properties

Properties available on `page`:

### Core

| Property | Description |
|----------|-------------|
| `page.title` | Page title |
| `page.content` | Raw markdown content |
| `page.metadata` | Frontmatter dict |
| `page._path` | URL path |
| `page.href` | Full URL path |
| `page.source_path` | Source file path |

### Computed

| Property | Description |
|----------|-------------|
| `page.kind` | Page kind (page, section, etc.) |
| `page.type` | Content type |
| `page.draft` | Is draft? |
| `page.hidden` | Is hidden? |
| `page.tags` | List of tags |
| `page.date` | Page date |

### Relationships

| Property | Description |
|----------|-------------|
| `page.section` | Parent section |
| `page.translations` | Available translations |

---

## Site Object Properties

Properties available on `site`:

| Property | Description |
|----------|-------------|
| `site.config` | Site configuration dict |
| `site.pages` | All pages |
| `site.sections` | All sections |
| `site.theme_config` | Theme configuration |
| `site.versioning_enabled` | Is versioning on? |
| `site.versions` | Available versions |

---

## Shortcuts

Bengal provides smart context wrappers that allow safe dot-notation access:

| Shortcut | Wraps | Safe Access |
|----------|-------|-------------|
| `params` | `page.metadata` | Returns `''` for missing keys |
| `config` | `site.config` | Returns `''` for missing keys |
| `theme` | `site.theme_config` | Returns `''` for missing keys |
| `section` | Current section | Returns `''` for missing properties |

### Using params (No `.get()` needed!)

```jinja2
{# Old pattern (no longer needed) #}
{{ params.get('author') }}
{{ params.get('description') }}

{# New pattern (clean and safe) #}
{{ params.author }}
{{ params.description }}
{{ params.social.twitter }}  {# Nested access is also safe #}
```

### Data Files with `| safe_access`

For raw dicts from `site.data`, use the `safe_access` filter:

```jinja2
{% set resume = site.data.resume | safe_access %}
{{ resume.name }}
{{ resume.contact.email }}
```

---

## Best Practices

### 1. Use Template Tests

```jinja2
{# ✅ Preferred #}
{% if page is draft %}
{% if page is featured %}
{% if page is outdated(90) %}

{# ❌ Verbose #}
{% if page.draft is defined and page.draft %}
{% if page.tags is defined and (page | has_tag('featured')) %}
```

### 2. Use Shortcuts (No `.get()` needed)

```jinja2
{# ✅ Preferred (safe dot access) #}
{{ params.author }}
{{ config.baseurl }}
{{ theme.hero_style }}

{# ❌ Verbose (old pattern) #}
{{ page.metadata.get('author') }}
{{ site.config.get('baseurl') }}
```

### 3. Use Built-in Functions

```jinja2
{# ✅ Use share_url for social sharing #}
<a href="{{ share_url('twitter', page) }}">Share on Twitter</a>

{# ✅ Use t() for UI strings (enables i18n) #}
<button>{{ t('search.placeholder', default='Search...') }}</button>

{# ✅ Use locale_date for localized dates #}
<time>{{ page.date | locale_date('long') }}</time>
```

### 4. Cache Function Calls

```jinja2
{# ✅ Cache at top of template #}
{% set _breadcrumbs = get_breadcrumbs(page) %}
{% set _menu = get_menu_lang('main', current_lang()) %}

{# Then use cached values #}
{% for item in _breadcrumbs %}...{% endfor %}
{% for item in _menu %}...{% endfor %}
```
