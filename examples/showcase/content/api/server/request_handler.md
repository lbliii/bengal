
---
title: "server.request_handler"
type: python-module
source_file: "bengal/server/request_handler.py"
css_class: api-content
description: "Custom HTTP request handler for the dev server.  Provides beautiful logging, custom 404 pages, and live reload support."
---

# server.request_handler

Custom HTTP request handler for the dev server.

Provides beautiful logging, custom 404 pages, and live reload support.

---

## Classes

### `BengalRequestHandler`

**Inherits from:** `RequestLogger`, `LiveReloadMixin`, `http.server.SimpleHTTPRequestHandler`
Custom HTTP request handler with beautiful logging, custom 404 page, and live reload support.

This handler combines:
- RequestLogger: Beautiful, minimal HTTP request logging
- LiveReloadMixin: Server-Sent Events for hot reload
- SimpleHTTPRequestHandler: Standard HTTP file serving




:::{rubric} Methods
:class: rubric-methods
:::
#### `handle`
```python
def handle(self) -> None
```

Override handle to suppress BrokenPipeError tracebacks.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `do_GET`
```python
def do_GET(self) -> None
```

Override GET to support SSE and safe HTML injection via mixin.

Request flow:
- Serve SSE endpoint at /__bengal_reload__ (long-lived connection)
- Try to serve HTML with injected live-reload script
- Fallback to default file serving for non-HTML



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `send_error`
```python
def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None
```

Override send_error to serve custom 404 page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`code`** (`int`) - HTTP error code
- **`message`** (`str | None`) = `None` - Error message
- **`explain`** (`str | None`) = `None` - Detailed explanation

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
