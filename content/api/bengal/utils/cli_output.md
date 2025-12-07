
---
title: "cli_output"
type: "python-module"
source_file: "bengal/utils/cli_output.py"
line_number: 1
description: "Centralized CLI output system for Bengal. Provides a unified interface for all CLI messaging with: - Profile-aware formatting (Writer, Theme-Dev, Developer) - Consistent indentation and spacing - Auto..."
---

# cli_output
**Type:** Module
**Source:** [View source](bengal/utils/cli_output.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›cli_output

Centralized CLI output system for Bengal.

Provides a unified interface for all CLI messaging with:
- Profile-aware formatting (Writer, Theme-Dev, Developer)
- Consistent indentation and spacing
- Automatic TTY detection
- Rich/fallback rendering

## Classes




### `MessageLevel`


**Inherits from:**`Enum`Message importance levels.












### `OutputStyle`


**Inherits from:**`Enum`Visual styles for messages.












### `CLIOutput`


Centralized CLI output manager.

Handles all terminal output with profile-aware formatting,
consistent spacing, and automatic TTY detection.









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, profile: Any | None = None, quiet: bool = False, verbose: bool = False, use_rich: bool | None = None)
```


Initialize CLI output manager.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `profile` | `Any \| None` | - | Build profile (Writer, Theme-Dev, Developer) |
| `quiet` | `bool` | `False` | Suppress non-critical output |
| `verbose` | `bool` | `False` | Show detailed output |
| `use_rich` | `bool \| None` | - | Force rich/plain output (None = auto-detect) |








#### `should_show`

:::{div} api-badge-group
:::

```python
def should_show(self, level: MessageLevel) -> bool
```


Determine if message should be shown based on level and settings.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `level` | `MessageLevel` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `header`

:::{div} api-badge-group
:::

```python
def header(self, text: str, mascot: bool = True, leading_blank: bool = True, trailing_blank: bool = True) -> None
```


Print a header message.
Example: "ᓚᘏᗢ  Building your site..."


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `mascot` | `bool` | `True` | *No description provided.* |
| `leading_blank` | `bool` | `True` | *No description provided.* |
| `trailing_blank` | `bool` | `True` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `subheader`

:::{div} api-badge-group
:::

```python
def subheader(self, text: str, icon: str | None = None, leading_blank: bool = True, trailing_blank: bool = False, width: int = 60) -> None
```


Print a subheader with subtle border (lighter than header).

Creates a horizontal line with text, providing visual structure
without the weight of a full boxed header.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | The subheader text |
| `icon` | `str \| None` | - | Optional icon/emoji to display before text |
| `leading_blank` | `bool` | `True` | Add blank line before (default: True) |
| `trailing_blank` | `bool` | `False` | Add blank line after (default: False) |
| `width` | `int` | `60` | Total width of the border line (default: 60) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
=== 📊 Statistics ========================================
    === 💡 Next steps ========================================
```




#### `phase`

:::{div} api-badge-group
:::

```python
def phase(self, name: str, status: str = 'Done', duration_ms: float | None = None, details: str | None = None, icon: str = '✓') -> None
```


Print a phase status line.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | *No description provided.* |
| `status` | `str` | `'Done'` | *No description provided.* |
| `duration_ms` | `float \| None` | - | *No description provided.* |
| `details` | `str \| None` | - | *No description provided.* |
| `icon` | `str` | `'✓'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
✓ Discovery     Done
    ✓ Rendering     501ms (245 pages)
    ✓ Assets        Done
```




#### `detail`

:::{div} api-badge-group
:::

```python
def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None
```


Print a detail/sub-item.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `indent` | `int` | `1` | *No description provided.* |
| `icon` | `str \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
├─ RSS feed ✓
    └─ Sitemap ✓
```




#### `success`

:::{div} api-badge-group
:::

```python
def success(self, text: str, icon: str = '✨') -> None
```


Print a success message.

Example: "✨ Built 245 pages in 0.8s"


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `icon` | `str` | `'✨'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `info`

:::{div} api-badge-group
:::

```python
def info(self, text: str, icon: str | None = None) -> None
```


Print an info message.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `icon` | `str \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `warning`

:::{div} api-badge-group
:::

```python
def warning(self, text: str, icon: str = '⚠️') -> None
```


Print a warning message.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `icon` | `str` | `'⚠️'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `error`

:::{div} api-badge-group
:::

```python
def error(self, text: str, icon: str = '❌') -> None
```


Print an error message.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `icon` | `str` | `'❌'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `tip`

:::{div} api-badge-group
:::

```python
def tip(self, text: str, icon: str = '💡') -> None
```


Print a subtle tip/instruction line.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `icon` | `str` | `'💡'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `error_header`

:::{div} api-badge-group
:::

```python
def error_header(self, text: str, mouse: bool = True) -> None
```


Print an error header with mouse emoji.

Example: "ᘛ⁐̤ᕐᐷ  3 template errors found"

The mouse represents errors that Bengal (the cat) needs to catch!


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | *No description provided.* |
| `mouse` | `bool` | `True` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `path`

:::{div} api-badge-group
:::

```python
def path(self, path: str, icon: str = '📂', label: str = 'Output') -> None
```


Print a path.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `path` | `str` | - | *No description provided.* |
| `icon` | `str` | `'📂'` | *No description provided.* |
| `label` | `str` | `'Output'` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
📂 Output:
       ↪ /Users/.../public
```




#### `metric`

:::{div} api-badge-group
:::

```python
def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None
```


Print a metric.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `label` | `str` | - | *No description provided.* |
| `value` | `Any` | - | *No description provided.* |
| `unit` | `str \| None` | - | *No description provided.* |
| `indent` | `int` | `0` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
⏱️  Performance:
       ├─ Total: 834ms
       └─ Throughput: 293.7 pages/sec
```




#### `table`

:::{div} api-badge-group
:::

```python
def table(self, data: list[dict[str, str]], headers: list[str]) -> None
```


Print a table (rich only, falls back to simple list).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `list[dict[str, str]]` | - | *No description provided.* |
| `headers` | `list[str]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `prompt`

:::{div} api-badge-group
:::

```python
def prompt(self, text: str, default: Any = None, type: Any = str, show_default: bool = True) -> Any
```


Prompt user for input with themed styling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | The prompt text to display |
| `default` | `Any` | - | Default value if user presses enter |
| `type` | `Any` | `str` | Type to convert input to (str, int, float, etc.) |
| `show_default` | `bool` | `True` | Whether to show the default value |







:::{rubric} Returns
:class: rubric-returns
:::


`Any` - User's input converted to the specified type
:::{rubric} Examples
:class: rubric-examples
:::


```python
name = cli.prompt("Enter site name")
    count = cli.prompt("How many pages?", default=3, type=int)
```




#### `confirm`

:::{div} api-badge-group
:::

```python
def confirm(self, text: str, default: bool = False) -> bool
```


Prompt user for yes/no confirmation with themed styling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | The prompt text to display |
| `default` | `bool` | `False` | Default value if user presses enter |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if user confirms, False otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
if cli.confirm("Delete all files?"):
        do_deletion()
```




#### `blank`

:::{div} api-badge-group
:::

```python
def blank(self, count: int = 1) -> None
```


Print blank lines.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `count` | `int` | `1` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `separator`

:::{div} api-badge-group
:::

```python
def separator(self, width: int = 78, style: str = 'dim') -> None
```


Print a horizontal separator line.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `width` | `int` | `78` | Width of the separator line |
| `style` | `str` | `'dim'` | Style to apply (dim, info, header, etc.) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
────────────────────────────────────────
```




#### `file_change_notice`

:::{div} api-badge-group
:::

```python
def file_change_notice(self, file_name: str, timestamp: str | None = None) -> None
```


Print a file change notification for dev server.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_name` | `str` | - | Name of the changed file (or summary like "file.md (+3 more)") |
| `timestamp` | `str \| None` | - | Optional timestamp string (defaults to current time HH:MM:SS) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
────────────────────────────────────────
    12:34:56 │ 📝 File changed: index.md
    ────────────────────────────────────────
```




#### `server_url_inline`

:::{div} api-badge-group
:::

```python
def server_url_inline(self, host: str, port: int) -> None
```


Print server URL in inline format (for after rebuild).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `host` | `str` | - | Server host |
| `port` | `int` | - | Server port |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
➜  Local: http://localhost:5173/
```




#### `request_log_header`

:::{div} api-badge-group
:::

```python
def request_log_header(self) -> None
```


Print table header for HTTP request logging.



:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
TIME     │ METHOD │ STA │ PATH
    ─────────┼────────┼─────┼──────────────────────
```




#### `http_request`

:::{div} api-badge-group
:::

```python
def http_request(self, timestamp: str, method: str, status_code: str, path: str, is_asset: bool = False) -> None
```


Print a formatted HTTP request log line.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `timestamp` | `str` | - | Request timestamp (HH:MM:SS format) |
| `method` | `str` | - | HTTP method (GET, POST, etc.) |
| `status_code` | `str` | - | HTTP status code as string |
| `path` | `str` | - | Request path |
| `is_asset` | `bool` | `False` | Whether this is an asset request (affects icon display) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
12:34:56 │ GET    │ 200 │ 📄 /index.html
    12:34:57 │ GET    │ 404 │ ❌ /missing.html
```

## Functions



### `get_cli_output`


```python
def get_cli_output() -> CLIOutput
```



Get the global CLI output instance.



**Returns**


`CLIOutput`




### `init_cli_output`


```python
def init_cli_output(profile: Any | None = None, quiet: bool = False, verbose: bool = False) -> CLIOutput
```



Initialize the global CLI output instance with settings.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `profile` | `Any \| None` | - | *No description provided.* |
| `quiet` | `bool` | `False` | *No description provided.* |
| `verbose` | `bool` | `False` | *No description provided.* |







**Returns**


`CLIOutput`



---
*Generated by Bengal autodoc from `bengal/utils/cli_output.py`*

