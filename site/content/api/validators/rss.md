
---
title: "validators.rss"
type: python-module
source_file: "bengal/health/validators/rss.py"
css_class: api-content
description: "RSS feed validator - checks RSS feed quality and completeness.  Validates: - RSS file exists and is readable - XML is well-formed and valid RSS 2.0 - Feed contains expected items - URLs are properl..."
---

# validators.rss

RSS feed validator - checks RSS feed quality and completeness.

Validates:
- RSS file exists and is readable
- XML is well-formed and valid RSS 2.0
- Feed contains expected items
- URLs are properly formatted
- Dates are in RFC 822 format

---

## Classes

### `RSSValidator`

**Inherits from:** `BaseValidator`
Validates RSS feed quality.

Checks:
- RSS file exists (if site has dated content)
- XML is well-formed
- Feed structure is valid RSS 2.0
- URLs are properly formatted
- Feed has reasonable number of items




:::{rubric} Methods
:class: rubric-methods
:::
#### `validate`
```python
def validate(self, site: 'Site') -> list[CheckResult]
```

Run RSS validation checks.



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
