
---
title: "server.live_reload"
type: python-module
source_file: "bengal/server/live_reload.py"
css_class: api-content
description: "Live reload functionality for the dev server.  Provides Server-Sent Events (SSE) endpoint and HTML injection for hot reload.  Architecture: - SSE Endpoint (/__bengal_reload__): Maintains persistent..."
---

# server.live_reload

Live reload functionality for the dev server.

Provides Server-Sent Events (SSE) endpoint and HTML injection for hot reload.

Architecture:
- SSE Endpoint (/__bengal_reload__): Maintains persistent connections to clients
- Live Reload Script: Injected into HTML pages to connect to SSE endpoint
- Client Queue: Each connected browser gets a queue for messages
- Reload Notifications: Broadcast to all clients when build completes

SSE Protocol:
    Client: EventSource('/__bengal_reload__')
    Server: data: reload

  (triggers page refresh)
    Server: : keepalive

  (every 30s to prevent timeout)

The live reload system enables automatic browser refresh after file changes
are detected and the site is rebuilt, providing a seamless development experience.

Note:
    Live reload currently requires manual implementation in the request handler.
    See plan/LIVE_RELOAD_ARCHITECTURE_PROPOSAL.md for implementation details.

---

## Classes

### `LiveReloadMixin`


Mixin class providing live reload functionality via SSE.

This class is designed to be mixed into an HTTP request handler.
It provides two key methods:
- handle_sse(): Handles the SSE endpoint (/__bengal_reload__)
- serve_html_with_live_reload(): Injects the live reload script into HTML

The SSE connection remains open, sending keepalive comments every 30 seconds
and "reload" messages when the site is rebuilt.




:::{rubric} Methods
:class: rubric-methods
:::
#### `handle_sse`
```python
def handle_sse(self) -> None
```

Handle Server-Sent Events endpoint for live reload.

Maintains a persistent HTTP connection and sends SSE messages:
- Keepalive comments (: keepalive) every 30 seconds
- Reload events (data: reload) when site is rebuilt

The connection remains open until the client disconnects or an error occurs.



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


```{note}
This method blocks until the client disconnects
```




---
#### `serve_html_with_live_reload`
```python
def serve_html_with_live_reload(self) -> bool
```

Serve HTML file with live reload script injected (with caching).

Uses file modification time caching to avoid re-reading/re-injecting
unchanged files during rapid navigation.



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

`bool` - True if HTML was served (with or without injection), False if not HTML


```{note}
Returns False for non-HTML files so the caller can handle them
```




---


## Functions

### `notify_clients_reload`
```python
def notify_clients_reload() -> None
```

Notify all connected SSE clients to reload.

Sends a "reload" message to all connected clients via their queues.
Clients with full queues are skipped to avoid blocking.

This is called after a successful build to trigger browser refresh.



:::{rubric} Returns
:class: rubric-returns
:::
`None`


```{note}
This is thread-safe and can be called from the build handler thread
```




---
### `set_reload_action`
```python
def set_reload_action(action: str) -> None
```

Set the next reload action for SSE clients.

Actions:
    - 'reload'      : full page reload
    - 'reload-css'  : CSS hot-reload (no page refresh)
    - 'reload-page' : explicit page reload (alias of 'reload')



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
* - `action`
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
