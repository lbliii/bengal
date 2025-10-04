---
title: "server.dev_server"
layout: api-reference
type: python-module
source_file: "../../bengal/server/dev_server.py"
---

# server.dev_server

Development server with file watching and hot reload.

**Source:** `../../bengal/server/dev_server.py`

---

## Classes

### QuietHTTPRequestHandler

**Inherits from:** `http.server.SimpleHTTPRequestHandler`
Custom HTTP request handler with beautiful, minimal logging.




**Methods:**

#### log_message

```python
def log_message(self, format: str, *args: Any) -> None
```

Log an HTTP request with beautiful formatting.

**Parameters:**

- **self**
- **format** (`str`) - Format string *args: Format arguments

**Returns:** `None`






---
#### log_error

```python
def log_error(self, format: str, *args: Any) -> None
```

Suppress error logging - we handle everything in log_message.

**Parameters:**

- **self**
- **format** (`str`) - Format string *args: Format arguments

**Returns:** `None`






---

### BuildHandler

**Inherits from:** `FileSystemEventHandler`
File system event handler that triggers site rebuild.




**Methods:**

#### __init__

```python
def __init__(self, site: Any) -> None
```

Initialize the build handler.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance

**Returns:** `None`






---
#### on_modified

```python
def on_modified(self, event: FileSystemEvent) -> None
```

Handle file modification events.

**Parameters:**

- **self**
- **event** (`FileSystemEvent`) - File system event

**Returns:** `None`






---

### DevServer


Development server with file watching and auto-rebuild.




**Methods:**

#### __init__

```python
def __init__(self, site: Any, host: str = 'localhost', port: int = 5173, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None
```

Initialize the dev server.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance
- **host** (`str`) = `'localhost'` - Server host
- **port** (`int`) = `5173` - Server port
- **watch** (`bool`) = `True` - Whether to watch for file changes
- **auto_port** (`bool`) = `True` - Whether to automatically find an available port if the specified one is in use
- **open_browser** (`bool`) = `False` - Whether to automatically open the browser

**Returns:** `None`






---
#### start

```python
def start(self) -> None
```

Start the development server with robust resource cleanup.

**Parameters:**

- **self**

**Returns:** `None`






---


