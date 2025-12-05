
---
title: "build_stats"
type: "python-module"
source_file: "bengal/bengal/utils/build_stats.py"
line_number: 1
description: "Build statistics display with colorful output and ASCII art."
---

# build_stats
**Type:** Module
**Source:** [View source](bengal/bengal/utils/build_stats.py#L1)



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

| Name | Type | Description |
|:-----|:-----|:------------|
| `file_path` | - | *No description provided.* |
| `message` | - | *No description provided.* |
| `warning_type` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `short_path` @property

```python
def short_path(self) -> str
```
Get shortened path for display.




## Methods



#### `short_path`
```python
def short_path(self) -> str
```


Get shortened path for display.



**Returns**


`str`




### `BuildStats`


Container for build statistics.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `total_pages` | - | *No description provided.* |
| `regular_pages` | - | *No description provided.* |
| `generated_pages` | - | *No description provided.* |
| `tag_pages` | - | *No description provided.* |
| `archive_pages` | - | *No description provided.* |
| `pagination_pages` | - | *No description provided.* |
| `total_assets` | - | *No description provided.* |
| `total_sections` | - | *No description provided.* |
| `taxonomies_count` | - | *No description provided.* |
| `build_time_ms` | - | *No description provided.* |
| `parallel` | - | *No description provided.* |
| `incremental` | - | *No description provided.* |
| `skipped` | - | *No description provided.* |
| `total_directives` | - | *No description provided.* |
| `directives_by_type` | - | *No description provided.* |
| `discovery_time_ms` | - | *No description provided.* |
| `taxonomy_time_ms` | - | *No description provided.* |
| `rendering_time_ms` | - | *No description provided.* |
| `assets_time_ms` | - | *No description provided.* |
| `postprocess_time_ms` | - | *No description provided.* |
| `health_check_time_ms` | - | *No description provided.* |
| `memory_rss_mb` | - | *No description provided.* |
| `memory_heap_mb` | - | *No description provided.* |
| `memory_peak_mb` | - | *No description provided.* |
| `cache_hits` | - | *No description provided.* |
| `cache_misses` | - | *No description provided.* |
| `time_saved_ms` | - | *No description provided.* |
| `menu_time_ms` | - | *No description provided.* |
| `related_posts_time_ms` | - | *No description provided.* |
| `fonts_time_ms` | - | *No description provided.* |
| `output_dir` | - | *No description provided.* |
| `changed_outputs` | - | *No description provided.* |
| `warnings` | - | *No description provided.* |
| `template_errors` | - | *No description provided.* |




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



#### `has_errors`
```python
def has_errors(self) -> bool
```


Check if build has any errors.



**Returns**


`bool`



#### `warnings_by_type`
```python
def warnings_by_type(self) -> dict[str, list]
```


Group warnings by type.



**Returns**


`dict[str, list]`



#### `__post_init__`
```python
def __post_init__(self)
```


Initialize mutable defaults.




#### `add_warning`
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







**Returns**


`None`



#### `add_template_error`
```python
def add_template_error(self, error: Any) -> None
```


Add a rich template error.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `error` | `Any` | - | *No description provided.* |







**Returns**


`None`



#### `add_directive`
```python
def add_directive(self, directive_type: str) -> None
```


Track a directive usage.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive_type` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```


Convert stats to dictionary.



**Returns**


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
*Generated by Bengal autodoc from `bengal/bengal/utils/build_stats.py`*

