
---
title: "server.response_wrapper"
type: python-module
source_file: "bengal/server/response_wrapper.py"
css_class: api-content
description: "Deprecated: ResponseBuffer is no longer used.  Kept temporarily to avoid import errors while tests are updated."
---

# server.response_wrapper

Deprecated: ResponseBuffer is no longer used.

Kept temporarily to avoid import errors while tests are updated.

---

## Classes

### `ResponseBuffer`


*No class description provided.*




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, *args, **kwargs)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `write`
```python
def write(self, data)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`data`**





---
#### `flush`
```python
def flush(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `get_buffered_data`
```python
def get_buffered_data(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `send_buffered`
```python
def send_buffered(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `send_modified`
```python
def send_modified(self, modified_data: bytes)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`modified_data`** (`bytes`)





---
#### `clear`
```python
def clear(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
