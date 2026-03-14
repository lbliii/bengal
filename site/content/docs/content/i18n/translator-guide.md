---
title: Translator Contributor Guide
description: How to contribute translations and PO file conventions
weight: 30
---
# Translator Contributor Guide

This guide explains how to contribute translations to a Bengal site using the standard gettext PO workflow.

## PO File Structure

Translations live in:

```
i18n/
├── en/LC_MESSAGES/messages.po
├── es/LC_MESSAGES/messages.po
└── ar/LC_MESSAGES/messages.po
```

Each `.po` file contains:

- **Header**: Metadata (charset, plural forms)
- **Entries**: `msgid` (source) and `msgstr` (translation)

## PO File Format

```po
# English translations for My Site
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\n"
"MIME-Version: 1.0\n"

msgid "Home"
msgstr "Home"

msgid "About"
msgstr "About"

msgid "Read more"
msgstr "Read more"
```

- **msgid**: The source string (from templates)
- **msgstr**: The translation. Empty `msgstr ""` means untranslated (fallback to key)

## Conventions

1. **Use UTF-8** for all PO files. Set `Content-Type: text/plain; charset=UTF-8` in the header.
2. **Keep msgid unchanged** — it's the lookup key. Never translate the msgid.
3. **Preserve placeholders** — if the source has `{name}`, keep it in the translation: `Hola {name}`.
4. **Plural forms** — use `msgid_plural` and `msgstr[0]`, `msgstr[1]` for languages with plural rules.

## Workflow for Contributors

1. **Get the template**: Ask the maintainer for `messages.pot` or run `bengal i18n extract` in the repo.
2. **Create your locale**: `mkdir -p i18n/XX/LC_MESSAGES` (e.g. `XX` = `fr` for French).
3. **Copy and translate**: Copy `messages.pot` to `i18n/XX/LC_MESSAGES/messages.po` and fill in `msgstr` values.
4. **Submit**: Open a PR with your new or updated `.po` file.

## Tools

- **[Poedit](https://poedit.net/)**: GUI editor for PO files, handles plural forms
- **[Lokalize](https://apps.kde.org/lokalize/)**: KDE translation tool
- **VS Code**: Extensions like "Gettext" for PO editing

## Checking Your Work

After adding translations:

```bash
bengal i18n compile
bengal build
bengal i18n status
```

`bengal i18n status` shows coverage. Aim for 100% for your locale.

## Plural Forms

For strings with counts (e.g. "1 item" vs "5 items"):

```po
msgid "%d item"
msgid_plural "%d items"
msgstr[0] "%d elemento"
msgstr[1] "%d elementos"
```

The plural rule depends on the language. See [Unicode CLDR](https://unicode-org.github.io/cldr-staging/charts/43/supplemental/language_plural_rules.html) for rules.
