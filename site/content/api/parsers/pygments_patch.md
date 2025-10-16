
---
title: "parsers.pygments_patch"
type: python-module
source_file: "bengal/rendering/parsers/pygments_patch.py"
css_class: api-content
description: "Pygments performance patch for python-markdown.  This module provides a process-wide performance optimization that replaces Pygments' lexer lookup functions with cached versions. This avoids expens..."
---

# parsers.pygments_patch

Pygments performance patch for python-markdown.

This module provides a process-wide performance optimization that replaces
Pygments' lexer lookup functions with cached versions. This avoids expensive
plugin discovery on every code block during markdown rendering.

Performance Impact (826-page site):
    - Before: 86s (73% in plugin discovery)
    - After: ~29s (3× faster)

Warning:
    This patch affects the global markdown.extensions.codehilite module state.
    It is safe for CLI tools and single-process applications, but may not be
    suitable for multi-tenant web applications.

Usage:
    # One-time application (typical usage):
    PygmentsPatch.apply()

    # Temporary patching (for testing):
    with PygmentsPatch():
        # Patch is active here
        parser.parse(content)
    # Patch is removed here

---

## Classes

### `PygmentsPatch`


Context manager and utility class for patching Pygments lexer lookups.

This patch replaces expensive Pygments plugin discovery with cached lexer
instances, dramatically improving markdown parsing performance.

The patch is applied at the module level to markdown.extensions.codehilite,
affecting all uses of that module in the current process.


:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `_patched`
  - `bool`
  - Class-level flag indicating if patch is currently active
* - `_codehilite_module`
  - `ModuleType | None`
  - Reference to the patched module (if active)
* - `_originals`
  - `dict[str, Any]`
  - Saved original functions for restoration
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self) -> None
```

Initialize the patch context manager.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `__enter__`
```python
def __enter__(self) -> PygmentsPatch
```

Apply the patch on context enter.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`PygmentsPatch`




---
#### `__exit__`
```python
def __exit__(self, *args: Any) -> None
```

Remove the patch on context exit.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `apply` @classmethod
```python
def apply(cls) -> bool
```

Apply the Pygments caching patch to markdown.extensions.codehilite.

This method is idempotent - calling it multiple times is safe.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - bool: True if patch was applied, False if already applied or failed.




---
#### `restore` @classmethod
```python
def restore(cls) -> bool
```

Restore the original Pygments functions.

This removes the patch and restores the original behavior.
Primarily useful for testing.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - bool: True if patch was restored, False if not currently patched.




---
#### `is_patched` @classmethod
```python
def is_patched(cls) -> bool
```

Check if the patch is currently active.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - bool: True if patched, False otherwise.




---


