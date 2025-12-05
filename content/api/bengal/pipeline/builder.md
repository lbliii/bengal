
---
title: "builder"
type: "python-module"
source_file: "bengal/bengal/pipeline/builder.py"
line_number: 1
description: "Pipeline builder for constructing declarative build pipelines. The Pipeline class provides a fluent API for defining build pipelines as a series of transformations on data streams. Example: >>> pipeli..."
---

# builder
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/builder.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›builder

Pipeline builder for constructing declarative build pipelines.

The Pipeline class provides a fluent API for defining build pipelines
as a series of transformations on data streams.

Example:
    >>> pipeline = (
    ...     Pipeline("bengal-build")
    ...     .source("files", lambda: discover_files(content_dir))
    ...     .filter("markdown", lambda f: f.suffix == ".md")
    ...     .map("parse", parse_markdown)
    ...     .map("page", create_page)
    ...     .parallel(workers=4)
    ...     .collect("all_pages")
    ...     .map("with_nav", lambda pages: (pages, build_nav(pages)))
    ...     .flat_map("render", lambda args: render_pages(*args))
    ...     .for_each("write", write_output)
    ... )
    >>> result = pipeline.run()

Related:
    - bengal/pipeline/core.py - Base Stream class
    - bengal/pipeline/streams.py - Stream implementations

## Classes




### `PipelineResult`


Result of pipeline execution.

Contains metrics and any errors encountered during execution.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | Pipeline name |
| `items_processed` | - | Number of items that flowed through |
| `elapsed_seconds` | - | Total execution time |
| `errors` | - | List of (stage_name, item_key, exception) tuples |
| `stages_executed` | - | Names of stages that ran |




:::{rubric} Properties
:class: rubric-properties
:::



#### `success` @property

```python
def success(self) -> bool
```
True if no errors occurred.

#### `items_per_second` @property

```python
def items_per_second(self) -> float
```
Processing rate.




## Methods



#### `success`
```python
def success(self) -> bool
```


True if no errors occurred.



**Returns**


`bool`



#### `items_per_second`
```python
def items_per_second(self) -> float
```


Processing rate.



**Returns**


`float`



#### `__str__`
```python
def __str__(self) -> str
```


Human-readable summary.



**Returns**


`str`




### `Pipeline`


Builder for constructing build pipelines.

Pipelines are defined declaratively using a fluent API.
Execution is deferred until `run()` is called.



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | Pipeline name for logging and debugging |







## Methods



#### `__init__`
```python
def __init__(self, name: str = 'pipeline') -> None
```


Initialize pipeline.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | `'pipeline'` | Pipeline name for logging |







**Returns**


`None`



#### `source`
```python
def source(self, name: str, producer: Callable[[], Any]) -> Pipeline
```


Add a source stage that produces initial items.

The producer function can return:
- A list of items
- An iterator/generator of items
- Any iterable


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Stage name for debugging and caching |
| `producer` | `Callable[[], Any]` | - | Function that returns items |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.source("files", lambda: Path(".").glob("**/*.md"))
```




#### `map`
```python
def map(self, name: str, fn: Callable[[Any], Any]) -> Pipeline
```


Add a map transformation stage.

Each input item is transformed by the function.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Stage name |
| `fn` | `Callable[[Any], Any]` | - | Transformation function |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.map("parse", parse_markdown)
```




#### `filter`
```python
def filter(self, name: str, predicate: Callable[[Any], bool]) -> Pipeline
```


Add a filter stage.

Only items where predicate returns True pass through.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Stage name |
| `predicate` | `Callable[[Any], bool]` | - | Filter function |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.filter("markdown", lambda f: f.suffix == ".md")
```




#### `flat_map`
```python
def flat_map(self, name: str, fn: Callable[[Any], Iterator[Any]]) -> Pipeline
```


Add a flat_map stage.

Each input item is transformed into multiple output items.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Stage name |
| `fn` | `Callable[[Any], Iterator[Any]]` | - | Function returning iterator of new items |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.flat_map("split", lambda page: page.sections)
```




#### `collect`
```python
def collect(self, name: str = 'collect') -> Pipeline
```


Collect all items into a single list.

This is a barrier - all upstream items must complete
before the list is emitted.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | `'collect'` | Stage name |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.collect("all_pages")
```




#### `combine`
```python
def combine(self, *other_pipelines: Pipeline) -> Pipeline
```


Combine with other pipelines.

Collects this pipeline and all others, emitting a tuple.



**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> content_pipeline.combine(nav_pipeline, name="render_context")
```




#### `parallel`
```python
def parallel(self, workers: int = 4) -> Pipeline
```


Enable parallel execution for the current stage.

Effective for I/O-bound operations.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `workers` | `int` | `4` | Number of worker threads |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.map("render", render_page).parallel(workers=8)
```




#### `cache`
```python
def cache(self, key_fn: Callable[[Any], str] | None = None) -> Pipeline
```


Add explicit caching with optional custom key function.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key_fn` | `Callable[[Any], str] \| None` | - | Optional function to compute cache key |







**Returns**


`Pipeline` - Self for chaining



#### `for_each`
```python
def for_each(self, name: str, fn: Callable[[Any], None]) -> Pipeline
```


Add a side-effect stage.

The function is called for each item but doesn't transform it.
Typically used for writing output.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Stage name |
| `fn` | `Callable[[Any], None]` | - | Side-effect function |







**Returns**


`Pipeline` - Self for chaining
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pipeline.for_each("write", write_to_disk)
```




#### `run`
```python
def run(self) -> PipelineResult
```


Execute the pipeline.

Iterates through all items, executing side effects,
and returns execution metrics.



**Returns**


`PipelineResult` - PipelineResult with metrics and any errors
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If pipeline has no stages





#### `__repr__`
```python
def __repr__(self) -> str
```


Debug representation.



**Returns**


`str`



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/builder.py`*
