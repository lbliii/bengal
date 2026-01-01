---
title: Admonitions
description: Reference for admonition directives (note, warning, tip, danger, etc.)
weight: 11
tags:
- reference
- directives
- admonitions
- callouts
keywords:
- admonitions
- note
- warning
- tip
- danger
- callouts
---

# Admonition Directives

Admonitions create styled callout boxes for notes, warnings, tips, and other important information.

## Key Terms

:::{glossary}
:tags: admonitions
:::

## Syntax

```markdown
:::{admonition-type} Optional Title
Content with **full markdown** support.
:::
```

## Available Types

| Type | Purpose | CSS Class |
|------|---------|-----------|
| `{note}` | General information | `admonition note` |
| `{tip}` | Helpful tips | `admonition tip` |
| `{warning}` | Warnings | `admonition warning` |
| `{caution}` | Cautions (renders as warning) | `admonition warning` |
| `{danger}` | Critical warnings | `admonition danger` |
| `{error}` | Error messages | `admonition error` |
| `{info}` | Informational content | `admonition info` |
| `{example}` | Examples | `admonition example` |
| `{success}` | Success messages | `admonition success` |
| `{seealso}` | Cross-references and related links | `admonition seealso` |

## Examples

::::{tab-set}

:::{tab-item} Basic Note
```markdown
:::{note}
This is a note with **markdown** support.
:::
```
:::

:::{tab-item} With Title
```markdown
:::{warning} Important
This feature requires admin access.
:::
```
:::

:::{tab-item} Without Title
```markdown
:::{tip}
Use this pattern for better performance.
:::
```
Renders as "Tip" (capitalized type name).
:::

:::{tab-item} Nested Content
Admonitions support full markdown including nested directives. Use named closers for clarity:

`````markdown
:::{note}
Here's a tip:

:::{tip}
Nested admonitions work!
:::
:::{/note}
`````
:::

::::{/tab-set}

### All Types

`````markdown
:::{note} Note
General information
:::

:::{tip} Tip
Helpful suggestion
:::

:::{warning} Warning
Something to be careful about
:::

:::{danger} Danger
Critical warning
:::

:::{error} Error
Error message
:::

:::{info} Info
Informational content
:::

:::{example} Example
Example usage
:::

:::{success} Success
Success message
:::

:::{caution} Caution
Cautionary note (renders as warning)
:::

:::{seealso} See Also
- [Related Topic](#)
- [Another Resource](#)
:::
`````

## Options

Admonitions support the `:class:` option for custom styling:

| Option | Description |
|--------|-------------|
| `:class:` | Additional CSS classes to apply |

`````markdown
:::{note} Custom Note
:class: highlight bordered

Content here
:::
`````

## Rendering

Admonitions render with icons and structured markup:

```html
<div class="admonition note">
  <p class="admonition-title">
    <span class="admonition-icon-wrapper"><!-- SVG icon --></span>
    <span class="admonition-title-text">Note</span>
  </p>
  <p>Content here</p>
</div>
```

CSS classes follow the pattern `admonition {type}`. The `caution` type maps to the `warning` CSS class.

With custom classes via `:class:`:

```html
<div class="admonition note highlight bordered">
  <!-- ... -->
</div>
```

## Best Practices

1. **Match type to severity**: Use `note`/`tip` for helpful info, `warning`/`caution` for potential issues, `danger`/`error` for critical problems
2. **Keep titles concise**: Short, descriptive titles (2-4 words) work best
3. **Use sparingly**: More than 2-3 admonitions per page can overwhelm readers
4. **Nest carefully**: Nested admonitions work but increase visual complexity
5. **Prefer `seealso` for links**: Group related links in a dedicated `seealso` block rather than inline
