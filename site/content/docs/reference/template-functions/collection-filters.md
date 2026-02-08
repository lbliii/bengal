---
title: Collection Filters
description: Filter, sort, group, and transform collections of pages or items
weight: 10
tags:
- reference
- filters
- collections
- where
- sort
category: reference
---

# Collection Filters

These filters work with lists of pages, dictionaries, or any iterable.

## where

Filter items where a key matches a value. Supports Hugo-like comparison operators.

:::{example-label} Basic Usage
:::

```kida
{# Filter by exact value (default) #}
{% let tutorials = site.pages |> where('category', 'tutorial') %}

{# Filter by nested attribute #}
{% let track_pages = site.pages |> where('metadata.track_id', 'getting-started') %}
```

:::{example-label} With Comparison Operators
:::

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal (default) | `where('status', 'published', 'eq')` |
| `ne` | Not equal | `where('status', 'draft', 'ne')` |
| `gt` | Greater than | `where('date', one_year_ago, 'gt')` |
| `gte` | Greater than or equal | `where('priority', 5, 'gte')` |
| `lt` | Less than | `where('weight', 100, 'lt')` |
| `lte` | Less than or equal | `where('order', 10, 'lte')` |
| `in` | Value in list | `where('tags', 'python', 'in')` |
| `not_in` | Value not in list | `where('status', ['archived'], 'not_in')` |

:::{example-label} Operator Examples
:::

```kida
{# Pages newer than a year ago #}
{% let recent = site.pages |> where('date', one_year_ago, 'gt') %}

{# Pages with priority 5 or higher #}
{% let important = site.pages |> where('metadata.priority', 5, 'gte') %}

{# Pages tagged with 'python' #}
{% let python_posts = site.pages |> where('tags', 'python', 'in') %}

{# Pages with specific statuses #}
{% let active = site.pages |> where('status', ['active', 'featured'], 'in') %}

{# Exclude archived pages #}
{% let live = site.pages |> where('status', ['archived', 'draft'], 'not_in') %}
```

## where_not

Filter items where a key does NOT equal a value. Shorthand for `where(key, value, 'ne')`.

```kida
{# Exclude drafts #}
{% let published = site.pages |> where_not('draft', true) %}

{# Exclude archived items #}
{% let active = users |> where_not('status', 'archived') %}
```

## sort_by

Sort items by a key, with optional reverse order.

```kida
{# Sort by date, newest first #}
{% let recent = site.pages |> sort_by('date', reverse=true) %}

{# Sort alphabetically by title #}
{% let alphabetical = site.pages |> sort_by('title') %}

{# Sort by weight (ascending) #}
{% let ordered = sections |> sort_by('weight') %}
```

## group_by

Group items by a key value, returning a dictionary.

```kida
{% let by_category = site.pages |> group_by('category') %}

{% for category, pages in by_category.items() %}
<h2>{{ category }}</h2>
<ul>
  {% for page in pages %}
  <li><a href="{{ page.href }}">{{ page.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

## group_by_year

Group pages by publication year. Returns dictionary sorted by year (newest first).

```kida
{% let by_year = site.pages |> group_by_year %}

{% for year, posts in by_year.items() %}
<h2>{{ year }}</h2>
<ul>
  {% for post in posts %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

**Parameters:**
- `date_attr`: Attribute containing the date (default: `'date'`)

## group_by_month

Group pages by year-month. Returns dictionary keyed by `(year, month)` tuples.

```kida
{% let by_month = site.pages |> group_by_month %}

{% for (year, month), posts in by_month.items() %}
<h2>{{ month | month_name }} {{ year }}</h2>
<ul>
  {% for post in posts %}
  <li><a href="{{ post.href }}">{{ post.title }}</a></li>
  {% end %}
</ul>
{% end %}
```

## archive_years

Get list of years with post counts for archive navigation.

```kida
{% let years = site.pages |> archive_years %}

<aside class="archive">
  <h3>Archive</h3>
  <ul>
    {% for item in years %}
    <li>
      <a href="/blog/{{ item.year }}/">{{ item.year }}</a>
      <span>({{ item.count }})</span>
    </li>
    {% end %}
  </ul>
</aside>
```

**Returns:** List of dicts with `year` and `count` keys, sorted newest first.

## limit

Take the first N items from a list.

```kida
{# Latest 5 posts #}
{% let latest = site.pages |> sort_by('date', reverse=true) |> limit(5) %}

{# Top 3 featured items #}
{% let featured = items |> where('featured', true) |> limit(3) %}
```

## offset

Skip the first N items from a list.

```kida
{# Skip first 10 items (pagination page 2) #}
{% let page_2 = items |> offset(10) |> limit(10) %}

{# Skip the featured post #}
{% let rest = posts |> offset(1) %}
```

## first

Get the first item from a list, or `None` if empty.

```kida
{# Get the featured post #}
{% let featured = site.pages |> where('metadata.featured', true) |> first %}

{% if featured %}
<div class="hero">
  <h1>{{ featured.title }}</h1>
</div>
{% end %}
```

## last

Get the last item from a list, or `None` if empty.

```kida
{# Get the oldest post #}
{% let oldest = site.pages |> sort_by('date') |> last %}

{# Get the final step #}
{% let final_step = steps |> last %}
```

## reverse

Reverse a list (returns a new list, original unchanged).

```kida
{# Oldest first #}
{% let chronological = site.pages |> sort_by('date') %}

{# Newest first (reversed) #}
{% let newest_first = chronological |> reverse %}
```

## uniq

Remove duplicate items while preserving order.

```kida
{# Get unique tags from all posts #}
{% let all_tags = [] %}
{% for page in site.pages %}
  {% let all_tags = all_tags + page.tags %}
{% end %}
{% let unique_tags = all_tags | uniq %}
```

## flatten

Flatten nested lists into a single list.

```kida
{# Combine all tags from all pages #}
{% let nested_tags = site.pages |> map(attribute='tags') |> list %}
{% let all_tags = nested_tags |> flatten |> uniq %}
```

## resolve_pages

Convert page paths (from indexes) to Page objects. Uses cached lookups for O(1) performance.

```kida
{# Get paths from index, then resolve to pages #}
{% let author_paths = site.indexes.author.get('Jane Smith') %}
{% let author_posts = author_paths | resolve_pages %}

{% for post in author_posts | sort_by('date', reverse=true) %}
  <h2>{{ post.title }}</h2>
{% end %}
```

**Use case:** Site indexes store page paths (strings) for efficiency. Use `resolve_pages` when you need full Page objects from index results.

---

## Set Operations

Perform set operations on lists of pages or items.

### union

Combine two lists, removing duplicates.

```kida
{# Combine featured and recent posts #}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let recent = site.pages |> sort_by('date', reverse=true) |> limit(5) %}
{% let combined = featured |> union(recent) %}
```

### intersect

Get items that appear in both lists.

```kida
{# Posts that are both featured AND tagged 'python' #}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let python = site.pages |> where('tags', 'python', 'in') %}
{% let featured_python = featured |> intersect(python) %}
```

### complement

Get items in the first list that are NOT in the second list.

```kida
{# All posts except featured ones #}
{% let all_posts = site.pages |> where('type', 'post') %}
{% let featured = site.pages |> where('metadata.featured', true) %}
{% let regular = all_posts |> complement(featured) %}
```

## Chaining Filters

Filters can be chained for powerful queries:

```kida
{# Recent Python tutorials, sorted by date #}
{% let result = site.pages
  |> where('category', 'tutorial')
  |> where('tags', 'python', 'in')
  |> where('draft', false)
  |> sort_by('date', reverse=true)
  |> limit(10) %}
```

## Hugo Migration Guide

Bengal's template functions are designed for easy migration from Hugo. Here's how common Hugo patterns translate:

### Filtering Pages

**Hugo:**
```go-html-template
{{ $posts := where .Site.RegularPages "Section" "blog" }}
{{ $recent := where .Site.RegularPages ".Date" ">" (now.AddDate -1 0 0) }}
```

**Bengal:**
```kida
{% let posts = site.pages |> where('section', 'blog') %}
{% let recent = site.pages |> where('date', one_year_ago, 'gt') %}
```

### Sorting

**Hugo:**
```go-html-template
{{ range .Site.RegularPages.ByDate.Reverse }}
{{ range sort .Site.RegularPages "Title" }}
```

**Bengal:**
```kida
{% for page in site.pages |> sort_by('date', reverse=true) %}
{% for page in site.pages |> sort_by('title') %}
```

### First/Last

**Hugo:**
```go-html-template
{{ $featured := (where .Site.RegularPages "Params.featured" true).First }}
{{ $oldest := .Site.RegularPages.ByDate.Last }}
```

**Bengal:**
```kida
{% let featured = site.pages |> where('metadata.featured', true) |> first %}
{% let oldest = site.pages |> sort_by('date') |> last %}
```

### Limiting

**Hugo:**
```go-html-template
{{ range first 5 .Site.RegularPages }}
```

**Bengal:**
```kida
{% for page in site.pages |> limit(5) %}
```

### Set Operations

**Hugo:**
```go-html-template
{{ $both := intersect $list1 $list2 }}
{{ $combined := union $list1 $list2 }}
{{ $diff := complement $list1 $list2 }}
```

**Bengal:**
```kida
{% let both = list1 |> intersect(list2) %}
{% let combined = list1 |> union(list2) %}
{% let diff = list1 |> complement(list2) %}
```

### Tag Filtering

**Hugo:**
```go-html-template
{{ $tagged := where .Site.RegularPages "Params.tags" "intersect" (slice "python" "web") }}
```

**Bengal:**
```kida
{# Check if page has 'python' tag #}
{% let tagged = site.pages |> where('tags', 'python', 'in') %}

{# Check if page has any of these tags #}
{% let tagged = site.pages |> where('tags', ['python', 'web'], 'in') %}
```

### Complex Queries

**Hugo:**
```go-html-template
{{ $result := where (where .Site.RegularPages "Section" "blog") ".Params.featured" true }}
```

**Bengal:**
```kida
{% let result = site.pages |> where('section', 'blog') |> where('metadata.featured', true) %}
```

## Quick Reference

| Filter | Purpose | Example |
|--------|---------|---------|
| `where(key, val)` | Filter by value | `pages \| where('type', 'post')` |
| `where(key, val, 'gt')` | Greater than | `pages \| where('date', cutoff, 'gt')` |
| `where(key, val, 'in')` | Value in list | `pages \| where('tags', 'python', 'in')` |
| `where_not(key, val)` | Exclude value | `pages \| where_not('draft', true)` |
| `sort_by(key)` | Sort ascending | `pages \| sort_by('title')` |
| `sort_by(key, reverse=true)` | Sort descending | `pages \| sort_by('date', reverse=true)` |
| `group_by(key)` | Group by value | `pages \| group_by('category')` |
| `limit(n)` | Take first N | `pages \| limit(5)` |
| `offset(n)` | Skip first N | `pages \| offset(10)` |
| `first` | First item | `pages \| first` |
| `last` | Last item | `pages \| last` |
| `reverse` | Reverse order | `pages \| reverse` |
| `uniq` | Remove duplicates | `tags \| uniq` |
| `flatten` | Flatten nested lists | `nested \| flatten` |
| `union(list2)` | Combine lists | `list1 \| union(list2)` |
| `intersect(list2)` | Common items | `list1 \| intersect(list2)` |
| `complement(list2)` | Difference | `list1 \| complement(list2)` |
