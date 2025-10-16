
---
title: "utils.rich_console"
type: python-module
source_file: "bengal/utils/rich_console.py"
css_class: api-content
description: "Rich console wrapper with profile-aware output.  Provides a singleton console instance that respects: - Build profiles (Writer/Theme-Dev/Developer) - Terminal capabilities - CI/CD environments"
---

# utils.rich_console

Rich console wrapper with profile-aware output.

Provides a singleton console instance that respects:
- Build profiles (Writer/Theme-Dev/Developer)
- Terminal capabilities
- CI/CD environments

---


## Functions

### `get_console`
```python
def get_console() -> Console
```

Get singleton rich console instance.



:::{rubric} Returns
:class: rubric-returns
:::
`Console` - Configured Console instance




---
### `should_use_rich`
```python
def should_use_rich() -> bool
```

Determine if we should use rich features.



:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if rich features should be enabled




---
### `detect_environment`
```python
def detect_environment() -> dict
```

Detect terminal and environment capabilities.



:::{rubric} Returns
:class: rubric-returns
:::
`dict` - Dictionary with environment info




---
### `reset_console`
```python
def reset_console()
```

Reset the console singleton (mainly for testing).







---
### `is_live_display_active`
```python
def is_live_display_active()
```

Check if a Live display is currently active on the console.

This function accesses the private `_live` attribute using `getattr()`
to safely handle cases where it might not exist, with a fallback that
assumes no Live display is active if an exception occurs.





```{note}
Tested against Rich >= 13.7.0 (as specified in pyproject.toml). Uses the private _live attribute since Rich does not provide a public API for detecting active Live displays. The getattr() call provides safe access with a sensible default value (None).
```




---
