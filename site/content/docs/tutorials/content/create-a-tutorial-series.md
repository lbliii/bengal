---
title: Create a Tutorial Series
nav_title: Tutorial Series
description: Build multi-part tutorials with series navigation and progress tracking
weight: 16
draft: false
lang: en
tags:
- tutorial
- intermediate
- series
- navigation
keywords:
- tutorial series
- multi-part content
- series navigation
- progress tracking
category: tutorial
---

# Create a Tutorial Series

In this tutorial, you'll learn how to create a multi-part tutorial series with navigation between parts, progress tracking, and a series overview page.

:::{tip}
**Default Theme Navigation**

Bengal's default theme includes prev/next navigation that works automatically:
- **Section-scoped** for `doc`, `tutorial` types — uses `weight` for ordering
- **Chronological** for `blog`, `page` types — sorted by date
- Enable with `navigation.prev_next` feature flag

This tutorial shows how to use **explicit series metadata** for multi-part content with progress bars and "Part X of Y" displays.
:::

:::{note}
**Who is this for?**
This guide is for content creators building courses, tutorials, or any multi-part content where readers progress through sequential lessons.
:::

## Goal

By the end of this tutorial, you will have:
1. A multi-part tutorial series with proper frontmatter
2. Prev/next navigation between parts
3. A series overview page showing all parts
4. Progress indicators showing completion status
5. A reusable series navigation component

## Prerequisites

*   A Bengal site with some existing content
*   Basic understanding of Jinja2 templates

## Steps

:::{steps}
:::{step} Structure Your Series Content
:description: Set up the frontmatter for a multi-part tutorial series.
:duration: 5 min

Let's create a 5-part tutorial series called "React from Scratch". First, create the directory structure:

```bash
mkdir -p content/tutorials/react-from-scratch
```

Create the series index at `content/tutorials/react-from-scratch/_index.md`:

```yaml
---
title: "React from Scratch"
description: "Build a complete React app from zero to deployment"
type: series-index
series_name: "React from Scratch"
difficulty: intermediate
estimated_time: "2 hours"
prerequisites:
  - Basic JavaScript knowledge
  - Node.js installed
---

# React from Scratch

Learn to build React applications from the ground up. This 5-part series takes you from zero to a fully deployed application.

## What You'll Learn

- Setting up a modern React development environment
- Component architecture and state management
- Styling approaches and best practices
- Testing your components
- Deploying to production

## Prerequisites

- Basic JavaScript knowledge (ES6+)
- Node.js 18+ installed
- A code editor (VS Code recommended)
```

Now create each part. Here's **Part 1** at `content/tutorials/react-from-scratch/01-setup.md`:

```yaml
---
title: "Part 1: Project Setup"
nav_title: "1. Setup"
date: 2024-01-15
weight: 1
series:
  name: "React from Scratch"
  part: 1
  total: 5
---

# Part 1: Project Setup

Let's set up our development environment and create our first React project.

## Create a New Project

```bash
npm create vite@latest my-react-app -- --template react
cd my-react-app
npm install
```

## Understanding the Structure

After creation, you'll see...

[... rest of content ...]
```

Create **Parts 2-5** with the same structure, incrementing `part`:

```yaml
# Part 2: content/tutorials/react-from-scratch/02-components.md
---
title: "Part 2: Building Components"
weight: 2
series:
  name: "React from Scratch"
  part: 2
  total: 5
---
```

```yaml
# Part 3: content/tutorials/react-from-scratch/03-state.md
---
title: "Part 3: State Management"
weight: 3
series:
  name: "React from Scratch"
  part: 3
  total: 5
---
```

```yaml
# Part 4: content/tutorials/react-from-scratch/04-styling.md
---
title: "Part 4: Styling Your App"
weight: 4
series:
  name: "React from Scratch"
  part: 4
  total: 5
---
```

```yaml
# Part 5: content/tutorials/react-from-scratch/05-deployment.md
---
title: "Part 5: Deployment"
weight: 5
series:
  name: "React from Scratch"
  part: 5
  total: 5
---
```

:::{tip}
**Naming Convention**
Prefix files with numbers (`01-`, `02-`) to keep them sorted in your file manager. Use `weight` for actual ordering.
:::
:::{/step}

:::{step} Create the Series Navigation Component
:description: Build a reusable prev/next navigation for series pages.
:duration: 5 min

Create `templates/partials/series-nav.html`:

```html
{# templates/partials/series-nav.html #}
{% if page.series %}
<nav class="series-nav" aria-label="Series navigation">
  {# Series header with progress #}
  <div class="series-header">
    <span class="series-badge">📚 Series</span>
    <h4 class="series-title">{{ page.series.name }}</h4>
    <div class="series-progress">
      <div class="progress-bar">
        <div class="progress-fill"
             style="width: {{ (page.series.part / page.series.total * 100) | round }}%">
        </div>
      </div>
      <span class="progress-text">
        Part {{ page.series.part }} of {{ page.series.total }}
      </span>
    </div>
  </div>

  {# Prev/Next links #}
  <div class="series-links">
    {% if page.prev_in_series %}
    <a href="{{ page.prev_in_series.href }}" class="series-link prev">
      <span class="link-direction">← Previous</span>
      <span class="link-title">{{ page.prev_in_series.title }}</span>
    </a>
    {% else %}
    <div class="series-link prev disabled">
      <span class="link-direction">← Previous</span>
      <span class="link-title">Start of series</span>
    </div>
    {% end %}

    {% if page.next_in_series %}
    <a href="{{ page.next_in_series.href }}" class="series-link next">
      <span class="link-direction">Next →</span>
      <span class="link-title">{{ page.next_in_series.title }}</span>
    </a>
    {% else %}
    <div class="series-link next completed">
      <span class="link-direction">🎉 Complete!</span>
      <span class="link-title">You finished the series</span>
    </div>
    {% end %}
  </div>
</nav>
{% end %}
```

Add the styles to `assets/css/series.css`:

```css
.series-nav {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
  margin: 2rem 0;
  background: var(--bg-secondary);
}

.series-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.series-badge {
  display: inline-block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.series-title {
  margin: 0.5rem 0;
  font-size: 1.125rem;
}

.series-progress {
  margin-top: 1rem;
}

.progress-bar {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.progress-text {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.series-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.series-link {
  padding: 1rem;
  border-radius: 8px;
  background: var(--bg);
  text-decoration: none;
  color: var(--text);
  transition: background 0.2s;
}

.series-link:hover:not(.disabled) {
  background: var(--bg-tertiary);
}

.series-link.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.series-link.completed {
  background: var(--color-success-bg);
  opacity: 1;
}

.link-direction {
  display: block;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
}

.link-title {
  font-weight: 500;
}

.series-link.prev {
  text-align: left;
}

.series-link.next {
  text-align: right;
}

@media (max-width: 600px) {
  .series-links {
    grid-template-columns: 1fr;
  }
}
```
:::{/step}

:::{step} Create the Series Overview Template
:description: Build a landing page showing all parts in the series.
:duration: 5 min

Create `templates/series-index/single.html` for the series overview page:

```html
{% extends "default/base.html" %}

{% block content %}
<article class="series-overview">
  <header class="series-overview-header">
    <span class="series-badge">📚 Tutorial Series</span>
    <h1>{{ page.title }}</h1>

    {% if page.description %}
    <p class="lead">{{ page.description }}</p>
    {% end %}

    <div class="series-meta">
      {% if page.metadata.difficulty %}
      <span class="meta-item">
        <strong>Difficulty:</strong> {{ page.metadata.difficulty | title }}
      </span>
      {% end %}
      {% if page.metadata.estimated_time %}
      <span class="meta-item">
        <strong>Time:</strong> {{ page.metadata.estimated_time }}
      </span>
      {% end %}
      {% if page.metadata.prerequisites %}
      <span class="meta-item">
        <strong>Prerequisites:</strong> {{ page.metadata.prerequisites | join(', ') }}
      </span>
      {% end %}
    </div>
  </header>

  <div class="series-content">
    {{ page.content | safe }}
  </div>

  {# List all parts #}
  <section class="series-parts">
    <h2>All Parts</h2>

    <ol class="parts-list">
      {% for part in section.pages | sort_by('weight') %}
      {% if part.series %}
      <li class="part-item">
        <a href="{{ part.href }}" class="part-link">
          <span class="part-number">Part {{ part.series.part }}</span>
          <span class="part-title">{{ part.title }}</span>
          <span class="part-time">{{ part.reading_time }} min</span>
        </a>
      </li>
      {% end %}
      {% end %}
    </ol>

    <a href="{{ section.pages | sort_by('weight') | first | attr('href') }}"
       class="btn btn-primary btn-large">
      Start Learning →
    </a>
  </section>
</article>
{% endblock %}
```

Add styles:

```css
.series-overview {
  max-width: 800px;
  margin: 0 auto;
}

.series-overview-header {
  text-align: center;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 2rem;
}

.series-overview-header h1 {
  font-size: 2.5rem;
  margin: 1rem 0;
}

.series-overview-header .lead {
  font-size: 1.25rem;
  color: var(--text-muted);
  max-width: 600px;
  margin: 0 auto;
}

.series-meta {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-top: 1.5rem;
  font-size: 0.875rem;
}

.series-parts {
  margin-top: 3rem;
}

.parts-list {
  list-style: none;
  padding: 0;
  counter-reset: part;
}

.part-item {
  margin-bottom: 0.5rem;
}

.part-link {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--bg-secondary);
  border-radius: 8px;
  text-decoration: none;
  color: var(--text);
  transition: background 0.2s, transform 0.2s;
}

.part-link:hover {
  background: var(--bg-tertiary);
  transform: translateX(4px);
}

.part-number {
  width: 80px;
  font-size: 0.875rem;
  color: var(--accent);
  font-weight: 600;
}

.part-title {
  flex: 1;
  font-weight: 500;
}

.part-time {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.btn-large {
  display: inline-block;
  margin-top: 2rem;
  padding: 1rem 2rem;
  font-size: 1.125rem;
}
```
:::{/step}

:::{step} Add Series Table of Contents Sidebar
:description: Show all parts in a sidebar for easy navigation.
:duration: 3 min

Create `templates/partials/series-toc.html`:

```html
{# templates/partials/series-toc.html #}
{% if page.series %}
<aside class="series-toc">
  <h4>
    <a href="{{ page._section.href }}">{{ page.series.name }}</a>
  </h4>

  <ol class="toc-parts">
    {% let series_pages = page._section.pages | sort_by('weight') %}
    {% for part in series_pages %}
    {% if part.series %}
    <li class="{% if part.eq(page) %}current{% end %}">
      <a href="{{ part.href }}">
        <span class="part-num">{{ part.series.part }}.</span>
        {{ part.nav_title or part.title }}
      </a>
    </li>
    {% end %}
    {% end %}
  </ol>

  <div class="toc-progress">
    {{ page.series.part }} / {{ page.series.total }} complete
  </div>
</aside>
{% end %}
```

Styles:

```css
.series-toc {
  position: sticky;
  top: 2rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 0.875rem;
}

.series-toc h4 {
  margin: 0 0 1rem;
  font-size: 0.875rem;
}

.series-toc h4 a {
  color: var(--text);
  text-decoration: none;
}

.toc-parts {
  list-style: none;
  padding: 0;
  margin: 0;
}

.toc-parts li {
  margin-bottom: 0.25rem;
}

.toc-parts a {
  display: block;
  padding: 0.5rem;
  border-radius: 4px;
  text-decoration: none;
  color: var(--text-muted);
}

.toc-parts a:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}

.toc-parts .current a {
  background: var(--accent);
  color: white;
}

.part-num {
  display: inline-block;
  width: 1.5rem;
  color: inherit;
}

.toc-progress {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
  text-align: center;
  color: var(--text-muted);
}
```

Include it in your series page layout:

```html
{% extends "default/base.html" %}

{% block content %}
<div class="series-layout">
  <aside class="series-sidebar">
    {% include "partials/series-toc.html" %}
  </aside>

  <article class="series-article">
    <h1>{{ page.title }}</h1>
    {{ page.content | safe }}

    {% include "partials/series-nav.html" %}
  </article>
</div>
{% endblock %}
```
:::{/step}

:::{step} Add Completion Celebration
:description: Celebrate when readers finish the series.
:duration: 2 min

Add a completion message to the series navigation for the last part:

```html
{# At the end of series-nav.html #}
{% if page.series and page.series.part == page.series.total %}
<div class="series-complete-banner">
  <div class="celebration">🎉</div>
  <h3>Congratulations!</h3>
  <p>You've completed "{{ page.series.name }}"</p>

  <div class="next-steps">
    <h4>What's Next?</h4>
    <ul>
      <li><a href="/tutorials/">Browse more tutorials</a></li>
      <li><a href="{{ share_url('twitter', page) }}">Share your achievement</a></li>
    </ul>
  </div>
</div>
{% end %}
```

Styles:

```css
.series-complete-banner {
  text-align: center;
  padding: 2rem;
  background: linear-gradient(135deg, var(--color-success-bg), var(--bg-secondary));
  border-radius: 12px;
  margin-top: 2rem;
}

.celebration {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.series-complete-banner h3 {
  margin: 0;
  color: var(--color-success);
}

.series-complete-banner p {
  color: var(--text-muted);
}

.next-steps {
  margin-top: 1.5rem;
  text-align: left;
  display: inline-block;
}

.next-steps h4 {
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.next-steps ul {
  margin: 0;
  padding-left: 1.25rem;
}

.next-steps a {
  color: var(--accent);
}
```
:::{/step}
:::{/steps}

## Summary

You now have a complete tutorial series system with:

- ✅ Multi-part content with series frontmatter
- ✅ Prev/next navigation with progress bar
- ✅ Series overview landing page
- ✅ Sidebar table of contents
- ✅ Completion celebration

## Next Steps

- **[Series Navigation Recipe](/docs/theming/recipes/series-navigation/)**: Quick reference
- **[Build a Multi-Author Blog](/docs/tutorials/sites/build-a-multi-author-blog/)**: Add author attribution
- **[Content Freshness](/docs/theming/recipes/content-freshness/)**: Show series age
