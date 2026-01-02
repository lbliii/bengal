---
title: Content Reuse
nav_title: Reuse
description: Snippets, data files, and DRY patterns
weight: 50
category: guide
icon: recycle
card_color: teal
---
# Reusing Content

Write once, publish everywhere. Bengal provides multiple ways to avoid repeating yourself.

## Reuse Strategies

```mermaid
flowchart LR
    subgraph "Single Source"
        A[Snippet]
        B[Data File]
        C[Shortcode]
    end

    subgraph "Multiple Outputs"
        D[Page 1]
        E[Page 2]
        F[Page 3]
    end

    A --> D
    A --> E
    B --> D
    B --> F
    C --> E
    C --> F
```

## Quick Reference

:::{tab-set}
:::{tab-item} Snippets
Reusable Markdown fragments stored in `_snippets/`:

```
_snippets/
├── install/
│   ├── pip.md
│   └── uv.md
└── warnings/
    └── experimental.md
```

Include in any page:
````markdown
```{include} _snippets/install/pip.md
```
````
:::

:::{tab-item} Data Files
Structured YAML/JSON in `data/`:

```yaml
# data/team.yaml
- name: Jane Doe
  role: Lead Developer
  github: janedoe
```

Access in templates:
```kida
{% for member in site.data.team %}
  {{ member.name }} - {{ member.role }}
{% end %}
```
:::

:::{tab-item} Filtering
Query content dynamically:

```kida
{# All tutorials #}
{% let tutorials = site.pages
   |> where('type', 'tutorial') %}

{# Recent posts #}
{% let recent = site.pages
   |> sort_by('date', reverse=true)
   |> take(5) %}
```
:::
:::{/tab-set}

## When to Use What

| Method | Best For | Example |
|--------|----------|---------|
| **Snippets** | Repeated prose blocks | Installation instructions, warnings |
| **Data Files** | Structured data | Team members, product features |
| **Filtering** | Dynamic lists | Recent posts, related pages |
| **Shortcodes** | Parameterized components | Video embeds, API badges |

:::{tip}
**Start with snippets** for common content blocks. Graduate to data files when you need structured data, and filtering when you need dynamic queries.
:::
