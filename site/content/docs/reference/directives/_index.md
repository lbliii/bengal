---
title: Directives Reference
description: Complete reference for all available markdown directives in Bengal
weight: 10
tags: [reference, directives, markdown, syntax]
keywords: [directives, markdown, syntax, reference, admonitions, tabs, cards]
---

# Directives Reference

Bengal extends Markdown with powerful directives using `:::{name}` or ` ```{name} ` syntax. Directives provide rich components like callouts, tabs, cards, and more.

## Key Terms

:::{glossary}
:tags: directives, core
:::

## Quick Reference

| Directive | Syntax | Purpose | Category |
|-----------|--------|---------|----------|
| `{note}` | ` ```{note} ` | Information callout | Admonitions |
| `{warning}` | ` ```{warning} ` | Warning callout | Admonitions |
| `{tip}` | ` ```{tip} ` | Tip callout | Admonitions |
| `{danger}` | ` ```{danger} ` | Danger callout | Admonitions |
| `{cards}` | ` :::{cards} ` | Card grid layout | Layout |
| `{card}` | ` :::{card} ` | Individual card | Layout |
| `{tab-set}` | ` :::{tab-set} ` | Tab container | Layout |
| `{tab-item}` | ` :::{tab-item} ` | Individual tab | Layout |
| `{dropdown}` | ` ```{dropdown} ` | Collapsible section | Layout |
| `{code-tabs}` | ` ```{code-tabs} ` | Multi-language code | Interactive |
| `{badge}` | ` ```{badge} ` | Styled badge | Formatting |
| `{button}` | ` :::{button} ` | Link button | Formatting |
| `{steps}` | ` :::{steps} ` | Step-by-step guide | Formatting |
| `{step}` | ` :::{step} ` | Individual step | Formatting |
| `{checklist}` | ` ```{checklist} ` | Styled checklist | Formatting |
| `{rubric}` | ` ```{rubric} ` | Pseudo-heading | Formatting |
| `{include}` | ` ```{include} ` | Include markdown file | Content Reuse |
| `{literalinclude}` | ` ```{literalinclude} ` | Include code file | Content Reuse |
| `{list-table}` | ` :::{list-table} ` | Table from lists | Formatting |
| `{data-table}` | ` :::{data-table} ` | Interactive data table | Interactive |
| `{child-cards}` | ` :::{child-cards} ` | Auto-generate cards from children | Navigation |
| `{breadcrumbs}` | ` :::{breadcrumbs} ` | Breadcrumb navigation | Navigation |
| `{siblings}` | ` :::{siblings} ` | Sibling page list | Navigation |
| `{prev-next}` | ` :::{prev-next} ` | Prev/next links | Navigation |
| `{related}` | ` :::{related} ` | Related pages by tags | Navigation |

## Directive Syntax

Bengal supports two directive syntax styles:

### Fenced Syntax (3 backticks)

```markdown
:::{directive-name} Optional Title
:option: value

Content here
:::
```

**Used for**: Admonitions, dropdowns, badges, checklists, code-tabs, include, literalinclude, rubric

### MyST Syntax (3 colons)

```markdown
:::{directive-name} Optional Title
:option: value

Content here
:::
```

**Used for**: Cards, tabs, buttons, steps, list-table

### Nesting Rules

When nesting directives, increase the fence level. **Container directives** (like `{steps}`, `{cards}`, `{grid}`, `{tab-set}`) require **4 fences minimum** (`::::`). Use higher fence counts (5, 6, etc.) for deeper nesting.

**Basic Nesting** (container with items):

```markdown
::::{cards}
:columns: 3

:::{card} Card Title
Card content here
:::
::::
```

**Deep Nesting** (admonitions within steps, tabs within cards, etc.):

```markdown
:::::{steps}

::::{step} First Step
:::{tip}
Remember to check the logs!
:::
::::

::::{step} Second Step
More content
::::
:::::
```

**Rule**:
- Container directives: **4 fences minimum** (`::::`)
- Nested items: 3 fences (`:::`)
- Each additional nesting level: increment fence count by 1
- Example: Container (4) → Step (4) → Admonition (3 colons) = Container needs 5 fences

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
::::{cards}
:columns: 3

:::{card} Card 1
:icon: book
:link: /docs/

Content here
:::

:::{card} Card 2
Content here
:::
::::
```

### Tabs

```markdown
::::{tab-set}

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
::::
```

## Next Steps

- Browse directive categories above for detailed syntax
- See [Content Reuse Guide](/docs/guides/content-reuse/) for include/literalinclude strategies
- Check [Writer Quickstart](/docs/getting-started/writer-quickstart/) for markdown basics
