---
title: Internationalization (i18n)
description: Localizing content, URLs, menus, taxonomy, sitemap, RSS, and templates
weight: 45
---

This page explains how to enable and use i18n in Bengal SSG.

## Configuration

Add an `[i18n]` section to `bengal.toml`:

```toml
[i18n]
strategy = "prefix"            # url structure: /en/..., /fr/...
content_structure = "dir"      # content/en/... and content/fr/...
default_language = "en"
default_in_subdir = false       # put default lang under /en/ only if true
share_taxonomies = false        # per-locale tag pages

[[i18n.languages]]
code = "en"
name = "English"
hreflang = "en"

[[i18n.languages]]
code = "fr"
name = "Français"
hreflang = "fr"
```

## Content Organization

- Directory per language (recommended):
  - `content/en/docs/...`
  - `content/fr/docs/...`

You can override language in front matter:

```yaml
---
title: Page title
lang: fr
translation_key: docs/getting-started
---
```

`translation_key` links pages across languages for alternate links and cross-links.

## URL Structure

- Pretty URLs preserved. When `strategy = "prefix"`:
  - Non-default: `/fr/docs/page/`
  - Default with `default_in_subdir = false`: `/docs/page/`
  - Default with `default_in_subdir = true`: `/en/docs/page/`

Taxonomy URLs are also prefixed under the active locale.

## Templates

Helpers available in all templates:

```jinja
<html lang="{{ current_lang() }}">

{{ t('nav.search') }}                 {# translate keys from i18n/<lang>.yaml #}

{% for alt in alternate_links(page) %}
  <link rel="alternate" hreflang="{{ alt.hreflang }}" href="{{ alt.href }}">
{% endfor %}

{% set main_menu = get_menu_lang('main', current_lang()) %}
```

Localized date formatting:

```jinja
<time datetime="{{ page.date | date_iso }}">{{ locale_date(page.date, 'long', current_lang()) }}</time>
```

## RSS and Sitemap

- Generate an RSS feed per locale at `/rss.xml` or `/<lang>/rss.xml` based on configuration.
- The sitemap includes `xhtml:link` alternate links for translated pages.

## Search / index.json

- The site-wide `index.json` appears under the locale when prefixed:
  - Default lang without sub-directory: `/index.json`
  - Non-default: `/<lang>/index.json`

## Menus

- Add `lang = "fr"` on menu items to restrict to a locale:

```toml
[[menu.main]]
name = "Accueil"
url = "/"
weight = 1
lang = "fr"
```

In templates, use `get_menu_lang('main', current_lang())`.

## i18n Files

Place translations in `i18n/<code>.yaml` (or `.yml`, `.json`, `.toml`). Example:

```yaml
nav:
  search: "Search"
  docs: "Documentation"
footer:
  rights: "All rights reserved."
```

Use parameter interpolation: `"Hello {name}"` ⇒ `{{ t('greeting', {'name': 'Alice'}) }}`.

## Notes

- Thread-safe: i18n helpers read from the render context, no global mutations.
- Taxonomies: set `share_taxonomies = true` to combine tags across languages.
