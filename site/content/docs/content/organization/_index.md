---
title: Content Organization
description: How content is structured in Bengal
weight: 10
draft: false
lang: en
tags: [content, organization, structure]
keywords: [pages, sections, bundles, frontmatter, structure]
category: explanation
---

# Content Organization

Understanding how content is structured in Bengal — pages, sections, bundles, and navigation.

## Content Hierarchy

Bengal organizes content in a familiar directory-based hierarchy:

```
content/
├── _index.md           # Homepage
├── about.md            # Single page
├── blog/               # Section (list page + children)
│   ├── _index.md       # Section index
│   ├── first-post.md   # Regular page
│   └── photo-gallery/  # Page bundle
│       ├── index.md    # Bundle's main content
│       └── hero.jpg    # Co-located asset
└── docs/
    ├── _index.md
    └── getting-started/
        ├── _index.md
        └── installation.md
```

## Core Concepts

### Pages

A **page** is any `.md` file that becomes an HTML page. Two types:

- **Single pages** — Standalone files like `about.md` → `/about/`
- **Index pages** — `_index.md` files that define a section

### Sections

A **section** is a directory containing an `_index.md`. Sections:
- Create list pages showing their children
- Can be nested to any depth
- Support cascade configuration

### Page Bundles

A **page bundle** is a directory with `index.md` (not `_index.md`) that groups a page with its assets:

```
my-post/
├── index.md        # The page content
├── hero.jpg        # Co-located image
├── data.json       # Co-located data
└── diagram.svg     # Co-located asset
```

Assets in a bundle are only available to that page.

## In This Section

- **[Frontmatter Reference](/docs/content/organization/frontmatter/)** — All available frontmatter fields
- **[Menus](/docs/content/organization/menus/)** — Navigation menu configuration


