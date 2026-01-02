---
title: Section Statistics
description: Display post counts, word counts, and reading time totals
weight: 120
draft: false
lang: en
tags:
- cookbook
- sections
- statistics
keywords:
- post count
- word count
- reading time
- section stats
category: cookbook
---

# Section Statistics

Display statistics about sections like post counts, total word count, and reading time.

:::{note}
**Partial Default Theme Support**

Bengal's default theme includes some statistics:
- **Word count** in docs meta (`partials/docs-meta.html`)
- **Post count** in author listings

This recipe shows how to use section-level properties like `section.post_count`, `section.word_count`, and `section.total_reading_time`.
:::

## The Pattern

```kida
<div class="section-stats">
  <span>{{ section.post_count }} articles</span>
  <span>{{ section.word_count | commas }} words</span>
  <span>{{ section.total_reading_time }} min total</span>
</div>
```

## What's Happening

| Property | Purpose |
|----------|---------|
| `section.post_count` | Number of regular pages in section |
| `section.post_count_recursive` | Including all subsections |
| `section.word_count` | Total words across all pages (counts from rendered HTML content) |
| `section.total_reading_time` | Sum of all reading times (minutes) |

:::{note}
**Word Count Implementation**

`section.word_count` counts words from each page's rendered HTML content (with HTML tags stripped). This differs from `page.word_count`, which counts words from the raw markdown source. For consistency, you can also sum individual page word counts:

```kida
{% let total_words = section.sorted_pages |> map(attribute='word_count') |> sum %}
```
:::

## Variations

:::{tab-set}
:::{tab-item} Section Header

```kida
<header class="section-header">
  <h1>{{ section.title }}</h1>
  <p class="section-description">{{ section.description }}</p>

  <ul class="stats">
    <li>
      <strong>{{ section.post_count }}</strong>
      <span>Articles</span>
    </li>
    <li>
      <strong>{{ section.word_count | commas }}</strong>
      <span>Words</span>
    </li>
    <li>
      <strong>{{ section.total_reading_time }}</strong>
      <span>Minutes to read all</span>
    </li>
  </ul>
</header>
```

:::{/tab-item}
:::{tab-item} Sidebar Widget

```kida
<aside class="stats-widget">
  <h3>Blog Stats</h3>
  <dl>
    <dt>Total Posts</dt>
    <dd>{{ section.post_count_recursive }}</dd>

    <dt>Categories</dt>
    <dd>{{ section.subsections | length }}</dd>

    <dt>Total Words</dt>
    <dd>{{ section.word_count | commas }}</dd>

    <dt>Reading Time</dt>
    <dd>{{ section.total_reading_time }} min</dd>
  </dl>
</aside>
```

:::{/tab-item}
:::{tab-item} Comparison Table

```kida
<div class="subsection-stats">
  <h2>Categories</h2>
  <table>
    <thead>
      <tr>
        <th>Category</th>
        <th>Posts</th>
        <th>Words</th>
        <th>Reading Time</th>
      </tr>
    </thead>
    <tbody>
    {% for sub in section.subsections |> sort_by('post_count', reverse=true) %}
      <tr>
        <td><a href="{{ sub.href }}">{{ sub.title }}</a></td>
        <td>{{ sub.post_count }}</td>
        <td>{{ sub.word_count | commas }}</td>
        <td>{{ sub.total_reading_time }} min</td>
      </tr>
    {% end %}
    </tbody>
  </table>
</div>
```

:::{/tab-item}
:::{tab-item} Progress Bars

```kida
{% let max_posts = section.subsections |> map(attribute='post_count') |> max %}

<div class="category-bars">
{% for sub in section.subsections |> sort_by('post_count', reverse=true) %}
  <div class="category-bar">
    <a href="{{ sub.href }}">{{ sub.title }}</a>
    <div class="bar">
      <div class="fill" style="width: {{ (sub.post_count / max_posts * 100) | round }}%"></div>
    </div>
    <span>{{ sub.post_count }}</span>
  </div>
{% end %}
</div>
```

:::{/tab-item}
:::{tab-item} Site-Wide

```kida
{% let blog = get_section('blog') %}
{% let docs = get_section('docs') %}

<footer class="site-stats">
  <h3>This Site</h3>
  <div class="stats-grid">
    <div class="stat">
      <span class="value">{{ blog.post_count_recursive }}</span>
      <span class="label">Blog Posts</span>
    </div>
    <div class="stat">
      <span class="value">{{ docs.post_count_recursive }}</span>
      <span class="label">Doc Pages</span>
    </div>
    <div class="stat">
      <span class="value">{{ (blog.word_count + docs.word_count) | commas }}</span>
      <span class="label">Total Words</span>
    </div>
  </div>
</footer>
```

:::{/tab-item}
:::{tab-item} By Author

Combine with author data:

```kida
{% let posts = section.regular_pages %}
{% let authors = posts |> map(attribute='author') |> uniq %}

<div class="author-stats">
  <h3>Contributors</h3>
  <ul>
  {% for author in authors if author %}
    {% let author_posts = posts |> where('author.name', author.name) %}
    <li>
      <span>{{ author.name }}</span>
      <span>{{ author_posts | length }} posts</span>
    </li>
  {% end %}
  </ul>
</div>
```

:::{/tab-item}
:::{/tab-set}

## Example CSS

```css
.section-stats {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.section-stats span {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.stats {
  display: flex;
  gap: 2rem;
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.stats li {
  text-align: center;
}

.stats strong {
  display: block;
  font-size: 2rem;
  color: var(--accent);
}

.stats span {
  font-size: 0.875rem;
  color: var(--text-muted);
}

/* Progress bars */
.category-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.category-bar a {
  min-width: 120px;
}

.category-bar .bar {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.category-bar .fill {
  height: 100%;
  background: var(--accent);
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.stat {
  text-align: center;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.stat .value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--accent);
}

.stat .label {
  font-size: 0.875rem;
  color: var(--text-muted);
}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#section-properties) — Section properties
- [Featured Posts](/docs/theming/recipes/featured-posts/) — Feature content
:::
