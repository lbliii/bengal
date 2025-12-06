---
title: Icon Reference
description: Bengal SVG icon library with theme-aware styling
date: 2025-12-06
tags:
  - reference
  - icons
weight: 20
---

# Icon Reference

Theme-aware SVG icons that adapt to light/dark mode.

## Syntax

| Syntax | Use | Example |
|--------|-----|---------|
| `:::{icon} name` | Block | `:::{icon} terminal :size: 48 :::` |
| `{icon}`name`` | Inline | `{icon}`terminal`` |
| `{icon}`name:size`` | Inline + size | `{icon}`terminal:16`` |
| `{icon}`name:size:class`` | Inline + size + class | `{icon}`terminal:24:icon-primary`` |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `:size:` | 24 | Icon size in pixels |
| `:class:` | — | CSS classes (`icon-primary`, `icon-success`, etc.) |
| `:aria-label:` | — | Accessibility label |

## Color Classes

| Class | Preview |
|-------|---------|
| `icon-primary` | {icon}`star:20:icon-primary` |
| `icon-success` | {icon}`check:20:icon-success` |
| `icon-warning` | {icon}`warning:20:icon-warning` |
| `icon-danger` | {icon}`error:20:icon-danger` |
| `icon-muted` | {icon}`info:20:icon-muted` |

---

## Icon Gallery

### Bengal

| Icon | Name | Description |
|------|------|-------------|
| {icon}`bengal-rosette:24` | `bengal-rosette` | Bengal signature rosette |
| {icon}`terminal:24` | `terminal` | CLI/commands |
| {icon}`docs:24` | `docs` | Documentation |

### Navigation

| Icon | Name | Description |
|------|------|-------------|
| {icon}`search:24` | `search` | Search |
| {icon}`menu:24` | `menu` | Menu toggle |
| {icon}`close:24` | `close` | Close/dismiss |
| {icon}`chevron-right:24` | `chevron-right` | Navigate forward |
| {icon}`chevron-left:24` | `chevron-left` | Navigate back |
| {icon}`chevron-down:24` | `chevron-down` | Expand |
| {icon}`chevron-up:24` | `chevron-up` | Collapse |
| {icon}`link:24` | `link` | Internal link |
| {icon}`external:24` | `external` | External link |

### Content

| Icon | Name | Description |
|------|------|-------------|
| {icon}`file:24` | `file` | File/document |
| {icon}`folder:24` | `folder` | Folder/directory |
| {icon}`code:24` | `code` | Code block |
| {icon}`notepad:24` | `notepad` | Notes/text |
| {icon}`copy:24` | `copy` | Copy |
| {icon}`edit:24` | `edit` | Edit |
| {icon}`bookmark:24` | `bookmark` | Bookmark |
| {icon}`tag:24` | `tag` | Tag/label |

### Status

| Icon | Name | Description |
|------|------|-------------|
| {icon}`check:24` | `check` | Success |
| {icon}`info:24` | `info` | Information |
| {icon}`warning:24` | `warning` | Warning |
| {icon}`error:24` | `error` | Error |

### Actions

| Icon | Name | Description |
|------|------|-------------|
| {icon}`download:24` | `download` | Download |
| {icon}`upload:24` | `upload` | Upload |
| {icon}`trash:24` | `trash` | Delete |
| {icon}`star:24` | `star` | Favorite |
| {icon}`heart:24` | `heart` | Like |

### Time & Location

| Icon | Name | Description |
|------|------|-------------|
| {icon}`clock:24` | `clock` | Time |
| {icon}`calendar:24` | `calendar` | Date |
| {icon}`pin:24` | `pin` | Location |

### Theme & Settings

| Icon | Name | Description |
|------|------|-------------|
| {icon}`settings:24` | `settings` | Settings |
| {icon}`palette:24` | `palette` | Theme |
| {icon}`sun:24` | `sun` | Light mode |
| {icon}`moon:24` | `moon` | Dark mode |

### Mid-Century Modern

| Icon | Name | Description |
|------|------|-------------|
| {icon}`atomic:24` | `atomic` | Atomic age symbol |
| {icon}`starburst:24` | `starburst` | Sputnik starburst |
| {icon}`boomerang:24` | `boomerang` | Retro boomerang |

---

## Custom Icons

Place SVG files in `themes/your-theme/assets/icons/`:

```
themes/my-theme/assets/icons/
            ├── my-icon.svg
└── another.svg
```

### SVG Requirements

```xml
<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
  <title>Icon Name</title>
  <!-- Use currentColor for theme awareness -->
  <path stroke="currentColor" stroke-width="1.5" .../>
  <!-- Depth layer at 20-35% opacity -->
  <path fill="currentColor" opacity="0.3" .../>
</svg>
```

- 24×24 viewBox
- Use `currentColor` for stroke/fill
- 1.5px strokes for glass aesthetic
- Optional depth shadows at 20-35% opacity
