---
title: RTL Layout Support
description: CSS authoring for Arabic, Hebrew, and bidirectional sites
weight: 20
---
# RTL Layout Support

Bengal automatically sets `dir="rtl"` on the `<html>` element for right-to-left locales (Arabic, Hebrew, Persian, Urdu, etc.). This enables correct text direction and layout mirroring.

## Automatic RTL Detection

These locales get `dir="rtl"` by default:

- Arabic (`ar`)
- Hebrew (`he`)
- Persian (`fa`)
- Urdu (`ur`)
- Yiddish (`yi`)
- Divehi (`dv`)
- Kurdish (`ku`)
- Pashto (`ps`)
- Sindhi (`sd`)

## Config Override

Override in `bengal.toml` for custom or lesser-known RTL locales:

```toml
[i18n]
languages = [
    { code = "en", name = "English" },
    { code = "ar", name = "العربية", rtl = true },
    { code = "custom-rtl", name = "Custom", rtl = true },
]
```

Set `rtl = false` to force LTR for a normally RTL locale.

## Template Variable

The `direction()` function returns `"rtl"` or `"ltr"` for the current page:

```html
<html lang="{{ current_lang() }}" dir="{{ direction() }}">
```

The default theme uses this automatically.

## CSS Authoring Guidelines

### Use Logical Properties

Prefer logical properties so layout flips automatically with `dir`:

| Physical | Logical |
|----------|---------|
| `margin-left` | `margin-inline-start` |
| `margin-right` | `margin-inline-end` |
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `left` | `inset-inline-start` |
| `right` | `inset-inline-end` |
| `text-align: left` | `text-align: start` |
| `text-align: right` | `text-align: end` |
| `border-left` | `border-inline-start` |
| `border-right` | `border-inline-end` |

### RTL-Specific Overrides

When logical properties aren't enough, use `[dir="rtl"]` selectors:

```css
/* Flip navigation in RTL */
[dir="rtl"] .nav-menu {
    flex-direction: row-reverse;
}

/* Adjust icon placement */
[dir="rtl"] .icon-before {
    margin-inline-start: 0.5rem;
    margin-inline-end: 0;
}
```

The default theme's language switcher already includes RTL-aware styles.

### Bidirectional Text

For mixed LTR/RTL content (e.g. English product names in Arabic text), wrap in `<bdi>`:

```html
<p>المنتج <bdi>SuperWidget</bdi> متاح الآن.</p>
```

`<bdi>` isolates the embedded text so it renders in its natural direction.

## Testing RTL

1. Add Arabic or Hebrew to your `languages` config
2. Create `content/ar/` (or `content/he/`) with translated content
3. Build and open `/ar/` (or `/he/`)
4. Verify `dir="rtl"` in the page source and that layout mirrors correctly
