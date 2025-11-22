# validators

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/health/validators/__init__.py

Health check validators for Bengal SSG.

Each validator checks a specific aspect of the build:

Phase 1 (Basic):
- OutputValidator: Page sizes, asset presence
- ConfigValidator: Configuration validity (integrates existing validator)
- MenuValidator: Menu structure integrity
- LinkValidator: Broken links detection

Phase 2 (Build-Time):
- NavigationValidator: Page navigation (next/prev, breadcrumbs)
- TaxonomyValidator: Tags, categories, generated pages
- RenderingValidator: HTML quality, template functions
- DirectiveValidator: Directive syntax, usage, and performance

Phase 3 (Advanced):
- CacheValidator: Incremental build cache integrity
- PerformanceValidator: Build performance metrics

Phase 4 (Production-Ready):
- RSSValidator: RSS feed quality and completeness
- SitemapValidator: Sitemap.xml validity for SEO
- FontValidator: Font downloads and CSS generation
- AssetValidator: Asset optimization and integrity

Phase 5 (Knowledge Graph):
- ConnectivityValidator: Page connectivity and orphan detection

*Note: Template has undefined variables. This is fallback content.*
