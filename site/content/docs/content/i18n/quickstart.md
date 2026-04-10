---
title: i18n Quickstart
description: Set up a bilingual site with gettext PO/MO in 5 minutes
weight: 10
---
# i18n Quickstart

This guide walks you through setting up a bilingual (English/Spanish) site with Bengal's gettext workflow.

## 1. Configure Languages

Add to `bengal.toml`:

```toml
[i18n]
default_language = "en"
strategy = "prefix"
content_structure = "dir"
fallback_to_default = true
gettext_domain = "messages"
languages = [
    { code = "en", name = "English", weight = 1 },
    { code = "es", name = "Español", weight = 2 },
]
```

- **strategy**: `prefix` produces `/en/`, `/es/` URLs
- **content_structure**: `dir` uses `content/en/`, `content/es/` folders
- **gettext_domain**: Domain name for PO/MO files (default `messages`)

## 2. Create Content Structure

```
content/
├── en/
│   ├── _index.md      # English home
│   └── about.md
└── es/
    ├── _index.md      # Spanish home
    └── about.md
```

Each locale has its own directory. Pages with the same path (e.g. `about.md`) are linked as translations via `translation_key`.

## 3. Extract UI Strings

Scan your templates for `t("key")` calls:

```bash
bengal i18n extract -o messages.pot
```

This creates `messages.pot` with all keys found in templates. Copy it to each locale:

```bash
mkdir -p i18n/en/LC_MESSAGES i18n/es/LC_MESSAGES
cp messages.pot i18n/en/LC_MESSAGES/messages.po
cp messages.pot i18n/es/LC_MESSAGES/messages.po
```

## 4. Add Translations

Edit each `.po` file. Example `i18n/es/LC_MESSAGES/messages.po`:

```po
msgid "Home"
msgstr "Inicio"

msgid "About"
msgstr "Acerca de"

msgid "Welcome"
msgstr "Bienvenido"
```

Use a PO editor like [Poedit](https://poedit.net/) for a friendlier workflow.

## 5. Compile and Build

```bash
bengal i18n compile
bengal build
```

The `compile` step converts `.po` → `.mo` (binary, faster at runtime). Output goes to `public/en/`, `public/es/`, etc.

## 6. Check Coverage

```bash
bengal i18n status
```

Shows per-locale translation coverage. Use `--fail-on-missing-translations` in CI to gate on completeness.

## Template Usage

In Kida or Jinja templates:

```html
{# Translate a key #}
{{ t("Home") }}

{# With parameters #}
{{ t("greeting", {"name": user.name}) }}

{# Override language #}
{{ t("About", lang="es") }}

{# Plural-aware translation #}
{{ nt("1 item", "{n} items", count) }}

{# Plural with extra params #}
{{ nt("1 {thing}", "{n} {thing}s", count, {"thing": "file"}) }}

{# Current locale and text direction #}
<html lang="{{ current_lang() }}" dir="{{ direction() }}">
```

## Next Steps

- [[docs/content/i18n/rtl|RTL Layout]] — RTL layout for Arabic/Hebrew
- [[docs/content/i18n/translator-guide|Translator Guide]] — Contributor workflow for translations
