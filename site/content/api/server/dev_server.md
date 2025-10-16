
---
title: "server.dev_server"
type: python-module
source_file: "bengal/server/dev_server.py"
css_class: api-content
description: "Development server with file watching and hot reload."
---

# server.dev_server

Development server with file watching and hot reload.

---

## Classes

### `DevServer`


Development server with file watching and auto-rebuild.

Provides a complete development environment for Bengal sites with:
- HTTP server for viewing the site locally
- File watching for automatic rebuilds
- Graceful shutdown handling
- Stale process detection and cleanup
- Automatic port fallback
- Optional browser auto-open

The server performs an initial build, then watches for changes and
automatically rebuilds only what's needed using incremental builds.

Features:
- Incremental + parallel builds (5-10x faster than full builds)
- Beautiful, minimal request logging
- Custom 404 error pages
- PID file tracking for stale process detection
- Comprehensive resource cleanup on shutdown




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any, host: str = DEFAULT_DEV_HOST, port: int = DEFAULT_DEV_PORT, watch: bool = True, auto_port: bool = True, open_browser: bool = False) -> None
```

Initialize the dev server.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 7 parameters (click to expand)
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
* - `site`
  - `Any`
  - -
  - Site instance
* - `host`
  - `str`
  - `DEFAULT_DEV_HOST`
  - Server host
* - `port`
  - `int`
  - `DEFAULT_DEV_PORT`
  - Server port
* - `watch`
  - `bool`
  - `True`
  - Whether to watch for file changes
* - `auto_port`
  - `bool`
  - `True`
  - Whether to automatically find an available port if the specified one is in use
* - `open_browser`
  - `bool`
  - `False`
  - Whether to automatically open the browser
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `start`
```python
def start(self) -> None
```

Start the development server with robust resource cleanup.

This method:
1. Checks for and handles stale processes
2. Performs an initial build
3. Creates HTTP server (with port fallback if needed)
4. Starts file watcher (if enabled)
5. Opens browser (if requested)
6. Runs until interrupted (Ctrl+C, SIGTERM, etc.)

The server uses ResourceManager for comprehensive cleanup handling,
ensuring all resources are properly released on shutdown regardless
of how the process exits.



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

:::{rubric} Raises
:class: rubric-raises
:::
- **`OSError`**: If no available port can be found- **`KeyboardInterrupt`**: When user presses Ctrl+C (handled gracefully)



---
