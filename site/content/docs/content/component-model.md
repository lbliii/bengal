---
title: The Component Model
description: 'Understanding Bengal''s Component Model: Identity, Mode, and Data.'
weight: 20
type: doc
variant: editorial
---

# The Component Model

Bengal uses a **Component Model** to organize content. This aligns the backend (how files are stored) with the frontend (how themes render them).

Think of every page as a **Component Instance**.

| Concept | Terminology | Schema Key | Definition | Example |
| :--- | :--- | :--- | :--- | :--- |
| **Identity** | **Type** | `type` | **What is it?**<br>Determines Logic (Sorting) & Template Family. | `blog`, `doc`, `api` |
| **Mode** | **Variant** | `variant` | **How does it look?**<br>Determines Visual State (CSS/Hero). | `magazine`, `wide` |
| **Data** | **Props** | `props` | **What data does it have?**<br>Content passed to template (Frontmatter). | `author`, `banner` |

---

## 1. Identity (Type) {#type}

The **Type** defines the fundamental nature of the content. It controls:

- **Sorting Logic**: Blog posts sort by date; Docs sort by weight.
- **Template Selection**: `type: blog` looks for `themes/[theme]/templates/blog/`.
- **URL Structure**: Different types may have different URL patterns.

### Available Types

| Type | Sorting | Use Case |
|------|---------|----------|
| `doc` | By weight | Technical documentation, guides |
| `blog` | By date (newest first) | Blog posts, news, articles |
| `page` | By weight | Static pages (about, contact) |
| `changelog` | By date | Release notes |
| `api` | By weight | API reference documentation |

### Full Examples

:::{tab-set}

:::{tab-item} Documentation Page
:icon: book-open

```yaml {5}
---
title: Installation Guide
description: How to install and configure Bengal
weight: 10
type: doc
tags:
  - getting-started
  - installation
---

# Installation Guide

Follow these steps to install Bengal...
```

**Line 5** is highlighted: `type: doc` tells Bengal this is documentation content.

**What happens**:
- Page sorted by `weight` (10) within its section
- Uses templates from `templates/doc/`
- Appears in documentation navigation
:::{/tab-item}

:::{tab-item} Blog Post
:icon: newspaper

```yaml {5}
---
title: Announcing Bengal 1.0
description: We're excited to announce the stable release
date: 2025-06-15
type: blog
tags:
  - announcement
  - release
category: news
author: Bengal Team
---

# Announcing Bengal 1.0

We're thrilled to share that Bengal 1.0 is now available...
```

**Line 5** is highlighted: `type: blog` tells Bengal this is a blog post — sorted by date.

**What happens**:
- Page sorted by `date` (newest first)
- Uses templates from `templates/blog/`
- Appears in blog feed and archives
- Date is required and prominently displayed
:::{/tab-item}

:::{tab-item} Static Page
:icon: file-text

```yaml {4}
---
title: About Us
description: Learn about our team and mission
type: page
---

# About Us

We're a team of developers passionate about documentation...
```

**Line 4** is highlighted: `type: page` tells Bengal this is a static page.

**What happens**:
- Page sorted by weight if specified
- Uses templates from `templates/page/`
- Not included in blog feeds or date-based archives
:::{/tab-item}

:::{tab-item} Changelog Entry
:icon: git-commit

```yaml {4-5}
---
title: Bengal 0.2.0
description: Major performance improvements and new features
type: changelog
date: 2025-06-01
weight: 5
---

# Bengal 0.2.0

## New Features

- Incremental builds with 10x faster rebuilds
- New shortcode system...
```

**Lines 4-5** are highlighted: `type: changelog` with `date` tells Bengal this is a release note.

**What happens**:
- Page sorted by date within the releases section
- Uses templates from `templates/changelog/`
- Formatted for release note presentation
:::{/tab-item}

:::{/tab-set}

---

## 2. Mode (Variant) {#variant}

The **Variant** defines the visual presentation. It controls:

- **CSS Classes**: Adds `.page-variant-[name]` to the `<body>`.
- **Partials**: Selects specific components (e.g., `page-hero-magazine.html`).
- **Layout Variations**: Different visual treatments for the same content type.

### Available Variants

| Variant | Effect | Best For |
|---------|--------|----------|
| `standard` | Default clean layout | Most content |
| `editorial` | Enhanced typography, wider margins | Long-form articles |
| `magazine` | Visual-heavy, featured images | Blog posts with media |
| `overview` | Landing page style | Section index pages |
| `wide` | Full-width content area | Code-heavy documentation |
| `minimal` | Stripped-down, distraction-free | Focus content |

### Full Examples

:::{tab-set}

:::{tab-item} Editorial Article
:icon: feather

```yaml {6}
---
title: "The Future of Static Sites"
description: "Why static is making a comeback"
date: 2025-06-01
type: blog
variant: editorial
author: "Jane Smith"
---

# The Future of Static Sites

In an era of increasingly complex web applications, there's a
quiet revolution happening...
```

**Line 6** is highlighted: `variant: editorial` applies enhanced typography for long-form reading.

**Visual effect**:
- Larger body text with better line height
- Pull quotes styled distinctively
- Wider content margins for readability
- Optimized for long-form reading
:::{/tab-item}

:::{tab-item} Magazine Layout
:icon: image

```yaml {6-7}
---
title: "Building Beautiful Documentation"
description: "A visual guide to documentation design"
date: 2025-06-01
type: blog
variant: magazine
banner_image: "/images/hero-docs.jpg"
featured: true
---

# Building Beautiful Documentation

![Hero Image](/images/hero-docs.jpg)

Documentation doesn't have to be boring...
```

**Lines 6-7** are highlighted: `variant: magazine` with `banner_image` creates a visual-first layout.

**Visual effect**:
- Large hero image at top
- Title overlaid on image or positioned dramatically
- Visual-first layout
- Cards and media prominently featured
:::{/tab-item}

:::{tab-item} Section Overview
:icon: compass

```yaml {6}
---
title: Documentation
description: Complete Bengal documentation
weight: 100
type: doc
variant: overview
icon: book-open
---

# Documentation

Welcome to Bengal documentation! Choose a section to get started.

:::{child-cards}
:::
```

**Line 6** is highlighted: `variant: overview` creates a landing page style with card navigation.

**Visual effect**:
- Section-style header
- Card grid for child pages
- Navigation-focused layout
- Less text, more visual navigation
:::{/tab-item}

:::{tab-item} Wide Code Docs
:icon: code

```yaml {5}
---
title: API Reference
description: Complete API documentation
type: doc
variant: wide
---

# API Reference

## `bengal.core.Page`

\`\`\`python
@dataclass
class Page:
    """Represents a single content page."""
    source_path: Path
    content: str
    metadata: dict[str, Any]
    rendered_html: str = ""
    # ... many more fields
\`\`\`
```

**Line 5** is highlighted: `variant: wide` provides full-width content area for code-heavy docs.

**Visual effect**:
- No sidebar or narrow margins
- Code blocks have maximum width
- Tables can be wider
- Ideal for API reference with large code samples
:::{/tab-item}

:::{/tab-set}

---

## 3. Data (Props) {#props}

**Props** are the data you pass to the component. Any frontmatter field that isn't `type` or `variant` becomes a prop.

### In Markdown Files

Use flat frontmatter (all fields at top level):

```yaml
---
title: "My Post"
description: "A description for SEO and previews"
author: "Jane Doe"
banner_image: "/images/hero.jpg"
featured: true
custom_field: "Any value you need"
---
```

### Full Examples by Content Type

:::{tab-set}

:::{tab-item} Blog Post Props
:icon: newspaper

```yaml {6-17}
---
title: "10 Tips for Better Documentation"
description: "Practical advice from years of writing docs"
date: 2025-06-01
type: blog
author: "Jane Doe"
author_image: "/images/authors/jane.jpg"
author_bio: "Technical writer with 10 years of experience"
category: "Writing"
tags:
  - documentation
  - writing
  - best-practices
reading_time: "8 min"
featured: true
banner_image: "/images/posts/docs-tips.jpg"
---
```

**Lines 6-17** are highlighted: all fields after `type` are **props** — custom data available in templates.

**In templates**:
```jinja
<img src="{{ page.author_image }}" alt="{{ page.author }}">
<span>{{ page.reading_time }} read</span>
{% if page.featured %}
  <span class="badge">Featured</span>
{% endif %}
```
:::{/tab-item}

:::{tab-item} Documentation Props
:icon: book-open

```yaml {6-12}
---
title: "Configuration Reference"
description: "All configuration options for Bengal"
weight: 30
type: doc
icon: settings
badge: "Updated"
badge_color: "green"
toc_depth: 3
show_edit_link: true
github_path: "docs/reference/configuration.md"
---
```

**Lines 6-12** are highlighted: props customize appearance — icons, badges, navigation.

**In templates**:
```jinja
{% if page.icon %}
  <i class="icon-{{ page.icon }}"></i>
{% endif %}
{% if page.badge %}
  <span class="badge badge-{{ page.badge_color }}">
    {{ page.badge }}
  </span>
{% endif %}
```
:::{/tab-item}

:::{tab-item} Project/Portfolio Props
:icon: briefcase

```yaml {6-19}
---
title: "E-Commerce Platform"
description: "Full-stack e-commerce solution"
date: 2025-03-15
type: page
project_url: "https://example.com"
github_url: "https://github.com/user/project"
technologies:
  - React
  - Node.js
  - PostgreSQL
  - Docker
status: "Production"
client: "Acme Corp"
thumbnail: "/images/projects/ecommerce-thumb.jpg"
gallery:
  - "/images/projects/ecommerce-1.jpg"
  - "/images/projects/ecommerce-2.jpg"
---
```

**Lines 6-19** are highlighted: rich props for portfolio pages — URLs, arrays, any structure you need.

**In templates**:
```jinja
<div class="tech-stack">
  {% for tech in page.technologies %}
    <span class="tech-badge">{{ tech }}</span>
  {% endfor %}
</div>
<a href="{{ page.project_url }}">View Live</a>
```
:::{/tab-item}

:::{tab-item} Event/Talk Props
:icon: calendar

```yaml {6-17}
---
title: "Building Fast Static Sites"
description: "Conference talk about Bengal SSG"
date: 2025-09-15
type: page
event_name: "PyCon 2025"
event_url: "https://pycon.org/2025"
location: "San Francisco, CA"
slides_url: "/slides/building-fast-static-sites.pdf"
video_url: "https://youtube.com/watch?v=..."
duration: "45 minutes"
audience_level: "Intermediate"
topics:
  - Static Site Generation
  - Performance
  - Python
---
```

**Lines 6-17** are highlighted: props for event/talk pages — links to slides, videos, event details.

**In templates**:
```jinja
<p>Presented at <a href="{{ page.event_url }}">{{ page.event_name }}</a></p>
<p>Duration: {{ page.duration }}</p>
{% if page.video_url %}
  <a href="{{ page.video_url }}">Watch Recording</a>
{% endif %}
```
:::{/tab-item}

:::{/tab-set}

---

## Combining Type, Variant, and Props

Here's how all three work together in real examples:

:::{tab-set}

:::{tab-item} Full Blog Post
:icon: file-text

```yaml {4-5,7-20}
---
title: "Migrating from WordPress to Bengal"
description: "A step-by-step guide to moving your blog"
type: blog
variant: magazine
date: 2025-06-01
author: "Alex Chen"
author_image: "/images/authors/alex.jpg"
banner_image: "/images/posts/wp-migration.jpg"
banner_alt: "WordPress to Bengal migration diagram"
category: "Tutorials"
tags:
  - migration
  - wordpress
  - tutorial
reading_time: "15 min"
difficulty: "Intermediate"
series: "Migration Guides"
series_order: 1
---
```

**Lines 4-5** are `type` and `variant`; **lines 7-20** are props. All three working together:
- `type: blog` — sorted by date, uses blog templates
- `variant: magazine` — visual layout with hero image
- Props — author info, metadata, series tracking
:::{/tab-item}

:::{tab-item} Full Documentation Page
:icon: book

```yaml {4-5,7-15}
---
title: "Template Functions Reference"
description: "Complete reference for Bengal template functions"
type: doc
variant: wide
weight: 50
icon: function
badge: "v0.2+"
toc_depth: 4
show_source_links: true
api_version: "0.2.0"
related_pages:
  - /docs/reference/template-variables/
  - /docs/tutorials/custom-templates/
---
```

**Lines 4-5** are `type` and `variant`; **lines 7-15** are props. All three working together:
- `type: doc` — sorted by weight, uses doc templates
- `variant: wide` — full-width for code examples
- Props — versioning, related content links
:::{/tab-item}

:::{tab-item} Full Section Index
:icon: folder

```yaml {4-5,7-12}
---
title: "Getting Started"
description: "Everything you need to begin with Bengal"
type: doc
variant: overview
weight: 10
icon: rocket
show_child_cards: true
card_columns: 2
featured_page: "/docs/get-started/quickstart/"
section_color: "blue"
---

# Getting Started

Welcome! Choose where to begin based on your experience.

:::{child-cards}
:columns: 2
:::
```

**Lines 4-5** are `type` and `variant`; **lines 7-12** are props. All three working together:
- `type: doc` — this section contains documentation
- `variant: overview` — landing page with card navigation
- Props — card layout, section appearance
:::{/tab-item}

:::{/tab-set}

---

## Cascading from Sections {#cascade}

Set `type` and `variant` once in a section's `_index.md` and all child pages inherit them:

```yaml {5-8}
# content/docs/_index.md
---
title: Documentation
description: Complete Bengal documentation
cascade:
  type: doc
  variant: standard
weight: 100
---
```

**Lines 5-8** are highlighted: the `cascade` block sets `type` and `variant` for all child pages automatically.

Now child pages don't need to specify `type`:

```yaml
# content/docs/installation.md (inherits type: doc)
---
title: Installation
weight: 10
---
```

---

## Site Skeletons {#skeletons}

Define entire site structures using **Skeleton Manifests** (`bengal project skeleton apply`).

:::{tab-set}

:::{tab-item} Blog Skeleton
:icon: newspaper

```yaml {7-8,14,24-25}
name: blog
description: A blog with posts, tags, and categories
version: "1.0"

structure:
  - path: index.md
    type: blog
    variant: magazine
    props:
      title: My Blog
      description: Welcome to my blog

  - path: posts/first-post.md
    type: blog
    props:
      title: My First Blog Post
      date: "2025-06-01"
      tags:
        - welcome
        - introduction
      category: meta

  - path: about.md
    type: page
    variant: standard
    props:
      title: About
      description: Learn more about me
```

**Highlighted lines**: Index and posts use `type: blog` (lines 7-8, 14); About page uses `type: page` (lines 24-25) — different template family.
:::{/tab-item}

:::{tab-item} Docs Skeleton
:icon: book-open

```yaml {7-10,17}
name: docs
description: Technical documentation
version: "1.0"

structure:
  - path: _index.md
    type: doc
    cascade:
      type: doc
      variant: standard
    props:
      title: Documentation
      weight: 100

  - path: getting-started/_index.md
    type: doc
    variant: overview
    props:
      title: Getting Started
      weight: 10
      icon: rocket
```

**Highlighted lines**: Root sets `type: doc` with cascade (lines 7-10); Getting started overrides `variant: overview` (line 17) for landing page style.
:::{/tab-item}

:::{tab-item} Portfolio Skeleton
:icon: briefcase

```yaml {7-8,18-19,21-26}
name: portfolio
description: Portfolio site with projects showcase
version: "1.0"

structure:
  - path: index.md
    type: page
    variant: home
    props:
      title: Portfolio
      description: Welcome to my portfolio

  - path: projects/_index.md
    props:
      title: Projects

  - path: projects/project-1.md
    type: page
    variant: project
    props:
      title: E-Commerce Platform
      featured: true
      technologies:
        - React
        - Node.js
      demo_url: https://example.com
```

**Highlighted lines**: Home page uses `variant: home` (lines 7-8); Projects use `variant: project` (lines 18-19) with rich props (lines 21-26).
:::{/tab-item}

:::{/tab-set}

---

## Quick Reference

| Field | Purpose | Examples |
|-------|---------|----------|
| `type` | What it is (logic + templates) | `doc`, `blog`, `page`, `changelog` |
| `variant` | How it looks (CSS + partials) | `standard`, `editorial`, `magazine`, `wide`, `overview` |
| `props` | Custom data for templates | `author`, `banner_image`, `featured`, anything else |

### In Templates

```jinja
{# Access type and variant #}
<body class="page-type-{{ page.type }} page-variant-{{ page.variant }}">

{# Access props directly #}
<h1>{{ page.title }}</h1>
<p>By {{ page.author }}</p>
{% if page.featured %}
  <span class="badge">Featured</span>
{% endif %}
```

---

## Legacy Migration

If you are coming from older Bengal versions:

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `layout` | `variant` | Automatic normalization |
| `hero_style` | `variant` | Automatic normalization |
| `metadata` dict | flat props | Move fields to top level |

The system automatically normalizes these for you—no changes required to existing content.
