
---
title: "utils.profile"
type: python-module
source_file: "bengal/utils/profile.py"
css_class: api-content
description: "Build profile system for persona-based observability.  Provides three profiles optimized for different user workflows: - Writer: Fast, clean builds for content authors - Theme Developer: Template-f..."
---

# utils.profile

Build profile system for persona-based observability.

Provides three profiles optimized for different user workflows:
- Writer: Fast, clean builds for content authors
- Theme Developer: Template-focused debugging for theme builders
- Developer: Full observability for framework contributors

Example:
    from bengal.utils.profile import BuildProfile

    profile = BuildProfile.from_cli_args(dev=True)
    config = profile.get_config()

    if config['track_memory']:
        # Enable memory tracking
        pass

---

## Classes

### `BuildProfile`

**Inherits from:** `Enum`
Build profiles for different user personas.

Each profile optimizes observability features for a specific workflow:
- WRITER: Content authors who want fast, clean builds
- THEME_DEV: Theme developers who need template debugging
- DEVELOPER: Framework contributors who need full observability




:::{rubric} Methods
:class: rubric-methods
:::
#### `from_string` @classmethod
```python
def from_string(cls, value: str) -> 'BuildProfile'
```

Parse profile from string.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`cls`**
- **`value`** (`str`) - Profile name (case-insensitive)

:::{rubric} Returns
:class: rubric-returns
:::
`'BuildProfile'` - BuildProfile enum value




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> BuildProfile.from_string("theme-dev")
    BuildProfile.THEME_DEV
```


---
#### `from_cli_args` @classmethod
```python
def from_cli_args(cls, profile: str | None = None, dev: bool = False, theme_dev: bool = False, verbose: bool = False, debug: bool = False) -> 'BuildProfile'
```

Determine profile from CLI arguments with proper precedence.

Precedence (highest to lowest):
1. --dev flag (full developer mode)
2. --theme-dev flag
3. --profile option
4. --verbose flag (legacy)
5. --debug flag (debug logging only, fast health checks)
6. Default (WRITER)

NOTE: --debug now only enables debug logging, not comprehensive health checks.
For full validation, use --dev or --profile=dev.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cls` | - | - | - |
| `profile` | `str | None` | `None` | Explicit profile name from --profile |
| `dev` | `bool` | `False` | --dev flag (full developer mode) |
| `theme_dev` | `bool` | `False` | --theme-dev flag |
| `verbose` | `bool` | `False` | --verbose flag (legacy) |
| `debug` | `bool` | `False` | --debug flag (debug logging only) |

:::{rubric} Returns
:class: rubric-returns
:::
`'BuildProfile'` - Determined BuildProfile




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> BuildProfile.from_cli_args(dev=True)
    BuildProfile.DEVELOPER

    >>> BuildProfile.from_cli_args(debug=True)
    BuildProfile.DEVELOPER  # Full dev mode with debug logging

    >>> BuildProfile.from_cli_args(verbose=True)
    BuildProfile.THEME_DEV
```


---
#### `get_config`
```python
def get_config(self) -> dict[str, Any]
```

Get configuration dictionary for this profile.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Configuration with feature toggles for this profile

Configuration keys:
    show_phase_timing: Show build phase timing
    track_memory: Enable memory profiling (tracemalloc + psutil)
    enable_debug_output: Print debug messages to stderr
    collect_metrics: Save metrics to .bengal-metrics/
    health_checks: Dict with enabled/disabled validator lists
    verbose_build_stats: Show detailed build statistics




---
#### `__str__`
```python
def __str__(self) -> str
```

String representation of profile.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---


## Functions

### `set_current_profile`
```python
def set_current_profile(profile: BuildProfile) -> None
```

Set the current build profile.

This is used by helper functions to determine behavior without
passing profile through every function call.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`profile`** (`BuildProfile`) - BuildProfile to set as current

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `get_current_profile`
```python
def get_current_profile() -> BuildProfile
```

Get the current build profile.



:::{rubric} Returns
:class: rubric-returns
:::
`BuildProfile` - Current profile, or WRITER if not set




---
### `should_show_debug`
```python
def should_show_debug() -> bool
```

Check if debug output should be shown.

This is a helper for conditional debug output without passing
profile through every function.



:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if debug output should be shown




:::{rubric} Examples
:class: rubric-examples
:::
```python
if should_show_debug():
```


---
### `should_track_memory`
```python
def should_track_memory() -> bool
```

Check if memory tracking should be enabled.



:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if memory should be tracked




---
### `should_collect_metrics`
```python
def should_collect_metrics() -> bool
```

Check if metrics collection should be enabled.



:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if metrics should be collected




---
### `get_enabled_health_checks`
```python
def get_enabled_health_checks() -> list[str]
```

Get list of enabled health check validators for current profile.



:::{rubric} Returns
:class: rubric-returns
:::
`list[str]` - List of validator names that should run, or 'all' string




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> get_enabled_health_checks()
    ['config', 'output', 'links']
```


---
### `is_validator_enabled`
```python
def is_validator_enabled(validator_name: str) -> bool
```

Check if a specific validator should run.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`validator_name`** (`str`) - Name of validator (e.g., 'config', 'links')

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if validator should run




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> is_validator_enabled('performance')
    False  # In writer mode
```


---
