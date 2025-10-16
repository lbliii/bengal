
---
title: "validators"
type: python-module
source_file: "bengal/health/validators/__init__.py"
css_class: api-content
description: "Health check validators for Bengal SSG.  Each validator checks a specific aspect of the build:  Phase 1 (Basic): - OutputValidator: Page sizes, asset presence - ConfigValidator: Configuration valid..."
---

# validators

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

---


