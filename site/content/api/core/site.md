
---
title: "core.site"
type: python-module
source_file: "bengal/core/site.py"
css_class: api-content
description: "Site Object - Represents the entire website and orchestrates the build."
---

# core.site

Site Object - Represents the entire website and orchestrates the build.

---

## Classes

### `Site`


Represents the entire website and orchestrates the build process.

Creation:
    Recommended: Site.from_config(root_path)
        - Loads configuration from bengal.toml
        - Applies all settings automatically
        - Use for production builds and CLI

    Direct instantiation: Site(root_path=path, config=config)
        - For unit testing with controlled state
        - For programmatic config manipulation
        - Advanced use case only

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 17 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `root_path`
  - `Path`
  - Root directory of the site
* - `config`
  - `dict[str, Any]`
  - Site configuration dictionary (from bengal.toml or explicit)
* - `pages`
  - `list[Page]`
  - All pages in the site
* - `sections`
  - `list[Section]`
  - All sections in the site
* - `assets`
  - `list[Asset]`
  - All assets in the site
* - `theme`
  - `str | None`
  - Theme name or path
* - `output_dir`
  - `Path`
  - Output directory for built site
* - `build_time`
  - `datetime | None`
  - Timestamp of the last build
* - `taxonomies`
  - `dict[str, dict[str, list[Page]]]`
  - Collected taxonomies (tags, categories, etc.)
* - `menu`
  - `dict[str, list[MenuItem]]`
  - -
* - `menu_builders`
  - `dict[str, MenuBuilder]`
  - -
* - `menu_localized`
  - `dict[str, dict[str, list[MenuItem]]]`
  - -
* - `menu_builders_localized`
  - `dict[str, dict[str, MenuBuilder]]`
  - -
* - `current_language`
  - `str | None`
  - -
* - `data`
  - `Any`
  - -
* - `_regular_pages_cache`
  - `list[Page] | None`
  - -
* - `_generated_pages_cache`
  - `list[Page] | None`
  - -
:::

::::

:::{rubric} Properties
:class: rubric-properties
:::
#### `title` @property

```python
@property
def title(self) -> str | None
```

Get site title from config.
#### `baseurl` @property

```python
@property
def baseurl(self) -> str | None
```

Get site baseurl from config.
#### `author` @property

```python
@property
def author(self) -> str | None
```

Get site author from config.
#### `regular_pages` @property

```python
@property
def regular_pages(self) -> list[Page]
```

Get only regular content pages (excludes generated taxonomy/archive pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.
#### `generated_pages` @property

```python
@property
def generated_pages(self) -> list[Page]
```

Get only generated pages (taxonomy, archive, pagination pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.

:::{rubric} Methods
:class: rubric-methods
:::
#### `title`
```python
def title(self) -> str | None
```

Get site title from config.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `baseurl`
```python
def baseurl(self) -> str | None
```

Get site baseurl from config.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `author`
```python
def author(self) -> str | None
```

Get site author from config.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str | None`




---
#### `regular_pages`
```python
def regular_pages(self) -> list[Page]
```

Get only regular content pages (excludes generated taxonomy/archive pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Page]` - List of regular Page objects (excludes tag pages, archive pages, etc.)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for page in site.regular_pages %}
```


---
#### `generated_pages`
```python
def generated_pages(self) -> list[Page]
```

Get only generated pages (taxonomy, archive, pagination pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Page]` - List of generated Page objects (tag pages, archive pages, pagination, etc.)




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Check if any tag pages need rebuilding
```


---
#### `__post_init__`
```python
def __post_init__(self) -> None
```

Initialize site from configuration.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `invalidate_page_caches`
```python
def invalidate_page_caches(self) -> None
```

Invalidate cached page lists when pages are modified.

Call this after:
- Adding/removing pages
- Modifying page metadata (especially _generated flag)
- Any operation that changes the pages list

This ensures cached properties (regular_pages, generated_pages) will
recompute on next access.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `invalidate_regular_pages_cache`
```python
def invalidate_regular_pages_cache(self) -> None
```

Invalidate the regular_pages cache.

Call this after modifying the pages list or page metadata that affects
the _generated flag.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `from_config` @classmethod
```python
def from_config(cls, root_path: Path, config_path: Path | None = None) -> Site
```

Create a Site instance from a configuration file.

This is the PREFERRED way to create a Site - it loads configuration
from bengal.toml (or bengal.yaml) and applies all settings properly.

Config Loading:
    1. Searches for config file: bengal.toml, bengal.yaml, bengal.yml
    2. Parses and validates configuration
    3. Flattens nested sections for easy access
    4. Returns Site with all settings applied

Important Config Sections:
    - [site]: title, baseurl, author, etc.
    - [build]: parallel, max_workers, incremental, etc.
    - [markdown]: parser selection ('mistune' recommended)
    - [features]: syntax_highlighting, search, etc.
    - [taxonomies]: tags, categories, series



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
* - `cls`
  - -
  - -
  - -
* - `root_path`
  - `Path`
  - -
  - Root directory of the site (Path object) The folder containing bengal.toml/bengal.yaml
* - `config_path`
  - `Path | None`
  - `None`
  - Optional explicit path to config file (Path object) If not provided, searches in root_path for: bengal.toml → bengal.yaml → bengal.yml
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Site` - Configured Site instance with all settings loaded




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Auto-detect config file in site directory
```


**See Also:** - Site() - Direct constructor for advanced use cases, - Site.for_testing() - Factory for test sites
---
#### `for_testing` @classmethod
```python
def for_testing(cls, root_path: Path | None = None, config: dict | None = None) -> Site
```

Create a Site instance for testing without requiring a config file.

This is a convenience factory for unit tests and integration tests
that need a Site object with custom configuration.



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
* - `cls`
  - -
  - -
  - -
* - `root_path`
  - `Path | None`
  - `None`
  - Root directory of the test site (defaults to current dir)
* - `config`
  - `dict | None`
  - `None`
  - Configuration dictionary (defaults to minimal config)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Site` - Configured Site instance ready for testing


```{note}
This bypasses config file loading, so you control all settings. Perfect for unit tests that need predictable behavior.
```




:::{rubric} Examples
:class: rubric-examples
:::
```python
# Minimal test site
```


---
#### `discover_content`
```python
def discover_content(self, content_dir: Path | None = None) -> None
```

Discover all content (pages, sections) in the content directory.

Scans the content directory recursively, creating Page and Section
objects for all markdown files and organizing them into a hierarchy.



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
* - `self`
  - -
  - -
  - -
* - `content_dir`
  - `Path | None`
  - `None`
  - Content directory path (defaults to root_path/content)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> site = Site.from_config(Path('/path/to/site'))
    >>> site.discover_content()
    >>> print(f"Found {len(site.pages)} pages in {len(site.sections)} sections")
```


---
#### `discover_assets`
```python
def discover_assets(self, assets_dir: Path | None = None) -> None
```

Discover all assets in the assets directory and theme assets.



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
* - `self`
  - -
  - -
  - -
* - `assets_dir`
  - `Path | None`
  - `None`
  - Assets directory path (defaults to root_path/assets)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `build`
```python
def build(self, parallel: bool = True, incremental: bool | None = None, verbose: bool = False, quiet: bool = False, profile: BuildProfile = None, memory_optimized: bool = False, strict: bool = False, full_output: bool = False) -> BuildStats
```

Build the entire site.

Delegates to BuildOrchestrator for actual build process.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 9 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `parallel`
  - `bool`
  - `True`
  - Whether to use parallel processing
* - `incremental`
  - `bool | None`
  - `None`
  - Whether to perform incremental build (only changed files)
* - `verbose`
  - `bool`
  - `False`
  - Whether to show detailed build information
* - `quiet`
  - `bool`
  - `False`
  - Whether to suppress progress output (minimal output mode)
* - `profile`
  - `BuildProfile`
  - `None`
  - Build profile (writer, theme-dev, or dev)
* - `memory_optimized`
  - `bool`
  - `False`
  - Use streaming build for memory efficiency (best for 5K+ pages)
* - `strict`
  - `bool`
  - `False`
  - Whether to fail on warnings
* - `full_output`
  - `bool`
  - `False`
  - Show full traditional output instead of live progress
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`BuildStats` - BuildStats object with build statistics




---
#### `serve`
```python
def serve(self, host: str = 'localhost', port: int = 5173, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None
```

Start a development server.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 6 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `host`
  - `str`
  - `'localhost'`
  - Server host
* - `port`
  - `int`
  - `5173`
  - Server port
* - `watch`
  - `bool`
  - `True`
  - Whether to watch for file changes and rebuild
* - `auto_port`
  - `bool`
  - `True`
  - Whether to automatically find an available port if the specified one is in use
* - `open_browser`
  - `bool`
  - `False`
  - Whether to automatically open the browser
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `clean`
```python
def clean(self) -> None
```

Clean the output directory by removing all generated files.

Useful for starting fresh or troubleshooting build issues.



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> site = Site.from_config(Path('/path/to/site'))
    >>> site.clean()  # Remove all files in public/
    >>> site.build()  # Rebuild from scratch
```


---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str`




---
#### `reset_ephemeral_state`
```python
def reset_ephemeral_state(self) -> None
```

Clear ephemeral/derived state that should not persist between builds.

This method is intended for long-lived Site instances (e.g., dev server)
to avoid stale object references across rebuilds.

Persistence contract:
- Persist: root_path, config, theme, output_dir, build_time
- Clear: pages, sections, assets
- Clear derived: taxonomies, menu, menu_builders, xref_index (if present)
- Clear caches: cached page lists



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
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
