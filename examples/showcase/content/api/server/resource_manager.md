---
title: "server.resource_manager"
layout: api-reference
type: python-module
source_file: "../../bengal/server/resource_manager.py"
---

# server.resource_manager

Resource lifecycle management for Bengal dev server.

Provides centralized cleanup handling for all termination scenarios:
- Normal exit (context manager)
- Ctrl+C (KeyboardInterrupt + signal handler)
- kill/SIGTERM (signal handler)
- Parent death (atexit handler)
- Exceptions (context manager __exit__)

**Source:** `../../bengal/server/resource_manager.py`

---

## Classes

### ResourceManager


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




**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize resource manager.

**Parameters:**

- **self**







---
#### register

```python
def register(self, name: str, resource: Any, cleanup_fn: Callable) -> Any
```

Register a resource with its cleanup function.

**Parameters:**

- **self**
- **name** (`str`) - Human-readable name for debugging
- **resource** (`Any`) - The resource object
- **cleanup_fn** (`Callable`) - Function to call to clean up (takes resource as arg)

**Returns:** `Any` - The resource (for chaining)






---
#### register_server

```python
def register_server(self, server: Any) -> Any
```

Register HTTP server for cleanup.

**Parameters:**

- **self**
- **server** (`Any`) - socketserver.TCPServer instance

**Returns:** `Any` - The server






---
#### register_observer

```python
def register_observer(self, observer: Any) -> Any
```

Register file system observer for cleanup.

**Parameters:**

- **self**
- **observer** (`Any`) - watchdog.observers.Observer instance

**Returns:** `Any` - The observer






---
#### register_pidfile

```python
def register_pidfile(self, pidfile_path) -> Any
```

Register PID file for cleanup.

**Parameters:**

- **self**
- **pidfile_path** - Path object to PID file

**Returns:** `Any` - The path






---
#### cleanup

```python
def cleanup(self, signum: Optional[int] = None) -> None
```

Clean up all resources (idempotent).

**Parameters:**

- **self**
- **signum** (`Optional[int]`) = `None` - Signal number if cleanup triggered by signal

**Returns:** `None`






---
#### __enter__

```python
def __enter__(self)
```

Context manager entry.

**Parameters:**

- **self**







---
#### __exit__

```python
def __exit__(self, exc_type, exc_val, exc_tb)
```

Context manager exit - ensure cleanup runs.

**Parameters:**

- **self**
- **exc_type**
- **exc_val**
- **exc_tb**







---


