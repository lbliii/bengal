
---
title: "streams"
type: "python-module"
source_file: "bengal/bengal/pipeline/streams.py"
line_number: 1
description: "Concrete stream implementations for the reactive dataflow pipeline. This module provides: - SourceStream: Entry point that produces items from a function - MapStream: Transforms each item - FilterStre..."
---

# streams
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/streams.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›streams

Concrete stream implementations for the reactive dataflow pipeline.

This module provides:
- SourceStream: Entry point that produces items from a function
- MapStream: Transforms each item
- FilterStream: Filters items based on predicate
- FlatMapStream: Transforms each item into multiple items
- CollectStream: Collects all items into a list
- CombineStream: Combines multiple streams
- ParallelStream: Marks stream for parallel execution
- CachedStream: Adds explicit disk caching

Related:
    - bengal/pipeline/core.py - Base Stream class and StreamItem
    - bengal/pipeline/builder.py - Pipeline builder API

## Classes




### `SourceStream`


**Inherits from:**`Stream[T]`Stream that produces items from a source function.

This is the entry point for pipelines - it produces initial items
that flow through subsequent transformations.









## Methods



#### `__init__`
```python
def __init__(self, producer: Callable[[], Iterator[StreamItem[T]]], name: str = 'source') -> None
```


Initialize source stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `producer` | `Callable[[], Iterator[StreamItem[T]]]` | - | Function that yields StreamItems |
| `name` | `str` | `'source'` | Stream name for debugging and caching |







**Returns**


`None`




### `MapStream`


**Inherits from:**`Stream[U]`Stream that transforms each item.

Each input item is transformed by the provided function,
producing one output item per input.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], fn: Callable[[T], U], name: str = 'map') -> None
```


Initialize map stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `fn` | `Callable[[T], U]` | - | Transformation function |
| `name` | `str` | `'map'` | Stream name |







**Returns**


`None`




### `FilterStream`


**Inherits from:**`Stream[T]`Stream that filters items based on predicate.

Only items where predicate returns True are passed through.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], predicate: Callable[[T], bool], name: str = 'filter') -> None
```


Initialize filter stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `predicate` | `Callable[[T], bool]` | - | Function returning True for items to keep |
| `name` | `str` | `'filter'` | Stream name |







**Returns**


`None`




### `FlatMapStream`


**Inherits from:**`Stream[U]`Stream that transforms each item into multiple items.

The transformation function returns an iterator, and all
results are flattened into the output stream.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], fn: Callable[[T], Iterator[U]], name: str = 'flat_map') -> None
```


Initialize flat_map stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `fn` | `Callable[[T], Iterator[U]]` | - | Function returning iterator of new values |
| `name` | `str` | `'flat_map'` | Stream name |







**Returns**


`None`




### `CollectStream`


**Inherits from:**`Stream[list[T]]`Stream that collects all items into a single list.

This is a barrier operation - all upstream items must complete
before the collected list is emitted as a single item.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], name: str = 'collect') -> None
```


Initialize collect stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `name` | `str` | `'collect'` | Stream name |







**Returns**


`None`




### `CombineStream`


**Inherits from:**`Stream[tuple[Any, ...]]`Stream that combines multiple streams.

Collects all upstream streams and emits a single tuple containing
the collected results from each stream.









## Methods



#### `__init__`
```python
def __init__(self, *upstreams: Stream[Any]) -> None
```


Initialize combine stream.



**Returns**


`None`




### `ParallelStream`


**Inherits from:**`Stream[T]`Stream that executes upstream transformations in parallel.

Uses a thread pool to process items concurrently.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], workers: int = 4) -> None
```


Initialize parallel stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `workers` | `int` | `4` | Number of worker threads |







**Returns**


`None`




### `CachedStream`


**Inherits from:**`Stream[T]`Stream with explicit caching using custom key function.

Allows specifying a custom key function for cache lookups,
enabling more control over cache behavior.









## Methods



#### `__init__`
```python
def __init__(self, upstream: Stream[T], key_fn: Callable[[T], str] | None = None) -> None
```


Initialize cached stream.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `upstream` | `Stream[T]` | - | Source stream |
| `key_fn` | `Callable[[T], str] \| None` | - | Optional function to compute cache key from value |







**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/streams.py`*
