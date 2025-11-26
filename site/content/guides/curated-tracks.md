---
title: Building Curated Learning Tracks
description: How to assemble multiple articles into linear learning paths or courses.
weight: 50
tags: [content-strategy, navigation, layout]
---

# Building Curated Learning Tracks

A common documentation requirement is to guide users through a specific sequence of articles—like an "Onboarding Course" or "Advanced Python Track"—without duplicating the content or forcing a strict hierarchy.

This guide shows you how to build **Curated Tracks** using Data Files and Layouts.

## The Concept

Instead of hard-coding "Next" links in every article, we define the *sequence* centrally in a data file. This allows a single article (e.g., "Installation") to belong to multiple tracks (e.g., "Beginner Track" and "Server Admin Track").

## Step 1: Define the Track

Create a data file `site/data/tracks.yaml` to define your sequences.

```yaml:site/data/tracks.yaml
onboarding:
  title: "New User Onboarding"
  description: "Go from zero to hero in 4 steps."
  items:
    - getting-started/installation
    - getting-started/configuration
    - tutorials/first-post
    - deployment/production

advanced:
  title: "Advanced Architecture"
  items:
    - reference/architecture/core-concepts
    - reference/architecture/caching-strategies
    - reference/architecture/plugin-development
```

## Step 2: Create the Track Logic

We need a way to find where the current page sits within a track. We can do this with a Jinja macro or partial.

Create `bengal/themes/default/templates/partials/track_nav.html`:

```jinja2
{% set current_slug = page.relative_path | replace('.md', '') %}

{# Check if page is in any track #}
{% for track_id, track in site.data.tracks.items() %}
  {% if current_slug in track.items %}

    {% set current_index = track.items.index(current_slug) %}
    {% set prev_slug = track.items[current_index - 1] if current_index > 0 else None %}
    {% set next_slug = track.items[current_index + 1] if current_index < (track.items|length - 1) else None %}

    <div class="track-navigation card mb-4">
      <div class="card-header">
        <strong>Track: {{ track.title }}</strong>
        <span class="float-end">{{ current_index + 1 }} of {{ track.items|length }}</span>
      </div>
      <div class="card-body d-flex justify-content-between">

        {% if prev_slug %}
          {% set prev_page = site.pages | selectattr("relative_path", "contains", prev_slug) | first %}
          <a href="{{ prev_page.url }}" class="btn btn-outline-primary">
            &larr; {{ prev_page.title }}
          </a>
        {% else %}
          <span></span> {# Spacer #}
        {% endif %}

        {% if next_slug %}
          {% set next_page = site.pages | selectattr("relative_path", "contains", next_slug) | first %}
          <a href="{{ next_page.url }}" class="btn btn-primary">
            {{ next_page.title }} &rarr;
          </a>
        {% else %}
          <a href="/tracks/" class="btn btn-success">Finish Track &check;</a>
        {% endif %}

      </div>
      <div class="progress" style="height: 4px;">
        <div class="progress-bar" role="progressbar"
             style="width: {{ ((current_index + 1) / track.items|length) * 100 }}%"></div>
      </div>
    </div>

  {% endif %}
{% endfor %}
```

## Step 3: Add to Layout

Include this partial in your `base.html` or `single.html` template, typically above or below the main content.

```html
<!-- In templates/single.html -->
{% block content %}

  <h1>{{ page.title }}</h1>

  {% include "partials/track_nav.html" %}

  <div class="content">
    {{ page.content }}
  </div>

  {% include "partials/track_nav.html" %}

{% endblock %}
```

## Step 4: Create a Track Overview Page

You probably want a landing page that lists all available tracks.

Create `site/content/tracks/_index.md`:

```markdown
---
title: Learning Tracks
layout: tracks_index
---
# Learning Tracks

Choose a path to master Bengal.
```

And the corresponding layout `templates/tracks_index.html`:

```jinja2
{% extends "base.html" %}

{% block content %}
<h1>{{ page.title }}</h1>

<div class="row">
{% for id, track in site.data.tracks.items() %}
  <div class="col-md-6 mb-4">
    <div class="card h-100">
      <div class="card-body">
        <h2 class="card-title">{{ track.title }}</h2>
        <p>{{ track.description }}</p>
        <p>{{ track.items|length }} Lessons</p>
        <a href="{{ site.pages | selectattr('relative_path', 'contains', track.items[0]) | first | attr('url') }}" class="btn btn-primary">
          Start Track
        </a>
      </div>
    </div>
  </div>
{% endfor %}
</div>
{% endblock %}
```

## Summary

By decoupling the **structure** (the track list) from the **content** (the articles), you can:
1.  Reuse the same article in multiple contexts.
2.  Update the order of a course without editing every single file.
3.  Provide users with a clear sense of progress.
