
---
title: "content_types.strategies"
type: python-module
source_file: "bengal/content_types/strategies.py"
css_class: api-content
description: "Concrete content type strategies.  Implements specific strategies for different content types like blog, docs, etc."
---

# content_types.strategies

Concrete content type strategies.

Implements specific strategies for different content types like blog, docs, etc.

---

## Classes

### `BlogStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for blog/news content with chronological ordering.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort by date (newest first).



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect blog sections by name or date-heavy content.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `ArchiveStrategy`

**Inherits from:** `BlogStrategy`
Strategy for archive/chronological content.

Similar to blog but uses simpler archive template.





### `DocsStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for documentation with weight-based ordering.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort by weight, then title (keeps manual ordering).



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect docs sections by name.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `ApiReferenceStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for API reference documentation.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Keep original discovery order (alphabetical).



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect API sections by name or content.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `CliReferenceStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for CLI reference documentation.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Keep original discovery order (alphabetical).



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect CLI sections by name or content.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `TutorialStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for tutorial content.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort by weight (for sequential tutorials).



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect tutorial sections by name.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `ChangelogStrategy`

**Inherits from:** `ContentTypeStrategy`
Strategy for changelog/release notes with chronological timeline.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort by date (newest first) or by version number.



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---
#### `detect_from_section`
```python
def detect_from_section(self, section: 'Section') -> bool
```

Detect changelog sections by name.



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
* - `section`
  - `'Section'`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---

### `PageStrategy`

**Inherits from:** `ContentTypeStrategy`
Default strategy for generic pages.




:::{rubric} Methods
:class: rubric-methods
:::
#### `sort_pages`
```python
def sort_pages(self, pages: list['Page']) -> list['Page']
```

Sort by weight, then title.



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
* - `pages`
  - `list['Page']`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list['Page']`




---


