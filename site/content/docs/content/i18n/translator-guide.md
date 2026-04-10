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

Bengal supports plural-aware translation through the `nt()` template function.

### Using nt() in Templates

```kida
{# Basic plural — {n} is automatically replaced with the count #}
{{ nt('1 item', '{n} items', count) }}

{# With extra parameters #}
{{ nt('1 {thing}', '{n} {thing}s', count, {'thing': 'file'}) }}
```

When no gettext catalog is loaded, `nt()` uses English-style selection (singular when n=1, plural otherwise). With a catalog, it uses `ngettext()` for correct plural rules.

### PO File Plural Entries

For languages with complex plural rules, use `msgid_plural` and indexed `msgstr`:

```po
# Spanish (2 forms: singular, plural)
msgid "1 item"
msgid_plural "{n} items"
msgstr[0] "1 elemento"
msgstr[1] "{n} elementos"
```

```po
# Polish (3 forms: singular, few, many)
msgid "1 item"
msgid_plural "{n} items"
msgstr[0] "1 element"
msgstr[1] "{n} elementy"
msgstr[2] "{n} elementów"
```

```po
# Arabic (6 forms: zero, one, two, few, many, other)
msgid "1 item"
msgid_plural "{n} items"
msgstr[0] "لا عناصر"
msgstr[1] "عنصر واحد"
msgstr[2] "عنصران"
msgstr[3] "{n} عناصر"
msgstr[4] "{n} عنصرًا"
msgstr[5] "{n} عنصر"
```

### Plural Rules Reference

The correct number of forms depends on the language:

| Language | Forms | Rule |
|----------|-------|------|
| English, Spanish, French | 2 | n == 1 ? singular : plural |
| Polish, Czech, Russian | 3 | Complex (singular, few, many) |
| Arabic | 6 | Complex (zero through other) |
| Japanese, Chinese, Korean | 1 | No plural distinction |

See [Unicode CLDR Plural Rules](https://unicode-org.github.io/cldr-staging/charts/43/supplemental/language_plural_rules.html) for the full reference.
