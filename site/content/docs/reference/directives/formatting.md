---
title: Formatting Directives
description: Reference for formatting directives (badge, button, steps, checklist, rubric, list-table)
weight: 13
tags: [reference, directives, formatting, badge, button, steps]
keywords: [badge, button, steps, checklist, rubric, list-table, formatting]
---

# Formatting Directives

Formatting directives provide styled components for badges, buttons, step-by-step guides, and more.

## Key Terms

Badge
:   A small styled label for tags, status indicators, or labels. Renders as an inline element with customizable CSS classes.

Button
:   A styled link element that appears as a button. Supports colors, sizes, icons, and link targets for calls-to-action.

Steps Container
:   A container directive (`{steps}`) that groups multiple step directives together. Requires 4 fences minimum (`::::`).

Step
:   An individual step directive (`{step}`) within a steps container. Contains content for one step in a sequential guide.

Checklist
:   A styled container for bullet lists and task lists. Provides visual styling for prerequisites, requirements, or task tracking.

Rubric
:   A pseudo-heading that looks like a heading but doesn't appear in the table of contents. Perfect for API documentation section labels.

List Table
:   A table created from nested lists, avoiding pipe character conflicts in type annotations. Useful for Python type hints and complex data structures.

## Badge

Create styled badges for labels, tags, or status indicators.

**Syntax**:

````markdown
:::{badge} Text
:class: badge-class
:::
````

**Options**:

- `:class:` - CSS classes (default: `badge badge-secondary`)

**Alias**: `{bdg}` (Sphinx-Design compatibility)

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

Create visual step-by-step guides.

### Steps Container (`{steps}`)

Container for multiple steps.

**Important**: Container directives like `{steps}` require **4 fences minimum** (`::::`). Use higher fence counts (5, 6, etc.) for deeper nesting (e.g., admonitions within steps, tabs within sets).

**Syntax**:

```markdown
::::{steps}
:class: custom-class
:style: compact

:::{step} Step Title
Step content with **markdown** support.
:::

:::{step} Next Step
More content
:::
::::
```

**Options**:

- `:class:` - Custom CSS class
- `:style:` - Style: `default`, `compact`

### Individual Step (`{step}`)

Single step within a steps container.

**Syntax**:

```markdown
:::{step} Optional Title
:class: custom-class

Step content with **markdown** and nested directives.
:::
```

**Options**:

- `:class:` - Custom CSS class

### Examples

**Basic Steps**:

````markdown
::::{steps}

:::{step} Install Dependencies
```bash
pip install bengal
```
:::

:::{step} Create Site
```bash
bengal new mysite
```
:::

:::{step} Build Site
```bash
bengal build
```
:::
::::
````

**Steps with Nested Admonitions**:

For nested directives like admonitions within steps, use 5 fences for the container:

````markdown
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
````

**Note**: The container uses 5 fences (`:::::`), steps use 4 fences (`::::`), and the nested admonition uses 3 colons (`:::`). Each nesting level requires incrementing the fence count.

## Checklist

Create styled checklist containers for bullet lists and task lists.

**Syntax**:

````markdown
:::{checklist} Optional Title
- Item one
- Item two
- [x] Completed item
- [ ] Unchecked item
:::
````

**Options**:

- Title (optional) - Checklist title

### Examples

**Basic Checklist**:

````markdown
:::{checklist} Prerequisites
- Python 3.10+
- Git installed
- Text editor
:::
````

**Task List**:

````markdown
:::{checklist} Setup Tasks
- [x] Install dependencies
- [x] Configure site
- [ ] Deploy to production
:::
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

**Important**: Container directives like `{list-table}` require **4 fences minimum** (`::::`). Use higher fence counts for deeper nesting.

**Syntax**:

````markdown
::::{list-table}
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
::::
````

**Options**:

- `:header-rows:` - Number of header rows (default: 0)
- `:widths:` - Space-separated column widths (percentages)
- `:class:` - CSS class

### Examples

**Basic Table**:

````markdown
::::{list-table}
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
::::
````

**With Column Widths**:

```markdown
::::{list-table}
:header-rows: 1
:widths: 20 30 50

* - Column 1
  - Column 2
  - Column 3
* - Data 1
  - Data 2
  - Data 3
::::
```

## Best Practices

1. **Badges**: Use for labels, tags, or status indicators
2. **Buttons**: Use for primary calls-to-action
3. **Steps**: Use for sequential instructions or tutorials
4. **Checklists**: Use for prerequisites, requirements, or task lists
5. **Rubrics**: Use for API documentation section labels
6. **List Tables**: Use when pipe characters conflict with code syntax

## Related

- [Layout Directives](/docs/reference/directives/layout/) - Cards, tabs, dropdowns
- [Admonitions](/docs/reference/directives/admonitions/) - Callout boxes
