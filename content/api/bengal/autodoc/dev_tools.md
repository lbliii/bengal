
---
title: "dev_tools"
type: "python-module"
source_file: "bengal/bengal/autodoc/dev_tools.py"
line_number: 1
description: "Template development and validation tools. Provides utilities for template development, testing, and debugging including sample data generation, performance profiling, and hot-reloading support."
---

# dev_tools
**Type:** Module
**Source:** [View source](bengal/bengal/autodoc/dev_tools.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[autodoc](/api/bengal/autodoc/) ›dev_tools

Template development and validation tools.

Provides utilities for template development, testing, and debugging including
sample data generation, performance profiling, and hot-reloading support.

## Classes




### `TemplatePerformanceMetrics`


Performance metrics for template rendering.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `template_name` | - | *No description provided.* |
| `render_time_ms` | - | *No description provided.* |
| `content_size_bytes` | - | *No description provided.* |
| `cache_hit` | - | *No description provided.* |
| `error_count` | - | *No description provided.* |
| `timestamp` | - | *No description provided.* |







## Methods



#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```


Convert to dictionary for serialization.



**Returns**


`dict[str, Any]`




### `SampleDataGenerator`


Generate sample data for testing templates.









## Methods



#### `__init__`
```python
def __init__(self)
```


*No description provided.*




#### `generate_python_module`
```python
def generate_python_module(self, name: str = 'sample_module') -> DocElement
```


Generate sample Python module element.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | `'sample_module'` | *No description provided.* |







**Returns**


`DocElement`



#### `generate_cli_command`
```python
def generate_cli_command(self, name: str = 'sample-command') -> DocElement
```


Generate sample CLI command element.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | `'sample-command'` | *No description provided.* |







**Returns**


`DocElement`



#### `generate_openapi_endpoint`
```python
def generate_openapi_endpoint(self, path: str = '/api/users', method: str = 'GET') -> DocElement
```


Generate sample OpenAPI endpoint element.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `path` | `str` | `'/api/users'` | *No description provided.* |
| `method` | `str` | `'GET'` | *No description provided.* |







**Returns**


`DocElement`



#### `generate_sample_config`
```python
def generate_sample_config(self) -> dict[str, Any]
```


Generate sample configuration for template testing.



**Returns**


`dict[str, Any]`




### `TemplateDebugger`


Debug template rendering with detailed error information.









## Methods



#### `__init__`
```python
def __init__(self, renderer: SafeTemplateRenderer, validator: TemplateValidator)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | `SafeTemplateRenderer` | - | *No description provided.* |
| `validator` | `TemplateValidator` | - | *No description provided.* |








#### `debug_template`
```python
def debug_template(self, template_name: str, context: dict[str, Any]) -> dict[str, Any]
```


Debug template rendering with comprehensive information.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template to debug |
| `context` | `dict[str, Any]` | - | Template context |







**Returns**


`dict[str, Any]` - Debug information including validation, rendering results, and errors



#### `get_debug_report`
```python
def get_debug_report(self) -> str
```


Generate human-readable debug report.



**Returns**


`str`



#### `export_debug_session`
```python
def export_debug_session(self, session_index: int, output_path: Path) -> None
```


Export debug session to JSON file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `session_index` | `int` | - | *No description provided.* |
| `output_path` | `Path` | - | *No description provided.* |







**Returns**


`None`




### `TemplateProfiler`


Profile template rendering performance.









## Methods



#### `__init__`
```python
def __init__(self)
```


*No description provided.*




#### `profile_template`
```python
def profile_template(self, template_name: str, renderer: SafeTemplateRenderer, context: dict[str, Any], cache_hit: bool = False) -> TemplatePerformanceMetrics
```


Profile template rendering performance.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template to profile |
| `renderer` | `SafeTemplateRenderer` | - | Template renderer |
| `context` | `dict[str, Any]` | - | Template context |
| `cache_hit` | `bool` | `False` | Whether this was a cache hit |







**Returns**


`TemplatePerformanceMetrics` - Performance metrics



#### `get_performance_summary`
```python
def get_performance_summary(self) -> dict[str, Any]
```


Get performance summary statistics.



**Returns**


`dict[str, Any]`



#### `export_metrics`
```python
def export_metrics(self, output_path: Path) -> None
```


Export performance metrics to JSON file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_path` | `Path` | - | *No description provided.* |







**Returns**


`None`




### `TemplateHotReloader`


Hot-reload templates during development.









## Methods



#### `__init__`
```python
def __init__(self, template_dirs: list[Path])
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_dirs` | `list[Path]` | - | *No description provided.* |








#### `register_reload_callback`
```python
def register_reload_callback(self, callback: callable) -> None
```


Register callback to be called when templates are reloaded.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `callback` | `callable` | - | *No description provided.* |







**Returns**


`None`



#### `check_for_changes`
```python
def check_for_changes(self) -> list[str]
```


Check for template file changes.



**Returns**


`list[str]` - List of changed template files



#### `trigger_reload`
```python
def trigger_reload(self, changed_files: list[str]) -> None
```


Trigger reload callbacks for changed files.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_files` | `list[str]` | - | *No description provided.* |







**Returns**


`None`



#### `start_watching`
```python
def start_watching(self, check_interval: float = 1.0) -> None
```


Start watching for template changes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `check_interval` | `float` | `1.0` | How often to check for changes (seconds) |







**Returns**


`None`

## Functions



### `create_development_tools`


```python
def create_development_tools(renderer: SafeTemplateRenderer, validator: TemplateValidator, template_dirs: list[Path]) -> dict[str, Any]
```



Create complete set of development tools.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | `SafeTemplateRenderer` | - | Safe template renderer |
| `validator` | `TemplateValidator` | - | Template validator |
| `template_dirs` | `list[Path]` | - | Template directories to watch |







**Returns**


`dict[str, Any]` - Dictionary of development tools



---
*Generated by Bengal autodoc from `bengal/bengal/autodoc/dev_tools.py`*

