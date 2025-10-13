
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
