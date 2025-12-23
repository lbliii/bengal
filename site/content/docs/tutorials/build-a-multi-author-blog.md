---
title: Build a Multi-Author Blog
nav_title: Multi-Author Blog
description: Create a blog with multiple authors, author pages, and bylines
weight: 15
draft: false
lang: en
tags:
- tutorial
- intermediate
- blog
- authors
keywords:
- multi-author
- author pages
- bylines
- team blog
category: tutorial
---

# Build a Multi-Author Blog

In this tutorial, you'll transform a single-author blog into a full multi-author publication with author profiles, individual author pages, and rich bylines.

:::{tip}
**Default Theme Has This Built-In!**

Bengal's default theme includes complete multi-author support:
- Author pages with social links and post listings
- Author bylines in blog posts (enable `content.author` feature)
- Author index page listing all contributors

If you're using the default theme, you may only need to **add frontmatter** — no template work required! This tutorial shows both how to use the built-in features and how to customize them.
:::

:::{note}
**Who is this for?**
This guide is for developers building team blogs, publication sites, or any content with multiple contributors. You should be familiar with Bengal basics from the [Build a Blog](/docs/tutorials/build-a-blog/) tutorial.
:::

## Goal

By the end of this tutorial, you will have:
1. Structured author data in frontmatter
2. Rich author bylines with avatars and social links
3. Dedicated author profile pages
4. An author listing page
5. Posts filtered by author

## Prerequisites

*   A Bengal site (run `bengal new site my-blog` if starting fresh)
*   Basic understanding of Jinja2 templates

## Steps

:::{steps}
:::{step} Define Author Metadata
:description: Add structured author information to your blog posts.
:duration: 3 min

Bengal supports two ways to specify authors in frontmatter:

**Simple (name only):**

```yaml
---
title: "Getting Started with Python"
author: Jane Smith
---
```

**Structured (full profile):**

```yaml
---
title: "Getting Started with Python"
author:
  name: Jane Smith
  avatar: /images/authors/jane.jpg
  bio: Senior developer and tech writer
  twitter: janesmith
  github: janesmith
  linkedin: janesmith
  website: https://janesmith.dev
---
```

Create a test post at `content/blog/python-basics.md`:

```yaml
---
title: "Python Basics for Beginners"
date: 2024-01-15
draft: false
author:
  name: Jane Smith
  avatar: /images/authors/jane.jpg
  bio: Senior developer specializing in Python and web technologies
  twitter: janesmith
  github: janesmith
tags: ["python", "tutorial"]
---

# Python Basics for Beginners

Learn the fundamentals of Python programming...
```

:::{tip}
**Avoid Repetition**
Instead of repeating full author data in every post, you can define authors in a data file and reference them. We'll cover this later.
:::
:::{/step}

:::{step} Create an Author Byline Component
:description: Display author information on blog posts.
:duration: 5 min

Create a reusable author byline partial at `templates/partials/author-byline.html`:

```html
{# templates/partials/author-byline.html #}
{% if page.author %}
<div class="author-byline">
  {% if page.author.avatar %}
  <img src="{{ page.author.avatar }}"
       alt="{{ page.author.name }}"
       class="author-avatar">
  {% else %}
  <div class="author-avatar-placeholder">
    {{ page.author.name[0] }}
  </div>
  {% endif %}

  <div class="author-info">
    <a href="/authors/{{ page.author.name | slugify }}/" class="author-name">
      {{ page.author.name }}
    </a>

    {% if page.author.bio %}
    <p class="author-bio">{{ page.author.bio }}</p>
    {% endif %}

    <div class="author-meta">
      <time datetime="{{ page.date | date_iso }}">
        {{ page.date | date('%B %d, %Y') }}
      </time>
      <span>·</span>
      <span>{{ page.reading_time }} min read</span>
    </div>

    <div class="author-social">
      {% if page.author.twitter %}
      <a href="https://twitter.com/{{ page.author.twitter }}"
         aria-label="Twitter">
        <svg class="icon"><use href="#icon-twitter"></use></svg>
      </a>
      {% endif %}
      {% if page.author.github %}
      <a href="https://github.com/{{ page.author.github }}"
         aria-label="GitHub">
        <svg class="icon"><use href="#icon-github"></use></svg>
      </a>
      {% endif %}
      {% if page.author.linkedin %}
      <a href="https://linkedin.com/in/{{ page.author.linkedin }}"
         aria-label="LinkedIn">
        <svg class="icon"><use href="#icon-linkedin"></use></svg>
      </a>
      {% endif %}
    </div>
  </div>
</div>
{% endif %}
```

Add matching styles in `assets/css/author.css`:

```css
.author-byline {
  display: flex;
  gap: 1rem;
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.author-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
}

.author-avatar-placeholder {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: bold;
}

.author-name {
  font-weight: 600;
  font-size: 1.125rem;
  text-decoration: none;
  color: var(--text);
}

.author-name:hover {
  color: var(--accent);
}

.author-bio {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0.25rem 0;
}

.author-meta {
  font-size: 0.875rem;
  color: var(--text-muted);
  display: flex;
  gap: 0.5rem;
}

.author-social {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.author-social a {
  color: var(--text-muted);
}

.author-social a:hover {
  color: var(--accent);
}

.author-social .icon {
  width: 18px;
  height: 18px;
}
```

Include the byline in your blog post template (`templates/blog/single.html`):

```html
{% extends "default/single.html" %}

{% block article_header %}
<header class="article-header">
  <h1>{{ page.title }}</h1>
  {% include "partials/author-byline.html" %}
</header>
{% endblock %}
```
:::{/step}

:::{step} Create Author Profile Pages
:description: Build individual pages for each author.
:duration: 5 min

Create an author directory structure:

```bash
mkdir -p content/authors
```

Create a profile for Jane at `content/authors/jane-smith.md`:

```yaml
---
title: Jane Smith
type: author
avatar: /images/authors/jane.jpg
bio: |
  Jane is a senior developer with 10 years of experience in Python
  and web technologies. She writes about best practices, tutorials,
  and the joy of clean code.
location: San Francisco, CA
twitter: janesmith
github: janesmith
linkedin: janesmith
website: https://janesmith.dev
---

## About Jane

Jane has been writing code since she was 12 years old. She's passionate
about developer experience and making complex topics accessible.

## Interests

- Python ecosystem
- Web performance
- Developer tools
- Teaching and mentoring
```

Create the author page template at `templates/authors/single.html`:

```html
{% extends "default/base.html" %}

{% block content %}
<article class="author-profile">
  <header class="author-header">
    {% if page.metadata.avatar %}
    <img src="{{ page.metadata.avatar }}"
         alt="{{ page.title }}"
         class="author-profile-avatar">
    {% endif %}

    <div class="author-header-info">
      <h1>{{ page.title }}</h1>

      {% if page.metadata.location %}
      <p class="author-location">📍 {{ page.metadata.location }}</p>
      {% endif %}

      {% if page.metadata.bio %}
      <p class="author-bio-long">{{ page.metadata.bio }}</p>
      {% endif %}

      <div class="author-links">
        {% if page.metadata.website %}
        <a href="{{ page.metadata.website }}">Website</a>
        {% endif %}
        {% if page.metadata.twitter %}
        <a href="https://twitter.com/{{ page.metadata.twitter }}">Twitter</a>
        {% endif %}
        {% if page.metadata.github %}
        <a href="https://github.com/{{ page.metadata.github }}">GitHub</a>
        {% endif %}
      </div>
    </div>
  </header>

  <div class="author-content">
    {{ page.content | safe }}
  </div>

  <section class="author-posts">
    <h2>Posts by {{ page.title }}</h2>

    {% set author_posts = site.pages
      | where('author.name', page.title)
      | sort_by('date', reverse=true) %}

    {% if author_posts %}
    <ul class="post-list">
      {% for post in author_posts %}
      <li>
        <a href="{{ post.href }}">{{ post.title }}</a>
        <time>{{ post.date | date('%B %d, %Y') }}</time>
      </li>
      {% endfor %}
    </ul>
    {% else %}
    <p>No posts yet.</p>
    {% endif %}
  </section>
</article>
{% endblock %}
```

Add styles to `assets/css/author.css`:

```css
.author-profile {
  max-width: 800px;
  margin: 0 auto;
}

.author-header {
  display: flex;
  gap: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.author-profile-avatar {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
}

.author-header-info h1 {
  margin: 0 0 0.5rem;
}

.author-location {
  color: var(--text-muted);
  margin: 0.5rem 0;
}

.author-bio-long {
  font-size: 1.125rem;
  line-height: 1.6;
}

.author-links {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.author-links a {
  padding: 0.5rem 1rem;
  background: var(--bg-secondary);
  border-radius: 4px;
  text-decoration: none;
}

.author-posts {
  margin-top: 3rem;
}

.post-list {
  list-style: none;
  padding: 0;
}

.post-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-color);
}

.post-list time {
  color: var(--text-muted);
  font-size: 0.875rem;
}
```
:::{/step}

:::{step} Create an Authors Listing Page
:description: Display all authors on a team page.
:duration: 3 min

Create `content/authors/_index.md`:

```yaml
---
title: Our Authors
description: Meet the writers behind our content
type: authors
---

# Our Authors

Meet the talented people who contribute to this blog.
```

Create the listing template at `templates/authors/list.html`:

```html
{% extends "default/base.html" %}

{% block content %}
<div class="authors-page">
  <header>
    <h1>{{ page.title }}</h1>
    {% if page.description %}
    <p class="lead">{{ page.description }}</p>
    {% endif %}
  </header>

  <div class="authors-grid">
    {% for author in section.pages | sort_by('title') %}
    <a href="{{ author.href }}" class="author-card">
      {% if author.metadata.avatar %}
      <img src="{{ author.metadata.avatar }}"
           alt="{{ author.title }}"
           class="author-card-avatar">
      {% else %}
      <div class="author-card-avatar-placeholder">
        {{ author.title[0] }}
      </div>
      {% endif %}

      <h2>{{ author.title }}</h2>

      {% if author.metadata.bio %}
      <p>{{ author.metadata.bio | truncate(100) }}</p>
      {% endif %}

      {% set post_count = site.pages | where('author.name', author.title) | length %}
      <span class="author-post-count">{{ post_count }} posts</span>
    </a>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

Add grid styles:

```css
.authors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.author-card {
  display: block;
  padding: 1.5rem;
  background: var(--bg-secondary);
  border-radius: 8px;
  text-decoration: none;
  color: var(--text);
  transition: transform 0.2s, box-shadow 0.2s;
}

.author-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.author-card-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  margin-bottom: 1rem;
}

.author-card h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.author-card p {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin: 0 0 1rem;
}

.author-post-count {
  font-size: 0.75rem;
  color: var(--accent);
  font-weight: 600;
}
```
:::{/step}

:::{step} Support Multiple Authors per Post
:description: Handle collaborative posts with multiple authors.
:duration: 3 min

For posts with multiple authors, use the `authors` field:

```yaml
---
title: "Collaborative Guide to Testing"
date: 2024-01-20
authors:
  - name: Jane Smith
    avatar: /images/authors/jane.jpg
  - name: John Doe
    avatar: /images/authors/john.jpg
---
```

Update your byline partial to handle multiple authors:

```html
{# templates/partials/author-byline.html #}
{% if page.authors %}
<div class="authors-byline">
  <span class="byline-label">Written by</span>
  <div class="authors-list">
    {% for author in page.authors %}
    <a href="/authors/{{ author.name | slugify }}/" class="author-chip">
      {% if author.avatar %}
      <img src="{{ author.avatar }}" alt="{{ author.name }}">
      {% endif %}
      <span>{{ author.name }}</span>
    </a>
    {% endfor %}
  </div>

  <div class="post-meta">
    <time>{{ page.date | date('%B %d, %Y') }}</time>
    <span>·</span>
    <span>{{ page.reading_time }} min read</span>
  </div>
</div>
{% elif page.author %}
{# Single author - use existing byline #}
<div class="author-byline">
  {# ... existing single author code ... #}
</div>
{% endif %}
```

Add styles for author chips:

```css
.authors-byline {
  padding: 1rem 0;
  border-bottom: 1px solid var(--border-color);
}

.byline-label {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.authors-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 0.5rem 0;
}

.author-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem 0.25rem 0.25rem;
  background: var(--bg-secondary);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text);
  font-size: 0.875rem;
}

.author-chip img {
  width: 28px;
  height: 28px;
  border-radius: 50%;
}

.author-chip:hover {
  background: var(--bg-tertiary);
}
```
:::{/step}

:::{step} Add Author Data File (Optional)
:description: Centralize author data to avoid repetition.
:duration: 3 min
:optional:

For larger teams, define authors in a data file instead of repeating info in every post.

Create `data/authors.yaml`:

```yaml
jane-smith:
  name: Jane Smith
  avatar: /images/authors/jane.jpg
  bio: Senior developer specializing in Python
  twitter: janesmith
  github: janesmith

john-doe:
  name: John Doe
  avatar: /images/authors/john.jpg
  bio: Frontend architect and design systems expert
  twitter: johndoe
  github: johndoe
```

Reference by key in frontmatter:

```yaml
---
title: "My Post"
author: jane-smith  # References data/authors.yaml
---
```

You'll need a custom template function to resolve this:

```python
# In a build hook or custom extension
def get_author(key):
    authors = site.data.get('authors', {})
    return authors.get(key)
```

:::{note}
This advanced pattern requires a build hook. See [Build Hooks](/docs/extending/build-hooks/) for details.
:::
:::{/step}
:::{/steps}

## Summary

You now have a fully functional multi-author blog with:

- ✅ Structured author data in frontmatter
- ✅ Rich bylines with avatars and social links
- ✅ Individual author profile pages
- ✅ Team listing page
- ✅ Support for collaborative posts

## Next Steps

- **[Author Byline Recipe](/docs/theming/recipes/author-byline/)**: Quick reference for byline patterns
- **[Social Sharing](/docs/theming/recipes/social-sharing-buttons/)**: Let authors share their posts
- **[Content Freshness](/docs/theming/recipes/content-freshness/)**: Show post age indicators
