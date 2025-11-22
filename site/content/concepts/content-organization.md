---
title: Content Organization
description: Understand how Bengal maps files to URLs and organizes content into sections.
weight: 20
---

Bengal uses **file-system routing**. This means the structure of your `content/` directory directly determines the structure and URLs of your generated site.

## The Content Tree

At its core, Bengal organizes content into two types of objects: **Pages** and **Sections**.

*   **Page**: A single content file (e.g., `about.md`).
*   **Section**: A folder containing pages (e.g., `blog/`).

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

Every content file begins with **Frontmatter**, a YAML block surrounded by `---`. This defines metadata for the page.

```yaml
---
title: My First Post
date: 2023-10-25
tags: [python, web]
weight: 10
---
```

### Common Variables

| Variable | Description |
| :--- | :--- |
| `title` | The title of the page (required). |
| `date` | Publication date (used for sorting). |
| `draft` | If `true`, the page is skipped unless `--build-drafts` is used. |
| `weight` | Number for sorting order (lower numbers come first). |
| `slug` | Override the URL path (e.g., `my-custom-url`). |
| `tags` | List of tags for taxonomy pages. |

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

