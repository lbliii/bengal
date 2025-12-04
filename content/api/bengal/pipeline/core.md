
---
title: "core"
type: "python-module"
source_file: "bengal/bengal/pipeline/core.py"
line_number: 1
description: "Core stream primitives for the reactive dataflow pipeline. This module defines the foundational types for Bengal\'s reactive build system: - StreamKey: Unique identifier for cache-friendly stream items..."
---

# core
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/core.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›core

Core stream primitives for the reactive dataflow pipeline.

This module defines the foundational types for Bengal's reactive build system:

- StreamKey: Unique identifier for cache-friendly stream items
- StreamItem: A single item flowing through the pipeline with metadata
- Stream: Abstract base class for all stream types

Design Principles:
    - Streams are lazy: transformations define a computation graph
      but don't execute until materialized
    - Items have keys for automatic caching and invalidation
    - Version tracking enables fine-grained incremental builds

Related:
    - bengal/pipeline/streams.py - Concrete stream implementations
    - bengal/pipeline/builder.py - Pipeline builder API

## Classes




### `StreamKey`


Unique identifier for a stream item.

StreamKeys enable:
- Cache lookup across builds
- Version-based invalidation
- Dependency tracking



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `source` | - | Name of the stream that produced this item |
| `id` | - | Unique identifier within the source stream |
| `version` | - | Content hash or timestamp for invalidation |







## Methods



#### `__str__`
```python
def __str__(self) -> str
```


Human-readable key representation.



**Returns**


`str`



#### `with_version`
```python
def with_version(self, version: str) -> StreamKey
```


Create new key with updated version.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `version` | `str` | - | *No description provided.* |







**Returns**


`StreamKey`




### `StreamItem`


A single item flowing through the pipeline.

Each item carries:
- A unique key for caching
- The actual value
- Timestamp for debugging/metrics


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `key` | - | Unique identifier for caching and invalidation |
| `value` | - | The actual data payload |
| `produced_at` | - | Unix timestamp when this item was created |







## Methods



#### `create` @classmethod
```python
def create(cls, source: str, id: str, value: T, version: str | None = None) -> StreamItem[T]
```


Create a stream item with automatic version computation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `str` | - | Name of the producing stream |
| `id` | `str` | - | Unique identifier within the stream |
| `value` | `T` | - | The actual data |
| `version` | `str \| None` | - | Content version (computed from value hash if not provided) |







**Returns**


`StreamItem[T]` - New StreamItem instance




#### `map_value`
```python
def map_value(self, fn: Callable[[T], U], new_source: str) -> StreamItem[U]
```


Transform the value while preserving the item structure.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `fn` | `Callable[[T], U]` | - | Transformation function |
| `new_source` | `str` | - | Source name for the new item |







**Returns**


`StreamItem[U]` - New StreamItem with transformed value




### `Stream`


**Inherits from:**`ABC`Abstract base class for reactive streams.

Streams are lazy - they define a computation graph but don't
execute until `run()` or `materialize()` is called.

Subclasses must implement `_produce()` to generate items.



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `name` | - | Human-readable name for debugging and caching |







## Methods



#### `__init__`
```python
def __init__(self, name: str | None = None) -> None
```


Initialize stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str \| None` | - | Optional name (defaults to class name) |







**Returns**


`None`




#### `iterate`
```python
def iterate(self) -> Iterator[StreamItem[T]]
```


Iterate over stream items with caching.

Items are cached by key. If an item with the same key and version
is requested again, the cached value is returned.



**Returns**


`Iterator[StreamItem[T]]`



#### `materialize`
```python
def materialize(self) -> list[T]
```


Execute stream and return all values.

This is a terminal operation that triggers stream execution.



**Returns**


`list[T]` - List of all values produced by the stream



#### `clear_cache`
```python
def clear_cache(self) -> None
```


Clear the stream's internal cache.



**Returns**


`None`



#### `disable_cache`
```python
def disable_cache(self) -> Stream[T]
```


Disable caching for this stream.



**Returns**


`Stream[T]`



#### `map`
```python
def map(self, fn: Callable[[T], U], name: str | None = None) -> MapStream[T, U]
```


Transform each item in the stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `fn` | `Callable[[T], U]` | - | Transformation function applied to each value |
| `name` | `str \| None` | - | Optional name for the new stream |







**Returns**


`MapStream[T, U]` - New stream with transformed values
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stream.map(lambda x: x * 2)
```




#### `filter`
```python
def filter(self, predicate: Callable[[T], bool], name: str | None = None) -> FilterStream[T]
```


Filter items based on predicate.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `predicate` | `Callable[[T], bool]` | - | Function returning True for items to keep |
| `name` | `str \| None` | - | Optional name for the new stream |







**Returns**


`FilterStream[T]` - New stream with filtered values
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stream.filter(lambda x: x > 0)
```




#### `flat_map`
```python
def flat_map(self, fn: Callable[[T], Iterator[U]], name: str | None = None) -> FlatMapStream[T, U]
```


Transform each item into multiple items.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `fn` | `Callable[[T], Iterator[U]]` | - | Function returning iterator of new values |
| `name` | `str \| None` | - | Optional name for the new stream |







**Returns**


`FlatMapStream[T, U]` - New stream with flattened values
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stream.flat_map(lambda x: [x, x + 1])
```




#### `collect`
```python
def collect(self, name: str | None = None) -> CollectStream[T]
```


Collect all items into a single list.

This is a barrier operation - all upstream items must complete
before the collected list is emitted.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str \| None` | - | Optional name for the new stream |







**Returns**


`CollectStream[T]` - Stream emitting a single list of all values
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stream.collect()  # Emits [item1, item2, ...]
```




#### `combine`
```python
def combine(self, *others: Stream[Any]) -> CombineStream
```


Combine with other streams.

Collects this stream and all others, then emits a tuple of results.



**Returns**


`CombineStream` - Stream emitting tuple of combined results
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pages.combine(nav).map(lambda args: render(*args))
```




#### `parallel`
```python
def parallel(self, workers: int = 4) -> ParallelStream[T]
```


Mark stream for parallel execution.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `workers` | `int` | `4` | Number of worker threads |







**Returns**


`ParallelStream[T]` - Stream marked for parallel execution



#### `cache`
```python
def cache(self, key_fn: Callable[[T], str] | None = None) -> CachedStream[T]
```


Add explicit caching with custom key function.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key_fn` | `Callable[[T], str] \| None` | - | Optional function to compute cache key from value |







**Returns**


`CachedStream[T]` - Stream with explicit caching



#### `for_each`
```python
def for_each(self, fn: Callable[[T], None]) -> None
```


Execute function for each item (side effect).

This is a terminal operation that triggers stream execution.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `fn` | `Callable[[T], None]` | - | Function to call for each value |







**Returns**


`None`



#### `run`
```python
def run(self) -> int
```


Execute stream and return count of items processed.

This is a terminal operation that triggers stream execution.



**Returns**


`int` - Number of items processed



#### `first`
```python
def first(self) -> T | None
```


Get first item from stream.



**Returns**


`T | None` - First value or None if stream is empty



#### `count`
```python
def count(self) -> int
```


Count items in stream.



**Returns**


`int` - Number of items



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/core.py`*

