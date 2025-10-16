
---
title: "utils.paths"
type: python-module
source_file: "bengal/utils/paths.py"
css_class: api-content
description: "Path utilities for Bengal SSG.  Provides consistent path management for temporary files, logs, and profiles."
---

# utils.paths

Path utilities for Bengal SSG.

Provides consistent path management for temporary files, logs, and profiles.

---

## Classes

### `BengalPaths`


Manages Bengal's directory structure for generated files.

Directory Structure:
- .bengal-cache.json         → output_dir/.bengal-cache.json (build cache)
- .bengal-cache/templates/   → output_dir/.bengal-cache/templates/ (Jinja2 bytecode)
- .bengal-build.log          → source_dir/.bengal-build.log (build logs)
- .bengal/profiles/          → source_dir/.bengal/profiles/ (performance profiles)

This provides a clean separation between:
1. Build outputs (public/) - deployable files
2. Build metadata (public/.bengal-cache*) - cache files
3. Development files (source/.bengal*) - logs, profiles




:::{rubric} Methods
:class: rubric-methods
:::
#### `get_profile_dir` @staticmethod
```python
def get_profile_dir(source_dir: Path) -> Path
```

Get the directory for storing performance profiles.



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
* - `source_dir`
  - `Path`
  - -
  - Source directory (where content/ and bengal.toml live)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to .bengal/profiles/ directory




---
#### `get_log_dir` @staticmethod
```python
def get_log_dir(source_dir: Path) -> Path
```

Get the directory for storing build logs.



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
* - `source_dir`
  - `Path`
  - -
  - Source directory (where content/ and bengal.toml live)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to .bengal/logs/ directory




---
#### `get_build_log_path` @staticmethod
```python
def get_build_log_path(source_dir: Path, custom_path: Path | None = None) -> Path
```

Get the path for the build log file.



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
* - `source_dir`
  - `Path`
  - -
  - Source directory
* - `custom_path`
  - `Path | None`
  - `None`
  - Optional custom path specified by user
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to build log file




---
#### `get_profile_path` @staticmethod
```python
def get_profile_path(source_dir: Path, custom_path: Path | None = None, filename: str = 'build_profile.stats') -> Path
```

Get the path for a performance profile file.



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
* - `source_dir`
  - `Path`
  - -
  - Source directory
* - `custom_path`
  - `Path | None`
  - `None`
  - Optional custom path specified by user
* - `filename`
  - `str`
  - `'build_profile.stats'`
  - Default filename for the profile
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to profile file




---
#### `get_cache_path` @staticmethod
```python
def get_cache_path(output_dir: Path) -> Path
```

Get the path for the build cache file.



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
  - `Path`
  - -
  - Output directory (public/)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to .bengal-cache.json




---
#### `get_template_cache_dir` @staticmethod
```python
def get_template_cache_dir(output_dir: Path) -> Path
```

Get the directory for Jinja2 bytecode cache.



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
  - `Path`
  - -
  - Output directory (public/)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Path` - Path to .bengal-cache/templates/




---
