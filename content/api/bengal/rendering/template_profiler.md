
---
title: "template_profiler"
type: "python-module"
source_file: "bengal/bengal/rendering/template_profiler.py"
line_number: 1
description: "Template profiling infrastructure for Bengal SSG. Provides timing instrumentation for template rendering to identify performance bottlenecks and optimize template code. Usage: # Enable via CLI bengal ..."
---

# template_profiler
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/template_profiler.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›template_profiler

Template profiling infrastructure for Bengal SSG.

Provides timing instrumentation for template rendering to identify
performance bottlenecks and optimize template code.

Usage:
    # Enable via CLI
    bengal build --profile-templates

    # Access report
    report = template_engine.get_template_profile()

Architecture:
    TemplateProfiler collects timing data for:
    - Individual template renders (base.html, partials/*.html)
    - Template function calls (get_menu_lang, get_auto_nav, etc.)
    - Include/extends resolution

    Data is thread-safe and aggregated across parallel renders.

See Also:
    - plan/active/rfc-template-performance-optimization.md
    - bengal/rendering/template_engine.py

## Classes




### `TemplateTimings`


Timing statistics for a single template.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | *No description provided.* |
| `render_times` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `count` @property

```python
def count(self) -> int
```
Number of times template was rendered.

#### `total_ms` @property

```python
def total_ms(self) -> float
```
Total render time in milliseconds.

#### `avg_ms` @property

```python
def avg_ms(self) -> float
```
Average render time in milliseconds.

#### `min_ms` @property

```python
def min_ms(self) -> float
```
Minimum render time in milliseconds.

#### `max_ms` @property

```python
def max_ms(self) -> float
```
Maximum render time in milliseconds.




## Methods



#### `count`
```python
def count(self) -> int
```


Number of times template was rendered.



**Returns**


`int`



#### `total_ms`
```python
def total_ms(self) -> float
```


Total render time in milliseconds.



**Returns**


`float`



#### `avg_ms`
```python
def avg_ms(self) -> float
```


Average render time in milliseconds.



**Returns**


`float`



#### `min_ms`
```python
def min_ms(self) -> float
```


Minimum render time in milliseconds.



**Returns**


`float`



#### `max_ms`
```python
def max_ms(self) -> float
```


Maximum render time in milliseconds.



**Returns**


`float`




### `FunctionTimings`


Timing statistics for a template function.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | *No description provided.* |
| `call_times` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `count` @property

```python
def count(self) -> int
```
Number of times function was called.

#### `total_ms` @property

```python
def total_ms(self) -> float
```
Total execution time in milliseconds.

#### `avg_ms` @property

```python
def avg_ms(self) -> float
```
Average execution time in milliseconds.




## Methods



#### `count`
```python
def count(self) -> int
```


Number of times function was called.



**Returns**


`int`



#### `total_ms`
```python
def total_ms(self) -> float
```


Total execution time in milliseconds.



**Returns**


`float`



#### `avg_ms`
```python
def avg_ms(self) -> float
```


Average execution time in milliseconds.



**Returns**


`float`




### `TemplateProfiler`


Collects and reports template rendering performance data.

Thread-safe implementation supports parallel builds.









## Methods



#### `__init__`
```python
def __init__(self) -> None
```


Initialize the profiler.



**Returns**


`None`



#### `enable`
```python
def enable(self) -> None
```


Enable profiling.



**Returns**


`None`



#### `disable`
```python
def disable(self) -> None
```


Disable profiling.



**Returns**


`None`



#### `is_enabled`
```python
def is_enabled(self) -> bool
```


Check if profiling is enabled.



**Returns**


`bool`



#### `start_template`
```python
def start_template(self, template_name: str) -> None
```


Mark start of template render.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template being rendered |







**Returns**


`None`



#### `end_template`
```python
def end_template(self, template_name: str) -> None
```


Mark end of template render and record timing.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template that finished rendering |







**Returns**


`None`



#### `record_function_call`
```python
def record_function_call(self, func_name: str, duration: float) -> None
```


Record a template function call timing.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `func_name` | `str` | - | Name of the function |
| `duration` | `float` | - | Execution time in seconds |







**Returns**


`None`



#### `get_report`
```python
def get_report(self) -> dict[str, Any]
```


Generate profiling report.



**Returns**


`dict[str, Any]` - Dictionary with template and function timing statistics



#### `reset`
```python
def reset(self) -> None
```


Clear all collected timing data.



**Returns**


`None`




### `ProfiledTemplate`


Wrapper around Jinja2 Template that adds render timing.

Delegates all attribute access to the wrapped template while
intercepting render() calls for profiling.









## Methods



#### `__init__`
```python
def __init__(self, template: Template, profiler: TemplateProfiler) -> None
```


Initialize the profiled template.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template` | `Template` | - | Jinja2 Template to wrap |
| `profiler` | `TemplateProfiler` | - | TemplateProfiler for recording timings |







**Returns**


`None`



#### `__getattr__`
```python
def __getattr__(self, name: str) -> Any
```


Delegate attribute access to wrapped template.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |







**Returns**


`Any`



#### `render`
```python
def render(self, *args, **kwargs) -> str
```


Render template with timing instrumentation.



**Returns**


`str` - Rendered template string

## Functions



### `profile_function`


```python
def profile_function(profiler: TemplateProfiler, func_name: str) -> Callable
```



Decorator factory for profiling template functions.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `profiler` | `TemplateProfiler` | - | TemplateProfiler instance |
| `func_name` | `str` | - | Name to record for this function |







**Returns**


`Callable` - Decorator that wraps function with timing
:::{rubric} Examples
:class: rubric-examples
:::


```python
@profile_function(profiler, "get_menu_lang")
    def get_menu_lang(menu_name, lang):
        ...
```





### `format_profile_report`


```python
def format_profile_report(report: dict[str, Any], top_n: int = 20) -> str
```



Format profiling report for CLI output.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `report` | `dict[str, Any]` | - | Profiling report from TemplateProfiler.get_report() |
| `top_n` | `int` | `20` | Number of top items to show per category |







**Returns**


`str` - Formatted report string for display




### `get_profiler`


```python
def get_profiler() -> TemplateProfiler | None
```



Get the global template profiler instance.



**Returns**


`TemplateProfiler | None`




### `enable_profiling`


```python
def enable_profiling() -> TemplateProfiler
```



Enable template profiling globally.



**Returns**


`TemplateProfiler` - The global TemplateProfiler instance




### `disable_profiling`


```python
def disable_profiling() -> None
```



Disable template profiling globally.



**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/template_profiler.py`*
