
---
title: "file_io"
type: "python-module"
source_file: "bengal/bengal/utils/file_io.py"
line_number: 1
description: "File I/O utilities with robust error handling. Provides standardized file reading/writing operations with consistent error handling, logging, and encoding fallback. Consolidates duplicate file I/O pat..."
---

# file_io
**Type:** Module
**Source:** [View source](bengal/bengal/utils/file_io.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›file_io

File I/O utilities with robust error handling.

Provides standardized file reading/writing operations with consistent error handling,
logging, and encoding fallback. Consolidates duplicate file I/O patterns found
throughout the codebase.

Example:
    from bengal.utils.file_io import read_text_file, load_json, load_yaml

    # Read text file with encoding fallback
    content = read_text_file(path, fallback_encoding='latin-1')

    # Load JSON with error handling
    data = load_json(path, on_error='return_empty')

    # Auto-detect and load data file
    data = load_data_file(path)  # Works for .json, .yaml, .toml

## Functions



### `read_text_file`


```python
def read_text_file(file_path: Path | str, encoding: str = 'utf-8', fallback_encoding: str | None = 'latin-1', on_error: str = 'raise', caller: str | None = None) -> str | None
```



Read text file with robust error handling and encoding fallback.

Consolidates patterns from:
- bengal/discovery/content_discovery.py:192 (UTF-8 with latin-1 fallback)
- bengal/rendering/template_functions/files.py:78 (file reading with logging)
- bengal/config/loader.py:137 (config file reading)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to file to read |
| `encoding` | `str` | `'utf-8'` | Primary encoding to try (default: 'utf-8') |
| `fallback_encoding` | `str \| None` | `'latin-1'` | Fallback encoding if primary fails (default: 'latin-1') |
| `on_error` | `str` | `'raise'` | Error handling strategy: - 'raise': Raise exception on error - 'return_empty': Return empty string on error - 'return_none': Return None on error |
| `caller` | `str \| None` | - | Caller identifier for logging context |







**Returns**


`str | None` - File contents as string, or None/empty string based on on_error.

Encoding notes:
- Strips UTF-8 BOM when present.
- If primary decode fails, tries `utf-8-sig` before the configured fallback.
:::{rubric} Raises
:class: rubric-raises
:::

- **`FileNotFoundError`**:If file doesn't exist and on_error='raise'
- **`ValueError`**:If path is not a file and on_error='raise'
- **`IOError`**:If file cannot be read and on_error='raise'

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> content = read_text_file('config.txt')
    >>> content = read_text_file('data.txt', fallback_encoding='latin-1')
    >>> content = read_text_file('optional.txt', on_error='return_empty')
```





### `load_json`


```python
def load_json(file_path: Path | str, on_error: str = 'return_empty', caller: str | None = None) -> Any
```



Load JSON file with error handling.

Consolidates patterns from:
- bengal/rendering/template_functions/data.py:80 (JSON loading)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to JSON file |
| `on_error` | `str` | `'return_empty'` | Error handling strategy ('raise', 'return_empty', 'return_none') |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`Any` - Parsed JSON data, or {} / None based on on_error
:::{rubric} Raises
:class: rubric-raises
:::

- **`FileNotFoundError`**:If file not found and on_error='raise' json.JSONDecodeError: If JSON is invalid and on_error='raise'

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> data = load_json('config.json')
    >>> data = load_json('optional.json', on_error='return_none')
```





### `load_yaml`


```python
def load_yaml(file_path: Path | str, on_error: str = 'return_empty', caller: str | None = None) -> Any
```



Load YAML file with error handling.

Consolidates patterns from:
- bengal/config/loader.py:142 (YAML config loading)
- bengal/rendering/template_functions/data.py:94 (YAML data loading)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to YAML file |
| `on_error` | `str` | `'return_empty'` | Error handling strategy ('raise', 'return_empty', 'return_none') |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`Any` - Parsed YAML data, or {} / None based on on_error
:::{rubric} Raises
:class: rubric-raises
:::

- **`FileNotFoundError`**:If file not found and on_error='raise' yaml.YAMLError: If YAML is invalid and on_error='raise'
- **`ImportError`**:If PyYAML not installed and on_error='raise'

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> data = load_yaml('config.yaml')
    >>> data = load_yaml('optional.yml', on_error='return_none')
```





### `load_toml`


```python
def load_toml(file_path: Path | str, on_error: str = 'return_empty', caller: str | None = None) -> Any
```



Load TOML file with error handling.

Consolidates patterns from:
- bengal/config/loader.py:137 (TOML config loading)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to TOML file |
| `on_error` | `str` | `'return_empty'` | Error handling strategy ('raise', 'return_empty', 'return_none') |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`Any` - Parsed TOML data, or {} / None based on on_error
:::{rubric} Raises
:class: rubric-raises
:::

- **`FileNotFoundError`**:If file not found and on_error='raise' toml.TomlDecodeError: If TOML is invalid and on_error='raise'

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> data = load_toml('config.toml')
    >>> data = load_toml('optional.toml', on_error='return_none')
```





### `load_data_file`


```python
def load_data_file(file_path: Path | str, on_error: str = 'return_empty', caller: str | None = None) -> Any
```



Auto-detect and load JSON/YAML/TOML file.

Consolidates pattern from:
- bengal/rendering/template_functions/data.py:40 (get_data function)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to data file (.json, .yaml, .yml, .toml) |
| `on_error` | `str` | `'return_empty'` | Error handling strategy ('raise', 'return_empty', 'return_none') |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`Any` - Parsed data, or {} / None based on on_error
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If file format is unsupported and on_error='raise'

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> data = load_data_file('config.json')
    >>> data = load_data_file('settings.yaml')
    >>> data = load_data_file('pyproject.toml')
```





### `write_text_file`


```python
def write_text_file(file_path: Path | str, content: str, encoding: str = 'utf-8', create_parents: bool = True, caller: str | None = None) -> None
```



Write text to file with parent directory creation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to file to write |
| `content` | `str` | - | Text content to write |
| `encoding` | `str` | `'utf-8'` | Text encoding (default: 'utf-8') |
| `create_parents` | `bool` | `True` | Create parent directories if they don't exist |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`IOError`**:If write fails

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> write_text_file('output/data.txt', 'Hello World')
    >>> write_text_file('result.json', json.dumps(data))
```





### `write_json`


```python
def write_json(file_path: Path | str, data: Any, indent: int | None = 2, create_parents: bool = True, caller: str | None = None) -> None
```



Write data as JSON file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| str` | - | Path to JSON file |
| `data` | `Any` | - | Data to serialize as JSON |
| `indent` | `int \| None` | `2` | JSON indentation (None for compact) |
| `create_parents` | `bool` | `True` | Create parent directories if needed |
| `caller` | `str \| None` | - | Caller identifier for logging |







**Returns**


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`TypeError`**:If data is not JSON serializable
- **`IOError`**:If write fails

:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> write_json('output.json', {'key': 'value'})
    >>> write_json('data.json', data, indent=None)  # Compact
```



---
*Generated by Bengal autodoc from `bengal/bengal/utils/file_io.py`*

