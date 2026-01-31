---
title: View Filters
description: Convert pages to normalized view objects for easier templating
weight: 90
tags:
- reference
- filters
- views
- releases
- posts
category: reference
---

# View Filters

Filters that convert pages to normalized view objects for easier templating.

## releases

Convert release pages to normalized `ReleaseView` objects with smart version detection and sorting.

```kida
{% for rel in pages | releases %}
  <h2>{{ rel.version }}</h2>
  <time>{{ rel.date | dateformat }}</time>
  <p>{{ rel.summary }}</p>
{% end %}
```

**Version Detection Priority:**
1. Explicit `version` field in frontmatter
2. Filename if versioned (e.g., `0.1.8.md` → `0.1.8`)
3. Version pattern in title (e.g., "Bengal 0.1.8" → `0.1.8`)
4. Full title as fallback

**Sorting:** By default, releases are sorted by **version** (highest first) using semantic comparison. This means `0.1.10` correctly sorts before `0.1.9`.

**ReleaseView Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `version` | string | Extracted version number |
| `name` | string | Release codename |
| `date` | datetime | Release date |
| `status` | string | Release status (stable, beta, rc) |
| `href` | string | URL to release page |
| `summary` | string | Brief description |
| `added` | tuple | List of added features |
| `changed` | tuple | List of changes |
| `fixed` | tuple | List of bug fixes |
| `deprecated` | tuple | Deprecated features |
| `removed` | tuple | Removed features |
| `security` | tuple | Security fixes |
| `breaking` | tuple | Breaking changes |
| `has_structured_changes` | bool | Has categorized changes |
| `change_types` | tuple | List of change types present |

**Preserve Input Order:**

```kida
{# Disable sorting to use custom order #}
{% for rel in pages | releases(false) %}
  {{ rel.version }}
{% end %}
```

**Supported Version Formats:**
- Semver: `0.1.8`, `1.0.0`, `2.0.0-beta`, `v1.2.3`
- Date-based: `26.01`, `2026.01.12`

## posts

Convert blog pages to normalized `PostView` objects for consistent access.

```kida
{% for post in pages | posts %}
  <article>
    <h2><a href="{{ post.href }}">{{ post.title }}</a></h2>
    <time>{{ post.date | dateformat }}</time>
    <p>{{ post.description }}</p>
    <span>{{ post.reading_time }} min read</span>
  </article>
{% end %}
```

**PostView Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `title` | string | Post title |
| `href` | string | URL to post |
| `date` | datetime | Publication date |
| `image` | string | Featured image URL |
| `description` | string | Post description |
| `excerpt` | string | Raw excerpt text |
| `author` | string | Author name |
| `author_avatar` | string | Author avatar URL |
| `reading_time` | int | Estimated reading time (minutes) |
| `word_count` | int | Total word count |
| `tags` | tuple | Tag names |
| `featured` | bool | Is featured post |
| `draft` | bool | Is draft |

## featured_posts

Get featured posts from a list.

```kida
{% for post in pages | featured_posts(3) %}
  <div class="featured">{{ post.title }}</div>
{% end %}
```

## release_view

Convert a single release item to a `ReleaseView`. Useful when you have a single release page.

```kida
{% let rel = page | release_view %}
{% if rel %}
  <h2>{{ rel.version }}</h2>
  <p>Released: {{ rel.date | dateformat }}</p>
{% end %}
```

Returns `None` if conversion fails.

## post_view

Convert a single page to a `PostView`. Useful for individual post pages.

```kida
{% let p = page | post_view %}
{% if p %}
  <h1>{{ p.title }}</h1>
  <span>{{ p.reading_time }} min read</span>
{% end %}
```

Returns `None` if conversion fails.
