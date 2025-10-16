
---
title: "validators.sitemap"
type: python-module
source_file: "bengal/health/validators/sitemap.py"
css_class: api-content
description: "Sitemap validator - checks sitemap.xml validity for SEO.  Validates: - Sitemap file exists - XML is well-formed - No duplicate URLs - URLs are properly formatted - Sitemap follows protocol"
---

# validators.sitemap

Sitemap validator - checks sitemap.xml validity for SEO.

Validates:
- Sitemap file exists
- XML is well-formed
- No duplicate URLs
- URLs are properly formatted
- Sitemap follows protocol

---

## Classes

### `SitemapValidator`

**Inherits from:** `BaseValidator`
Validates sitemap.xml for SEO.

Checks:
- Sitemap file exists
- XML is well-formed
- Follows sitemap protocol (http://www.sitemaps.org/)
- No duplicate URLs
- URLs are absolute and properly formatted
- Sitemap includes expected pages




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run sitemap validation checks.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[CheckResult]`




---


