
---
title: "build_stats"
type: "python-module"
source_file: "bengal/utils/build_stats.py"
line_number: 1
description: "Build statistics display with colorful output and ASCII art."
---

# build_stats
**Type:** Module
**Source:** [View source](bengal/utils/build_stats.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›build_stats

Build statistics display with colorful output and ASCII art.

## Classes




### `BuildWarning`


A build warning or error.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`file_path`
: 

`message`
: 

`warning_type`
: 

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `short_path` @property

```python
def short_path(self) -> str
```
Get shortened path for display.







### `BuildStats`


Container for build statistics.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`total_pages`
: 

`regular_pages`
: 

`generated_pages`
: 

`tag_pages`
: 

`archive_pages`
: 

`pagination_pages`
: 

`total_assets`
: 

`total_sections`
: 

`taxonomies_count`
: 

`build_time_ms`
: 

`parallel`
: 

`incremental`
: 

`skipped`
: 

`total_directives`
: 

`directives_by_type`
: 

`discovery_time_ms`
: 

`taxonomy_time_ms`
: 

`rendering_time_ms`
: 

`assets_time_ms`
: 

`postprocess_time_ms`
: 

`health_check_time_ms`
: 

`memory_rss_mb`
: 

`memory_heap_mb`
: 

`memory_peak_mb`
: 

`cache_hits`
: 

`cache_misses`
: 

`time_saved_ms`
: 

`menu_time_ms`
: 

`related_posts_time_ms`
: 

`fonts_time_ms`
: 

`output_dir`
: 

`changed_outputs`
: 

`warnings`
: 

`template_errors`
: 

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `has_errors` @property

```python
def has_errors(self) -> bool
```
Check if build has any errors.

#### `warnings_by_type` @property

```python
def warnings_by_type(self) -> dict[str, list]
```
Group warnings by type.




## Methods



#### `__post_init__`

:::{div} api-badge-group
:::

```python
def __post_init__(self)
```


Initialize mutable defaults.




#### `add_warning`

:::{div} api-badge-group
:::

```python
def add_warning(self, file_path: str, message: str, warning_type: str = 'other') -> None
```


Add a warning to the build.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `str` | - | *No description provided.* |
| `message` | `str` | - | *No description provided.* |
| `warning_type` | `str` | `'other'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `add_template_error`

:::{div} api-badge-group
:::

```python
def add_template_error(self, error: Any) -> None
```


Add a rich template error.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `error` | `Any` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `add_directive`

:::{div} api-badge-group
:::

```python
def add_directive(self, directive_type: str) -> None
```


Track a directive usage.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive_type` | `str` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Convert stats to dictionary.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`

## Functions



### `format_time`


```python
def format_time(ms: float) -> str
```



Format milliseconds for display.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `ms` | `float` | - | *No description provided.* |







**Returns**


`str`




### `display_warnings`


```python
def display_warnings(stats: BuildStats) -> None
```



Display grouped warnings and errors.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `stats` | `BuildStats` | - | Build statistics with warnings |







**Returns**


`None`




### `display_simple_build_stats`


```python
def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None
```



Display simple build statistics for writers.

Clean, minimal output focused on success/failure and critical issues only.
Perfect for content authors who just want to know "did it work?"


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `stats` | `BuildStats` | - | Build statistics to display |
| `output_dir` | `str \| None` | - | Output directory path to display |







**Returns**


`None`




### `display_build_stats`


```python
def display_build_stats(stats: BuildStats, show_art: bool = True, output_dir: str | None = None) -> None
```



Display build statistics in a colorful table.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `stats` | `BuildStats` | - | Build statistics to display |
| `show_art` | `bool` | `True` | Whether to show ASCII art |
| `output_dir` | `str \| None` | - | Output directory path to display |







**Returns**


`None`




### `show_building_indicator`


```python
def show_building_indicator(text: str = 'Building') -> None
```



Show a building indicator (minimal - header is shown by build orchestrator).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | `'Building'` | *No description provided.* |







**Returns**


`None`




### `show_error`


```python
def show_error(message: str, show_art: bool = True) -> None
```



Show an error message with mouse emoji (errors that Bengal needs to catch!).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `show_art` | `bool` | `True` | *No description provided.* |







**Returns**


`None`




### `show_welcome`


```python
def show_welcome() -> None
```



Show welcome banner with Bengal cat mascot.



**Returns**


`None`




### `show_clean_success`


```python
def show_clean_success(output_dir: str) -> None
```



Show clean success message using CLI output system.

Note: This is now only used for --force mode (when there's no prompt).
Regular clean uses inline success message after prompt confirmation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_dir` | `str` | - | *No description provided.* |







**Returns**


`None`




### `display_template_errors`


```python
def display_template_errors(stats: BuildStats) -> None
```



Display all collected template errors.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `stats` | `BuildStats` | - | Build statistics with template errors |







**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/utils/build_stats.py`*

