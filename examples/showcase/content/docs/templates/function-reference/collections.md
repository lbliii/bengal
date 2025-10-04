---
title: "Collection Functions"
description: "8 powerful functions for filtering, sorting, and transforming lists and collections"
date: 2025-10-04
weight: 2
tags: ["templates", "functions", "collections", "lists", "filtering"]
toc: true
---

# Collection Functions

Bengal provides **8 powerful collection functions** for filtering, sorting, grouping, and transforming lists and dictionaries in templates. These are essential for working with posts, pages, tags, and any list data.

---

## 📚 Function Overview

| Function | Purpose | Example |
|----------|---------|---------|
| `where` | Filter by key=value | `{{ posts | where('draft', false) }}` |
| `where_not` | Exclude by key=value | `{{ posts | where_not('hidden', true) }}` |
| `group_by` | Group items by key | `{{ posts | group_by('category') }}` |
| `sort_by` | Sort by key | `{{ posts | sort_by('date', reverse=true) }}` |
| `limit` | Take first N items | `{{ posts | limit(5) }}` |
| `offset` | Skip first N items | `{{ posts | offset(10) }}` |
| `uniq` | Remove duplicates | `{{ tags | uniq }}` |
| `flatten` | Flatten nested lists | `{{ nested | flatten }}` |

---

## 🔍 where

Filter items where key equals value.

### Signature

```jinja2
{{ items | where(key, value) }}
```

### Parameters

- **items** (list): List of dictionaries or objects to filter
- **key** (str): Dictionary key or object attribute to check
- **value** (any): Value to match

### Returns

Filtered list containing only items where `item[key] == value`.

### Examples

#### Filter Published Posts

```jinja2
{# Get only published posts #}
{% set published = posts | where('draft', false) %}

{% for post in published %}
  <article>{{ post.title }}</article>
{% endfor %}
```

#### Filter by Category

```jinja2
{# Get posts in specific category #}
{% set tutorials = posts | where('category', 'tutorial') %}
{% set guides = posts | where('category', 'guide') %}
```

#### Filter by Tag

```jinja2
{# Get posts with specific tag #}
{% set python_posts = posts | where('tags', 'python') %}
```

**Note:** For tags (lists), use `posts_by_tag` function instead for better matching.

#### Chain with Sort and Limit

```jinja2
{# Get 5 most recent published posts #}
{% set recent = posts 
    | where('draft', false) 
    | sort_by('date', reverse=true) 
    | limit(5) 
%}
```

### Advanced Examples

```{example} Complex Filtering

**Filter by multiple criteria:**
```jinja2
{# Published posts in specific category #}
{% set featured = posts 
    | where('draft', false)
    | where('featured', true)
    | where('category', 'tutorial')
%}
```

**Filter by year:**
```jinja2
{# Posts from 2025 #}
{% set posts_2025 = posts | where('year', 2025) %}
```

**Filter pages in section:**
```jinja2
{# Get all docs pages #}
{% set docs = all_pages | where('section', 'docs') %}
```
```

### Works With Objects and Dicts

```{note} Flexible Access
The `where` filter works with both:
- **Dictionaries:** `item['key']`
- **Objects:** `item.key`

Example:
```jinja2
{# Both work #}
{{ pages | where('type', 'post') }}  {# object.type #}
{{ data | where('status', 'active') }}  {# dict['status'] #}
```
```

---

## 🚫 where_not

Filter items where key does NOT equal value (exclude matching items).

### Signature

```jinja2
{{ items | where_not(key, value) }}
```

### Parameters

- **items** (list): List to filter
- **key** (str): Key to check
- **value** (any): Value to exclude

### Returns

Filtered list containing only items where `item[key] != value`.

### Examples

#### Exclude Drafts

```jinja2
{# Get all non-draft posts #}
{% set published = posts | where_not('draft', true) %}
```

#### Exclude Hidden Pages

```jinja2
{# Get all visible pages #}
{% set visible = pages | where_not('hidden', true) %}
```

#### Exclude Archive

```jinja2
{# Get current posts (not archived) #}
{% set current = posts | where_not('status', 'archived') %}
```

### Comparison with where

````{tabs}
:id: where-vs-where-not

### Tab: where (Include)

**Include matching items:**
```jinja2
{% set tutorials = posts | where('category', 'tutorial') %}
```

Result: Only posts WHERE category IS 'tutorial'

**Use when:** You know what you want

### Tab: where_not (Exclude)

**Exclude matching items:**
```jinja2
{% set not_tutorials = posts | where_not('category', 'tutorial') %}
```

Result: All posts WHERE category IS NOT 'tutorial'

**Use when:** You know what you don't want
````

### Combine Both

````{example} Include and Exclude

```jinja2
{# Published posts, excluding archived #}
{% set active = posts
    | where('draft', false)
    | where_not('archived', true)
    | sort_by('date', reverse=true)
%}
```

**Result:** Posts that ARE published AND are NOT archived
````

---

## 📊 group_by

Group items by a key value.

### Signature

```jinja2
{{ items | group_by(key) }}
```

### Parameters

- **items** (list): List to group
- **key** (str): Key to group by

### Returns

Dictionary mapping key values to lists of items: `{key_value: [items...]}`

### Examples

#### Group Posts by Category

```jinja2
{# Group all posts by category #}
{% set by_category = posts | group_by('category') %}

{% for category, category_posts in by_category.items() %}
  <section>
    <h2>{{ category }} ({{ category_posts | length }})</h2>
    <ul>
      {% for post in category_posts %}
        <li><a href="{{ post.url }}">{{ post.title }}</a></li>
      {% endfor %}
    </ul>
  </section>
{% endfor %}
```

**Output:**
```html
<section>
  <h2>Tutorials (15)</h2>
  <ul>
    <li><a href="/post1/">First Tutorial</a></li>
    ...
  </ul>
</section>
<section>
  <h2>Guides (8)</h2>
  ...
</section>
```

#### Group by Year

```jinja2
{# Archive by year #}
{% set by_year = posts | group_by('year') %}

{% for year, year_posts in by_year.items() | sort(reverse=true) %}
  <div class="year-archive">
    <h2>{{ year }}</h2>
    <ul>
      {% for post in year_posts | sort_by('date', reverse=true) %}
        <li>
          <span class="date">{{ post.date | format_date('%b %d') }}</span>
          <a href="{{ post.url }}">{{ post.title }}</a>
        </li>
      {% endfor %}
    </ul>
  </div>
{% endfor %}
```

#### Group by Author

```jinja2
{# Posts by author #}
{% set by_author = posts | group_by('author') %}

{% for author, author_posts in by_author.items() %}
  <div class="author-section">
    <h3>{{ author }} ({{ author_posts | length }} posts)</h3>
    {% for post in author_posts | sort_by('date', reverse=true) | limit(5) %}
      <article>{{ post.title }}</article>
    {% endfor %}
  </div>
{% endfor %}
```

### Advanced Patterns

```{example} Nested Grouping

**Group by category, then sort each group:**
```jinja2
{% set by_category = posts | where('draft', false) | group_by('category') %}

{% for category in categories %}
  <section>
    <h2>{{ category }}</h2>
    {% for post in by_category.get(category, []) | sort_by('date', reverse=true) %}
      <article>{{ post.title }}</article>
    {% endfor %}
  </section>
{% endfor %}
```

**Count items per group:**
```jinja2
{% set by_tag = posts | group_by('primary_tag') %}

<h3>Popular Tags</h3>
<ul>
  {% for tag, tag_posts in by_tag.items() | sort(attribute=1, reverse=true) %}
    <li>{{ tag }}: {{ tag_posts | length }} posts</li>
  {% endfor %}
</ul>
```
```

---

## 🔢 sort_by

Sort items by a key value.

### Signature

```jinja2
{{ items | sort_by(key, reverse=False) }}
```

### Parameters

- **items** (list): List to sort
- **key** (str): Key to sort by
- **reverse** (bool, optional): Sort descending. Default: `False` (ascending)

### Returns

Sorted list.

### Examples

#### Sort by Date (Newest First)

```jinja2
{# Most recent posts first #}
{% set recent = posts | sort_by('date', reverse=true) %}

{% for post in recent %}
  <article>
    <time>{{ post.date }}</time>
    <h2>{{ post.title }}</h2>
  </article>
{% endfor %}
```

#### Sort Alphabetically

```jinja2
{# Sort pages by title #}
{% set pages_alpha = pages | sort_by('title') %}

<ul class="index">
  {% for page in pages_alpha %}
    <li><a href="{{ page.url }}">{{ page.title }}</a></li>
  {% endfor %}
</ul>
```

#### Sort by Weight

```jinja2
{# Sort by custom weight field (lowest first) #}
{% set ordered = pages | sort_by('weight') %}

<nav>
  {% for page in ordered %}
    <a href="{{ page.url }}">{{ page.title }}</a>
  {% endfor %}
</nav>
```

#### Sort by Popularity

```jinja2
{# Sort by view count (highest first) #}
{% set popular = posts | sort_by('views', reverse=true) | limit(10) %}

<div class="popular-posts">
  <h3>Most Popular</h3>
  {% for post in popular %}
    <div>{{ post.title }} ({{ post.views }} views)</div>
  {% endfor %}
</div>
```

### Multiple Sort Keys

```{example} Complex Sorting

**Sort by category, then date within each category:**
```jinja2
{# Group first, then sort within groups #}
{% set by_category = posts | group_by('category') %}

{% for category, category_posts in by_category.items() %}
  <section>
    <h2>{{ category }}</h2>
    {% for post in category_posts | sort_by('date', reverse=true) %}
      <article>{{ post.title }}</article>
    {% endfor %}
  </section>
{% endfor %}
```

**Sort by boolean (featured first), then date:**
```jinja2
{# Two-stage sort #}
{% set featured = posts | where('featured', true) | sort_by('date', reverse=true) %}
{% set normal = posts | where_not('featured', true) | sort_by('date', reverse=true) %}

<section class="featured">
  {% for post in featured %}
    <article>{{ post.title }}</article>
  {% endfor %}
</section>

<section class="normal">
  {% for post in normal %}
    <article>{{ post.title }}</article>
  {% endfor %}
</section>
```
```

---

## ✂️ limit

Limit items to first N items.

### Signature

```jinja2
{{ items | limit(count) }}
```

### Parameters

- **items** (list): List to limit
- **count** (int): Maximum number of items to return

### Returns

First N items from list.

### Examples

#### Show Recent 5 Posts

```jinja2
{# Show 5 most recent #}
{% set recent = posts | sort_by('date', reverse=true) | limit(5) %}

<div class="recent-posts">
  <h3>Recent Posts</h3>
  {% for post in recent %}
    <article>{{ post.title }}</article>
  {% endfor %}
</div>
```

#### Top 3 Popular Posts

```jinja2
{# Top 3 by views #}
{% set top_3 = posts | sort_by('views', reverse=true) | limit(3) %}
```

#### Pagination (First Page)

```jinja2
{# First 10 posts (page 1) #}
{% set page_size = 10 %}
{% set page_1 = posts | sort_by('date', reverse=true) | limit(page_size) %}
```

### Combine with offset for Pagination

```{example} Manual Pagination

```jinja2
{% set page_size = 10 %}
{% set page_num = 1 %}  {# or from URL #}
{% set start = (page_num - 1) * page_size %}

{# Get one page of posts #}
{% set page_posts = posts 
    | sort_by('date', reverse=true)
    | offset(start)
    | limit(page_size)
%}

<div class="posts">
  {% for post in page_posts %}
    <article>{{ post.title }}</article>
  {% endfor %}
</div>

{# Pagination controls #}
<nav class="pagination">
  {% if page_num > 1 %}
    <a href="?page={{ page_num - 1 }}">Previous</a>
  {% endif %}
  
  {% if posts | length > page_num * page_size %}
    <a href="?page={{ page_num + 1 }}">Next</a>
  {% endif %}
</nav>
```
```

---

## ⏭️ offset

Skip first N items.

### Signature

```jinja2
{{ items | offset(count) }}
```

### Parameters

- **items** (list): List to skip from
- **count** (int): Number of items to skip

### Returns

Items after skipping first N items.

### Examples

#### Skip First Post (Already Featured)

```jinja2
{# Show first post differently #}
{% set first_post = posts | sort_by('date', reverse=true) | first %}
{% set rest = posts | sort_by('date', reverse=true) | offset(1) %}

<article class="featured">
  <h1>{{ first_post.title }}</h1>
  {{ first_post.content }}
</article>

<div class="other-posts">
  {% for post in rest | limit(10) %}
    <article class="summary">{{ post.title }}</article>
  {% endfor %}
</div>
```

#### Pagination (Page 2)

```jinja2
{# Second page - skip first 10 #}
{% set page_2 = posts 
    | sort_by('date', reverse=true) 
    | offset(10) 
    | limit(10) 
%}
```

#### Older Posts Archive

```jinja2
{# Skip 20 most recent, show older #}
{% set archive = posts 
    | sort_by('date', reverse=true) 
    | offset(20) 
%}

<div class="archive">
  <h2>Older Posts</h2>
  {% for post in archive %}
    <div>{{ post.date | format_date('%Y-%m-%d') }} - {{ post.title }}</div>
  {% endfor %}
</div>
```

### Pagination Pattern

```{tip} Use with limit for Pagination
The classic pagination pattern:

```jinja2
{# Page N of results #}
{% set page_num = 2 %}  {# From URL #}
{% set page_size = 10 %}
{% set start = (page_num - 1) * page_size %}

{% set page_results = items | offset(start) | limit(page_size) %}
```

Or use the built-in `paginate` function for easier pagination!
```

---

## 🔖 uniq

Remove duplicate items while preserving order.

### Signature

```jinja2
{{ items | uniq }}
```

### Parameters

- **items** (list): List with potential duplicates

### Returns

List with duplicates removed, maintaining original order.

### Examples

#### Remove Duplicate Tags

```jinja2
{# Collect all tags from posts #}
{% set all_tags = [] %}
{% for post in posts %}
  {% set _ = all_tags.extend(post.tags) %}
{% endfor %}

{# Remove duplicates #}
{% set unique_tags = all_tags | uniq | sort %}

<div class="tag-cloud">
  {% for tag in unique_tags %}
    <a href="/tags/{{ tag | slugify }}/" class="tag">{{ tag }}</a>
  {% endfor %}
</div>
```

#### Unique Categories

```jinja2
{# Get unique categories #}
{% set categories = posts | map(attribute='category') | list | uniq %}

<nav class="categories">
  {% for category in categories | sort %}
    <a href="/{{ category }}/">{{ category }}</a>
  {% endfor %}
</nav>
```

#### Deduplicate Related Posts

```jinja2
{# Get related posts without duplicates #}
{% set related = [] %}
{% for tag in page.tags %}
  {% set _ = related.extend(posts | where('tags', tag)) %}
{% endfor %}

{% set unique_related = related | uniq | where_not('url', page.url) | limit(5) %}

<aside class="related">
  <h3>Related Posts</h3>
  {% for post in unique_related %}
    <article>{{ post.title }}</article>
  {% endfor %}
</aside>
```

### Behavior with Objects

```{note} Works with All Types
`uniq` works with:
- **Simple types:** strings, numbers, booleans
- **Objects:** Compares by identity (same object)
- **Dicts:** Uses linear search (slower for large lists)

For best performance with large lists of objects, use `where` filtering instead.
```

---

## 📦 flatten

Flatten nested lists into a single list (one level).

### Signature

```jinja2
{{ items | flatten }}
```

### Parameters

- **items** (list): List of lists to flatten

### Returns

Flattened list (one level deep only).

### Examples

#### Flatten Tags from All Posts

```jinja2
{# Collect and flatten tags #}
{% set all_tags = posts | map(attribute='tags') | list | flatten | uniq %}

<div class="all-tags">
  {% for tag in all_tags | sort %}
    <span class="tag">{{ tag }}</span>
  {% endfor %}
</div>
```

**How it works:**
```jinja2
posts | map(attribute='tags')  {# [[tag1, tag2], [tag3, tag4], ...] #}
| list                          {# Convert to list #}
| flatten                       {# [tag1, tag2, tag3, tag4, ...] #}
| uniq                          {# Remove duplicates #}
```

#### Combine Multiple Lists

```jinja2
{# Combine featured and regular posts #}
{% set featured = posts | where('featured', true) | limit(3) %}
{% set recent = posts | where_not('featured', true) | limit(5) %}

{% set combined = [featured, recent] | flatten %}

{% for post in combined %}
  <article>{{ post.title }}</article>
{% endfor %}
```

#### Flatten Nested Categories

```jinja2
{# If categories is list of lists #}
{% set nested_cats = [['python', 'django'], ['javascript', 'react'], ['devops']] %}
{% set all_cats = nested_cats | flatten %}

{# Result: ['python', 'django', 'javascript', 'react', 'devops'] #}
```

### One Level Only

```{warning} Single Level Flattening
`flatten` only flattens **one level** deep:

```jinja2
{% set nested = [[1, 2], [3, 4]] | flatten %}
{# Result: [1, 2, 3, 4] ✓ #}

{% set deeply_nested = [[[1, 2]], [[3, 4]]] | flatten %}
{# Result: [[1, 2], [3, 4]] (still nested!) #}
```

For deep nesting, apply flatten multiple times or use recursion.
```

---

## 🎯 Common Patterns

### Recent Posts Sidebar

```jinja2
<aside class="sidebar">
  <h3>Recent Posts</h3>
  <ul>
    {% for post in posts 
        | where('draft', false) 
        | sort_by('date', reverse=true) 
        | limit(5) 
    %}
      <li>
        <a href="{{ post.url }}">{{ post.title }}</a>
        <time>{{ post.date | time_ago }}</time>
      </li>
    {% endfor %}
  </ul>
</aside>
```

### Archive by Year and Month

```jinja2
{% set by_year = posts | where('draft', false) | group_by('year') %}

<nav class="archive">
  {% for year in by_year.keys() | sort(reverse=true) %}
    <div class="year">
      <h2>{{ year }}</h2>
      
      {% set by_month = by_year[year] | group_by('month') %}
      {% for month in by_month.keys() | sort(reverse=true) %}
        <div class="month">
          <h3>{{ month | month_name }}</h3>
          <ul>
            {% for post in by_month[month] | sort_by('date', reverse=true) %}
              <li><a href="{{ post.url }}">{{ post.title }}</a></li>
            {% endfor %}
          </ul>
        </div>
      {% endfor %}
    </div>
  {% endfor %}
</nav>
```

### Tag Cloud with Counts

```jinja2
{# Collect all tags #}
{% set all_tags = posts | map(attribute='tags') | list | flatten %}

{# Count occurrences #}
{% set tag_counts = {} %}
{% for tag in all_tags %}
  {% set _ = tag_counts.update({tag: tag_counts.get(tag, 0) + 1}) %}
{% endfor %}

{# Display tag cloud #}
<div class="tag-cloud">
  {% for tag, count in tag_counts.items() | sort %}
    <a href="/tags/{{ tag | slugify }}/" 
       class="tag tag-size-{{ (count / 5) | int }}">
      {{ tag }} ({{ count }})
    </a>
  {% endfor %}
</div>
```

### Featured + Recent Posts

```jinja2
{# Show featured posts differently #}
{% set featured = posts 
    | where('featured', true) 
    | where('draft', false)
    | sort_by('date', reverse=true) 
    | limit(3) 
%}

{% set recent = posts 
    | where_not('featured', true)
    | where('draft', false) 
    | sort_by('date', reverse=true) 
    | limit(10) 
%}

<section class="featured">
  <h2>Featured</h2>
  <div class="featured-grid">
    {% for post in featured %}
      <article class="featured-post">
        <h3>{{/* post.title */}}</h3>
        <p>{{/* post.content | strip_html | truncatewords(30) */}}</p>
      </article>
    {% endfor %}
  </div>
</section>

<section class="recent">
  <h2>Recent Posts</h2>
  {% for post in recent %}
    <article class="post-summary">
      <h3><a href="{{ post.url }}">{{ post.title }}</a></h3>
      <time>{{ post.date | time_ago }}</time>
    </article>
  {% endfor %}
</section>
```

---

## 📊 Performance Tips

```{success} Efficient Filtering

**Good:** Filter early, sort once
```jinja2
{% set results = posts 
    | where('draft', false)      # Filter first (fast)
    | where('category', 'tech')  # Filter more
    | sort_by('date', reverse=true)  # Then sort
    | limit(10)                  # Finally limit
%}
```

**Avoid:** Sorting before filtering
```jinja2
{% set results = posts 
    | sort_by('date', reverse=true)  # Sorting ALL posts
    | where('draft', false)          # Then filtering (wasted work)
%}
```

**Principle:** Filter → Sort → Limit (smallest to largest operation)
```

```{tip} Cache Expensive Operations

```jinja2
{# Cache filtered posts #}
{% set published_posts = posts | where('draft', false) %}

{# Reuse multiple times #}
{% set recent = published_posts | sort_by('date', reverse=true) | limit(5) %}
{% set by_cat = published_posts | group_by('category') %}
{% set total = published_posts | length %}
```

Avoid recalculating the same filter multiple times!
```

---

## 📚 Related Functions

- **[Advanced Collection Functions](advanced-collections.md)** - sample, shuffle, chunk
- **[Taxonomy Functions](taxonomies.md)** - related_posts, posts_by_tag
- **[Pagination Functions](pagination.md)** - paginate, page_url, page_range

---

## 💡 Best Practices

```{note} Chain Functions Logically

**Typical order:**
1. **Filter** (`where`, `where_not`) - Reduce dataset
2. **Group** (`group_by`) - Organize data
3. **Sort** (`sort_by`) - Order results
4. **Limit/Offset** (`limit`, `offset`) - Paginate

Example:
```jinja2
{% set results = posts
    | where('draft', false)           # 1. Filter
    | where('category', 'tutorial')   # 1. Filter more
    | sort_by('date', reverse=true)   # 2. Sort
    | limit(10)                       # 3. Limit
%}
```
```

```{warning} Empty Lists
All collection functions handle empty lists gracefully:

```jinja2
{% set empty = [] %}
{{ empty | where('key', 'value') }}  {# Returns [] #}
{{ empty | sort_by('date') }}        {# Returns [] #}
{{ empty | limit(10) }}              {# Returns [] #}
```

No need for `{% if items %}` checks before filtering!
```

```{success} Performance
Collection functions are **fast**:
- `where`: O(n) - linear scan
- `sort_by`: O(n log n) - Python's Timsort
- `group_by`: O(n log n) - sort + group
- `limit`/`offset`: O(1) - slice operation

Safe to chain multiple operations on 1000s of items!
```

---

**Module:** `bengal.rendering.template_functions.collections`  
**Functions:** 8  
**Last Updated:** October 4, 2025

