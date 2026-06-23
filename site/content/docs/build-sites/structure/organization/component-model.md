---


title: The Component Model
nav_title: Component Model
description: 'Understanding Bengal''s Component Model: Identity, Mode, and Data.'
weight: 20
variant: editorial
tags:
- persona-writer
- persona-themer
aliases:
  - /docs/content/organization/component-model/
aliases:
  - /docs/build-sites/structure/organization/component-model/
  - /docs/content/organization/component-model/
---

# The Component Model

Bengal uses a **Component Model** to organize content — aligning how files are
stored with how themes render them. Every page is a **component instance** with
three dimensions:

:::{note}
**Do I need this?** Read this when you need to understand `type`, `variant`, and
frontmatter props — especially for mixed-content sites or custom templates.
Skip if you only write simple docs pages with defaults.
:::

| Concept | Terminology | Key | Controls | Example |
| :--- | :--- | :--- | :--- | :--- |
| **Identity** | **Type** | `type` | Sorting, template family, URL patterns | `blog`, `doc`, `api` |
| **Mode** | **Variant** | `variant` | Visual layout, CSS, partials | `magazine`, `wide` |
| **Data** | **Props** | *(frontmatter)* | Custom fields passed to templates | `author`, `banner_image` |

## 1. Identity (Type) {#type}

The **Type** defines what the content *is*:

- **Sorting** — blog posts by date; docs by weight
- **Templates** — `type: blog` → `templates/blog/`
- **URL structure** — type-specific patterns when configured

| Type | Sorting | Use Case |
|------|---------|----------|
| `doc` | By weight | Technical documentation, guides |
| `blog` | By date (newest first) | Blog posts, news, articles |
| `page` | By weight | Static pages (about, contact) |
| `changelog` | By date | Release notes |
| `api` | By weight | API reference documentation |

```yaml
---
title: Installation Guide
weight: 10
type: doc
---
```

:::{dropdown} More type examples
:icon: book-open

See [[docs/build-sites/structure/organization/component-model-reference#type|Component Model Reference → Type examples]] for blog, page, changelog, and API patterns with template notes.
:::

## 2. Mode (Variant) {#variant}

The **Variant** defines how content *looks*:

- Sets `data-variant` on `<body>` for CSS targeting
- Selects layout partials (hero style, width, navigation density)

| Variant | Effect | Best For |
|---------|--------|----------|
| `standard` | Default clean layout | Most content |
| `editorial` | Enhanced typography, wider margins | Long-form articles |
| `magazine` | Visual-heavy, featured images | Blog posts with media |
| `overview` | Landing page style | Section index pages |
| `wide` | Full-width content area | Code-heavy documentation |
| `minimal` | Stripped-down, distraction-free | Focus content |

```yaml
---
title: Release Notes
type: doc
variant: wide
---
```

:::{dropdown} More variant examples
:icon: palette

See [[docs/build-sites/structure/organization/component-model-reference#variant|Component Model Reference → Variant examples]] for editorial, magazine, overview, and wide layouts.
:::

## 3. Data (Props) {#props}

**Props** are any frontmatter fields that are not `type` or `variant`. Templates
access them as `page.author`, `page.banner_image`, etc.

```yaml
---
title: "My Post"
type: blog
author: "Jane Doe"
featured: true
banner_image: "/images/hero.jpg"
---
```

:::{dropdown} Props examples by content type
:icon: list

See [[docs/build-sites/structure/organization/component-model-reference#props|Component Model Reference → Props examples]] for blog, doc, portfolio, and event prop patterns with template snippets.
:::

## Cascading from Sections {#cascade}

Set `type` and `variant` once in a section's `_index.md` — child pages inherit via `cascade`:

```yaml
---
title: Documentation
cascade:
  type: doc
  variant: standard
weight: 100
---
```

Child pages omit `type`:

```yaml
---
title: Installation
weight: 10
---
```

## Site Skeletons {#skeletons}

Scaffold entire site structures from `skeleton.yaml` manifests when running
`bengal new site --template …`. See
[[docs/examples/sites/skeleton-quickstart|Skeleton YAML Quickstart]] for a
walkthrough.

:::{dropdown} Skeleton manifest example
:icon: file-text

```yaml
name: blog
structure:
  - path: index.md
    type: blog
    props:
      title: My Blog
  - path: posts/hello.md
    type: blog
    props:
      title: Hello World
      date: "2026-01-15"
```

Full skeleton tab examples: [[docs/build-sites/structure/organization/component-model-reference#skeletons|Component Model Reference → Skeletons]].
:::

## Quick Reference

| Field | Purpose | Examples |
|-------|---------|----------|
| `type` | What it is (logic + templates) | `doc`, `blog`, `page`, `changelog` |
| `variant` | How it looks (CSS + partials) | `standard`, `editorial`, `magazine`, `wide` |
| `props` | Custom template data | `author`, `banner_image`, `featured` |

```jinja
<body data-type="{{ page.type }}" data-variant="{{ page.variant or '' }}">
<h1>{{ page.title }}</h1>
{% if page.featured %}<span class="badge">Featured</span>{% end %}
```

## Next Steps

- [[docs/build-sites/structure/organization/component-model-reference|Component Model Reference]] — exhaustive copy-paste examples
- [[docs/build-sites/structure/organization/frontmatter|Frontmatter]] — all standard fields
- [[docs/build-sites/structure/organization/menus|Menus]] — navigation from your content tree
- [[docs/build-sites/customize|Theming]] — template overrides for types and variants

## Legacy Migration

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `layout` | `variant` | Automatic normalization |
| `hero_style` | `variant` | Automatic normalization |
| `metadata` dict | flat props | Move fields to top level |

Bengal normalizes legacy fields automatically — existing content keeps working.
