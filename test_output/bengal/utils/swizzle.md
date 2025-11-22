# swizzle

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/swizzle.py

SwizzleManager - Safe template override management for themes.

Features:
- Copy ("swizzle") a theme template/partial into project `templates/` preserving relative path
- Track provenance in `.bengal/themes/sources.json`
- List swizzled files
- Naive update: if local file is unchanged from its original swizzle, replace with upstream

Note: Three-way merge can be added later; for now we only auto-update when no local edits.

*Note: Template has undefined variables. This is fallback content.*
