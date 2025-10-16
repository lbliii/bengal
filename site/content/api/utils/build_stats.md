
---
title: "utils.build_stats"
type: python-module
source_file: "bengal/utils/build_stats.py"
css_class: api-content
description: "Build statistics display with colorful output and ASCII art."
---

# utils.build_stats

Build statistics display with colorful output and ASCII art.

---

## Classes

### `BuildWarning`


A build warning or error.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `file_path`
  - `str`
  - -
* - `message`
  - `str`
  - -
* - `warning_type`
  - `str`
  - -
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `short_path` @property

```python
@property
def short_path(self) -> str
```

Get shortened path for display.

:::{rubric} Methods
:class: rubric-methods
:::
#### `short_path`
```python
def short_path(self) -> str
```

Get shortened path for display.



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

### `BuildStats`


Container for build statistics.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 32 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `total_pages`
  - `int`
  - -
* - `regular_pages`
  - `int`
  - -
* - `generated_pages`
  - `int`
  - -
* - `tag_pages`
  - `int`
  - -
* - `archive_pages`
  - `int`
  - -
* - `pagination_pages`
  - `int`
  - -
* - `total_assets`
  - `int`
  - -
* - `total_sections`
  - `int`
  - -
* - `taxonomies_count`
  - `int`
  - -
* - `build_time_ms`
  - `float`
  - -
* - `parallel`
  - `bool`
  - -
* - `incremental`
  - `bool`
  - -
* - `skipped`
  - `bool`
  - -
* - `total_directives`
  - `int`
  - -
* - `directives_by_type`
  - `dict[str, int]`
  - -
* - `discovery_time_ms`
  - `float`
  - -
* - `taxonomy_time_ms`
  - `float`
  - -
* - `rendering_time_ms`
  - `float`
  - -
* - `assets_time_ms`
  - `float`
  - -
* - `postprocess_time_ms`
  - `float`
  - -
* - `memory_rss_mb`
  - `float`
  - -
* - `memory_heap_mb`
  - `float`
  - -
* - `memory_peak_mb`
  - `float`
  - -
* - `cache_hits`
  - `int`
  - -
* - `cache_misses`
  - `int`
  - -
* - `time_saved_ms`
  - `float`
  - -
* - `menu_time_ms`
  - `float`
  - -
* - `related_posts_time_ms`
  - `float`
  - -
* - `fonts_time_ms`
  - `float`
  - -
* - `output_dir`
  - `str`
  - -
* - `warnings`
  - `list`
  - -
* - `template_errors`
  - `list`
  - -
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `has_errors` @property

```python
@property
def has_errors(self) -> bool
```

Check if build has any errors.
#### `warnings_by_type` @property

```python
@property
def warnings_by_type(self) -> dict[str, list]
```

Group warnings by type.

:::{rubric} Methods
:class: rubric-methods
:::
#### `has_errors`
```python
def has_errors(self) -> bool
```

Check if build has any errors.



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

`bool`




---
#### `warnings_by_type`
```python
def warnings_by_type(self) -> dict[str, list]
```

Group warnings by type.



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

`dict[str, list]`




---
#### `__post_init__`
```python
def __post_init__(self)
```

Initialize mutable defaults.



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
#### `add_warning`
```python
def add_warning(self, file_path: str, message: str, warning_type: str = 'other') -> None
```

Add a warning to the build.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `file_path`
  - `str`
  - -
  - -
* - `message`
  - `str`
  - -
  - -
* - `warning_type`
  - `str`
  - `'other'`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `add_template_error`
```python
def add_template_error(self, error: Any) -> None
```

Add a rich template error.



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
* - `error`
  - `Any`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `add_directive`
```python
def add_directive(self, directive_type: str) -> None
```

Track a directive usage.



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
* - `directive_type`
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
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

Convert stats to dictionary.



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

`dict[str, Any]`




---


## Functions

### `format_time`
```python
def format_time(ms: float) -> str
```

Format milliseconds for display.



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
* - `ms`
  - `float`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
### `display_warnings`
```python
def display_warnings(stats: BuildStats) -> None
```

Display grouped warnings and errors.



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
* - `stats`
  - `BuildStats`
  - -
  - Build statistics with warnings
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `display_simple_build_stats`
```python
def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None
```

Display simple build statistics for writers.

Clean, minimal output focused on success/failure and critical issues only.
Perfect for content authors who just want to know "did it work?"



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
* - `stats`
  - `BuildStats`
  - -
  - Build statistics to display
* - `output_dir`
  - `str | None`
  - `None`
  - Output directory path to display
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `display_build_stats`
```python
def display_build_stats(stats: BuildStats, show_art: bool = True, output_dir: str | None = None) -> None
```

Display build statistics in a colorful table.



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
* - `stats`
  - `BuildStats`
  - -
  - Build statistics to display
* - `show_art`
  - `bool`
  - `True`
  - Whether to show ASCII art
* - `output_dir`
  - `str | None`
  - `None`
  - Output directory path to display
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `show_building_indicator`
```python
def show_building_indicator(text: str = 'Building') -> None
```

Show a building indicator (static or animated based on terminal).



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
* - `text`
  - `str`
  - `'Building'`
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `show_error`
```python
def show_error(message: str, show_art: bool = True) -> None
```

Show an error message with art.



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
* - `message`
  - `str`
  - -
  - -
* - `show_art`
  - `bool`
  - `True`
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `show_welcome`
```python
def show_welcome() -> None
```

Show welcome banner using Rich for stable borders.



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `show_clean_success`
```python
def show_clean_success(output_dir: str) -> None
```

Show clean success message using CLI output system.

Note: This is now only used for --force mode (when there's no prompt).
Regular clean uses inline success message after prompt confirmation.



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
* - `output_dir`
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
### `display_template_errors`
```python
def display_template_errors(stats: BuildStats) -> None
```

Display all collected template errors.



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
* - `stats`
  - `BuildStats`
  - -
  - Build statistics with template errors
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
