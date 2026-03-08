---
name: bengal-taxonomy
description: Configures and uses taxonomy (tags, categories, indexes) in Bengal sites. Use when adding tags, categories, or querying content by section, author, or date.
---

# Bengal Taxonomy

Use tags, categories, and built-in indexes to organize and query content.

## Frontmatter

Add taxonomy fields to content:

```yaml
---
title: My Post
tags: [python, bengal, ssg]
category: tutorial
params:
  author: Jane Doe
date: '2026-01-01'
---
```

## Built-in Indexes

Bengal provides O(1) query indexes. Use `site.indexes.*.get(key) | resolve_pages`:

| Index | Key | Use Case |
|-------|-----|----------|
| section | Section name | `site.indexes.section.get('posts')` |
| author | Author name | `site.indexes.author.get('Jane Doe')` |
| category | Category | `site.indexes.category.get('tutorial')` |
| date_range | Year or Year-Month | `site.indexes.date_range.get('2026-01')` |

## Template Queries

**Section listing (e.g., blog posts):**

```kida
{% let blog_posts = site.indexes.section.get('posts') | resolve_pages %}
{% for post in blog_posts | sort_by('date', reverse=true) %}
  <h2>{{ post.title }}</h2>
  <p>{{ post.description }}</p>
{% end %}
```

**Author archive:**

```kida
{% let author_posts = site.indexes.author.get('Jane Doe') | resolve_pages %}
<p>{{ author_posts | length }} posts</p>
```

**Monthly archive:**

```kida
{% let jan_posts = site.indexes.date_range.get('2026-01') | resolve_pages %}
```

## Displaying Tags on a Page

```kida
{% let safe_tags = page.tags ?? [] %}
{% for tag in safe_tags %}
  {% if tag %}
  <a href="/tags/{{ tag }}">{{ tag }}</a>
  {% end %}
{% endfor %}
```

Use `?? []` and `{% if tag %}` to guard against malformed frontmatter.

## Tag Index Pages

Bengal's default theme generates tag index pages at `/tags/<tag>/`. Ensure your theme has a tag list template. Tags are derived from frontmatter; no config needed.

## Checklist

- [ ] Add tags, category, params.author to frontmatter
- [ ] Use site.indexes for O(1) queries (not where filters)
- [ ] Use resolve_pages filter after index lookup
- [ ] Guard tag iteration with ?? [] and {% if tag %}

## Additional Resources

See [references/taxonomy-index.md](references/taxonomy-index.md) for index details.
