
---
title: "core.asset"
type: python-module
source_file: "bengal/core/asset.py"
css_class: api-content
description: "Asset Object - Handles images, CSS, JS, and other static files."
---

# core.asset

Asset Object - Handles images, CSS, JS, and other static files.

---

## Classes

### `Asset`


Represents a static asset file (image, CSS, JS, etc.).

Attributes:
    source_path: Path to the source asset file
    output_path: Path where the asset will be copied
    asset_type: Type of asset (css, js, image, font, etc.)
    fingerprint: Hash-based fingerprint for cache busting
    minified: Whether the asset has been minified
    optimized: Whether the asset has been optimized
    bundled: Whether CSS @import statements have been inlined

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`source_path`** (`Path`)- **`output_path`** (`Path | None`)- **`asset_type`** (`str | None`)- **`fingerprint`** (`str | None`)- **`minified`** (`bool`)- **`optimized`** (`bool`)- **`bundled`** (`bool`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__post_init__`
```python
def __post_init__(self) -> None
```

Determine asset type from file extension.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `is_css_entry_point`
```python
def is_css_entry_point(self) -> bool
```

Check if this asset is a CSS entry point that should be bundled.

Entry points are CSS files named 'style.css' at any level.
These files typically contain @import statements that pull in other CSS.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if this is a CSS entry point (e.g., style.css)




---
#### `is_css_module`
```python
def is_css_module(self) -> bool
```

Check if this asset is a CSS module (imported by an entry point).

CSS modules are CSS files that are NOT entry points.
They should be bundled into entry points, not copied separately.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if this is a CSS module (e.g., components/buttons.css)




---
#### `minify`
```python
def minify(self) -> 'Asset'
```

Minify the asset (for CSS and JS).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`'Asset'` - Self for method chaining




---
#### `bundle_css`
```python
def bundle_css(self) -> str
```

Bundle CSS by resolving all @import statements recursively.

This creates a single CSS file from an entry point that has @imports.
Works without any external dependencies.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Bundled CSS content as a string




---
#### `hash`
```python
def hash(self) -> str
```

Generate a hash-based fingerprint for the asset.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Hash string (first 8 characters of SHA256)




---
#### `optimize`
```python
def optimize(self) -> 'Asset'
```

Optimize the asset (especially for images).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`'Asset'` - Self for method chaining




---
#### `copy_to_output`
```python
def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path
```

Copy the asset to the output directory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`output_dir`** (`Path`) - Output directory path
- **`use_fingerprint`** (`bool`) = `True` - Whether to include fingerprint in filename

:::{rubric} Returns
:class: rubric-returns
:::
`Path` - Path where the asset was copied




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
