---
title: "core.asset"
layout: api-reference
type: python-module
source_file: "../../bengal/core/asset.py"
---

# core.asset

Asset Object - Handles images, CSS, JS, and other static files.

**Source:** `../../bengal/core/asset.py`

---

## Classes

### Asset


Represents a static asset file (image, CSS, JS, etc.).

Attributes:
    source_path: Path to the source asset file
    output_path: Path where the asset will be copied
    asset_type: Type of asset (css, js, image, font, etc.)
    fingerprint: Hash-based fingerprint for cache busting
    minified: Whether the asset has been minified
    optimized: Whether the asset has been optimized

::: info
This is a dataclass.
:::

**Attributes:**

- **source_path** (`Path`)- **output_path** (`Optional[Path]`)- **asset_type** (`Optional[str]`)- **fingerprint** (`Optional[str]`)- **minified** (`bool`)- **optimized** (`bool`)

**Methods:**

#### __post_init__

```python
def __post_init__(self) -> None
```

Determine asset type from file extension.

**Parameters:**

- **self**

**Returns:** `None`






---
#### minify

```python
def minify(self) -> 'Asset'
```

Minify the asset (for CSS and JS).

**Parameters:**

- **self**

**Returns:** `'Asset'` - Self for method chaining






---
#### hash

```python
def hash(self) -> str
```

Generate a hash-based fingerprint for the asset.

**Parameters:**

- **self**

**Returns:** `str` - Hash string (first 8 characters of SHA256)






---
#### optimize

```python
def optimize(self) -> 'Asset'
```

Optimize the asset (especially for images).

**Parameters:**

- **self**

**Returns:** `'Asset'` - Self for method chaining






---
#### copy_to_output

```python
def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path
```

Copy the asset to the output directory.

**Parameters:**

- **self**
- **output_dir** (`Path`) - Output directory path
- **use_fingerprint** (`bool`) = `True` - Whether to include fingerprint in filename

**Returns:** `Path` - Path where the asset was copied






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


