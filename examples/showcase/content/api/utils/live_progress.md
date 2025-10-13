
---
title: "utils.live_progress"
type: python-module
source_file: "bengal/utils/live_progress.py"
css_class: api-content
description: "Live progress display system with profile-aware output.  Provides in-place progress updates that minimize terminal scrolling while showing appropriate detail for each user profile."
---

# utils.live_progress

Live progress display system with profile-aware output.

Provides in-place progress updates that minimize terminal scrolling
while showing appropriate detail for each user profile.

---

## Classes

### `PhaseStatus`

**Inherits from:** `Enum`
Status of a build phase.





### `PhaseProgress`


Track progress for a single build phase.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`name`** (`str`)- **`status`** (`PhaseStatus`)- **`current`** (`int`)- **`total`** (`int | None`)- **`current_item`** (`str`)- **`elapsed_ms`** (`float`)- **`start_time`** (`float | None`)- **`metadata`** (`dict`)- **`recent_items`** (`list[str]`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `get_percentage`
```python
def get_percentage(self) -> float | None
```

Get completion percentage.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`float | None`




---
#### `get_elapsed_str`
```python
def get_elapsed_str(self) -> str
```

Get formatted elapsed time string.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---

### `LiveProgressManager`


Manager for live progress updates across build phases.

Features:
- Profile-aware display (Writer/Theme-Dev/Developer)
- In-place updates (no scrolling)
- Graceful fallback for CI/non-TTY
- Context manager for clean setup/teardown




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, profile: BuildProfile, console: Console | None = None, enabled: bool = True)
```

Initialize live progress manager.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`profile`** (`BuildProfile`) - Build profile (Writer/Theme-Dev/Developer)
- **`console`** (`Console | None`) = `None` - Rich console instance (creates one if not provided)
- **`enabled`** (`bool`) = `True` - Whether live progress is enabled





---
#### `__enter__`
```python
def __enter__(self)
```

Enter context manager.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `__exit__`
```python
def __exit__(self, *args)
```

Exit context manager.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `add_phase`
```python
def add_phase(self, phase_id: str, name: str, total: int | None = None)
```

Register a new phase.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`phase_id`** (`str`) - Unique identifier for the phase
- **`name`** (`str`) - Display name for the phase
- **`total`** (`int | None`) = `None` - Total number of items to process (if known)





---
#### `start_phase`
```python
def start_phase(self, phase_id: str)
```

Mark phase as running.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`phase_id`** (`str`) - Phase identifier





---
#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None, **metadata)
```

Update phase progress.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`phase_id`** (`str`) - Phase identifier
- **`current`** (`int | None`) = `None` - Current progress count
- **`current_item`** (`str | None`) = `None` - Current item being processed **metadata: Additional metadata to track





---
#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None)
```

Mark phase as complete.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`phase_id`** (`str`) - Phase identifier
- **`elapsed_ms`** (`float | None`) = `None` - Total elapsed time in milliseconds (optional)





---
#### `fail_phase`
```python
def fail_phase(self, phase_id: str, error: str)
```

Mark phase as failed.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`phase_id`** (`str`) - Phase identifier
- **`error`** (`str`) - Error message





---
