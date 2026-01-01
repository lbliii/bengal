---
title: Author Byline
description: Display author information with avatar and social links
weight: 70
draft: false
lang: en
tags:
- cookbook
- author
- byline
keywords:
- author info
- byline
- avatar
- social links
category: cookbook
---

# Author Byline

Display author information including avatar, bio, and social links.

:::{note}
**Built into Default Theme**

Bengal's default theme includes full author support out of the box:
- **Author pages** at `/authors/{name}/` with posts, social links, and bio
- **Author bylines** in blog posts (enable with `content.author` feature)
- **Author index** for O(1) lookup via `site.indexes.author`

This recipe shows how to customize the display or build your own author components.
:::

## The Pattern

### Frontmatter Setup

```yaml
---
title: "Getting Started with Bengal"
author:
  name: Jane Smith
  avatar: /images/authors/jane.jpg
  bio: Senior developer and tech writer
  twitter: janesmith
  github: janesmith
---
```

Or use a simple string for name-only:

```yaml
---
author: Jane Smith
---
```

### Template Code

```kida
{% if page.author %}
<div class="author-byline">
  {% if page.author.avatar %}
  <img src="{{ page.author.avatar }}" alt="{{ page.author.name }}" class="author-avatar">
  {% end %}

  <div class="author-info">
    <span class="author-name">{{ page.author.name }}</span>
    {% if page.author.bio %}
    <p class="author-bio">{{ page.author.bio }}</p>
    {% end %}
  </div>
</div>
{% end %}
```

## What's Happening

| Component | Purpose |
|-----------|---------|
| `page.author` | Primary Author object (or None) |
| `page.author.name` | Author's display name |
| `page.author.avatar` | Path to avatar image |
| `page.author.bio` | Short biography |
| `page.author.twitter` | Twitter handle (without @) |

## Variations

:::{tab-set}
:::{tab-item} With Social Links

```kida
{% if page.author %}
<div class="author-byline">
  <img src="{{ page.author.avatar or '/images/default-avatar.png' }}"
       alt="{{ page.author.name }}">

  <div class="author-info">
    <span class="author-name">{{ page.author.name }}</span>

    <div class="author-social">
      {% if page.author.twitter %}
      <a href="https://twitter.com/{{ page.author.twitter }}">
        <i class="icon-twitter"></i>
      </a>
      {% end %}
      {% if page.author.github %}
      <a href="https://github.com/{{ page.author.github }}">
        <i class="icon-github"></i>
      </a>
      {% end %}
      {% if page.author.linkedin %}
      <a href="https://linkedin.com/in/{{ page.author.linkedin }}">
        <i class="icon-linkedin"></i>
      </a>
      {% end %}
      {% if page.author.mastodon %}
      <a href="{{ page.author.mastodon }}">
        <i class="icon-mastodon"></i>
      </a>
      {% end %}
    </div>
  </div>
</div>
{% end %}
```

:::{/tab-item}
:::{tab-item} Multiple Authors

```kida
{% if page.authors %}
<div class="authors">
  <span class="authors-label">Written by</span>
  {% for author in page.authors %}
  <div class="author">
    {% if author.avatar %}
    <img src="{{ author.avatar }}" alt="{{ author.name }}">
    {% end %}
    <span>{{ author.name }}</span>
  </div>
  {% end %}
</div>
{% end %}
```

Frontmatter for multiple authors:

```yaml
---
authors:
  - name: Jane Smith
    avatar: /images/jane.jpg
  - name: John Doe
    avatar: /images/john.jpg
---
```

:::{/tab-item}
:::{tab-item} Compact Inline

```kida
{% if page.author %}
<p class="byline">
  By {{ page.author.name }}
  {% if page.date %}
  · {{ page.date | date('%B %d, %Y') }}
  {% end %}
  · {{ page.reading_time }} min read
</p>
{% end %}
```

:::{/tab-item}
:::{tab-item} Link to Author Page

```kida
{% if page.author %}
<a href="/authors/{{ page.author.name | slugify }}/" class="author-link">
  {% if page.author.avatar %}
  <img src="{{ page.author.avatar }}" alt="">
  {% end %}
  {{ page.author.name }}
</a>
{% end %}
```

:::{/tab-item}
:::{tab-item} Full Author Card

```kida
{% if page.author %}
<aside class="author-card">
  <div class="author-header">
    {% if page.author.avatar %}
    <img src="{{ page.author.avatar }}" alt="{{ page.author.name }}" class="avatar">
    {% end %}
    <div>
      <h4>{{ page.author.name }}</h4>
      {% if page.author.bio %}
      <p>{{ page.author.bio }}</p>
      {% end %}
    </div>
  </div>

  {% if page.author.website %}
  <a href="{{ page.author.website }}" class="author-website">
    Visit website →
  </a>
  {% end %}
</aside>
{% end %}
```

:::{/tab-item}
:::{/tab-set}

## Example CSS

```css
.author-byline {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
}

.author-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}

.author-name {
  font-weight: 600;
}

.author-bio {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0.25rem 0 0;
}

.author-social {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.author-social a {
  color: var(--text-muted);
}

.author-social a:hover {
  color: var(--accent);
}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#author-properties) — Author properties
- [Build a Multi-Author Blog](/docs/tutorials/sites/build-a-multi-author-blog/) — Full tutorial
:::
