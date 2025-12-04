
---
title: "watcher"
type: "python-module"
source_file: "bengal/bengal/pipeline/watcher.py"
line_number: 1
description: "File watcher for pipeline-based incremental rebuilds. This module provides file watching infrastructure for the reactive pipeline, enabling automatic incremental rebuilds when files change. Key Compon..."
---

# watcher
**Type:** Module
**Source:** [View source](bengal/bengal/pipeline/watcher.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[pipeline](/api/bengal/pipeline/) ›watcher

File watcher for pipeline-based incremental rebuilds.

This module provides file watching infrastructure for the reactive pipeline,
enabling automatic incremental rebuilds when files change.

Key Components:
    - FileWatcher: Watches directories for changes with debouncing
    - WatchEvent: Represents a single file change event
    - PipelineRebuildHandler: Triggers pipeline rebuilds on changes

Usage:
    >>> from bengal.pipeline.watcher import FileWatcher
    >>> watcher = FileWatcher(content_dir, debounce_ms=300)
    >>> watcher.on_change(lambda events: rebuild(events))
    >>> watcher.start()

Integration:
    This module integrates with the reactive pipeline system to enable
    watch mode builds. When files change, only affected items are
    reprocessed through the pipeline.

Related:
    - bengal/server/build_handler.py - Existing dev server handler
    - bengal/pipeline/build.py - Pipeline factories
    - bengal/pipeline/cache.py - Cache invalidation on changes

## Classes




### `ChangeType`


**Inherits from:**`Enum`Type of file change event.












### `WatchEvent`


A single file change event.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `path` | - | Path to the changed file |
| `change_type` | - | Type of change (created, modified, deleted, moved) |
| `timestamp` | - | When the change occurred |
| `old_path` | - | Previous path for moved files (None otherwise) |




:::{rubric} Properties
:class: rubric-properties
:::



#### `is_content` @property

```python
def is_content(self) -> bool
```
True if this is a content file change.

#### `is_template` @property

```python
def is_template(self) -> bool
```
True if this is a template file change.

#### `is_asset` @property

```python
def is_asset(self) -> bool
```
True if this is an asset file change.

#### `is_config` @property

```python
def is_config(self) -> bool
```
True if this is a config file change.




## Methods



#### `is_content`
```python
def is_content(self) -> bool
```


True if this is a content file change.



**Returns**


`bool`



#### `is_template`
```python
def is_template(self) -> bool
```


True if this is a template file change.



**Returns**


`bool`



#### `is_asset`
```python
def is_asset(self) -> bool
```


True if this is an asset file change.



**Returns**


`bool`



#### `is_config`
```python
def is_config(self) -> bool
```


True if this is a config file change.



**Returns**


`bool`




### `WatchBatch`


A batch of file changes collected during debounce period.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `events` | - | List of change events |
| `started_at` | - | When the batch started |
| `finalized_at` | - | When the batch was finalized (debounce expired) |




:::{rubric} Properties
:class: rubric-properties
:::



#### `changed_paths` @property

```python
def changed_paths(self) -> list[Path]
```
Get unique paths of all changed files.

#### `has_content_changes` @property

```python
def has_content_changes(self) -> bool
```
True if batch contains content file changes.

#### `has_template_changes` @property

```python
def has_template_changes(self) -> bool
```
True if batch contains template file changes.

#### `has_config_changes` @property

```python
def has_config_changes(self) -> bool
```
True if batch contains config file changes.

#### `needs_full_rebuild` @property

```python
def needs_full_rebuild(self) -> bool
```
True if changes require full rebuild (config or templates).

#### `content_paths` @property

```python
def content_paths(self) -> list[Path]
```
Get paths of changed content files.




## Methods



#### `changed_paths`
```python
def changed_paths(self) -> list[Path]
```


Get unique paths of all changed files.



**Returns**


`list[Path]`



#### `has_content_changes`
```python
def has_content_changes(self) -> bool
```


True if batch contains content file changes.



**Returns**


`bool`



#### `has_template_changes`
```python
def has_template_changes(self) -> bool
```


True if batch contains template file changes.



**Returns**


`bool`



#### `has_config_changes`
```python
def has_config_changes(self) -> bool
```


True if batch contains config file changes.



**Returns**


`bool`



#### `needs_full_rebuild`
```python
def needs_full_rebuild(self) -> bool
```


True if changes require full rebuild (config or templates).



**Returns**


`bool`



#### `content_paths`
```python
def content_paths(self) -> list[Path]
```


Get paths of changed content files.



**Returns**


`list[Path]`



#### `add`
```python
def add(self, event: WatchEvent) -> None
```


Add an event to the batch.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `event` | `WatchEvent` | - | *No description provided.* |







**Returns**


`None`



#### `finalize`
```python
def finalize(self) -> None
```


Mark batch as finalized.



**Returns**


`None`




### `FileWatcher`


Watches directories for file changes with debouncing.

Collects file change events and batches them together, waiting for
a debounce period before notifying handlers. This prevents rapid
successive changes from triggering multiple rebuilds.









## Methods



#### `__init__`
```python
def __init__(self, watch_dirs: list[Path] | None = None) -> None
```


Initialize file watcher.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `watch_dirs` | `list[Path] \| None` | - | Directories to watch (default: current directory) |







**Returns**


`None`



#### `on_change`
```python
def on_change(self, handler: Callable[[WatchBatch], None]) -> None
```


Register a handler to be called when files change.

The handler receives a WatchBatch containing all changes
that occurred during the debounce period.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `handler` | `Callable[[WatchBatch], None]` | - | Function to call with WatchBatch |







**Returns**


`None`



#### `start`
```python
def start(self) -> None
```


Start watching for file changes.

Uses watchdog library for efficient file system monitoring.



**Returns**


`None`



#### `stop`
```python
def stop(self) -> None
```


Stop watching for file changes.



**Returns**


`None`




### `PipelineWatcher`


Watches files and triggers pipeline-based incremental rebuilds.

Combines FileWatcher with the reactive pipeline to automatically
rebuild only affected content when files change.









## Methods



#### `__init__`
```python
def __init__(self, site: Any) -> None
```


Initialize pipeline watcher.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Any` | - | Bengal Site instance |







**Returns**


`None`



#### `start`
```python
def start(self) -> None
```


Start watching and rebuilding.



**Returns**


`None`



#### `stop`
```python
def stop(self) -> None
```


Stop watching.



**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/pipeline/watcher.py`*

