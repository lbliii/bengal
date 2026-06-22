---
title: Content
description: Author, organize, and validate your documentation
weight: 20
icon: file-text
tags:
- persona-writer
---

# The Content System

**Writing content?** Start with [[docs/content/authoring|Authoring]] and
[[docs/content/organization|Organization]]. **Pulling from GitHub or APIs?**
See [[docs/content/sources|Remote Sources]]. **Maintaining multiple doc
versions?** Read [[docs/content/versioning|Versioned Documentation]].

Bengal transforms Markdown files into structured, validated documentation sites
with rich directives, cross-references, and automated validation.

:::{glossary}
:tags: persona-writer
:limit: 4
:collapsed: true
:::

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## How Content Flows

```mermaid
flowchart LR
    subgraph Sources
        A[Local .md files]
        B[GitHub repos ⚡]
        C[Notion/APIs ⚡]
    end

    subgraph Processing
        D[Discovery]
        E[Frontmatter Parsing]
        F[MyST Directives]
        G[Cross-References]
    end

    subgraph Output
        H[HTML Pages]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
```

:::{note}
⚡ Remote sources require optional dependencies. Install with `pip install bengal[all-sources]` or individually: `bengal[github]`, `bengal[notion]`, `bengal[rest]`.
:::

## Key Features

| Feature | Description |
|---------|-------------|
| **Component Model** | `type`, `variant`, and `props` define page identity, appearance, and data |
| **MyST Directives** | Tabs, cards, admonitions, code blocks, and 60+ directives |
| **Cross-References** | `[[path]]` syntax with O(1) lookups and auto-title resolution |
| **Validation** | `bengal check` checks links, directives, and frontmatter |
| **Graph Analysis** | `bengal graph report` finds orphan pages and suggests links |

:::{tip}
**New to Bengal?** Start with [Organization](./organization/) to understand how files become pages, then explore [Authoring](./authoring/) for MyST syntax.

**Working on a larger site?** Use [Analysis](./analysis/) to optimize internal linking and [Validation](./validation/) for automated quality checks.
:::
