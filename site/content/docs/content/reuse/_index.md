---
title: Content Reuse
description: DRY content strategies with snippets and data files
weight: 50
draft: false
lang: en
tags: [reuse, snippets, dry]
keywords: [reuse, snippets, includes, data, dry]
category: guide
---

# Content Reuse

Write once, publish everywhere — strategies for DRY documentation.

## Overview

Bengal provides several mechanisms for content reuse:

- **Snippets** — Reusable content fragments via `_snippets/`
- **Data files** — YAML/JSON data accessible in templates
- **Shortcodes** — Parameterized content components
- **Filtering** — Query and filter content dynamically

## Snippets

The `_snippets/` directory contains reusable content fragments:

```
_snippets/
├── install/
│   ├── pip.md
│   ├── uv.md
│   └── pipx.md
└── warnings/
    ├── experimental.md
    └── breaking-change.md
```

Include snippets in your content:

```markdown
## Installation

{{< include "_snippets/install/pip.md" >}}
```

## Data Files

Store structured data in `data/` directory:

```yaml
# data/team.yaml
- name: Jane Doe
  role: Lead Developer
  github: janedoe
```

Access in templates:

```jinja
{% for member in site.data.team %}
  <div class="team-member">{{ member.name }}</div>
{% endfor %}
```

## Content Filtering

Query content dynamically:

```jinja
{% set tutorials = site.pages | selectattr("params.type", "equalto", "tutorial") %}
{% for page in tutorials %}
  <a href="{{ page.url }}">{{ page.title }}</a>
{% endfor %}
```

## In This Section

- **[Snippets](/docs/content/reuse/snippets/)** — Using the include directives and `_snippets/` system
- **[Filtering](/docs/content/reuse/filtering/)** — Advanced content queries with set intersections

