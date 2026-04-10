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

## Default Theme RTL Support

The default theme is fully RTL-ready out of the box:

- **CSS logical properties** — All directional styles use `margin-inline-start`, `padding-inline-end`, `text-align: start`, etc. instead of physical `left`/`right` properties. Layout mirrors automatically with `dir="rtl"`.
- **Bidirectional text isolation** — Navigation titles in the docs sidebar, breadcrumbs, prev/next links, and menus are wrapped in `<bdi>` tags to prevent mixed-direction text from corrupting visual order.
- **Breadcrumb separator** — Flips from `›` to `‹` in RTL contexts.
- **Navigation arrows** — Prev/next arrows flip direction via `scaleX(-1)` in RTL.

No custom CSS is needed for RTL when using the default theme.

## CSS Authoring Guidelines

If you're building a custom theme or overriding styles, follow these conventions.

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
| `float: left` | `float: inline-start` |
| `float: right` | `float: inline-end` |

### RTL-Specific Overrides

When logical properties aren't enough, use `[dir="rtl"]` selectors:

```css
/* Flip navigation arrows in RTL */
[dir="rtl"] .nav-arrow {
    display: inline-block;
    transform: scaleX(-1);
}

/* Change breadcrumb separator in RTL */
[dir="rtl"] .breadcrumbs li:not(:last-child)::after {
    content: '‹';  /* Mirrors › */
}
```

### Bidirectional Text Isolation

For mixed LTR/RTL content (e.g. English product names in Arabic navigation), wrap in `<bdi>`:

```html
{# In navigation templates #}
<a href="{{ item.href }}"><bdi>{{ item.title }}</bdi></a>

{# In body content #}
<p>المنتج <bdi>SuperWidget</bdi> متاح الآن.</p>
```

`<bdi>` isolates the embedded text so it renders in its natural direction without affecting surrounding text. The default theme already wraps navigation titles in `<bdi>` — add it to any custom templates that display user-authored titles in navigation contexts.

## Testing RTL

1. Add Arabic or Hebrew to your `languages` config
2. Create `content/ar/` (or `content/he/`) with translated content
3. Build and open `/ar/` (or `/he/`)
4. Verify in the page source:
   - `<html lang="ar" dir="rtl">` is present
   - Layout mirrors correctly (sidebar on right, text right-aligned)
   - Navigation arrows point in the correct direction
   - Breadcrumb separators use `‹` instead of `›`
5. Check mixed-direction content: English words in Arabic paragraphs should display correctly
