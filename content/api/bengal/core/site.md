
---
title: "site"
type: "python-module"
source_file: "bengal/bengal/core/site.py"
line_number: 1
description: "Site Object - Represents the entire website and orchestrates the build."
---

# site
**Type:** Module
**Source:** [View source](bengal/bengal/core/site.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›site

Site Object - Represents the entire website and orchestrates the build.

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


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `root_path` | - | Root directory of the site |
| `config` | - | Site configuration dictionary (from bengal.toml or explicit) |
| `pages` | - | All pages in the site |
| `sections` | - | All sections in the site |
| `assets` | - | All assets in the site |
| `theme` | - | Theme name or path |
| `output_dir` | - | Output directory for built site |
| `build_time` | - | Timestamp of the last build |
| `taxonomies` | - | Collected taxonomies (tags, categories, etc.) |
| `menu` | - | *No description provided.* |
| `menu_builders` | - | *No description provided.* |
| `menu_localized` | - | *No description provided.* |
| `menu_builders_localized` | - | *No description provided.* |
| `current_language` | - | *No description provided.* |
| `data` | - | *No description provided.* |
| `_regular_pages_cache` | - | *No description provided.* |
| `_generated_pages_cache` | - | *No description provided.* |
| `_listable_pages_cache` | - | *No description provided.* |
| `_theme_obj` | - | *No description provided.* |
| `_query_registry` | - | *No description provided.* |
| `_section_registry` | - | *No description provided.* |
| `_config_hash` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `title` @property

```python
def title(self) -> str | None
```
Get site title from config.

#### `baseurl` @property

```python
def baseurl(self) -> str | None
```
Get site baseurl from config.

#### `author` @property

```python
def author(self) -> str | None
```
Get site author from config.

#### `config_hash` @property

```python
def config_hash(self) -> str
```
Get deterministic hash of the resolved configuration.

Used for automatic cache invalidation when configuration changes.
The hash captures the effective config state including:
- Base config from files
- Environment variable overrides
- Build profile settings

#### `theme_config` @property

```python
def theme_config(self) -> Theme
```
Get theme configuration object.

Available in templates as `site.theme_config` for accessing theme settings:
- site.theme_config.name: Theme name
- site.theme_config.default_appearance: Default light/dark/system mode
- site.theme_config.default_palette: Default color palette
- site.theme_config.config: Additional theme-specific config

#### `indexes` @property

```python
def indexes(self)
```
Access to query indexes for O(1) page lookups.

Provides pre-computed indexes for common page queries:
    site.indexes.section.get('blog')        # All blog posts
    site.indexes.author.get('Jane Smith')   # Posts by Jane
    site.indexes.category.get('tutorial')   # Tutorial pages
    site.indexes.date_range.get('2024')     # 2024 posts

Indexes are built during the build phase and provide O(1) lookups
instead of O(n) filtering. This makes templates scale to large sites.

#### `regular_pages` @property

```python
def regular_pages(self) -> list[Page]
```
Get only regular content pages (excludes generated taxonomy/archive pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.

#### `generated_pages` @property

```python
def generated_pages(self) -> list[Page]
```
Get only generated pages (taxonomy, archive, pagination pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.

#### `listable_pages` @property

```python
def listable_pages(self) -> list[Page]
```
Get pages that should appear in listings (excludes hidden pages).

This property respects the visibility system:
- Excludes pages with `hidden: true`
- Excludes pages with `visibility.listings: false`
- Excludes draft pages

Use this for:
- "Recent posts" sections
- Archive pages
- Category/tag listings
- Any public-facing page list

Use `site.pages` when you need ALL pages including hidden ones
(e.g., for sitemap generation where you filter separately).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.




## Methods



#### `title`
```python
def title(self) -> str | None
```


Get site title from config.



**Returns**


`str | None`



#### `baseurl`
```python
def baseurl(self) -> str | None
```


Get site baseurl from config.



**Returns**


`str | None`



#### `author`
```python
def author(self) -> str | None
```


Get site author from config.



**Returns**


`str | None`



#### `config_hash`
```python
def config_hash(self) -> str
```


Get deterministic hash of the resolved configuration.

Used for automatic cache invalidation when configuration changes.
The hash captures the effective config state including:
- Base config from files
- Environment variable overrides
- Build profile settings



**Returns**


`str` - 16-character hex string (truncated SHA-256)



#### `theme_config`
```python
def theme_config(self) -> Theme
```


Get theme configuration object.

Available in templates as `site.theme_config` for accessing theme settings:
- site.theme_config.name: Theme name
- site.theme_config.default_appearance: Default light/dark/system mode
- site.theme_config.default_palette: Default color palette
- site.theme_config.config: Additional theme-specific config



**Returns**


`Theme` - Theme configuration object



#### `indexes`
```python
def indexes(self)
```


Access to query indexes for O(1) page lookups.

Provides pre-computed indexes for common page queries:
    site.indexes.section.get('blog')        # All blog posts
    site.indexes.author.get('Jane Smith')   # Posts by Jane
    site.indexes.category.get('tutorial')   # Tutorial pages
    site.indexes.date_range.get('2024')     # 2024 posts

Indexes are built during the build phase and provide O(1) lookups
instead of O(n) filtering. This makes templates scale to large sites.

:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set blog_posts = site.indexes.section.get('blog') | resolve_pages %}
    {% for post in blog_posts %}
        <h2>{{ post.title }}</h2>
    {% endfor %}
```




#### `regular_pages`
```python
def regular_pages(self) -> list[Page]
```


Get only regular content pages (excludes generated taxonomy/archive pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.



**Returns**


`list[Page]` - List of regular Page objects (excludes tag pages, archive pages, etc.)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for page in site.regular_pages %}
        <article>{{ page.title }}</article>
    {% endfor %}
```




#### `generated_pages`
```python
def generated_pages(self) -> list[Page]
```


Get only generated pages (taxonomy, archive, pagination pages).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.



**Returns**


`list[Page]` - List of generated Page objects (tag pages, archive pages, pagination, etc.)
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Check if any tag pages need rebuilding
    for page in site.generated_pages:
        if page.metadata.get("type") == "tag":
            # ... process tag page
```




#### `listable_pages`
```python
def listable_pages(self) -> list[Page]
```


Get pages that should appear in listings (excludes hidden pages).

This property respects the visibility system:
- Excludes pages with `hidden: true`
- Excludes pages with `visibility.listings: false`
- Excludes draft pages

Use this for:
- "Recent posts" sections
- Archive pages
- Category/tag listings
- Any public-facing page list

Use `site.pages` when you need ALL pages including hidden ones
(e.g., for sitemap generation where you filter separately).

PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
The cache is automatically invalidated when pages are modified.



**Returns**


`list[Page]` - List of Page objects that should appear in public listings
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% for post in site.listable_pages | where('section', 'blog') | sort_by('date', reverse=true) | limit(5) %}
        <article>{{ post.title }}</article>
    {% endfor %}
```




#### `__post_init__`
```python
def __post_init__(self) -> None
```


Initialize site from configuration.



**Returns**


`None`




#### `invalidate_page_caches`
```python
def invalidate_page_caches(self) -> None
```


Invalidate cached page lists when pages are modified.

Call this after:
- Adding/removing pages
- Modifying page metadata (especially _generated flag or visibility)
- Any operation that changes the pages list

This ensures cached properties (regular_pages, generated_pages, listable_pages)
will recompute on next access.



**Returns**


`None`



#### `invalidate_regular_pages_cache`
```python
def invalidate_regular_pages_cache(self) -> None
```


Invalidate the regular_pages cache.

Call this after modifying the pages list or page metadata that affects
the _generated flag.



**Returns**


`None`



#### `from_config` @classmethod
```python
def from_config(cls, root_path: Path, config_path: Path | None = None, environment: str | None = None, profile: str | None = None) -> Site
```


Create a Site instance from configuration.

This is the PREFERRED way to create a Site - it loads configuration
from config/ directory or single config file and applies all settings.

Config Loading (Priority):
    1. config/ directory (if exists) - Environment-aware, profile-native
    2. bengal.yaml / bengal.toml (single file) - Traditional
    3. Auto-detect environment from platform (Netlify, Vercel, GitHub Actions)

Directory Structure (Recommended):
    config/
    ├── _default/          # Base config
    │   ├── site.yaml
    │   ├── build.yaml
    │   └── features.yaml
    ├── environments/      # Environment overrides
    │   ├── local.yaml
    │   ├── preview.yaml
    │   └── production.yaml
    └── profiles/          # Build profiles
        ├── writer.yaml
        ├── theme-dev.yaml
        └── dev.yaml

Important Config Sections:
    - [site]: title, baseurl, author, etc.
    - [build]: parallel, max_workers, incremental, etc.
    - [markdown]: parser selection ('mistune' recommended)
    - [features]: rss, sitemap, search, json, etc.
    - [taxonomies]: tags, categories, series


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `root_path` | `Path` | - | Root directory of the site (Path object) |
| `config_path` | `Path \| None` | - | Optional explicit path to config file (Path object) Only used for single-file configs, ignored if config/ exists |
| `environment` | `str \| None` | - | Environment name (e.g., 'production', 'local') Auto-detected if not specified (Netlify, Vercel, GitHub) |
| `profile` | `str \| None` | - | Profile name (e.g., 'writer', 'dev') Optional, only applies if config/ directory exists |







**Returns**


`Site` - Configured Site instance with all settings loaded
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Auto-detect config (prefers config/ directory)
    site = Site.from_config(Path('/path/to/site'))

    # Explicit environment
    site = Site.from_config(
        Path('/path/to/site'),
        environment='production'
    )

    # With profile
    site = Site.from_config(
        Path('/path/to/site'),
        environment='local',
        profile='dev'
    )

For Testing:
    If you need a Site for testing, use Site.for_testing() instead.
    It creates a minimal Site without requiring a config file.
```


**See Also:**- Site() - Direct constructor for advanced use cases,- Site.for_testing() - Factory for test sites

#### `for_testing` @classmethod
```python
def for_testing(cls, root_path: Path | None = None, config: dict | None = None) -> Site
```


Create a Site instance for testing without requiring a config file.

This is a convenience factory for unit tests and integration tests
that need a Site object with custom configuration.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `root_path` | `Path \| None` | - | Root directory of the test site (defaults to current dir) |
| `config` | `dict \| None` | - | Configuration dictionary (defaults to minimal config) |







**Returns**


`Site` - Configured Site instance ready for testing
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Minimal test site
    site = Site.for_testing()

    # Test site with custom root path
    site = Site.for_testing(Path('/tmp/test_site'))

    # Test site with custom config
    config = {'site': {'title': 'My Test Site'}}
    site = Site.for_testing(config=config)
```

:::{note}This bypasses config file loading, so you control all settings. Perfect for unit tests that need predictable behavior.:::




#### `discover_content`
```python
def discover_content(self, content_dir: Path | None = None) -> None
```


Discover all content (pages, sections) in the content directory.

Scans the content directory recursively, creating Page and Section
objects for all markdown files and organizing them into a hierarchy.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content_dir` | `Path \| None` | - | Content directory path (defaults to root_path/content) |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> site = Site.from_config(Path('/path/to/site'))
    >>> site.discover_content()
    >>> print(f"Found {len(site.pages)} pages in {len(site.sections)} sections")
```




#### `discover_assets`
```python
def discover_assets(self, assets_dir: Path | None = None) -> None
```


Discover all assets in the assets directory and theme assets.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `assets_dir` | `Path \| None` | - | Assets directory path (defaults to root_path/assets) |







**Returns**


`None`








#### `build`
```python
def build(self, parallel: bool = True, incremental: bool | None = None, verbose: bool = False, quiet: bool = False, profile: BuildProfile = None, memory_optimized: bool = False, strict: bool = False, full_output: bool = False, profile_templates: bool = False, use_pipeline: bool = False) -> BuildStats
```


Build the entire site.

Delegates to BuildOrchestrator for actual build process, or uses
the reactive dataflow pipeline if use_pipeline is True.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `parallel` | `bool` | `True` | Whether to use parallel processing |
| `incremental` | `bool \| None` | - | Whether to perform incremental build (only changed files) |
| `verbose` | `bool` | `False` | Whether to show detailed build information |
| `quiet` | `bool` | `False` | Whether to suppress progress output (minimal output mode) |
| `profile` | `BuildProfile` | - | Build profile (writer, theme-dev, or dev) |
| `memory_optimized` | `bool` | `False` | Use streaming build for memory efficiency (best for 5K+ pages) |
| `strict` | `bool` | `False` | Whether to fail on warnings |
| `full_output` | `bool` | `False` | Show full traditional output instead of live progress |
| `profile_templates` | `bool` | `False` | Enable template profiling for performance analysis |
| `use_pipeline` | `bool` | `False` | Use reactive dataflow pipeline (experimental) |







**Returns**


`BuildStats` - BuildStats object with build statistics




#### `serve`
```python
def serve(self, host: str = 'localhost', port: int = 5173, watch: bool = True, auto_port: bool = True, open_browser: bool = False, use_pipeline: bool = False) -> None
```


Start a development server.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `host` | `str` | `'localhost'` | Server host |
| `port` | `int` | `5173` | Server port |
| `watch` | `bool` | `True` | Whether to watch for file changes and rebuild |
| `auto_port` | `bool` | `True` | Whether to automatically find an available port if the specified one is in use |
| `open_browser` | `bool` | `False` | Whether to automatically open the browser |
| `use_pipeline` | `bool` | `False` | Whether to use reactive dataflow pipeline for builds |







**Returns**


`None`



#### `clean`
```python
def clean(self) -> None
```


Clean the output directory by removing all generated files.

Useful for starting fresh or troubleshooting build issues.



**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> site = Site.from_config(Path('/path/to/site'))
    >>> site.clean()  # Remove all files in public/
    >>> site.build()  # Rebuild from scratch
```






#### `__repr__`
```python
def __repr__(self) -> str
```


*No description provided.*



**Returns**


`str`



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



**Returns**


`None`




#### `get_section_by_path`
```python
def get_section_by_path(self, path: Path | str) -> Section | None
```


Look up a section by its path (O(1) operation).

Uses the section registry for fast lookups without scanning the section tree.
Paths are normalized before lookup to handle case-insensitive filesystems
and symlinks consistently.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `path` | `Path \| str` | - | Section path (absolute, relative to content/, or relative to root) |







**Returns**


`Section | None` - Section object if found, None otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> section = site.get_section_by_path("blog")
    >>> section = site.get_section_by_path("docs/guides")
    >>> section = site.get_section_by_path(Path("/site/content/blog"))

Performance:
    O(1) lookup after registry is built (via register_sections)
```




#### `register_sections`
```python
def register_sections(self) -> None
```


Build the section registry for path-based lookups.

Scans all sections recursively and populates _section_registry with
normalized path → Section mappings. This enables O(1) section lookups
without scanning the section hierarchy.

Must be called after discover_content() and before any code that uses
get_section_by_path() or page._section property.

Build ordering invariant:
    1. discover_content()       → Creates Page/Section objects
    2. register_sections()      → Builds path→section registry (THIS)
    3. setup_page_references()  → Sets page._section via property setter
    4. apply_cascades()         → Lookups resolve via registry
    5. generate_urls()          → Uses correct section hierarchy

Performance:
    O(n) where n = number of sections. Typical: < 10ms for 1000 sections.



**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> site.discover_content()
    >>> site.register_sections()  # Build registry
    >>> section = site.get_section_by_path("blog")  # O(1) lookup
```



---
*Generated by Bengal autodoc from `bengal/bengal/core/site.py`*

