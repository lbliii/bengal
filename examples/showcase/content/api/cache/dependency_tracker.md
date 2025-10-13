
---
title: "cache.dependency_tracker"
type: python-module
source_file: "bengal/cache/dependency_tracker.py"
css_class: api-content
description: "Dependency Tracker - Tracks dependencies during the build process."
---

# cache.dependency_tracker

Dependency Tracker - Tracks dependencies during the build process.

---

## Classes

### `DependencyTracker`


Tracks dependencies between pages and their templates, partials, and config files.

This is used during the build process to populate the BuildCache with dependency
information, which is then used for incremental builds.

Thread-safe: Uses thread-local storage to track current page per thread.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, cache: BuildCache)
```

Initialize the dependency tracker.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`cache`** (`BuildCache`) - BuildCache instance to store dependencies in





---
#### `start_page`
```python
def start_page(self, page_path: Path) -> None
```

Mark the start of processing a page (thread-safe).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_path`** (`Path`) - Path to the page being processed

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `track_template`
```python
def track_template(self, template_path: Path) -> None
```

Record that the current page depends on a template (thread-safe).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_path`** (`Path`) - Path to the template file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `track_partial`
```python
def track_partial(self, partial_path: Path) -> None
```

Record that the current page depends on a partial/include (thread-safe).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`partial_path`** (`Path`) - Path to the partial file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `track_config`
```python
def track_config(self, config_path: Path) -> None
```

Record that the current page depends on the config file (thread-safe).
All pages depend on config, so this marks it as a global dependency.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`config_path`** (`Path`) - Path to the config file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `track_asset`
```python
def track_asset(self, asset_path: Path) -> None
```

Record an asset file (for cache invalidation).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`asset_path`** (`Path`) - Path to the asset file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `track_taxonomy`
```python
def track_taxonomy(self, page_path: Path, tags: set[str]) -> None
```

Record taxonomy (tags/categories) dependencies.

When a page's tags change, tag pages need to be regenerated.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_path`** (`Path`) - Path to the page
- **`tags`** (`set[str]`) - Set of tags/categories for this page

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `end_page`
```python
def end_page(self) -> None
```

Mark the end of processing a page (thread-safe).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `get_changed_files`
```python
def get_changed_files(self, root_path: Path) -> set[Path]
```

Get all files that have changed since the last build.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`root_path`** (`Path`) - Root path of the site

:::{rubric} Returns
:class: rubric-returns
:::
`set[Path]` - Set of paths that have changed




---
#### `find_new_files`
```python
def find_new_files(self, current_files: set[Path]) -> set[Path]
```

Find files that are new (not in cache).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`current_files`** (`set[Path]`) - Set of current file paths

:::{rubric} Returns
:class: rubric-returns
:::
`set[Path]` - Set of new file paths




---
#### `find_deleted_files`
```python
def find_deleted_files(self, current_files: set[Path]) -> set[Path]
```

Find files that were deleted (in cache but not on disk).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`current_files`** (`set[Path]`) - Set of current file paths

:::{rubric} Returns
:class: rubric-returns
:::
`set[Path]` - Set of deleted file paths




---
