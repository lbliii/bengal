---
title: Multilingual Sites
nav_title: i18n
description: Serve your documentation in multiple languages with proper URL routing and translations
weight: 60
icon: globe
tags:
- i18n
- multilingual
- internationalization
- localization
keywords:
- i18n
- multilingual
- languages
- translation
- localization
category: how-to
---
# Multilingual Sites

Bengal supports full internationalization (i18n) with content routing, UI translations, and SEO-friendly hreflang tags.

## Quick Start

### 1. Configure Languages

```yaml
# config/_default/i18n.yaml
i18n:
  strategy: "prefix"           # URL prefix strategy (/en/, /fr/)
  default_language: "en"
  default_in_subdir: false     # Default lang at root, others in subdirs
  languages:
    - code: "en"
      name: "English"
      weight: 1
    - code: "fr"
      name: "Français"
      weight: 2
    - code: "es"
      name: "Español"
      weight: 3
```

### 2. Organize Content by Language

```tree
content/
├── en/
│   ├── _index.md
│   └── docs/
│       ├── _index.md
│       └── getting-started.md
├── fr/
│   ├── _index.md
│   └── docs/
│       ├── _index.md
│       └── getting-started.md
└── es/
    ├── _index.md
    └── docs/
        └── getting-started.md
```

### 3. Add UI Translations

```yaml
# i18n/en.yaml
nav:
  home: "Home"
  docs: "Documentation"
  search: "Search"

footer:
  copyright: "© 2026 My Project"

content:
  read_more: "Read more"
  minutes_read: "{minutes} min read"
```

```yaml
# i18n/fr.yaml
nav:
  home: "Accueil"
  docs: "Documentation"
  search: "Rechercher"

footer:
  copyright: "© 2026 Mon Projet"

content:
  read_more: "Lire la suite"
  minutes_read: "{minutes} min de lecture"
```

### 4. Build and Verify

```bash
bengal build
```

**Output:**
```
public/
├── index.html              # English (default at root)
├── docs/
│   └── getting-started/
├── fr/
│   ├── index.html
│   └── docs/
│       └── getting-started/
└── es/
    ├── index.html
    └── docs/
        └── getting-started/
```

---

## Configuration Reference

### Strategy Options

| Strategy | Description | URL Pattern |
|----------|-------------|-------------|
| `"none"` | Single language (default) | `/docs/page/` |
| `"prefix"` | Language in URL path | `/en/docs/page/`, `/fr/docs/page/` |

### Full Configuration

```yaml
i18n:
  # URL strategy
  strategy: "prefix"

  # Default language code
  default_language: "en"

  # Put default language in subdir too? (false = root)
  default_in_subdir: false

  # Language list with metadata
  languages:
    - code: "en"
      name: "English"
      hreflang: "en"        # For SEO (usually same as code)
      weight: 1             # Sort order in language switchers
    - code: "fr"
      name: "Français"
      hreflang: "fr"
      weight: 2
```

---

## Template Functions

### t() — Translate UI Strings

```kida
{# Basic translation #}
{{ t('nav.home') }}

{# With parameters #}
{{ t('content.minutes_read', {'minutes': page.reading_time}) }}

{# Force specific language #}
{{ t('nav.home', {}, 'fr') }}

{# With default fallback text #}
{{ t('custom.key', {}, None, 'Fallback text') }}
```

**Signature:** `t(key, params={}, lang=None, default=None)`

If a translation key is missing, Bengal automatically falls back to the default language. If still not found, returns the provided `default` or the key itself.

### current_lang() — Get Current Language

```kida
{% let lang = current_lang() %}
<html lang="{{ lang }}">

{% if current_lang() == 'fr' %}
  {# French-specific content #}
{% end %}
```

### languages() — List All Languages

```kida
{# Language switcher #}
<nav class="language-switcher">
  {% for lang in languages() %}
    <a href="/{{ lang.code }}/"
       {% if lang.code == current_lang() %}class="active"{% end %}>
      {{ lang.name }}
    </a>
  {% end %}
</nav>
```

**Returns:** List of language objects with:
- `code` — Language code (e.g., `"en"`)
- `name` — Display name (e.g., `"English"`)
- `hreflang` — SEO attribute
- `weight` — Sort order

### alternate_links() — Generate hreflang Tags

```kida
{# In <head> for SEO #}
{% for alt in alternate_links(page) %}
  <link rel="alternate" hreflang="{{ alt.hreflang }}" href="{{ alt.href }}">
{% end %}
```

**Output:**
```html
<link rel="alternate" hreflang="en" href="/docs/getting-started/">
<link rel="alternate" hreflang="fr" href="/fr/docs/getting-started/">
<link rel="alternate" hreflang="x-default" href="/docs/getting-started/">
```

### locale_date() — Localized Dates

```kida
{# Format with locale-aware output #}
{{ locale_date(page.date, 'medium') }}
{# → "Dec 19, 2025" (English) or "19 déc. 2025" (French) #}

{{ locale_date(page.date, 'long') }}
{# → "December 19, 2025" or "19 décembre 2025" #}

{# Force specific locale #}
{{ locale_date(page.date, 'medium', lang='fr') }}
```

**Format options:** `short`, `medium`, `long`

:::{tip}
For full date formatting, install Babel: `pip install babel`
:::

---

## Content Linking Across Languages

### Link Translations with translation_key

Pages with the same `translation_key` are linked as translations:

```yaml
# content/en/docs/getting-started.md
---
title: Getting Started
translation_key: getting-started
---

# content/fr/docs/getting-started.md
---
title: Démarrage
translation_key: getting-started
---
```

Bengal uses `translation_key` to:
- Generate `alternate_links()` for SEO
- Enable language switchers to link to the same page in other languages

### Per-Page Language Override

Override the directory-based language:

```yaml
---
title: Page in French
lang: fr
---
```

---

## Translation File Formats

Bengal supports multiple formats for translation files:

```
i18n/
├── en.yaml      # YAML (recommended)
├── fr.yaml
├── es.json      # JSON also works
└── de.toml      # TOML also works
```

### Nested Keys

```yaml
# i18n/en.yaml
nav:
  home: "Home"
  docs:
    title: "Documentation"
    description: "Learn how to use..."

errors:
  404:
    title: "Page Not Found"
    message: "The page you're looking for doesn't exist."
```

Access with dot notation:

```kida
{{ t('nav.docs.title') }}
{{ t('errors.404.message') }}
```

---

## Integration with Other Features

### Menus

Use `get_menu_lang()` to get language-aware menu items:

```kida
{% for item in get_menu_lang('main', current_lang()) %}
  <a href="{{ item.url }}">{{ item.name }}</a>
{% end %}
```

For the default menu without language awareness:

```kida
{% for item in get_menu('main') %}
  <a href="{{ item.url }}">{{ item.name }}</a>
{% end %}
```

### RSS Feeds

RSS feeds are generated per-language when using `prefix` strategy:

- `/rss.xml` — Default language
- `/fr/rss.xml` — French
- `/es/rss.xml` — Spanish

### Search

Search indexes are built per-language for accurate results:

- `/index.json` — Default language
- `/fr/index.json` — French

---

## Example: Complete Language Switcher

```kida
{# templates/partials/language-switcher.html #}
<div class="language-switcher">
  <button aria-label="Select language">
    {{ current_lang() | upper }}
  </button>

  <ul class="dropdown">
    {% for lang in languages() %}
      {% let is_current = lang.code == current_lang() %}
      <li>
        <a href="/{{ lang.code }}/"
           {% if is_current %}aria-current="true"{% end %}
           lang="{{ lang.code }}">
          {{ lang.name }}
        </a>
      </li>
    {% end %}
  </ul>
</div>
```

---

## Troubleshooting

### Translations Not Loading

1. Check file exists: `i18n/<lang>.yaml`
2. Verify YAML syntax is valid
3. Check key path matches: `t('nav.home')` needs `nav.home:` in file

### Wrong Language Displayed

1. Verify `lang` frontmatter or directory structure
2. Check `i18n.strategy` is set to `"prefix"`
3. Ensure content is in correct language directory

### Missing hreflang Tags

1. Add `translation_key` to linked pages
2. Verify pages exist in both languages
3. Check `alternate_links(page)` is in `<head>`

---

:::{seealso}
- [[docs/reference/template-functions|Template Functions Reference]]
- [[docs/building/configuration|Configuration Reference]]
- [[docs/theming/templating|Templating Guide]]
:::
