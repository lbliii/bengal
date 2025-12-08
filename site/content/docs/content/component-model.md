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

## 1. Identity (Type)

The **Type** defines the fundamental nature of the content. It controls:
*   **Sorting Logic**: Blog posts sort by date; Docs sort by weight.
*   **Template Selection**: `type: blog` looks for `themes/[theme]/templates/blog/`.

```yaml
type: blog
```

## 2. Mode (Variant)

The **Variant** defines the visual presentation. It controls:
*   **CSS Classes**: Adds `.page-variant-[name]` to the `<body>`.
*   **Partials**: Selects specific components (e.g., `page-hero-magazine.html`).

```yaml
variant: magazine
```

## 3. Data (Props)

**Props** are the data you pass to the component.

**In Markdown files**, use flat frontmatter (all fields at top level):
```yaml
---
title: "My Post"
author: "Jane Doe"
banner_image: "/images/hero.jpg"
---
```

**In Skeleton Manifests** (`bengal skeleton apply`), you can use `props:` to group content separately from structural fields:
```yaml
structure:
  - path: blog/
    type: blog              # Identity (structural)
    variant: magazine       # Mode (structural)
    props:                 # Data (content)
      title: "Engineering Blog"
      banner_image: "/images/hero.jpg"
```
This separation makes it clear what's structural (type, variant) vs what's content (title, images).

## Site Skeletons

You can define an entire site structure using a **Skeleton Manifest** (`bengal skeleton apply`).

```yaml
structure:
  - path: blog/
    type: blog
    variant: magazine

    props:
      title: "Engineering Blog"
      description: "Deep dives."

    pages:
      - path: post-1.md
        props:
          title: "Hello World"
```

## Legacy Migration

If you are coming from older Bengal versions:
*   `layout` field $\to$ mapped to `variant`.
*   `hero_style` field $\to$ mapped to `variant`.
*   `metadata` dictionary $\to$ mapped to `props`.

The system automatically normalizes these for you.
