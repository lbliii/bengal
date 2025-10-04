---
title: "core.site"
layout: api-reference
type: python-module
source_file: "../../bengal/core/site.py"
---

# core.site

Site Object - Represents the entire website and orchestrates the build.

**Source:** `../../bengal/core/site.py`

---

## Classes

### Site


Represents the entire website and orchestrates the build process.

Attributes:
    root_path: Root directory of the site
    config: Site configuration dictionary
    pages: All pages in the site
    sections: All sections in the site
    assets: All assets in the site
    theme: Theme name or path
    output_dir: Output directory for built site
    build_time: Timestamp of the last build
    taxonomies: Collected taxonomies (tags, categories, etc.)

::: info
This is a dataclass.
:::

**Attributes:**

- **root_path** (`Path`)- **config** (`Dict[str, Any]`)- **pages** (`List[Page]`)- **sections** (`List[Section]`)- **assets** (`List[Asset]`)- **theme** (`Optional[str]`)- **output_dir** (`Path`)- **build_time** (`Optional[datetime]`)- **taxonomies** (`Dict[str, Dict[str, List[Page]]]`)- **menu** (`Dict[str, List[MenuItem]]`)- **menu_builders** (`Dict[str, MenuBuilder]`)
**Properties:**

#### regular_pages

```python
@property
def regular_pages(self) -> List[Page]
```

Get only regular content pages (excludes generated taxonomy/archive pages).

**Methods:**

#### regular_pages

```python
def regular_pages(self) -> List[Page]
```

Get only regular content pages (excludes generated taxonomy/archive pages).

**Parameters:**

- **self**

**Returns:** `List[Page]` - List of regular Page objects (excludes tag pages, archive pages, etc.)


**Examples:**

{% for page in site.regular_pages %}





---
#### __post_init__

```python
def __post_init__(self) -> None
```

Initialize site from configuration.

**Parameters:**

- **self**

**Returns:** `None`






---
#### from_config

```python
def from_config(cls, root_path: Path, config_path: Optional[Path] = None) -> 'Site'
```

Create a Site instance from a configuration file.

**Parameters:**

- **cls**
- **root_path** (`Path`) - Root directory of the site
- **config_path** (`Optional[Path]`) = `None` - Optional path to config file (auto-detected if not provided)

**Returns:** `'Site'` - Configured Site instance






---
#### discover_content

```python
def discover_content(self, content_dir: Optional[Path] = None) -> None
```

Discover all content (pages, sections) in the content directory.

**Parameters:**

- **self**
- **content_dir** (`Optional[Path]`) = `None` - Content directory path (defaults to root_path/content)

**Returns:** `None`






---
#### discover_assets

```python
def discover_assets(self, assets_dir: Optional[Path] = None) -> None
```

Discover all assets in the assets directory and theme assets.

**Parameters:**

- **self**
- **assets_dir** (`Optional[Path]`) = `None` - Assets directory path (defaults to root_path/assets)

**Returns:** `None`






---
#### build

```python
def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False) -> BuildStats
```

Build the entire site.

Delegates to BuildOrchestrator for actual build process.

**Parameters:**

- **self**
- **parallel** (`bool`) = `True` - Whether to use parallel processing
- **incremental** (`bool`) = `False` - Whether to perform incremental build (only changed files)
- **verbose** (`bool`) = `False` - Whether to show detailed build information

**Returns:** `BuildStats` - BuildStats object with build statistics






---
#### serve

```python
def serve(self, host: str = 'localhost', port: int = 8000, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None
```

Start a development server.

**Parameters:**

- **self**
- **host** (`str`) = `'localhost'` - Server host
- **port** (`int`) = `8000` - Server port
- **watch** (`bool`) = `True` - Whether to watch for file changes and rebuild
- **auto_port** (`bool`) = `True` - Whether to automatically find an available port if the specified one is in use
- **open_browser** (`bool`) = `False` - Whether to automatically open the browser

**Returns:** `None`






---
#### clean

```python
def clean(self) -> None
```

Clean the output directory.

**Parameters:**

- **self**

**Returns:** `None`






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


