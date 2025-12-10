---
title: Icon Reference
description: SVG icon library with theme-aware styling
weight: 25
icon: star
tags:
- reference
- icons
- svg
keywords:
- icons
- svg
- phosphor
- inline icons
- theme-aware
---
# Icon Reference

Theme-aware SVG icons powered by [Phosphor Icons](https://phosphoricons.com/), a comprehensive open-source icon library with 6,000+ icons. All icons adapt to light/dark mode using `currentColor`.

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

## Quick Preview

All icons at 32px for easy viewing:

**Navigation**: {icon}`menu:32` {icon}`search:32` {icon}`close:32` {icon}`chevron-up:32` {icon}`chevron-down:32` {icon}`chevron-left:32` {icon}`chevron-right:32` {icon}`link:32` {icon}`external:32`

**Status**: {icon}`check:32` {icon}`info:32` {icon}`warning:32` {icon}`error:32`

**Files**: {icon}`file:32` {icon}`folder:32` {icon}`code:32` {icon}`notepad:32` {icon}`copy:32` {icon}`edit:32`

**Actions**: {icon}`download:32` {icon}`upload:32` {icon}`trash:32` {icon}`star:32` {icon}`heart:32` {icon}`bookmark:32` {icon}`tag:32`

**Time & Location**: {icon}`clock:32` {icon}`calendar:32` {icon}`pin:32`

**Theme**: {icon}`settings:32` {icon}`palette:32` {icon}`sun:32` {icon}`moon:32`

**Bengal**: {icon}`bengal-rosette:32` {icon}`terminal:32` {icon}`docs:32`

**Mid-Century**: {icon}`atomic:32` {icon}`starburst:32` {icon}`boomerang:32`

---

## Custom Icons

Place SVG files in `themes/your-theme/assets/icons/`:

```
themes/my-theme/assets/icons/
├── my-icon.svg
└── another.svg
```

Then use with the same syntax:

```markdown
{icon}`my-icon:24`
```

### Icon Source

Bengal uses [Phosphor Icons](https://phosphoricons.com/) - a high-quality, open-source icon library with:

- **6,000+ icons** covering all common use cases
- **Multiple weights**: Thin, Light, Regular, Bold, Fill, Duotone
- **MIT License** - free for commercial use
- **Consistent design** - all icons follow the same design principles
- **Theme-aware** - uses `currentColor` for automatic light/dark mode support

### SVG Format

Phosphor icons use:
- `viewBox="0 0 256 256"` (scales automatically via width/height)
- `fill="currentColor"` on paths (theme-aware)
- `fill="none"` on root SVG element
- Clean, minimal design optimized for UI

Icons are automatically sized via the `:size:` parameter and inherit colors from the current theme.

## Related

- [Formatting Directives](/docs/reference/directives/formatting/) — Buttons with icons
- [Assets](/docs/theming/assets/) — Asset pipeline for custom icons
- [Content Authoring](/docs/content/authoring/) — Using icons in content
