# Bengal Theme Structure

## Override Hierarchy

1. Site `templates/` — highest priority
2. Site `static/` — site-level assets
3. Theme `templates/` and `assets/`
4. Parent theme (if theme has parent)

## theme.yaml

```yaml
name: my-theme
version: 1.0.0
parent: null   # Or "default" to extend

features:
  navigation:
    breadcrumbs: true
  content:
    excerpts: true
```

## Key Templates

- `base.html` — Root layout
- `home.html` — Home page
- `blog/single.html` — Blog post
- `blog/list.html` — Blog listing
- `doc/home.html` — Doc section
- `404.html` — Not found

## Partials

Reusable components in `templates/partials/`:
- `navigation-components.html`
- `components/post-card.html`
- `tag-nav.html`
