# asset_extractor

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/rendering/asset_extractor.py

Asset extraction utilities for tracking page-to-asset dependencies.

Extracts references to assets (images, stylesheets, scripts, fonts) from
rendered HTML to populate the AssetDependencyMap cache. This enables
incremental builds to discover only the assets needed for changed pages.

Asset types tracked:
- Images: <img src>, <picture> <source srcset>
- Stylesheets: <link href> with rel=stylesheet
- Scripts: <script src>
- Fonts: <link href> with rel=preload type=font
- Data URLs, IFrames, and other embedded resources

*Note: Template has undefined variables. This is fallback content.*
