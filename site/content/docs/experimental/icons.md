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

## Two Syntaxes

Bengal provides two ways to use icons:

| Syntax | Use Case | Example |
|--------|----------|---------|
| Block directive | Standalone icons | `:::{icon} terminal` |
| Inline syntax | Tables, paragraphs | `{icon}`terminal`` |

---

## Block Directive (Standalone)

Use the `:::{icon}` directive for standalone icons:

```markdown
:::{icon} terminal
:size: 48
:class: icon-primary
:::
```

**Result:**

:::{icon} terminal
:size: 48
:class: icon-primary
:::

---

## Inline Syntax (Tables & Paragraphs)

Use `{icon}`name`` for inline icons in tables and text:

```markdown
| Icon | Name | Description |
|------|------|-------------|
| {icon}`terminal` | Terminal | CLI icon |
| {icon}`docs:20` | Docs | Documentation |
```

**Result:**

| Icon | Name | Description |
|------|------|-------------|
| {icon}`terminal` | Terminal | CLI command prompt |
| {icon}`docs` | Docs | Documentation pages |
| {icon}`bengal-rosette` | Rosette | Bengal signature |

### Inline Syntax Options

The inline syntax supports size and class options with colons:

| Pattern | Description | Example |
|---------|-------------|---------|
| `{icon}`name`` | Default 24px | {icon}`terminal` |
| `{icon}`name:size`` | Custom size | {icon}`terminal:16` |
| `{icon}`name:size:class`` | Size + class | {icon}`bengal-rosette:20:icon-primary` |

---

## Available Icons

### Bengal Rosette

The signature Bengal cat rosette pattern—inspired by the spotted coat.

:::{icon} bengal-rosette
:size: 64
:class: icon-primary
:::

**Inline:** {icon}`bengal-rosette:32`

---

### Documentation

Stacked pages with a bookmark tab for that tactile feel.

:::{icon} docs
:size: 64
:class: icon-primary
:::

**Inline:** {icon}`docs:32`

---

### Terminal

CLI window with title bar dots and command prompt.

:::{icon} terminal
:size: 64
:class: icon-primary
:::

**Inline:** {icon}`terminal:32`

---

## Size Comparison

| Size | Terminal | Docs | Rosette |
|------|----------|------|---------|
| 16px | {icon}`terminal:16` | {icon}`docs:16` | {icon}`bengal-rosette:16` |
| 24px | {icon}`terminal:24` | {icon}`docs:24` | {icon}`bengal-rosette:24` |
| 32px | {icon}`terminal:32` | {icon}`docs:32` | {icon}`bengal-rosette:32` |

---

## Color Variants

Add CSS classes to colorize icons:

| Variant | Example | Inline Syntax |
|---------|---------|---------------|
| Primary | {icon}`bengal-rosette:24:icon-primary` | `{icon}`bengal-rosette:24:icon-primary`` |
| Success | {icon}`bengal-rosette:24:icon-success` | `{icon}`bengal-rosette:24:icon-success`` |
| Warning | {icon}`bengal-rosette:24:icon-warning` | `{icon}`bengal-rosette:24:icon-warning`` |
| Danger | {icon}`bengal-rosette:24:icon-danger` | `{icon}`bengal-rosette:24:icon-danger`` |
| Muted | {icon}`bengal-rosette:24:icon-muted` | `{icon}`bengal-rosette:24:icon-muted`` |

---

## Directive Options (Block Syntax)

Full directive syntax:

```markdown
:::{icon} icon-name
:size: 24
:class: my-custom-class
:aria-label: Description for screen readers
:::
```

### Available Options

- **`:size:`** (default: `24`) — Icon size in pixels
- **`:class:`** (default: none) — Additional CSS classes
- **`:aria-label:`** (default: none) — Accessibility label (adds `role="img"`)

---

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

Then use them:

```markdown
:::{icon} my-icon
:::

Or inline: {icon}`my-icon`
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

---

## Design Principles

Bengal icons follow these design principles:

1. **Theme-aware**: Use `currentColor` for automatic light/dark adaptation
2. **Stroke-based**: 2px stroke width for consistency with UI
3. **Organic feel**: Rounded stroke caps/joins for warmth
4. **Accessible**: Support for `aria-label` and high contrast
5. **Tactile**: Match Bengal's neumorphic aesthetic

:::{tip}
Toggle between light and dark mode using the theme switcher in the header to see how icons adapt to different themes!
:::
