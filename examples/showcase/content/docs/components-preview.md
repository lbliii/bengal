---
title: "Component Preview"
description: "Preview theme components with demo data while developing"
weight: 66
toc: true
---

# Component Preview

The dev server exposes a component gallery at `/__bengal_components__/` where you can browse and render theme components (partials) in isolation.

## Create a component manifest

Manifests live under `themes/<theme>/dev/components/*.yaml` in your project (or bundled theme). Each manifest names a `template` and any number of `variants` with `context`.

```yaml
name: "Article Card"
template: "partials/article-card.html"
variants:
  - id: "default"
    name: "Default"
    context:
      page:
        title: "Hello Bengal"
        url: "/hello-bengal/"
        excerpt: "A friendly introduction to Bengal SSG."
```

## View components

Start the dev server and open:

```text
http://localhost:5173/__bengal_components__/
```

Click a component to see its variants, or link directly:

```text
http://localhost:5173/__bengal_components__/view?c=card
```

## Notes

- Live reload applies; edits to templates/styles update previews.
- Theme inheritance and site overrides are respected.
- Use this to iterate quickly on partials before wiring them into pages.


