
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
- **`root_path`** (`Path`)- **`config`** (`dict[str, Any]`)- **`pages`** (`list[Page]`)- **`sections`** (`list[Section]`)- **`assets`** (`list[Asset]`)- **`theme`** (`str | None`)- **`output_dir`** (`Path`)- **`build_time`** (`datetime | None`)- **`taxonomies`** (`dict[str, dict[str, list[Page]]]`)- **`menu`** (`dict[str, list[MenuItem]]`)- **`menu_builders`** (`dict[str, MenuBuilder]`)- **`menu_localized`** (`dict[str, dict[str, list[MenuItem]]]`)- **`menu_builders_localized`** (`dict[str, dict[str, MenuBuilder]]`)- **`current_language`** (`str | None`)- **`_regular_pages_cache`** (`list[Page] | None`)

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
- **`self`**

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
- **`self`**

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
- **`self`**

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
- **`self`**

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
#### `__post_init__`
```python
def __post_init__(self) -> None
```

Initialize site from configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

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
- **`self`**

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
- **`cls`**
- **`root_path`** (`Path`) - Root directory of the site
- **`config_path`** (`Path | None`) = `None` - Optional explicit path to config file (auto-detected from root_path if not provided)

:::{rubric} Returns
:class: rubric-returns
:::
`Site` - Configured Site instance with all settings loaded



```{warning}
In production/normal builds, use Site.from_config() instead! Passing config={} will override bengal.toml settings and use defaults.
```



:::{rubric} Examples
:class: rubric-examples
:::
```python
site = Site.from_config(Path('/path/to/site'))
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
- **`self`**
- **`content_dir`** (`Path | None`) = `None` - Content directory path (defaults to root_path/content)

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
- **`self`**
- **`assets_dir`** (`Path | None`) = `None` - Assets directory path (defaults to root_path/assets)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `build`
```python
def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False, quiet: bool = False, profile: BuildProfile = None, memory_optimized: bool = False, strict: bool = False, full_output: bool = False) -> BuildStats
```

Build the entire site.

Delegates to BuildOrchestrator for actual build process.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `parallel` | `bool` | `True` | Whether to use parallel processing |
| `incremental` | `bool` | `False` | Whether to perform incremental build (only changed files) |
| `verbose` | `bool` | `False` | Whether to show detailed build information |
| `quiet` | `bool` | `False` | Whether to suppress progress output (minimal output mode) |
| `profile` | `BuildProfile` | `None` | Build profile (writer, theme-dev, or dev) |
| `memory_optimized` | `bool` | `False` | Use streaming build for memory efficiency (best for 5K+ pages) |
| `strict` | `bool` | `False` | Whether to fail on warnings |
| `full_output` | `bool` | `False` | Show full traditional output instead of live progress |

:::{rubric} Returns
:class: rubric-returns
:::
`BuildStats` - BuildStats object with build statistics




---
#### `serve`
```python
def serve(self, host: str = 'localhost', port: int = 8000, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None
```

Start a development server.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `host` | `str` | `'localhost'` | Server host |
| `port` | `int` | `8000` | Server port |
| `watch` | `bool` | `True` | Whether to watch for file changes and rebuild |
| `auto_port` | `bool` | `True` | Whether to automatically find an available port if the specified one is in use |
| `open_browser` | `bool` | `False` | Whether to automatically open the browser |

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
- **`self`**

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
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
