---
title: Building Curated Learning Tracks
description: How to assemble multiple articles into linear learning paths or courses.
weight: 50
tags: [content-strategy, navigation, layout]
---

# Building Curated Learning Tracks

A common need is to guide users through a specific sequence of articles—like a "Getting Started Course" or "Advanced Python Track"—without duplicating the content or forcing a strict hierarchy.

Bengal provides built-in support for **Curated Tracks** with automatic navigation, progress tracking, and beautiful layouts. You just need to define your tracks in a data file.

## The Concept

Instead of hard-coding "Next" links in every article, you define the *sequence* centrally in a data file. This allows a single article (e.g., "Installation") to belong to several tracks (e.g., "Beginner Track" and "Server Admin Track").

Bengal automatically:
- Adds navigation between track pages
- Shows progress indicators
- Creates track listing pages
- Handles track overview pages

## Step 1: Define Your Tracks

Create a data file `site/data/tracks.yaml` to define your sequences:

```yaml:site/data/tracks.yaml
getting-started:
  title: "Bengal Essentials"
  description: "Master the basics of Bengal, from installation to creating your first theme."
  items:
    - docs/getting-started/installation.md
    - docs/getting-started/writer-quickstart.md
    - docs/getting-started/themer-quickstart.md
    - docs/getting-started/contributor-quickstart.md

content-mastery:
  title: "Content Mastery"
  description: "Advanced techniques for organizing and managing documentation at scale."
  items:
    - docs/guides/content-workflow.md
    - docs/guides/content-reuse.md
    - docs/guides/curated-tracks.md
    - docs/guides/advanced-filtering.md
```

**Track Structure**:
- `title`: Display name for the track
- `description`: Brief description shown on track cards
- `items`: List of page paths (relative to `site/content/`) in order

**Page Paths**: Use paths relative to `site/content/`, including the `.md` extension. For example, `docs/getting-started/installation.md` refers to `site/content/docs/getting-started/installation.md`.

## Step 2: Add Track Navigation to Pages

Track navigation automatically appears on any page that's listed in a track. The navigation component shows:
- Current track name and position
- Previous/Next buttons
- Progress bar

If you want to customize where the navigation appears, include the built-in partial in your template:

```jinja2
{% include "partials/track_nav.html" %}
```

The default theme already includes this automatically, so you typically don't need to do anything.

## Step 3: Create a Track Listing Page

Create a page that lists all available tracks:

```markdown:site/content/tracks/_index.md
---
title: Learning Tracks
description: Structured learning paths to help you master Bengal.
layout: tracks/list
---

Choose a track to start learning.
```

The `tracks/list` layout automatically:
- Displays all tracks in a beautiful grid
- Shows track descriptions and lesson counts
- Provides "Start Learning" buttons
- Links to the first lesson in each track

## Step 4: Create Individual Track Pages (Optional)

If you want a dedicated overview page for a specific track, create a page with the track template:

```markdown:site/content/tracks/getting-started.md
---
title: Bengal Essentials
description: Master the basics of Bengal
layout: tracks/single
track_id: getting-started
---

Welcome to the Bengal Essentials track! This track will guide you through...

[Your track introduction content here]
```

The `tracks/single` layout provides:
- A pillar-page style layout with all track lessons in one page
- Left sidebar with track navigation and progress
- Right sidebar with table of contents from all lessons
- Section-by-section navigation within the page

**Note**: The `track_id` in frontmatter should match the key in `tracks.yaml`. If omitted, Bengal uses the page slug.

## How It Works

When a page is listed in `tracks.yaml`:
1. **Automatic Detection**: Bengal detects which track(s) the page belongs to
2. **Navigation**: The `track_nav.html` partial automatically shows Previous/Next buttons
3. **Progress**: Progress bars show position within the track
4. **Links**: All navigation links are automatically generated

## Track Item Paths

Track items can reference pages in two ways:

**Full path** (recommended):
```yaml
items:
  - docs/getting-started/installation.md
```

**Relative path** (without `.md` extension):
```yaml
items:
  - getting-started/installation
```

Bengal's `get_page()` helper function resolves both formats automatically.

## Summary

By using Bengal's built-in track system, you can:
1. **Reuse content**: The same article can belong to several tracks
2. **Update easily**: Change track order by editing `tracks.yaml`
3. **Provide guidance**: Users get clear navigation and progress indicators
4. **No custom code**: Everything works out of the box with built-in templates

The track system decouples the **structure** (the track list) from the **content** (the articles), making it easy to create flexible learning paths without duplicating content or maintaining manual navigation links.
