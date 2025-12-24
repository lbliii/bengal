---
title: Directives Reference
nav_title: Directives
description: Complete reference for all available markdown directives in Bengal
weight: 10
icon: code
tags: [reference, directives, markdown, syntax]
keywords: [directives, markdown, syntax, reference, admonitions, tabs, cards, youtube, vimeo, video, audio, figure, media, embed]
---

# Directives Reference

Bengal extends Markdown with powerful directives using `:::{name}` or ` ```{name} ` syntax. Directives provide rich components like callouts, tabs, cards, and more.

## Key Terms

:::{glossary}
:tags: directives, core
:limit: 3
:::

## Quick Reference

### Admonitions

| Directive | Purpose |
|-----------|---------|
| `{note}` | Information callout |
| `{tip}` | Helpful suggestion |
| `{warning}` | Warning callout |
| `{caution}` | Cautionary note (renders as warning) |
| `{danger}` | Critical warning |
| `{error}` | Error message |
| `{info}` | Informational content |
| `{example}` | Example usage |
| `{success}` | Success message |
| `{seealso}` | Cross-reference callout |

### Layout

| Directive | Aliases | Purpose |
|-----------|---------|---------|
| `{cards}` | `{grid}` | Card grid container |
| `{card}` | `{grid-item-card}` | Individual card |
| `{child-cards}` | — | Auto-generate cards from children |
| `{tab-set}` | `{tabs}` | Tab container |
| `{tab-item}` | `{tab}` | Individual tab |
| `{dropdown}` | `{details}` | Collapsible section |
| `{container}` | `{div}` | Generic wrapper |

### Formatting

| Directive | Aliases | Purpose |
|-----------|---------|---------|
| `{badge}` | `{bdg}` | Styled badge |
| `{button}` | — | Link button |
| `{build}` | — | Build-time badge |
| `{steps}` | — | Step-by-step guide |
| `{step}` | — | Individual step |
| `{checklist}` | — | Styled checklist |
| `{rubric}` | — | Pseudo-heading (not in TOC) |
| `{list-table}` | — | Table from lists |

### Content Reuse

| Directive | Purpose |
|-----------|---------|
| `{include}` | Include markdown file |
| `{literalinclude}` | Include code file with syntax highlighting |

### Interactive

| Directive | Aliases | Purpose |
|-----------|---------|---------|
| `{code-tabs}` | `{code_tabs}` | Multi-language code tabs |
| `{data-table}` | — | Interactive data table |

### Media Embeds

| Directive | Purpose |
|-----------|---------|
| `{youtube}` | YouTube embed (privacy-enhanced by default) |
| `{vimeo}` | Vimeo embed (DNT by default) |
| `{video}` | Self-hosted HTML5 video |
| `{audio}` | Self-hosted HTML5 audio |
| `{figure}` | Image with caption |
| `{gist}` | GitHub Gist embed |
| `{codepen}` | CodePen embed |
| `{codesandbox}` | CodeSandbox embed |
| `{stackblitz}` | StackBlitz embed |
| `{asciinema}` | Terminal recording |
| `{gallery}` | Image gallery |

### Navigation

| Directive | Purpose |
|-----------|---------|
| `{child-cards}` | Auto-generate cards from child sections/pages |
| `{breadcrumbs}` | Breadcrumb navigation trail |
| `{siblings}` | Sibling page links |
| `{prev-next}` | Previous/next navigation links |
| `{related}` | Related pages by shared tags |

### Versioning

| Directive | Aliases | Purpose |
|-----------|---------|---------|
| `{since}` | `{versionadded}` | Mark feature as new |
| `{deprecated}` | `{versionremoved}` | Mark feature as deprecated |
| `{changed}` | `{versionchanged}` | Mark behavior change |

### Other

| Directive | Aliases | Purpose |
|-----------|---------|---------|
| `{glossary}` | — | Render terms from glossary data |
| `{target}` | `{anchor}` | Create link target |
| `{icon}` | `{svg-icon}` | Inline SVG icon |
| `{example-label}` | — | Example label for documentation |
| `{marimo}` | — | Interactive Python notebook |
| `{gallery}` | — | Image gallery |

## Directive Syntax

Bengal supports MyST-style directive syntax using triple colons `:::`. Most directives use this format:

```markdown
:::{directive-name} Optional Title
:option: value

Content here
:::
```

### Named Closers

For nested directives, use named closers (`:::{/name}`) to avoid ambiguity:

```markdown
:::{cards}
:columns: 3

:::{card} First Card
Content
:::{/card}

:::{card} Second Card
Content
:::{/card}

:::{/cards}
```

### Deep Nesting

Named closers are particularly useful for deeply nested structures:

```markdown
:::{steps}

:::{step} First Step
:::{tip}
Remember to check the logs!
:::
:::{/step}

:::{step} Second Step
:::{warning}
This step requires admin access.
:::
:::{/step}

:::{/steps}
```

### Directive Options

Options are specified with `:option: value` syntax on separate lines after the directive name:

```markdown
:::{card} Card Title
:icon: rocket
:link: /docs/quickstart/
:color: blue

Card content here.
:::
```

Boolean options can omit the value:

```markdown
:::{tab-item} Python
:selected:

Python code here.
:::
```

## Categories

:::{child-cards}
:columns: 2
:include: pages
:fields: title, description
:::

## Common Options

Many directives support these common options:

- `:class:` - Custom CSS class
- `:id:` - Element ID
- `:title:` - Title text (alternative to title in directive name)

## Examples

### Basic Admonition

```markdown
:::{note}
This is a note with **markdown** support.
:::
```

### Card Grid

```markdown
:::{cards}
:columns: 3

:::{card} Card 1
:icon: book
:link: docs/getting-started

Content here
:::

:::{card} Card 2
Content here
:::

:::{/cards}
```

### Tabs

```markdown
:::{tab-set}

:::{tab-item} Python
```python
print("Hello")
```
:::

:::{tab-item} JavaScript
```javascript
console.log("Hello");
```
:::

:::{/tab-set}
```

## Glossary Directive

The `{glossary}` directive renders terms from a centralized glossary data file (`data/glossary.yaml`) as a styled definition list. Filter terms by tags to show relevant definitions for each page.

### Syntax

```markdown
:::{glossary}
:tags: directives, core
:sorted: true
:collapsed: true
:limit: 3
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:tags:` | (required) | Comma-separated tags to filter terms (OR logic) |
| `:sorted:` | `false` | Sort terms alphabetically |
| `:show-tags:` | `false` | Display tag badges under each term |
| `:collapsed:` | `false` | Wrap in collapsible `<details>` element |
| `:limit:` | (all) | Show only first N terms; remaining in expandable section |
| `:source:` | `data/glossary.yaml` | Custom glossary file path |

### Examples

:::{example-label} Basic Usage
:::

Show terms tagged with "directives":

```markdown
:::{glossary}
:tags: directives
:::
```

:::{example-label} Progressive Disclosure
:::

Show first 3 terms, rest expandable:

```markdown
:::{glossary}
:tags: directives, core
:limit: 3
:::
```

:::{example-label} Fully Collapsed
:::

Entire glossary in collapsible section:

```markdown
:::{glossary}
:tags: formatting
:collapsed: true
:::
```

:::{example-label} Both Options
:::

Collapsed, with limited terms when expanded:

```markdown
:::{glossary}
:tags: layout
:collapsed: true
:limit: 2
:::
```

### Glossary Data Format

Terms are defined in `data/glossary.yaml`:

```yaml
terms:
  - term: Directive
    definition: Extended markdown syntax using `{name}` that creates rich components.
    tags: [directives, core]

  - term: Admonition
    definition: A styled callout box for **important** information.
    tags: [directives, admonitions]
```

**Note**: Definitions support inline markdown: backticks for `code`, `**bold**`, and `*italic*`.

## Next Steps

- Browse directive categories above for detailed syntax
- See [[docs/content/reuse|Content Reuse]] for include/literalinclude strategies
- Check [[docs/get-started/quickstart-writer|Writer Quickstart]] for markdown basics
