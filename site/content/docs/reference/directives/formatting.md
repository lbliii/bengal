---
title: Formatting Directives
nav_title: Formatting
description: Reference for formatting directives (badge, icon, button, steps, checklist,
  rubric, list-table)
weight: 13
tags:
- reference
- directives
- formatting
- badge
- icon
- button
- steps
keywords:
- badge
- icon
- button
- steps
- checklist
- rubric
- list-table
- formatting
---

# Formatting Directives

Formatting directives provide styled components for badges, buttons, step-by-step guides, and more.

## Key Terms

:::{glossary}
:tags: formatting
:::

## Badge

Create styled badges for labels, tags, or status indicators.

**Aliases**: `{bdg}`

**Syntax**:

````markdown
:::{badge} Text
:class: badge-class
:::
````

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | `badge badge-secondary` | CSS classes for the badge |

Common badge classes: `badge-primary`, `badge-secondary`, `badge-success`, `badge-danger`, `badge-warning`, `badge-info`, `badge-cli-command`, `api-badge`

### Examples

**Basic Badge**:

````markdown
:::{badge} New
:::
````

**Custom Class**:

````markdown
:::{badge} Deprecated
:class: badge-danger
:::
````

**CLI Command Badge**:

````markdown
:::{badge} bengal build
:class: badge-cli-command
:::
````

## Icon

Embed inline SVG icons from Bengal's built-in icon library.

**Aliases**: `icon`, `svg-icon`

**Syntax**:

```markdown
:::{icon} terminal
:::

:::{icon} docs
:size: 16
:class: text-muted
:::
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:size:` | `24` | Icon size in pixels |
| `:class:` | — | Additional CSS classes |
| `:aria-label:` | — | Accessibility label (uses icon name if omitted) |

Icons are loaded from Bengal's theme assets. If an icon is not found, a placeholder is rendered.

### Examples

**Basic Icon**:

```markdown
:::{icon} home
:::
```

**Sized Icon**:

```markdown
:::{icon} arrow-right
:size: 16
:::
```

**With Accessibility Label**:

```markdown
:::{icon} external-link
:aria-label: Opens in new window
:::
```

:::{tip}
Use `bengal icons list` to see all available icons in your theme.
:::

## Button

Create styled link buttons for calls-to-action.

**Syntax**:

```markdown
:::{button} /path/to/page/
:color: primary
:style: pill
:size: large
:icon: rocket
:target: _blank

Button Text
:::
```

**Options**:

- `:color:` - Color: `primary` (default), `secondary`, `success`, `danger`, `warning`, `info`, `light`, `dark`
- `:style:` - Style: `default` (rounded), `pill` (fully rounded), `outline`
- `:size:` - Size: `small`, `medium` (default), `large`
- `:icon:` - Icon name (same as cards)
- `:target:` - Link target (e.g., `_blank` for external links)

### Examples

**Basic Button**:

```markdown
:::{button} /docs/
Get Started
:::
```

**Primary CTA**:

```markdown
:::{button} /signup/
:color: primary
:style: pill
:size: large

Sign Up Free
:::
```

**External Link**:

```markdown
:::{button} https://github.com/yourproject
:color: secondary
:target: _blank

View on GitHub
:::
```

## Steps

Create visual step-by-step guides using **named closers** for clean, readable syntax.

### Steps Container (`{steps}`)

Container for multiple steps. Use `:::{/steps}` to close.

**Syntax**:

```markdown
:::{steps}
:class: custom-class
:style: compact
:start: 1

:::{step} Step Title
Step content with **markdown** support.
:::{/step}

:::{step} Next Step
More content
:::{/step}

:::{/steps}
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | — | Custom CSS class for the container |
| `:style:` | `default` | Visual style: `default`, `compact` |
| `:start:` | `1` | Start numbering from this value |

### Individual Step (`{step}`)

Single step within a steps container. Use `:::{/step}` to close.

**Syntax**:

```markdown
:::{step} Step Title
:class: custom-class
:description: Brief context before diving into the step content.
:duration: 5 min
:optional:

Step content with **markdown** and nested directives.
:::{/step}
```

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| `:class:` | — | Custom CSS class for the step |
| `:description:` | — | Lead-in text rendered before main content |
| `:optional:` | `false` | Mark step as optional/skippable |
| `:duration:` | — | Estimated time (e.g., "5 min", "1 hour") |

### Examples

**Basic Steps**:

````markdown
:::{steps}

:::{step} Install Dependencies
```bash
pip install bengal
```
:::{/step}

:::{step} Create Site
```bash
bengal new mysite
```
:::{/step}

:::{step} Build Site
```bash
bengal build
```
:::{/step}

:::{/steps}
````

**Steps with Nested Admonitions**:

Named closers eliminate fence-counting for complex nesting:

````markdown
:::{steps}

:::{step} First Step
:::{tip}
Remember to check the logs!
:::
:::{/step}

:::{step} Second Step
More content
:::{/step}

:::{/steps}
````

**Note**: Named closers (`:::{/name}`) explicitly close directives, making deeply nested content readable without counting colons.

## Checklist

Create styled checklist containers for bullet lists and task lists with optional progress tracking.

**Syntax**:

````markdown
:::{checklist} Optional Title
:style: numbered
:show-progress:
:compact:
- Item one
- Item two
- [x] Completed item
- [ ] Unchecked item
:::{/checklist}
````

**Options**:

| Option | Default | Description |
|--------|---------|-------------|
| Title | — | Optional title shown above the list |
| `:style:` | `default` | Visual style: `default`, `numbered`, `minimal` |
| `:show-progress:` | `false` | Display completion percentage for task lists |
| `:compact:` | `false` | Tighter spacing between items |
| `:class:` | — | Additional CSS classes |

### Examples

**Basic Checklist**:

````markdown
:::{checklist} Prerequisites
- Python 3.10+
- Git installed
- Text editor
:::{/checklist}
````

**Task List with Progress**:

````markdown
:::{checklist} Setup Tasks
:show-progress:
- [x] Install dependencies
- [x] Configure site
- [ ] Deploy to production
:::{/checklist}
````

**Numbered Checklist**:

````markdown
:::{checklist} Getting Started Steps
:style: numbered
- Create a new project
- Install dependencies
- Configure settings
:::{/checklist}
````

## Rubric

Create pseudo-headings that look like headings but don't appear in the table of contents. Perfect for API documentation labels.

**Syntax**:

````markdown
:::{rubric} Label Text
:class: custom-class
:::
````

**Options**:

- `:class:` - Custom CSS class

**Note**: Rubrics don't contain content - they're label-only directives. Content after the rubric is separate markdown.

### Examples

**API Documentation**:

````markdown
:::{rubric} Parameters
:class: rubric-parameters
:::

- `param1` (str): First parameter
- `param2` (int): Second parameter

:::{rubric} Returns
:class: rubric-returns
:::

Returns a dictionary with results.
````

## List Table

Create tables from nested lists (avoids pipe character issues in type annotations).

**Syntax**:

````markdown
:::{list-table}
:header-rows: 1
:widths: 20 30 50
:class: custom-class

* - Header 1
  - Header 2
  - Header 3
* - Row 1, Col 1
  - Row 1, Col 2
  - Row 1, Col 3
* - Row 2, Col 1
  - Row 2, Col 2
  - Row 2, Col 3
:::
````

**Options**:

- `:header-rows:` - Number of header rows (default: 0)
- `:widths:` - Space-separated column widths (percentages)
- `:class:` - CSS class

### Examples

**Basic Table**:

````markdown
:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description
* - `name`
  - `str`
  - User name
* - `age`
  - `int`
  - User age
:::
````

**With Column Widths**:

```markdown
:::{list-table}
:header-rows: 1
:widths: 20 30 50

* - Column 1
  - Column 2
  - Column 3
* - Data 1
  - Data 2
  - Data 3
:::
```

## Best Practices

1. **Badges**: Use for labels, tags, or status indicators
2. **Buttons**: Use for primary calls-to-action
3. **Steps**: Use for sequential instructions or tutorials
4. **Checklists**: Use for prerequisites, requirements, or task lists
5. **Rubrics**: Use for API documentation section labels
6. **List Tables**: Use when pipe characters conflict with code syntax

## Related

- [Icon Reference](/docs/reference/icons/) - SVG icons for content and templates
- [Layout Directives](/docs/reference/directives/layout/) - Cards, tabs, dropdowns
- [Admonitions](/docs/reference/directives/admonitions/) - Callout boxes
