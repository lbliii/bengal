---
title: Internationalization (i18n)
description: Multi-language sites with gettext PO/MO, RTL support, and translation workflows
weight: 25
category: guide
icon: languages
card_color: green
tags:
- persona-operator
---

# Internationalization

Bengal supports multi-language sites with directory-based content, gettext PO/MO translation files, plural-aware translations via `nt()`, and full RTL (right-to-left) layout support for Arabic, Hebrew, and other bidirectional languages.

## Do I Need This?

:::{note}
**Skip this if**: Your site is single-language only.
**Read this if**: You need translated content, hreflang SEO, RTL layouts, or a translator workflow.
:::

## Quick Start

1. **Configure languages** in `bengal.toml`:

```toml
[i18n]
default_language = "en"
strategy = "prefix"
content_structure = "dir"
languages = [
    { code = "en", name = "English", weight = 1 },
    { code = "es", name = "Español", weight = 2 },
    { code = "ar", name = "العربية", weight = 3, rtl = true },
]
```

2. **Create content per locale**:

```
content/
├── en/
│   ├── _index.md
│   └── about.md
├── es/
│   ├── _index.md
│   └── about.md
└── ar/
    ├── _index.md
    └── about.md
```

3. **Add PO translation files** for UI strings:

```
i18n/
├── en/LC_MESSAGES/messages.po
├── es/LC_MESSAGES/messages.po
└── ar/LC_MESSAGES/messages.po
```

4. **Use `t()` in templates**:

```html
<nav>
  <a href="/">{{ t("Home") }}</a>
  <a href="/about/">{{ t("About") }}</a>
</nav>
```

5. **Compile and build**:

```bash
bengal i18n compile
bengal build
```

## Translation Workflow

| Step | Command | Description |
|------|---------|-------------|
| Extract | `bengal i18n extract` | Scan templates for `t()` calls, generate `.pot` |
| Translate | Edit `.po` files | Add translations with a PO editor (e.g. Poedit) |
| Compile | `bengal i18n compile` | Compile `.po` → `.mo` for faster loading |
| Status | `bengal i18n status` | Check translation coverage per locale |
| Build | `bengal build` | Generate site |

## Key Concepts

- **Content structure**: `dir` (content/en/, content/es/) or `file` (about.en.md, about.es.md)
- **URL strategy**: `prefix` (/en/, /es/) or `subdomain` (en.example.com)
- **Fallback**: When a key is missing, Bengal falls back to the default language
- **RTL**: Arabic and Hebrew get `dir="rtl"` on `<html>` automatically

## Guides

:::{child-cards}
:columns: 2
:include: pages
:fields: title, description, icon
:exclude: _index.md
:::
