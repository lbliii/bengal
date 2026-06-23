---
title: Directive Kitchen Sink
nav_title: Kitchen Sink
description: Live gallery of Bengal MyST directives — see every component type in action
weight: 5
icon: grid
tags:
- reference
- directives
- persona-writer
keywords:
- directives
- kitchen sink
- gallery
- examples
---

# Directive Kitchen Sink

Every directive category on one page — live examples you can copy into your own
content. For option reference and edge cases, see the category pages linked at
the bottom.

:::{note}
**Do I need this?** Skim this page when you want to see what Bengal can render.
Use category reference pages when you need exhaustive option lists.
:::

## Admonitions

:::{note} Note
Informational callout with **markdown** support.
:::

:::{tip}
Helpful suggestion — great for shortcuts and best practices.
:::

:::{warning} Warning
Something may break or needs attention before you proceed.
:::

:::{danger}
Critical — data loss, security, or irreversible action possible.
:::

## Layout

::::{cards}
:columns: 2

:::{card} Cards
:icon: layout
:link: ./layout.md
Two-column card grid for navigation and feature highlights.
:::

:::{card} Child Cards
:icon: folder
:link: ./layout.md
Auto-generates cards from section children via `{child-cards}`.
:::

::::{/cards}

::::{tab-set}

:::{tab-item} Tab A
First panel content.
:::

:::{tab-item} Tab B
:selected:
Second panel, selected by default.
:::

::::{/tab-set}

:::{dropdown} Dropdown / Details
:icon: chevron-down

Collapsed content for advanced options, edge cases, or long prose you do not
want above the fold.
:::

## Formatting & UI

{bdg-primary}`New` {bdg-secondary}`Badge`

:::{checklist} Example checklist
:show-progress:
- [x] Install Bengal
- [ ] Write your first page
- [ ] Deploy to production
:::

:::{steps}

:::{step} First step
Do the obvious thing first.
:::

:::{step} Second step
Follow up with the next action.
:::

:::{/steps}

:::{button} Get Started
:link: /docs/get-started/
:style: primary
:::

## Code & Data

:::{code-tabs}

```python hello.py
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

```javascript hello.js
function greet(name) {
  console.log(`Hello, ${name}!`);
}
```

:::

## Versioning

:::{since} 0.4.0
Symbol cross-linking in Python autodoc output.
:::

:::{deprecated} 0.4.0
The in-repo `chirpui` bridge theme — use external theme packages instead.
:::

:::{changed} 0.4.0
OpenAPI autodoc now generates one page per endpoint by default.
:::

## Glossary (progressive disclosure)

:::{glossary}
:tags: directives, core
:limit: 3
:collapsed: true
:::

## Roles & Cross-References

- Keyboard: {kbd}`Ctrl+C`
- Abbreviation: {abbr}`SSG (Static Site Generator)`
- Inline math: {math}`E = mc^2`
- Document link: {doc}`/docs/get-started/quickstart-writer`

## Category Reference

:::{child-cards}
:columns: 2
:include: pages
:fields: title, description
:::

## Next Steps

- [[docs/build-sites/write/authoring/callouts|Authoring → Callouts]] — when to use each admonition type
- [[docs/build-sites/write/authoring/interactive|Authoring → Interactive]] — tabs, steps, and checklists in guides
- [[docs/get-started/quickstart-writer|Writer Quickstart]] — put directives to work in your first site
