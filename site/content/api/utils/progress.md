
---
title: "utils.progress"
type: python-module
source_file: "bengal/utils/progress.py"
css_class: api-content
description: "Python module documentation"
---

# utils.progress

*No module description provided.*

---

## Classes

### `ProgressReporter`

**Inherits from:** `Protocol`
Contract for reporting build progress and user-facing messages.

Implementations: CLI, server, noop (tests), rich, etc.




:::{rubric} Methods
:class: rubric-methods
:::
#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `label`
  - `str`
  - -
  - -
* - `total`
  - `int | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `current`
  - `int | None`
  - `None`
  - -
* - `current_item`
  - `str | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `elapsed_ms`
  - `float | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `log`
```python
def log(self, message: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `message`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---

### `NoopReporter`


Default reporter that does nothing (safe for tests and quiet modes).




:::{rubric} Methods
:class: rubric-methods
:::
#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `label`
  - `str`
  - -
  - -
* - `total`
  - `int | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `current`
  - `int | None`
  - `None`
  - -
* - `current_item`
  - `str | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `elapsed_ms`
  - `float | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `log`
```python
def log(self, message: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `message`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---

### `LiveProgressReporterAdapter`


Adapter to bridge LiveProgressManager to ProgressReporter.

Delegates phase methods directly and prints simple lines for log().




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, live_progress_manager: Any)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `live_progress_manager`
  - `Any`
  - -
  - -
:::

::::




---
#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `label`
  - `str`
  - -
  - -
* - `total`
  - `int | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `current`
  - `int | None`
  - `None`
  - -
* - `current_item`
  - `str | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
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
* - `phase_id`
  - `str`
  - -
  - -
* - `elapsed_ms`
  - `float | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `log`
```python
def log(self, message: str) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
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
* - `message`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
