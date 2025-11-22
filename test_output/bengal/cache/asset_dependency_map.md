# asset_dependency_map

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/asset_dependency_map.py

Asset Dependency Map for incremental builds.

Tracks which pages reference which assets to enable on-demand asset discovery.
This allows incremental builds to discover only assets needed for changed pages,
skipping asset discovery for unchanged pages.

Architecture:
- Mapping: source_path → set[asset_urls] (which pages use which assets)
- Storage: .bengal/asset_deps.json (compact format)
- Tracking: Built during page parsing by extracting asset references
- Incremental: Only discover assets for changed pages

Performance Impact:
- Asset discovery skipped for unchanged pages (~50ms saved per 100 pages)
- Focus on only needed assets in incremental builds
- Incremental asset fingerprinting possible

Asset Types Tracked:
- Images: img src, picture sources
- Stylesheets: link href
- Scripts: script src
- Fonts: @font-face urls
- Other: data URLs, imports, includes

*Note: Template has undefined variables. This is fallback content.*
