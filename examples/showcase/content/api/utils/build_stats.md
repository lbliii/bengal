---
title: "utils.build_stats"
layout: api-reference
type: python-module
source_file: "../../bengal/utils/build_stats.py"
---

# utils.build_stats

Build statistics display with colorful output and ASCII art.

**Source:** `../../bengal/utils/build_stats.py`

---

## Classes

### BuildWarning


A build warning or error.

::: info
This is a dataclass.
:::

**Attributes:**

- **file_path** (`str`)- **message** (`str`)- **warning_type** (`str`)
**Properties:**

#### short_path

```python
@property
def short_path(self) -> str
```

Get shortened path for display.

**Methods:**

#### short_path

```python
def short_path(self) -> str
```

Get shortened path for display.

**Parameters:**

- **self**

**Returns:** `str`






---

### BuildStats


Container for build statistics.

::: info
This is a dataclass.
:::

**Attributes:**

- **total_pages** (`int`)- **regular_pages** (`int`)- **generated_pages** (`int`)- **tag_pages** (`int`)- **archive_pages** (`int`)- **pagination_pages** (`int`)- **total_assets** (`int`)- **total_sections** (`int`)- **taxonomies_count** (`int`)- **build_time_ms** (`float`)- **parallel** (`bool`)- **incremental** (`bool`)- **skipped** (`bool`)- **total_directives** (`int`)- **directives_by_type** (`Dict[str, int]`)- **discovery_time_ms** (`float`)- **taxonomy_time_ms** (`float`)- **rendering_time_ms** (`float`)- **assets_time_ms** (`float`)- **postprocess_time_ms** (`float`)- **warnings** (`list`)- **template_errors** (`list`)
**Properties:**

#### has_errors

```python
@property
def has_errors(self) -> bool
```

Check if build has any errors.
#### warnings_by_type

```python
@property
def warnings_by_type(self) -> Dict[str, list]
```

Group warnings by type.

**Methods:**

#### has_errors

```python
def has_errors(self) -> bool
```

Check if build has any errors.

**Parameters:**

- **self**

**Returns:** `bool`






---
#### warnings_by_type

```python
def warnings_by_type(self) -> Dict[str, list]
```

Group warnings by type.

**Parameters:**

- **self**

**Returns:** `Dict[str, list]`






---
#### __post_init__

```python
def __post_init__(self)
```

Initialize mutable defaults.

**Parameters:**

- **self**







---
#### add_warning

```python
def add_warning(self, file_path: str, message: str, warning_type: str = 'other') -> None
```

Add a warning to the build.

**Parameters:**

- **self**
- **file_path** (`str`)
- **message** (`str`)
- **warning_type** (`str`) = `'other'`

**Returns:** `None`






---
#### add_template_error

```python
def add_template_error(self, error: Any) -> None
```

Add a rich template error.

**Parameters:**

- **self**
- **error** (`Any`)

**Returns:** `None`






---
#### add_directive

```python
def add_directive(self, directive_type: str) -> None
```

Track a directive usage.

**Parameters:**

- **self**
- **directive_type** (`str`)

**Returns:** `None`






---
#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert stats to dictionary.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]`






---


## Functions

### format_time

```python
def format_time(ms: float) -> str
```

Format milliseconds for display.

**Parameters:**

- **ms** (`float`)

**Returns:** `str`





---
### display_warnings

```python
def display_warnings(stats: BuildStats) -> None
```

Display grouped warnings and errors.

**Parameters:**

- **stats** (`BuildStats`) - Build statistics with warnings

**Returns:** `None`





---
### display_build_stats

```python
def display_build_stats(stats: BuildStats, show_art: bool = True, output_dir: str = None) -> None
```

Display build statistics in a colorful table.

**Parameters:**

- **stats** (`BuildStats`) - Build statistics to display
- **show_art** (`bool`) = `True` - Whether to show ASCII art
- **output_dir** (`str`) = `None` - Output directory path to display

**Returns:** `None`





---
### show_building_indicator

```python
def show_building_indicator(text: str = 'Building') -> None
```

Show a building indicator.

**Parameters:**

- **text** (`str`) = `'Building'`

**Returns:** `None`





---
### show_error

```python
def show_error(message: str, show_art: bool = True) -> None
```

Show an error message with art.

**Parameters:**

- **message** (`str`)
- **show_art** (`bool`) = `True`

**Returns:** `None`





---
### show_welcome

```python
def show_welcome() -> None
```

Show welcome banner.


**Returns:** `None`





---
### show_clean_success

```python
def show_clean_success(output_dir: str) -> None
```

Show clean success message.

**Parameters:**

- **output_dir** (`str`)

**Returns:** `None`





---
### display_template_errors

```python
def display_template_errors(stats: BuildStats) -> None
```

Display all collected template errors.

**Parameters:**

- **stats** (`BuildStats`) - Build statistics with template errors

**Returns:** `None`





---
