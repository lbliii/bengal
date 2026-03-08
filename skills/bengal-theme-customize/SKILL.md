---
name: bengal-theme-customize
description: Customizes or extends Bengal themes. Use when changing the default theme, adding custom templates, or creating a new theme.
---

# Bengal Theme Customize

Customize or extend Bengal themes.

## Override Templates

Place templates at site root to override the default theme:

```
site-root/
├── templates/           # Overrides theme templates
│   ├── base.html        # Override base layout
│   ├── home.html        # Override home page
│   └── blog/
│       └── single.html  # Override blog post template
```

Templates in `templates/` take precedence over theme templates. Override only what you need.

## Add Static Assets

```
site-root/
├── static/              # Site-level static files
│   ├── css/
│   ├── js/
│   └── images/
```

Reference with `asset_url('path/to/file.css')` in templates.

## Theme Config (bengal.toml)

```toml
[theme]
name = "default"
# features = ["search", "rss"]
```

The default theme supports features in `theme.yaml`. Override in config if needed.

## Create a Custom Theme

```
site-root/
├── themes/
│   └── my-theme/
│       ├── theme.yaml   # Theme metadata
│       ├── templates/   # Theme templates
│       │   ├── base.html
│       │   └── ...
│       └── assets/      # Theme assets
│           ├── css/
│           └── js/
```

Set `[theme] name = "my-theme"` in bengal.toml.

## Theme Structure (Default)

```
themes/default/
├── theme.yaml       # Features, appearance, icons
├── templates/       # Kida/Jinja templates
│   ├── base.html
│   ├── home.html
│   ├── blog/
│   ├── doc/
│   └── partials/
└── assets/
    ├── css/
    ├── js/
    └── icons/
```

## Template Context

Use `theme.*` for theme config in templates:

```kida
{{ theme.hero_style }}
{{ theme.default_palette }}
```

## Checklist

- [ ] Create templates/ for overrides
- [ ] Create static/ for site assets
- [ ] Or create themes/my-theme/ for full custom theme
- [ ] Set theme name in bengal.toml
- [ ] Use asset_url() for asset paths

## Additional Resources

See [references/theme-structure.md](references/theme-structure.md) for directory layout.
