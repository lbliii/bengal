
---
title: "commands.clean"
type: python-module
source_file: "bengal/cli/commands/clean.py"
css_class: api-content
description: "Clean commands for removing generated files."
---

# commands.clean

Clean commands for removing generated files.

---


## Functions

### `clean`
```python
def clean(force: bool, config: str, source: str) -> None
```

🧹 Clean the output directory.

Removes all generated files from the output directory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`force`** (`bool`)
- **`config`** (`str`)
- **`source`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `cleanup`
```python
def cleanup(force: bool, port: int, source: str) -> None
```

🔧 Clean up stale Bengal server processes.

Finds and terminates any stale 'bengal serve' processes that may be
holding ports or preventing new servers from starting.

This is useful if a previous server didn't shut down cleanly.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`force`** (`bool`)
- **`port`** (`int`)
- **`source`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
