
---
title: "server.resource_manager"
type: python-module
source_file: "bengal/server/resource_manager.py"
css_class: api-content
description: "Resource lifecycle management for Bengal dev server.  Provides centralized cleanup handling for all termination scenarios: - Normal exit (context manager) - Ctrl+C (KeyboardInterrupt + signal handl..."
---

# server.resource_manager

Resource lifecycle management for Bengal dev server.

Provides centralized cleanup handling for all termination scenarios:
- Normal exit (context manager)
- Ctrl+C (KeyboardInterrupt + signal handler)
- kill/SIGTERM (signal handler)
- Parent death (atexit handler)
- Exceptions (context manager __exit__)

---

## Classes

### `ResourceManager`


Centralized resource lifecycle management.

Ensures all resources are cleaned up regardless of how the process exits.

Usage:
    with ResourceManager() as rm:
        server = rm.register_server(httpd)
        observer = rm.register_observer(watcher)
        # Resources automatically cleaned up on exit

Features:
- Idempotent cleanup (safe to call multiple times)
- LIFO cleanup order (like context managers)
- Timeout protection (won't hang forever)
- Thread-safe registration
- Handles all termination scenarios




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

Initialize resource manager.



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




---
#### `register`
```python
def register(self, name: str, resource: Any, cleanup_fn: Callable) -> Any
```

Register a resource with its cleanup function.



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
* - `name`
  - `str`
  - -
  - Human-readable name for debugging
* - `resource`
  - `Any`
  - -
  - The resource object
* - `cleanup_fn`
  - `Callable`
  - -
  - Function to call to clean up (takes resource as arg)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any` - The resource (for chaining)




---
#### `register_server`
```python
def register_server(self, server: Any) -> Any
```

Register HTTP server for cleanup.



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
* - `server`
  - `Any`
  - -
  - socketserver.TCPServer instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any` - The server




---
#### `register_observer`
```python
def register_observer(self, observer: Any) -> Any
```

Register file system observer for cleanup.



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
* - `observer`
  - `Any`
  - -
  - watchdog.observers.Observer instance
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any` - The observer




---
#### `register_pidfile`
```python
def register_pidfile(self, pidfile_path) -> Any
```

Register PID file for cleanup.



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
* - `pidfile_path`
  - -
  - -
  - Path object to PID file
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`Any` - The path




---
#### `cleanup`
```python
def cleanup(self, signum: int | None = None) -> None
```

Clean up all resources (idempotent).



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
* - `signum`
  - `int | None`
  - `None`
  - Signal number if cleanup triggered by signal
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `__enter__`
```python
def __enter__(self)
```

Context manager entry.



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




---
#### `__exit__`
```python
def __exit__(self, exc_type, *args)
```

Context manager exit - ensure cleanup runs.



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
* - `exc_type`
  - -
  - -
  - -
:::

::::




---


