
---
title: "fonts.downloader"
type: python-module
source_file: "bengal/fonts/downloader.py"
css_class: api-content
description: "Font downloader using Google Fonts API.  No external dependencies - uses only Python stdlib."
---

# fonts.downloader

Font downloader using Google Fonts API.

No external dependencies - uses only Python stdlib.

---

## Classes

### `FontVariant`


A specific font variant (weight + style).

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 4 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `family`
  - `str`
  - -
* - `weight`
  - `int`
  - -
* - `style`
  - `str`
  - -
* - `url`
  - `str`
  - -
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `filename` @property

```python
@property
def filename(self) -> str
```

Generate filename for this variant.

:::{rubric} Methods
:class: rubric-methods
:::
#### `filename`
```python
def filename(self) -> str
```

Generate filename for this variant.



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

`str`




---

### `GoogleFontsDownloader`


Downloads fonts from Google Fonts.

Uses the Google Fonts CSS API to get font URLs, then downloads
the actual .woff2 files. No API key required.




:::{rubric} Methods
:class: rubric-methods
:::
#### `download_font`
```python
def download_font(self, family: str, weights: list[int], styles: list[str] | None = None, output_dir: Path | None = None) -> list[FontVariant]
```

Download a font family with specified weights.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 5 parameters (click to expand)
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
* - `family`
  - `str`
  - -
  - Font family name (e.g., "Inter", "Roboto")
* - `weights`
  - `list[int]`
  - -
  - List of weights (e.g., [400, 700])
* - `styles`
  - `list[str] | None`
  - `None`
  - List of styles (e.g., ["normal", "italic"])
* - `output_dir`
  - `Path | None`
  - `None`
  - Directory to save font files
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[FontVariant]` - List of downloaded FontVariant objects




---


