---
title: Bengal Icon System
description: Custom SVG icons with theme-aware styling and the icon directive
date: 2025-12-06
tags:
  - experimental
  - icons
  - theming
weight: 20
---

# Bengal Icon System

Bengal includes a custom icon system with theme-aware SVG icons that adapt to light/dark mode and palette colors.

## Quick Start

Use the `:::{icon}` directive to inline SVG icons:

```markdown
:::{icon} terminal
:::
```

**Result:**

:::{icon} terminal
:::

## Available Icons

### Bengal Rosette

The signature Bengal cat rosette pattern—inspired by the spotted coat of Bengal cats.

:::{icon} bengal-rosette
:size: 48
:class: icon-primary
:::

**Use cases**: Brand signature, decorative separators, loading states, section headers.

### Documentation

Stacked pages with a bookmark tab for that tactile feel.

:::{icon} docs
:size: 48
:class: icon-primary
:::

**Use cases**: Documentation links, tutorials, reference sections.

### Terminal

CLI window with title bar dots and command prompt.

:::{icon} terminal
:size: 48
:class: icon-primary
:::

**Use cases**: CLI documentation, command references, terminal output.

## Icon Sizes

Use the `:size:` option to control icon size (in pixels):

| Size | Example | Code |
|------|---------|------|
| 16px | :::{icon} terminal
:size: 16
::: | `:size: 16` |
| 24px (default) | :::{icon} terminal
:size: 24
::: | `:size: 24` |
| 32px | :::{icon} terminal
:size: 32
::: | `:size: 32` |
| 48px | :::{icon} terminal
:size: 48
::: | `:size: 48` |

```markdown
:::{icon} terminal
:size: 32
:::
```

## Color Variants

Icons inherit `currentColor` by default, so they adapt to their container's text color. Add CSS classes for color variants:

| Variant | Example | Class |
|---------|---------|-------|
| Primary | :::{icon} bengal-rosette
:size: 24
:class: icon-primary
::: | `icon-primary` |
| Success | :::{icon} bengal-rosette
:size: 24
:class: icon-success
::: | `icon-success` |
| Warning | :::{icon} bengal-rosette
:size: 24
:class: icon-warning
::: | `icon-warning` |
| Danger | :::{icon} bengal-rosette
:size: 24
:class: icon-danger
::: | `icon-danger` |
| Muted | :::{icon} bengal-rosette
:size: 24
:class: icon-muted
::: | `icon-muted` |

```markdown
:::{icon} bengal-rosette
:class: icon-primary
:::
```

## Directive Syntax

Full directive syntax:

```markdown
:::{icon} icon-name
:size: 24
:class: my-custom-class
:aria-label: Description for screen readers
:::
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `:size:` | `24` | Icon size in pixels |
| `:class:` | (none) | Additional CSS classes |
| `:aria-label:` | (none) | Accessibility label (adds `role="img"`) |

## All Icons Gallery

Here are all available icons at 48px:

**Bengal Rosette:**

:::{icon} bengal-rosette
:size: 48
:::

**Documentation:**

:::{icon} docs
:size: 48
:::

**Terminal:**

:::{icon} terminal
:size: 48
:::

## Design Principles

Bengal icons follow these design principles:

1. **Theme-aware**: Use `currentColor` for automatic light/dark adaptation
2. **Stroke-based**: 2px stroke width for consistency with UI
3. **Organic feel**: Rounded stroke caps/joins for warmth
4. **Accessible**: Support for `aria-label` and high contrast
5. **Tactile**: Match Bengal's neumorphic aesthetic

## Adding Custom Icons

Place SVG files in your theme's `assets/icons/` directory:

```
themes/
└── my-theme/
    └── assets/
        └── icons/
            ├── my-icon.svg
            └── another-icon.svg
```

Then use them with the directive:

```markdown
:::{icon} my-icon
:::
```

### SVG Requirements

For best results, icons should:

- Use 24×24 viewBox
- Use `stroke="currentColor"` for lines
- Use `fill="currentColor"` for filled elements
- Include `stroke-width="2"` for consistency
- Use `stroke-linecap="round"` and `stroke-linejoin="round"`

Example SVG structure:

```xml
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <title>Icon Name</title>
  <path d="..." stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

:::{tip}
Toggle between light and dark mode using the theme switcher in the header to see how icons adapt to different themes!
:::
