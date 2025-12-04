---
title: Admonitions
description: Reference for admonition directives (note, warning, tip, danger, etc.)
weight: 11
tags: [reference, directives, admonitions, callouts]
keywords: [admonitions, note, warning, tip, danger, callouts]
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
| `{caution}` | Cautions | `admonition warning` |
| `{danger}` | Critical warnings | `admonition danger` |
| `{error}` | Error messages | `admonition error` |
| `{info}` | Informational content | `admonition info` |
| `{example}` | Examples | `admonition example` |
| `{success}` | Success messages | `admonition success` |

## Examples

### Basic Note

```markdown
:::{note}
This is a note with **markdown** support.
:::
```

### With Title

```markdown
:::{warning} Important
This feature requires admin access.
:::
```

### Without Title (Uses Type Name)

```markdown
:::{tip}
Use this pattern for better performance.
:::
```

Renders as "Tip" (capitalized type name).

### Nested Content

Admonitions support full markdown including nested directives:

```markdown
::::{note}
Here's a tip:

:::{tip}
Nested admonitions work!
:::
::::
```

### All Types

````markdown
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
Cautionary note
:::
````

## Options

Admonitions support standard directive options:

- `:class:` - Additional CSS classes
- `:id:` - Element ID

````markdown
:::{note} Custom Note
:class: custom-class
:id: my-note

Content here
:::
````

## Rendering

Admonitions render as:

```html
<div class="admonition note">
  <p class="admonition-title">Note</p>
  <div>Content here</div>
</div>
```

## Best Practices

1. **Use appropriate types**: Choose the type that best matches the content's importance
2. **Keep titles concise**: Short, descriptive titles work best
3. **Use sparingly**: Too many admonitions can overwhelm readers
4. **Nest carefully**: Nested admonitions work but can be visually busy
