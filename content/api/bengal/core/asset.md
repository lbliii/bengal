
---
title: "asset"
type: "python-module"
source_file: "bengal/bengal/core/asset.py"
line_number: 1
description: "Asset handling for static files (images, CSS, JS, fonts, etc.). Provides asset discovery, processing (minification, optimization, bundling), fingerprinting for cache-busting, and atomic output writing..."
---

# asset
**Type:** Module
**Source:** [View source](bengal/bengal/core/asset.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[core](/api/bengal/core/) ›asset

Asset handling for static files (images, CSS, JS, fonts, etc.).

Provides asset discovery, processing (minification, optimization, bundling),
fingerprinting for cache-busting, and atomic output writing. Handles CSS
nesting transformation, CSS bundling via @import resolution, and image
optimization.

Key Concepts:
    - Entry points: CSS/JS files that serve as bundle roots (style.css, bundle.js)
    - Modules: CSS/JS files imported by entry points (bundled, not copied separately)
    - Fingerprinting: Hash-based cache-busting via filename suffixes
    - Atomic writes: Crash-safe file writing using temporary files

Related Modules:
    - bengal.orchestration.asset: Asset discovery and orchestration
    - bengal.utils.css_minifier: CSS minification implementation
    - bengal.utils.atomic_write: Atomic file writing utilities

See Also:
    - bengal/core/asset.py:Asset class for asset representation

## Classes




### `Asset`


Represents a static asset file (image, CSS, JS, etc.).


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `source_path` | - | Path to the source asset file |
| `output_path` | - | Path where the asset will be copied |
| `asset_type` | - | Type of asset (css, js, image, font, etc.) |
| `fingerprint` | - | Hash-based fingerprint for cache busting |
| `minified` | - | Whether the asset has been minified |
| `optimized` | - | Whether the asset has been optimized |
| `bundled` | - | Whether CSS @import statements have been inlined |
| `logical_path` | - | *No description provided.* |







## Methods



#### `__post_init__`
```python
def __post_init__(self) -> None
```


Determine asset type from file extension.



**Returns**


`None`




#### `is_css_entry_point`
```python
def is_css_entry_point(self) -> bool
```


Check if this asset is a CSS entry point that should be bundled.

Entry points are CSS files named 'style.css' at any level.
These files typically contain @import statements that pull in other CSS.



**Returns**


`bool` - True if this is a CSS entry point (e.g., style.css)



#### `is_css_module`
```python
def is_css_module(self) -> bool
```


Check if this asset is a CSS module (imported by an entry point).

CSS modules are CSS files that are NOT entry points.
They should be bundled into entry points, not copied separately.



**Returns**


`bool` - True if this is a CSS module (e.g., components/buttons.css)



#### `is_js_entry_point`
```python
def is_js_entry_point(self) -> bool
```


Check if this asset is a JS entry point for bundling.

The JS bundle entry point is named 'bundle.js' and contains
all theme JavaScript concatenated together.



**Returns**


`bool` - True if this is a JS bundle entry point



#### `is_js_module`
```python
def is_js_module(self) -> bool
```


Check if this asset is a JS module (should be bundled, not copied separately).

JS modules are individual JS files that will be bundled into bundle.js.
They should not be copied separately when bundling is enabled.

Excludes:
- Third-party libraries (*.min.js) - copied separately for caching
- The bundle entry point itself



**Returns**


`bool` - True if this is a JS module that should be bundled



#### `minify`
```python
def minify(self) -> Asset
```


Minify the asset (for CSS and JS).



**Returns**


`Asset` - Self for method chaining



#### `bundle_css`
```python
def bundle_css(self) -> str
```


Bundle CSS by resolving all @import statements recursively.

This creates a single CSS file from an entry point that has @imports.
Works without any external dependencies.

Preserves @layer blocks when bundling @import statements.



**Returns**


`str` - Bundled CSS content as a string






#### `hash`
```python
def hash(self) -> str
```


Generate a hash-based fingerprint for the asset.



**Returns**


`str` - Hash string (first 8 characters of SHA256)



#### `optimize`
```python
def optimize(self) -> Asset
```


Optimize the asset (especially for images).



**Returns**


`Asset` - Self for method chaining




#### `copy_to_output`
```python
def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path
```


Copy the asset to the output directory.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_dir` | `Path` | - | Output directory path |
| `use_fingerprint` | `bool` | `True` | Whether to include fingerprint in filename |







**Returns**


`Path` - Path where the asset was copied




#### `__repr__`
```python
def __repr__(self) -> str
```


*No description provided.*



**Returns**


`str`



---
*Generated by Bengal autodoc from `bengal/bengal/core/asset.py`*
