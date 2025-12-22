---
title: Organize Content
nav_title: Content
description: Map files to URLs and organize content into sections
weight: 20
type: doc
draft: false
lang: en
tags:
- content
- organization
- structure
- frontmatter
keywords:
- content organization
- frontmatter
- sections
- pages
- structure
category: documentation
---

Bengal uses **file-system routing**. This means the structure of your `content/` directory directly determines the structure and URLs of your generated site.

## The Content Tree

At its core, Bengal organizes content into two types of objects: **Pages** and **Sections**.

Page
:   A single content file (e.g., `about.md`) that becomes a URL on your site. Each markdown file in your `content/` directory becomes a page.

Section
:   A folder containing pages (e.g., `blog/`). Sections organize related pages together and can have their own listing pages.

### Mapping Files to URLs

Bengal maps your file paths to URLs automatically.

| File Path | Generated URL | Type |
| :--- | :--- | :--- |
| `content/about.md` | `/about/` | Page |
| `content/blog/post-1.md` | `/blog/post-1/` | Page |
| `content/docs/setup.md` | `/docs/setup/` | Page |
| `content/blog/` | `/blog/` | Section |

## Index Files: `_index.md` vs `index.md`

This is the most important concept in Bengal's organization. The filename dictates whether a file represents a **Section** or a **Page**.

### `_index.md` (Section Bundle)

Use `_index.md` to define metadata and content for a **Section** (a folder).

*   **Purpose**: Adds a title, description, or listing content to a folder (e.g., `/blog/`).
*   **Behavior**: It allows the folder to contain *other* pages.
*   **Example**: `content/blog/_index.md` creates the `/blog/` listing page.

```yaml
# content/blog/_index.md
---
title: Our Blog
cascade:
  type: post
---
Welcome to our engineering blog. Here are our latest updates.
```

### `index.md` (Leaf Bundle)

Use `index.md` to create a **Page** that lives in its own folder.

*   **Purpose**: Keeps a page's assets (images, data) together with the content.
*   **Behavior**: It is a "leaf" node; it does not have child pages (conceptually).
*   **Example**: `content/about/index.md` creates `/about/`. You can put `me.jpg` in `content/about/` and refer to it easily.

:::{warning}
**Collision Warning**: Do not put both `_index.md` and `index.md` in the same folder. Bengal will prefer `_index.md` and log a warning.
:::

## Frontmatter

Frontmatter
:   Metadata at the top of your markdown file (between `---` delimiters) that controls how Bengal processes and displays your page. Written in YAML format.

Every content file begins with **Frontmatter**, a YAML block surrounded by `---`. This defines metadata for the page.

```yaml
---
title: My First Post
date: 2023-10-25
tags: [python, web]
weight: 10
---
```

### Supported Frontmatter Keys

Bengal supports the following frontmatter keys with their types and default values:

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `string` | filename-derived | Page title. If omitted, Bengal generates a title from the filename (e.g., `my-post.md` → "My Post"). |
| `nav_title` | `string` | `title` value | Short title for navigation menus. Falls back to `title` if not specified. |
| `date` | `datetime` or `string` | `None` | Publication date. Used for sorting, archives, and RSS feeds. Accepts ISO format (`2023-10-25`) or full datetime (`2023-10-25T14:30:00`). |
| `tags` | `list[string]` | `[]` | List of tag strings for taxonomy pages and filtering. Example: `tags: [python, web, tutorial]` |
| `slug` | `string` | filename-derived | Override the URL path. If not specified, Bengal generates a slug from the filename. Example: `slug: my-custom-url` |
| `weight` | `integer` | `None` | Sort weight within section. Lower numbers appear first. Used for manual ordering in sidebars and listings. |
| `lang` | `string` | site default | Language code for i18n (e.g., `"en"`, `"es"`, `"fr"`). If not specified, uses the site's default language. |
| `type` | `string` | `None` | Page type that determines which layout/template to use (e.g., `"doc"`, `"post"`, `"page"`). Can be cascaded from section `_index.md`. |
| `variant` | `string` | `None` | Visual variant for CSS/layout customization. Use for different visual styles within the same type. |
| `description` | `string` | auto-generated | Page description for SEO meta tags. If omitted, Bengal generates one from content (max 160 chars). |
| `draft` | `boolean` | `false` | If `true`, the page is skipped during builds unless `--build-drafts` is used. Useful for work-in-progress content. |
| `hidden` | `boolean` | `false` | If `true`, the page is excluded from listings, sitemap, and search, but still renders and is accessible by URL. |
| `keywords` | `list[string]` or `string` | `[]` | SEO keywords. Can be a list (`keywords: [python, web]`) or comma-separated string (`keywords: "python, web"`). |
| `category` | `string` | `None` | Single category for taxonomy pages. Unlike tags, categories are single-valued (e.g., `category: tutorial`). |
| `aliases` | `list[string]` | `[]` | Alternative URLs that redirect to this page. Useful for preserving old URLs after restructuring. |

### Example Frontmatter

Here's a complete example using all common fields:

```yaml
---
title: Getting Started with Bengal
date: 2025-10-26
tags: [tutorial, beginner, static-sites]
slug: getting-started
weight: 1
lang: en
type: doc
description: Learn how to build your first site with Bengal SSG
draft: false
keywords: [bengal, static site generator, tutorial]
---
```

### Field Details

**Title**: If you omit `title`, Bengal automatically generates one from the filename:
- `my-first-post.md` → `"My First Post"`
- `autodoc/python.md` → `"Api Reference"`
- For `_index.md` files, uses the parent directory name instead of "Index"

**Date**: Flexible date parsing supports multiple formats:
- `date: 2023-10-25` (ISO date)
- `date: 2023-10-25T14:30:00` (ISO datetime)
- `date: "October 25, 2023"` (natural language)

**Tags**: Used for taxonomy pages and filtering. Tags are case-sensitive and should be consistent across pages.

**Weight**: Lower numbers appear first. Useful for documentation ordering:
- `weight: 1` appears before `weight: 10`
- Pages without weight are sorted by date (newest first) or title (alphabetical)

**Type**: Determines which template/layout to use. Common types:
- `doc` - Documentation pages
- `post` - Blog posts
- `page` - Regular pages
- `changelog` - Release notes

**Draft**: Draft pages are excluded from builds by default. Use `bengal build --build-drafts` to include them.

**Hidden**: Hidden pages render and are accessible by URL but are excluded from:
- Navigation menus
- Site listings (`site.pages`)
- Sitemap.xml
- Search index
- RSS feeds

## Visibility System

For granular control over page visibility, use the `visibility` object in frontmatter:

```yaml
---
title: Partially Hidden Page
visibility:
  menu: false        # Exclude from navigation menus
  listings: true     # Include in site.pages queries
  sitemap: true      # Include in sitemap.xml
  search: false      # Exclude from search index
  rss: false         # Exclude from RSS feeds
  robots: "noindex, follow"  # Custom robots meta directive
---
```

The `hidden: true` shorthand expands to restrictive defaults for all visibility settings.

## Sorting & Ordering

By default, Bengal sorts pages in lists (like your blog feed or sidebar) using the following priority:

1.  **Weight**: Lower weights appear first (e.g., `1` comes before `10`).
2.  **Date**: Newer dates appear first (for blog posts).
3.  **Title**: Alphabetical order.

To manually order your documentation sidebar, simply add `weight` to your frontmatter:

```yaml
---
title: Introduction
weight: 1
---
```

## Cascading Metadata

You can apply metadata to **all pages within a section** using the `cascade` key in that section's `_index.md`.

This is useful for setting the `type` or `layout` for a whole directory without repeating it in every file.

```yaml
# content/blog/_index.md
---
title: Blog
cascade:
  type: blog-post  # Applies to all pages in content/blog/**
  banner: default.jpg
---
```

Any page inside `content/blog/` will now automatically have `type: blog-post` unless it specifically overrides it.

## Validating Frontmatter

Want to catch frontmatter errors at build time? Use [Content Collections](/docs/content/collections/) to define schemas that validate your content automatically. Collections are optional but helpful for teams or sites with strict content requirements.
