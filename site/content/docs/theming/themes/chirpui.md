---
title: Chirp UI Theme
description: Build a Bengal site with the optional Chirp UI component library
weight: 20
category: guide
icon: palette
card_color: green
---
# Chirp UI Theme

Bengal includes an optional `chirpui` theme that renders the site shell, pages,
docs, lists, search, tags, and blog templates with Chirp UI Kida components.
It lives beside `default`; switching to it does not modify the default theme.

Install Chirp UI 0.7 or newer in the environment that builds the site:

```bash
uv add chirp-ui
```

Then select the theme:

```toml
[build]
theme = "chirpui"
```

The theme loads Chirp UI through `theme.toml` provider libraries and fingerprints
`chirp_ui/chirpui.css` through Bengal's normal asset manifest. Bengal does not
bundle `chirp-ui` as a hard dependency, so builds that use this theme should
fail fast if the package is missing.

## Scope

- Uses Chirp UI component macros for the site shell, navigation, docs drawer,
  heroes, document headers, detail headers, profile headers, rendered content,
  panels, nav trees, resource indexes, index cards, badges, breadcrumbs, empty
  states, buttons, metrics, post cards, timelines, and search headers.
- Adds local browser behavior for theme toggles, static page filtering, and the
  mobile docs drawer trigger.
- Groups search results by content type, makes browse/index pages filterable,
  and keeps nested docs navigation open on the active branch.
- Keeps a small Bengal bridge stylesheet for documentation layout, search
  results, skip links, and footer spacing.
- Avoids default theme templates, classes, CSS, and JavaScript.

## Current Limitations

The bundled theme is ready for preview and fixture coverage, but sites with
custom taxonomies, unusual menus, or heavily customized default-theme partials
should verify their pages before switching production builds.

## Preview Coverage

The integration fixture exercises nested documentation, blog posts, changelog
releases, archives, author pages, tags, search, and generated 404 output. It is
intended to grow into the visual regression fixture for future theme work.
