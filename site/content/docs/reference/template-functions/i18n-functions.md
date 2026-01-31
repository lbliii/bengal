---
title: Internationalization Functions
description: Translation, language detection, and localized formatting
weight: 40
tags:
- reference
- functions
- i18n
- translation
category: reference
---

# Internationalization (i18n)

These functions support multilingual sites with translations, language detection, and localized formatting.

## t

Translate UI strings using translation files.

```kida
{# Basic translation #}
{{ t('nav.home') }}

{# With interpolation parameters #}
{{ t('content.minutes_read', {'minutes': page.reading_time}) }}

{# Force specific language #}
{{ t('nav.home', lang='fr') }}
```

**Parameters:**
- `key`: Dot-notation path to translation (e.g., `'nav.home'`, `'errors.404.title'`)
- `params`: Optional dictionary for string interpolation
- `lang`: Optional language code override

**Translation Files:**

Place translation files in `i18n/` directory:

```yaml
# i18n/en.yaml
nav:
  home: "Home"
  docs: "Documentation"

content:
  minutes_read: "{minutes} min read"
```

```yaml
# i18n/fr.yaml
nav:
  home: "Accueil"
  docs: "Documentation"

content:
  minutes_read: "{minutes} min de lecture"
```

## current_lang

Get the current page's language code.

```kida
<html lang="{{ current_lang() }}">

{% if current_lang() == 'fr' %}
  {# French-specific content #}
{% end %}

{# Use in conditional logic #}
{% let is_english = current_lang() == 'en' %}
```

**Returns:** Language code string (e.g., `"en"`, `"fr"`) or `None`

## languages

Get list of all configured languages.

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
- `hreflang` — SEO attribute value
- `weight` — Sort order

## alternate_links

Generate hreflang links for SEO.

```kida
{# In <head> #}
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

**Returns:** List of dictionaries with:
- `hreflang` — Language code for SEO
- `href` — Full URL to alternate version

## locale_date

Format dates according to locale.

```kida
{# Format with current locale #}
{{ locale_date(page.date, 'medium') }}
{# → "Dec 19, 2025" (English) or "19 déc. 2025" (French) #}

{{ locale_date(page.date, 'long') }}
{# → "December 19, 2025" or "19 décembre 2025" #}

{# Force specific locale #}
{{ locale_date(page.date, 'medium', lang='fr') }}
```

**Parameters:**
- `date`: Date object or string
- `format`: Format style (`'short'`, `'medium'`, `'long'`)
- `lang`: Optional language code override

:::{tip}
For full locale date formatting, install Babel: `pip install babel`
:::

## i18n Configuration

Configure languages in your site config:

```yaml
# config/_default/i18n.yaml
i18n:
  strategy: "prefix"           # URL prefix strategy (/en/, /fr/)
  default_language: "en"
  default_in_subdir: false     # Default lang at root
  languages:
    - code: "en"
      name: "English"
      weight: 1
    - code: "fr"
      name: "Français"
      weight: 2
```

:::{seealso}
See [[docs/content/i18n|Multilingual Sites Guide]] for complete i18n setup.
:::
