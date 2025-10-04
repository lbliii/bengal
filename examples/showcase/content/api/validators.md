---
title: "validators"
layout: api-reference
type: python-module
source_file: "../../bengal/health/validators/__init__.py"
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

Phase 3 Lite (Advanced):
- CacheValidator: Incremental build cache integrity
- PerformanceValidator: Build performance metrics

**Source:** `../../bengal/health/validators/__init__.py`

---


