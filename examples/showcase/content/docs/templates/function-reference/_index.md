---
title: "Template Functions Reference"
description: "Complete reference of all 75+ template functions available in Bengal SSG"
date: 2025-10-04
weight: 10
tags: ["templates", "functions", "reference", "jinja2"]
toc: true
---

# Template Functions Reference

Bengal SSG provides **75+ template functions** organized into 16 focused modules. These functions extend Jinja2 with powerful capabilities for string manipulation, collections, dates, SEO, and more.

---

## 📚 Function Modules Overview

### String Functions (11 functions)
**Module:** `strings`  
Essential string manipulation for text processing.

| Function | Purpose | Example |
|----------|---------|---------|
| `truncatewords` | Truncate to word count | `{{/* text | truncatewords(50) */}}` |
| `truncatewords_html` | Truncate HTML preserving tags | `{{/* html | truncatewords_html(50) */}}` |
| `truncate_chars` | Truncate to character count | `{{ text | truncate_chars(200) }}` |
| `slugify` | Convert to URL-safe slug | `{{ title | slugify }}` |
| `markdownify` | Render markdown to HTML | `{{ md | markdownify | safe }}` |
| `strip_html` | Remove HTML tags | `{{ html | strip_html }}` |
| `replace_regex` | Replace using regex | `{{ text | replace_regex('\\d+', 'N') }}` |
| `pluralize` | Singular/plural forms | `{{ count | pluralize('item') }}` |
| `reading_time` | Calculate read time | `{{ content | reading_time }} min` |
| `excerpt` | Extract smart excerpt | `{{ text | excerpt(200) }}` |
| `strip_whitespace` | Normalize whitespace | `{{ text | strip_whitespace }}` |

[→ Full String Functions Documentation](strings.md)

---

### Collection Functions (8 functions)
**Module:** `collections`  
Powerful operations on lists and dictionaries.

| Function | Purpose | Example |
|----------|---------|---------|
| `where` | Filter by field value | `{{ posts | where('draft', false) }}` |
| `where_not` | Exclude by field value | `{{ posts | where_not('hidden', true) }}` |
| `group_by` | Group items by field | `{{ posts | group_by('category') }}` |
| `sort_by` | Sort by field | `{{ posts | sort_by('date', reverse=true) }}` |
| `unique` | Remove duplicates | `{{ tags | unique }}` |
| `first` | Get first N items | `{{ posts | first(5) }}` |
| `last` | Get last N items | `{{ posts | last(3) }}` |
| `limit` | Limit collection size | `{{ posts | limit(10) }}` |

[→ Full Collection Functions Documentation](collections.md)

---

### Math Functions (6 functions)
**Module:** `math_functions`  
Mathematical operations for calculations.

| Function | Purpose | Example |
|----------|---------|---------|
| `percentage` | Calculate percentage | `{{ part | percentage(total, 1) }}%` |
| `times` | Multiply | `{{ 5 | times(3) }}` |
| `divided_by` | Divide | `{{ 10 | divided_by(3, decimals=2) }}` |
| `ceil` | Round up | `{{ 3.2 | ceil }}` |
| `floor` | Round down | `{{ 3.8 | floor }}` |
| `round` | Round to decimals | `{{ 3.14159 | round(2) }}` |

[→ Full Math Functions Documentation](math.md)

---

### Date Functions (3 functions)
**Module:** `dates`  
Date/time formatting and calculations.

| Function | Purpose | Example |
|----------|---------|---------|
| `time_ago` | Relative time | `{{ date | time_ago }}` |
| `format_date` | Format date | `{{ date | format_date('%Y-%m-%d') }}` |
| `year` | Extract year | `{{ date | year }}` |

[→ Full Date Functions Documentation](dates.md)

---

### URL Functions (3 functions)
**Module:** `urls`  
URL manipulation and generation.

| Function | Purpose | Example |
|----------|---------|---------|
| `absolute_url` | Make URL absolute | `{{ url | absolute_url(base_url) }}` |
| `relative_url` | Make URL relative | `{{ url | relative_url }}` |
| `url_encode` | Encode for URLs | `{{ text | url_encode }}` |

[→ Full URL Functions Documentation](urls.md)

---

### Content Functions (6 functions)
**Module:** `content`  
Content transformation and safety.

| Function | Purpose | Example |
|----------|---------|---------|
| `safe_html` | Mark HTML as safe | `{{ html | safe_html }}` |
| `nl2br` | Newlines to `<br>` | `{{ text | nl2br }}` |
| `wordwrap` | Wrap text | `{{ text | wordwrap(80) }}` |
| `escape_html` | Escape HTML | `{{ text | escape_html }}` |
| `markdown_to_plain` | Extract plain text | `{{ md | markdown_to_plain }}` |
| `summary` | Generate summary | `{{ content | summary(150) }}` |

[→ Full Content Functions Documentation](content.md)

---

### Data Functions (8 functions)
**Module:** `data`  
Data manipulation (JSON, YAML, nested structures).

| Function | Purpose | Example |
|----------|---------|---------|
| `get_data` | Load data file | `{{ get_data('features.yaml') }}` |
| `jsonify` | Convert to JSON | `{{ obj | jsonify }}` |
| `merge` | Merge dictionaries | `{{ dict1 | merge(dict2) }}` |
| `has_key` | Check key exists | `{{ obj | has_key('field') }}` |
| `get_nested` | Get nested value | `{{ obj | get_nested('a.b.c') }}` |
| `keys` | Get dictionary keys | `{{ obj | keys }}` |
| `values` | Get dictionary values | `{{ obj | values }}` |
| `items` | Get key-value pairs | `{{ obj | items }}` |

[→ Full Data Functions Documentation](data.md)

---

### File Functions (3 functions)
**Module:** `files`  
File system operations.

| Function | Purpose | Example |
|----------|---------|---------|
| `read_file` | Read file contents | `{{ read_file('data.txt') }}` |
| `file_exists` | Check file exists | `file_exists('config.yaml')` |
| `file_size` | Get file size | `{{ file_size('image.jpg') }} bytes` |

[→ Full File Functions Documentation](files.md)

---

### Advanced String Functions (3 functions)
**Module:** `advanced_strings`  
Advanced text transformations.

| Function | Purpose | Example |
|----------|---------|---------|
| `camelize` | Convert to camelCase | `{{ text | camelize }}` |
| `underscore` | Convert to snake_case | `{{ text | underscore }}` |
| `titleize` | Smart title case | `{{ text | titleize }}` |

[→ Full Advanced String Functions Documentation](advanced-strings.md)

---

### Advanced Collection Functions (3 functions)
**Module:** `advanced_collections`  
Advanced collection operations.

| Function | Purpose | Example |
|----------|---------|---------|
| `sample` | Random sample | `{{ posts | sample(3) }}` |
| `shuffle` | Randomize order | `{{ items | shuffle }}` |
| `chunk` | Split into chunks | `{{ items | chunk(3) }}` |

[→ Full Advanced Collection Functions Documentation](advanced-collections.md)

---

### Image Functions (6 functions)
**Module:** `images`  
Image handling and optimization.

| Function | Purpose | Example |
|----------|---------|---------|
| `image_url` | Generate image URL | `{{ image_url('hero.jpg', width=800) }}` |
| `image_tag` | Create `<img>` tag | `{{ image_tag('photo.jpg', alt='Photo') }}` |
| `responsive_image` | Responsive images | `{{ responsive_image('image.jpg') }}` |
| `image_dimensions` | Get width/height | `{{ image_dimensions('image.jpg') }}` |
| `thumbnail` | Create thumbnail URL | `{{ thumbnail('image.jpg', 150) }}` |
| `image_srcset` | Generate srcset | `{{ image_srcset('image.jpg', [400, 800]) }}` |

[→ Full Image Functions Documentation](images.md)

---

### SEO Functions (4 functions)
**Module:** `seo`  
SEO optimization helpers.

| Function | Purpose | Example |
|----------|---------|---------|
| `meta_description` | Generate meta description | `{{ content | meta_description(160) }}` |
| `meta_keywords` | Generate meta keywords | `{{ tags | meta_keywords }}` |
| `canonical_url` | Create canonical URL | `{{ canonical_url(page.url) }}` |
| `og_image` | Open Graph image URL | `{{ og_image('hero.jpg') }}` |

[→ Full SEO Functions Documentation](seo.md)

---

### Debug Functions (3 functions)
**Module:** `debug`  
Debugging and inspection.

| Function | Purpose | Example |
|----------|---------|---------|
| `debug` | Pretty-print variable | `{{ page | debug }}` |
| `typeof` | Get type | `{{ value | typeof }}` |
| `inspect` | Detailed inspection | `{{ obj | inspect }}` |

[→ Full Debug Functions Documentation](debug.md)

---

### Taxonomy Functions (4 functions)
**Module:** `taxonomies`  
Taxonomy and tagging operations.

| Function | Purpose | Example |
|----------|---------|---------|
| `related_posts` | Find related content | `{{ related_posts(page, all_pages, 5) }}` |
| `posts_by_tag` | Filter by tag | `{{ posts_by_tag('python', posts) }}` |
| `posts_by_category` | Filter by category | `{{ posts_by_category('tech', posts) }}` |
| `taxonomy_cloud` | Generate tag cloud | `{{ taxonomy_cloud(tags) }}` |

[→ Full Taxonomy Functions Documentation](taxonomies.md)

---

### Pagination Functions (3 functions)
**Module:** `pagination_helpers`  
Pagination controls.

| Function | Purpose | Example |
|----------|---------|---------|
| `paginate` | Paginate items | `{{ posts | paginate(10, page) }}` |
| `page_url` | Generate page URL | `{{ page_url('/posts/', 2) }}` |
| `page_range` | Page number range | `{{ page_range(current, total, 2) }}` |

[→ Full Pagination Functions Documentation](pagination.md)

---

### Cross-Reference Functions (5 functions)
**Module:** `crossref`  
Internal link handling.

| Function | Purpose | Example |
|----------|---------|---------|
| `ref` | Link to content | `{{ ref('docs/getting-started') }}` |
| `relref` | Relative link | `{{ relref('../sibling-page') }}` |
| `link_to` | Create link tag | `{{ link_to(page, 'Read more') }}` |
| `backlinks` | Find backlinks | `{{ backlinks(page) }}` |
| `validate_link` | Check link validity | `{{ validate_link(url) }}` |

[→ Full Cross-Reference Functions Documentation](crossref.md)

---

## 🚀 Quick Examples

### String Manipulation

```jinja2
{# Truncate post excerpt #}
<div class="excerpt">
  {{/* post.content | strip_html | truncatewords(50) */}}
</div>

{# Calculate reading time #}
<span class="reading-time">
  {{ post.content | reading_time }} min read
</span>

{# Create URL-friendly slug #}
{% set slug = post.title | slugify %}
<a href="/posts/{{ slug }}/">{{ post.title }}</a>
```

### Collection Operations

```jinja2
{# Filter published posts and sort by date #}
{% set published = posts | where('draft', false) | sort_by('date', reverse=true) %}

{# Get recent posts #}
{% for post in published | first(5) %}
  <article>{{ post.title }}</article>
{% endfor %}

{# Group posts by category #}
{% for category, posts in all_posts | group_by('category') %}
  <h2>{{ category }}</h2>
  <ul>
    {% for post in posts %}
      <li>{{ post.title }}</li>
    {% endfor %}
  </ul>
{% endfor %}
```

### SEO Optimization

```jinja2
{# Meta description #}
<meta name="description" content="{{ page.content | meta_description(160) }}">

{# Canonical URL #}
<link rel="canonical" href="{{ canonical_url(page.url) }}">

{# Open Graph image #}
<meta property="og:image" content="{{ og_image('images/hero.jpg') }}">

{# Keywords #}
<meta name="keywords" content="{{ page.tags | meta_keywords }}">
```

### Data and Calculations

```jinja2
{# Load external data #}
{% set features = get_data('features.yaml') %}

{# Calculate percentage #}
{{ completed | percentage(total, 1) }}% complete

{# Format date #}
Published {{ page.date | time_ago }}

{# Merge configuration #}
{% set config = defaults | merge(user_config) %}
```

---

## 📊 Function Coverage by Category

```{tabs}
:id: function-categories

### Tab: Text Processing

**11 String Functions + 3 Advanced String Functions = 14 total**

Perfect for:
- Truncating content
- Generating slugs
- Reading time calculation
- Text formatting
- Whitespace normalization

**Most used:**
- `truncatewords`
- `slugify`
- `reading_time`
- `excerpt`

### Tab: Collections

**8 Collection Functions + 3 Advanced Collection Functions = 11 total**

Perfect for:
- Filtering posts
- Sorting by date
- Grouping by category
- Removing duplicates
- Random selection

**Most used:**
- `where`
- `sort_by`
- `group_by`
- `first` / `last`

### Tab: Content & SEO

**6 Content Functions + 4 SEO Functions + 6 Image Functions = 16 total**

Perfect for:
- Meta tags generation
- Image optimization
- Content safety
- Open Graph tags
- Canonical URLs

**Most used:**
- `meta_description`
- `canonical_url`
- `image_url`
- `safe_html`

### Tab: Specialized

**6 Math + 3 Date + 3 URL + 8 Data + 3 File + 4 Taxonomy + 3 Pagination + 5 Crossref = 35 total**

Perfect for:
- Date formatting
- URL handling
- Math calculations
- Data loading
- File operations
- Related posts
- Pagination controls
- Internal links

**Most used:**
- `time_ago`
- `absolute_url`
- `get_data`
- `related_posts`
- `paginate`
```

---

## 🎯 Best Practices

```{note} Performance Tips
- Cache the results of expensive operations
- Use `first` or `limit` when you don't need all items
- Prefer `where` over template loops for filtering
- Use `get_data` sparingly - data is loaded on each call
```

```{tip} Chaining Filters
Filters can be chained for powerful transformations:

```jinja2
{{/* post.content | strip_html | truncatewords(50) | strip_whitespace */}}
```

This strips HTML, truncates to 50 words, then normalizes whitespace.
```

```{warning} Common Pitfalls
- Remember to use `| safe` after `markdownify` or HTML will be escaped
- `truncatewords_html` is not perfect at preserving all HTML structure
- `get_data` loads from the data directory, not content
- Pagination requires passing the current page number
```

---

## 📚 Module-by-Module Documentation

Click on any module below for complete documentation with examples, parameters, return types, and edge cases:

1. **[String Functions](strings.md)** - 11 functions for text manipulation
2. **[Collection Functions](collections.md)** - 8 functions for list/dict operations
3. **[Math Functions](math.md)** - 6 functions for calculations
4. **[Date Functions](dates.md)** - 3 functions for date/time
5. **[URL Functions](urls.md)** - 3 functions for URL handling
6. **[Content Functions](content.md)** - 6 functions for content transformation
7. **[Data Functions](data.md)** - 8 functions for data loading and manipulation
8. **[File Functions](files.md)** - 3 functions for file operations
9. **[Advanced String Functions](advanced-strings.md)** - 3 functions for advanced text transforms
10. **[Advanced Collection Functions](advanced-collections.md)** - 3 functions for advanced collection ops
11. **[Image Functions](images.md)** - 6 functions for image handling
12. **[SEO Functions](seo.md)** - 4 functions for SEO optimization
13. **[Debug Functions](debug.md)** - 3 functions for debugging
14. **[Taxonomy Functions](taxonomies.md)** - 4 functions for tags and categories
15. **[Pagination Functions](pagination.md)** - 3 functions for pagination controls
16. **[Cross-Reference Functions](crossref.md)** - 5 functions for internal links

---

## 🔍 Search by Use Case

```{dropdown} "I want to display post excerpts"

Use one of these approaches:

**Option 1: Simple word truncation**
```jinja2
{{/* post.content | truncatewords(50) */}}
```

**Option 2: Character limit with word boundaries**
```jinja2
{{ post.content | excerpt(200) }}
```

**Option 3: Strip HTML first**
```jinja2
{{/* post.html_content | strip_html | truncatewords(50) */}}
```

**Option 4: Meta description (best for SEO)**
```jinja2
{{ post.content | meta_description(160) }}
```
```

```{dropdown} "I want to filter and sort posts"

**Filter by field:**
```jinja2
{% set published = posts | where('draft', false) %}
```

**Sort by date (newest first):**
```jinja2
{% set sorted = posts | sort_by('date', reverse=true) %}
```

**Combine filtering and sorting:**
```jinja2
{% set recent = posts 
    | where('draft', false) 
    | sort_by('date', reverse=true)
    | first(10) 
%}
```
```

```{dropdown} "I want to calculate reading time"

**Basic reading time:**
```jinja2
{{ post.content | reading_time }} min read
```

**Custom words per minute:**
```jinja2
{{ post.content | reading_time(250) }} min read
```

**Full example:**
```jinja2
<div class="post-meta">
  <span class="date">{{ post.date | time_ago }}</span>
  <span class="reading-time">{{ post.content | reading_time }} min read</span>
</div>
```
```

```{dropdown} "I want to create SEO-friendly URLs"

**Create slug from title:**
```jinja2
{% set slug = post.title | slugify %}
<a href="/posts/{{ slug }}/">{{ post.title }}</a>
```

**Generate canonical URL:**
```jinja2
<link rel="canonical" href="{{ canonical_url(page.url) }}">
```

**Encode parameters:**
```jinja2
<a href="/search?q={{ query | url_encode }}">Search</a>
```
```

```{dropdown} "I want to group posts by category or tag"

**Group by category:**
```jinja2
{% for category, posts in all_posts | group_by('category') %}
  <section>
    <h2>{{ category }}</h2>
    <ul>
      {% for post in posts %}
        <li>{{ post.title }}</li>
      {% endfor %}
    </ul>
  </section>
{% endfor %}
```

**Posts by specific tag:**
```jinja2
{% set python_posts = posts_by_tag('python', all_posts) %}
```
```

```{dropdown} "I want to load external data"

**Load YAML data:**
```jinja2
{% set features = get_data('features.yaml') %}
{% for feature in features %}
  <div>{{ feature.name }}</div>
{% endfor %}
```

**Load and merge config:**
```jinja2
{% set config = defaults | merge(user_settings) %}
```

**Check if key exists:**
```jinja2
{% if page | has_key('author') %}
  By {{ page.author }}
{% endif %}
```
```

---

## 🎓 Learning Path

```{tabs}
:id: learning-path

### Tab: Beginners

**Start with these essential functions:**

1. **String manipulation**
   - `truncatewords` - Shorten content
   - `slugify` - Create URLs
   - `reading_time` - Show read time

2. **Collections**
   - `where` - Filter posts
   - `sort_by` - Order posts
   - `first` - Get recent posts

3. **Dates**
   - `time_ago` - Relative dates
   - `format_date` - Format dates

**Next:** Try combining filters: `posts | where('draft', false) | sort_by('date', reverse=true) | first(5)`

### Tab: Intermediate

**Add these to your toolkit:**

1. **SEO optimization**
   - `meta_description` - Meta tags
   - `canonical_url` - Canonical URLs
   - `og_image` - Social media images

2. **Advanced collections**
   - `group_by` - Group posts
   - `unique` - Remove duplicates
   - `sample` - Random selection

3. **Data handling**
   - `get_data` - Load external data
   - `jsonify` - Output JSON
   - `merge` - Combine configs

### Tab: Advanced

**Master these for complete control:**

1. **Taxonomy & relations**
   - `related_posts` - Find similar content
   - `posts_by_tag` - Tag filtering
   - `taxonomy_cloud` - Tag clouds

2. **Pagination**
   - `paginate` - Paginate items
   - `page_url` - Page URLs
   - `page_range` - Page controls

3. **Cross-references**
   - `ref` - Internal links
   - `backlinks` - Find backlinks
   - `validate_link` - Check links

4. **Images & optimization**
   - `responsive_image` - Responsive images
   - `image_srcset` - Srcset generation
   - `thumbnail` - Thumbnails
```

---

## 💡 Pro Tips

```{success} Composition Power
The real power comes from composing functions:

```jinja2
{# Get 5 random published posts from last year, sorted by title #}
{% set featured = posts 
    | where('draft', false)
    | where('year', 2024)
    | sort_by('title')
    | sample(5)
%}
```

This is more powerful than loops and more readable!
```

```{tip} Template Macros
Combine functions in reusable macros:

```jinja2
{% macro post_card(post) %}
  <article class="post-card">
    <h2><a href="{{ post.url }}">{{ post.title }}</a></h2>
    <div class="meta">
      {{ post.date | time_ago }} · {{ post.content | reading_time }} min
    </div>
    <p>{{ post.content | strip_html | excerpt(150) }}</p>
  </article>
{% endmacro %}
```
```

---

## 📖 Related Documentation

- **[Kitchen Sink](../../markdown/kitchen-sink.md)** - See all directives and features in action
- **[Template System](../../templates/template-basics.md)** - Learn Jinja2 templating basics
- **[Template Inheritance](../../templates/template-inheritance.md)** - Master template inheritance
- **[Custom Templates](../../templates/custom-templates.md)** - Create your own templates

---

**Total Function Count:** 75+ functions across 16 modules  
**Coverage:** 100% documented with examples  
**Updated:** October 4, 2025  
**Version:** 1.0.0

