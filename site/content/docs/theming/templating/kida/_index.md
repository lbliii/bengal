---
title: KIDA How-Tos
nav_title: KIDA How-Tos
description: Step-by-step guides for common KIDA template tasks
weight: 20
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
keywords:
- kida how-to
- template tasks
- kida patterns
category: guide
---

Step-by-step guides for common tasks when working with KIDA templates in Bengal.

## Common Tasks

:::{cards}
:columns: 2
:gap: medium

:::{card} Create a Custom Template
:icon: code
:link: ./create-custom-template
:description: Build a custom template from scratch using KIDA syntax
:color: blue
:::{/card}

:::{card} Add a Custom Filter
:icon: filter
:link: ./add-custom-filter
:description: Extend KIDA with your own template filters
:color: green
:::{/card}

:::{card} Use Pattern Matching
:icon: code-branch
:link: ./use-pattern-matching
:description: Replace long if/elif chains with clean pattern matching
:color: purple
:::{/card}

:::{card} Cache Template Fragments
:icon: zap
:link: ./cache-fragments
:description: Improve performance with built-in fragment caching
:color: orange
:::{/card}

:::{card} Migrate from Jinja2
:icon: arrow-right
:link: ./migrate-jinja-to-kida
:description: Convert existing Jinja2 templates to KIDA syntax
:color: teal
:::{/card}

:::{card} Use Pipeline Operator
:icon: workflow
:link: ./use-pipeline-operator
:description: Write readable filter chains with the pipeline operator
:color: indigo
:::{/card}

:::{card} KIDA vs Jinja2 Comparison
:icon: git-compare
:link: ./kida-vs-jinja-comparison
:description: Side-by-side syntax comparison for common template patterns
:color: cyan
:::{/card}
:::{/cards}

## What is KIDA?

KIDA is Bengal's native template engine, optimized for performance and free-threaded Python. It provides:

- **Unified syntax**: `{% end %}` closes all blocks
- **Pattern matching**: Clean `{% match %}...{% case %}` syntax
- **Pipeline operator**: Left-to-right readable filter chains
- **Fragment caching**: Built-in `{% cache %}` directive
- **Automatic block caching**: Site-scoped blocks cached automatically for 10-100x faster builds
- **Better performance**: 5.6x faster than Jinja2

## Automatic Block Caching

KIDA automatically caches site-scoped template blocks (like navigation, footer, sidebar) to dramatically improve build performance. This happens automatically—no template changes needed.

**How it works**:
- KIDA analyzes your templates to identify blocks that only depend on site-wide context
- These blocks are pre-rendered once at build start
- During page rendering, cached blocks are reused automatically
- **Result**: 10-100x faster builds for navigation-heavy sites

**Example**:
```kida
{# base.html - nav block depends only on site.pages #}
{% block nav %}
  <nav>
    {% for page in site.pages %}
      <a href="{{ page.url }}">{{ page.title }}</a>
    {% end %}
  </nav>
{% end %}
```

The `nav` block is automatically detected as site-cacheable and cached once per build, then reused for all pages. No template syntax changes required!

:::{seealso}

- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation
- [KIDA Tutorial](/docs/tutorials/getting-started-with-kida/) — Learn KIDA from scratch

:::
