---
title: Featured Posts
description: Highlight featured content in sidebars and homepages
weight: 110
draft: false
lang: en
tags:
- cookbook
- featured
- sections
keywords:
- featured posts
- highlight content
- pinned posts
category: cookbook
---

# Featured Posts

Highlight important content using the `featured` frontmatter flag.

## The Pattern

### Frontmatter Setup

Mark posts as featured:

```yaml
---
title: "Our Most Important Post"
featured: true
---
```

### Template Code

```jinja2
{% set featured = section.featured_posts %}

{% if featured %}
<section class="featured-posts">
  <h2>Featured</h2>
  {% for post in featured | limit(3) %}
  <article class="featured-card">
    <h3><a href="{{ post.href }}">{{ post.title }}</a></h3>
    <p>{{ post.description }}</p>
  </article>
  {% endfor %}
</section>
{% endif %}
```

## What's Happening

| Property | Purpose |
|----------|---------|
| `section.featured_posts` | Pages with `featured: true` in this section |
| `page.metadata.featured` | Check if a page is featured |

## Variations

### Featured Hero

Single featured post as hero:

```jinja2
{% set hero = section.featured_posts | first %}

{% if hero %}
<header class="hero">
  {% if hero.metadata.cover_image %}
  <img src="{{ hero.metadata.cover_image }}" alt="">
  {% endif %}
  <div class="hero-content">
    <span class="label">Featured</span>
    <h1><a href="{{ hero.href }}">{{ hero.title }}</a></h1>
    <p>{{ hero.description }}</p>
    <a href="{{ hero.href }}" class="btn">Read More</a>
  </div>
</header>
{% endif %}
```

### Featured + Regular Posts

```jinja2
{% set all_posts = section.sorted_pages %}
{% set featured = section.featured_posts | limit(3) %}
{% set regular = all_posts | complement(featured) | limit(10) %}

<div class="posts-layout">
  <aside class="featured-sidebar">
    <h3>Featured</h3>
    {% for post in featured %}
    <article class="featured-item">
      <a href="{{ post.href }}">{{ post.title }}</a>
    </article>
    {% endfor %}
  </aside>

  <main class="posts-main">
    {% for post in regular %}
    <article>
      <h2><a href="{{ post.href }}">{{ post.title }}</a></h2>
      <p>{{ post.excerpt }}</p>
    </article>
    {% endfor %}
  </main>
</div>
```

### Featured Badge in Lists

```jinja2
{% for post in section.sorted_pages %}
<article class="{% if post.metadata.featured %}is-featured{% endif %}">
  {% if post.metadata.featured %}
  <span class="badge">⭐ Featured</span>
  {% endif %}
  <h2><a href="{{ post.href }}">{{ post.title }}</a></h2>
</article>
{% endfor %}
```

### Featured Grid

```jinja2
{% set featured = section.featured_posts | limit(4) %}

<div class="featured-grid">
  {% for post in featured %}
  <article class="grid-item">
    {% if post.metadata.cover_image %}
    <img src="{{ post.metadata.cover_image }}" alt="">
    {% endif %}
    <div class="content">
      <h3><a href="{{ post.href }}">{{ post.title }}</a></h3>
      <time>{{ post.date | date('%B %d, %Y') }}</time>
    </div>
  </article>
  {% endfor %}
</div>
```

### Site-Wide Featured

Get featured posts from any section:

```jinja2
{% set all_featured = site.pages | where('metadata.featured', true) | limit(5) %}

<section class="site-featured">
  <h2>Editor's Picks</h2>
  {% for post in all_featured %}
  <a href="{{ post.href }}">
    <span class="section-name">{{ post.section }}</span>
    {{ post.title }}
  </a>
  {% endfor %}
</section>
```

### Featured with Priority

Support priority ordering:

```yaml
---
featured: true
featured_priority: 1  # Lower = higher priority
---
```

```jinja2
{% set featured = section.featured_posts | sort_by('metadata.featured_priority') %}
```

### Rotating Featured

Show different featured posts based on day:

```jinja2
{% set featured = section.featured_posts %}
{% set today_index = now().timetuple().tm_yday % (featured | length) %}
{% set todays_featured = featured[today_index] %}

<aside class="daily-pick">
  <h3>Today's Pick</h3>
  <a href="{{ todays_featured.href }}">{{ todays_featured.title }}</a>
</aside>
```

## Example CSS

```css
.featured-card {
  border: 2px solid var(--accent);
  border-radius: 8px;
  padding: 1.5rem;
  background: var(--bg-secondary);
}

.featured-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.grid-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
}

.grid-item img {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.grid-item .content {
  padding: 1rem;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  color: white;
}

.is-featured {
  border-left: 4px solid var(--accent);
  padding-left: 1rem;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--accent);
  color: white;
  border-radius: 4px;
}
```

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/#section-properties) — Section properties
- [List Recent Posts](/docs/theming/recipes/list-recent-posts/) — Recent posts pattern
:::
