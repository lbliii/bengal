
---
title: "defaults"
type: "python-module"
source_file: "bengal/bengal/config/defaults.py"
line_number: 1
description: "Single source of truth for all Bengal configuration defaults. All config access should use these defaults via get_default() or specialized helpers like get_max_workers(). Provides centralized default ..."
---

# defaults
**Type:** Module
**Source:** [View source](bengal/bengal/config/defaults.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[config](/api/bengal/config/) ›defaults

Single source of truth for all Bengal configuration defaults.

All config access should use these defaults via get_default() or
specialized helpers like get_max_workers(). Provides centralized
default values for all configuration options.

Key Concepts:
    - Default values: Centralized default configuration values
    - Worker configuration: Auto-detection of optimal worker count
    - Fast imports: Avoids heavy dependencies for fast import time
    - Specialized helpers: get_max_workers(), etc. for common config access

Related Modules:
    - bengal.config.loader: Configuration loading from files
    - bengal.config.env_overrides: Environment variable overrides
    - bengal.orchestration.build: Build orchestration using config

See Also:
    - bengal/config/defaults.py:get_default() for default value access
    - bengal/config/defaults.py:get_max_workers() for worker configuration

## Functions



### `get_max_workers`


```python
def get_max_workers(config_value: int | None = None) -> int
```



Resolve max_workers with auto-detection.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config_value` | `int \| None` | - | User-configured value from site.config.get("max_workers") - None or 0 = auto-detect based on CPU count - Positive int = use that value |







**Returns**


`int` - Resolved worker count (always >= 1)
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> get_max_workers(None)  # Auto-detect
    11  # On a 12-core machine
    >>> get_max_workers(0)     # Also auto-detect
    11
    >>> get_max_workers(8)     # Use specified
    8
```





### `get_default`


```python
def get_default(key: str, nested_key: str | None = None) -> Any
```



Get default value for a config key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | Top-level config key (e.g., "max_workers", "theme") |
| `nested_key` | `str \| None` | - | Optional nested key using dot notation (e.g., "lunr.prebuilt") |







**Returns**


`Any` - Default value, or None if key not found
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> get_default("max_workers")
    None  # Means auto-detect
    >>> get_default("content", "excerpt_length")
    200
    >>> get_default("search", "lunr.prebuilt")
    True
    >>> get_default("theme", "name")
    'default'
```





### `get_pagination_per_page`


```python
def get_pagination_per_page(config_value: int | None = None) -> int
```



Resolve pagination per_page with default.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config_value` | `int \| None` | - | User-configured value |







**Returns**


`int` - Items per page (default: 10, minimum: 1)




### `normalize_bool_or_dict`


```python
def normalize_bool_or_dict(value: bool | dict[str, Any] | None, key: str, default_enabled: bool = True) -> dict[str, Any]
```



Normalize config values that can be bool or dict.

This standardizes handling of config keys like `health_check`, `search`,
`graph`, etc. that accept both:
- `key: false` (bool to disable)
- `key: { enabled: true, ... }` (dict with options)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `bool \| dict[str, Any] \| None` | - | The config value (bool, dict, or None) |
| `key` | `str` | - | The config key name (for defaults lookup) |
| `default_enabled` | `bool` | `True` | Whether the feature is enabled by default |







**Returns**


`dict[str, Any]` - Normalized dict with 'enabled' key and any other options
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> normalize_bool_or_dict(False, "health_check")
    {'enabled': False}

    >>> normalize_bool_or_dict(True, "search")
    {'enabled': True, 'lunr': {'prebuilt': True, ...}, 'ui': {...}}

    >>> normalize_bool_or_dict({'verbose': True}, "health_check")
    {'enabled': True, 'verbose': True}

    >>> normalize_bool_or_dict(None, "graph")
    {'enabled': True, 'path': '/graph/'}
```





### `is_feature_enabled`


```python
def is_feature_enabled(config: dict[str, Any], key: str, default: bool = True) -> bool
```



Check if a bool/dict config feature is enabled.

Convenience function for quick enable/disable checks without
needing the full normalized dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config` | `dict[str, Any]` | - | The site config dictionary |
| `key` | `str` | - | The config key to check (e.g., "health_check", "search") |
| `default` | `bool` | `True` | Default value if key not present |







**Returns**


`bool` - True if feature is enabled, False otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> is_feature_enabled({"health_check": False}, "health_check")
    False

    >>> is_feature_enabled({"search": {"enabled": True}}, "search")
    True

    >>> is_feature_enabled({}, "graph")  # Not in config
    True  # Default is True
```





### `get_feature_config`


```python
def get_feature_config(config: dict[str, Any], key: str, default_enabled: bool = True) -> dict[str, Any]
```



Get normalized config for a bool/dict feature.

This is the main entry point for accessing features that can be
configured as either bool or dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config` | `dict[str, Any]` | - | The site config dictionary |
| `key` | `str` | - | The config key (e.g., "health_check", "search", "graph") |
| `default_enabled` | `bool` | `True` | Whether the feature is enabled by default |







**Returns**


`dict[str, Any]` - Normalized dict with 'enabled' key and feature options
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> cfg = get_feature_config({"health_check": False}, "health_check")
    >>> cfg["enabled"]
    False

    >>> cfg = get_feature_config({"search": {"ui": {"modal": False}}}, "search")
    >>> cfg["enabled"]
    True
    >>> cfg["ui"]["modal"]
    False
```



---
*Generated by Bengal autodoc from `bengal/bengal/config/defaults.py`*

