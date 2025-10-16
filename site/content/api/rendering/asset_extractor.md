
---
title: "rendering.asset_extractor"
type: python-module
source_file: "bengal/rendering/asset_extractor.py"
css_class: api-content
description: "Asset extraction utilities for tracking page-to-asset dependencies.  Extracts references to assets (images, stylesheets, scripts, fonts) from rendered HTML to populate the AssetDependencyMap cache...."
---

# rendering.asset_extractor

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

---

## Classes

### `AssetExtractorParser`

**Inherits from:** `HTMLParser`
HTML parser for extracting asset references from rendered content.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

Initialize the asset extractor parser.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
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
:::

::::




---
#### `handle_starttag`
```python
def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None
```

Extract asset references from opening tags.

Handles:
- <img src>, <img srcset>
- <script src>
- <link href>
- <source srcset>
- <iframe src>
- <picture> with sources



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `tag`
  - `str`
  - -
  - -
* - `attrs`
  - `list[tuple[str, str | None]]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `handle_endtag`
```python
def handle_endtag(self, tag: str) -> None
```

Handle closing tags.



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
* - `tag`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `handle_data`
```python
def handle_data(self, data: str) -> None
```

Extract @import URLs from style tag content.

Handles:
- @import url('...')
- @import url("...")
- @import url(...) - without quotes



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
* - `data`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `feed`
```python
def feed(self, data: str) -> AssetExtractorParser
```

Parse HTML and return self for chaining.



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
* - `data`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`AssetExtractorParser` - self to allow parser(html).get_assets() pattern




---
#### `get_assets`
```python
def get_assets(self) -> set[str]
```

Get all extracted asset URLs.

Filters out empty strings and returns normalized set.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
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
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of asset URLs/paths




---


## Functions

### `extract_assets_from_html`
```python
def extract_assets_from_html(html_content: str) -> set[str]
```

Extract all asset references from rendered HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `html_content`
  - `str`
  - -
  - Rendered HTML content
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of asset URLs/paths referenced in the HTML




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> html = '<img src="/images/logo.png" /><script src="/js/app.js"></script>'
    >>> assets = extract_assets_from_html(html)
    >>> assert "/images/logo.png" in assets
    >>> assert "/js/app.js" in assets
```


---
