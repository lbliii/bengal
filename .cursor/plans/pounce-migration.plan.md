---
name: ""
overview: ""
todos: []
isProject: false
---

# Pounce Migration Plan: Replace ThreadingTCPServer with Pounce ASGI

**Status**: Planning  
**Scope**: Bengal dev server (`bengal serve`)  
**Goal**: Use Pounce as the sole HTTP server, remove ThreadingTCPServer and BengalRequestHandler.

**Prerequisite**: Pounce 0.2.0 ships first. This plan targets `bengal-pounce>=0.2.0`.

---

## Pounce 0.2.0 Compatibility

The plan assumes Pounce 0.2.0 is available. Relevant 0.2.0 features:


| Feature                                  | Use in Bengal             | Notes                                                           |
| ---------------------------------------- | ------------------------- | --------------------------------------------------------------- |
| **Server.shutdown()**                    | PounceBackend             | Programmatic shutdown; thread-safe                              |
| **Connection draining**                  | Graceful shutdown         | `shutdown_timeout` for clean exit                               |
| **SSE compression**                      | Auto-disabled             | Pounce detects `text/event-stream`, skips compression           |
| **access_log_filter**                    | Skip `/__bengal_reload__` | `(method, path, status) -> bool`; exclude long-lived SSE        |
| **debug**                                | Optional                  | `debug=True` for rich error pages in dev                        |
| **StaticFiles / create_static_handler**  | Not used                  | We need HTML injection + rebuilding page; custom app is simpler |
| **Static via ServerConfig.static_files** | Not used                  | Same reason; our app handles static with custom logic           |
| **port=0**                               | Ephemeral port            | test_bengal_compat uses it; verify for port fallback            |
| **No breaking changes**                  | Stable API                | CHIRP adoption docs confirm Server, ServerConfig, run() stable  |


**Config for dev server**: `access_log=True`, `compression=True` (SSE auto-excluded), `debug=True` optional, `access_log_filter` to skip SSE path.

---

## Current State

### Architecture

```
DevServer
  └── _create_server() → create_threading_tcp_backend()
        └── ThreadingTCPServer + BengalRequestHandler
  └── ResourceManager (cleanup: SSE shutdown, server shutdown, watcher, PID)
  └── WatcherRunner + BuildTrigger (file watching, rebuilds)
```

### BengalRequestHandler Responsibilities


| Feature                             | Location                                      | Transport    |
| ----------------------------------- | --------------------------------------------- | ------------ |
| SSE `/__bengal_reload__`            | `live_reload.handle_sse()` → `run_sse_loop()` | HTTP (wfile) |
| HTML injection (live reload script) | `live_reload.serve_html_with_live_reload()`   | HTTP         |
| Static file serving                 | `SimpleHTTPRequestHandler`                    | HTTP         |
| Build-aware asset caching           | `serve_asset_with_cache()`                    | HTTP         |
| Rebuilding page (during builds)     | `responses.get_rebuilding_page_html()`        | HTTP         |
| Custom 404                          | `responses` + handler                         | HTTP         |
| Request logging                     | `RequestLogger` mixin                         | HTTP         |


### Pre-Wired (Already Done)

- `create_bengal_dev_app()` — ASGI skeleton (501 for SSE, 404 elsewhere)
- `run_sse_loop(write_fn)` — transport-agnostic SSE loop
- `build_state` — shared `build_in_progress`, `active_palette`
- `responses.get_rebuilding_page_html()` — palettes, path placeholder
- `ServerBackend` protocol — `start()`, `shutdown()`, `port`

---

## Target Architecture

```
DevServer
  └── _create_server() → create_pounce_backend()
        └── PounceBackend(Server(config, app))
  └── app = create_bengal_dev_app(output_dir, build_in_progress, active_palette)
        ├── GET /__bengal_reload__ → SSE (run_sse_loop via async bridge)
        └── * → static files (with HTML injection, rebuilding page, 404)
```

---

## Phase 1: Complete the ASGI App

### 1.1 Wire SSE in `create_bengal_dev_app`

**Problem**: `run_sse_loop(write_fn)` is sync and blocks. ASGI `send` is async.

**Options**:

- **A. Thread bridge**: Run `run_sse_loop` in `asyncio.to_thread()` or a dedicated thread. The `write_fn` queues bytes; an async task drains the queue and calls `await send({"type": "http.response.body", "body": chunk, "more_body": True})`. Complexity: medium. Risk: thread coordination.
- **B. Async refactor**: Add `async def run_sse_loop_async(send, ...)` that uses `asyncio.Condition` instead of `threading.Condition`. Reuse the same event logic. Complexity: low. Risk: duplicate code paths until we remove sync version.
- **C. Sync in thread, send via queue**: Spawn thread that runs `run_sse_loop`. `write_fn` puts bytes on a queue. ASGI handler awaits `queue.get()` in a loop and sends. Clean separation. Complexity: low.

**Recommendation**: **C** — minimal changes to `run_sse_loop`, clear boundary.

**Tasks**:

1. In `asgi_app.py`, for `GET /__bengal_reload__`:
  - Create `queue: asyncio.Queue[bytes]`
  - `write_fn = lambda b: queue.put_nowait(b)` (run in thread)
  - Start thread: `threading.Thread(target=run_sse_loop, args=(write_fn,), daemon=True)`
  - Send headers (`text/event-stream`, cache-control, etc.)
  - Loop: `while True: chunk = await queue.get(); await send({"type": "http.response.body", "body": chunk, "more_body": True})` until sentinel/empty
  - Handle disconnect: catch `BrokenPipeError` / `ConnectionResetError`, set `_shutdown_requested` or use a sentinel
2. Register `register_sse_shutdown()` in ResourceManager so SSE clients exit before server shutdown (unchanged).

### 1.2 Static File Serving with HTML Injection

**Options**:

- **A. Pounce `StaticFiles` / `create_static_handler**`: Use Pounce's static handler, then wrap with middleware that intercepts HTML responses and injects the live reload script. Pounce's static handler returns full responses; we need to buffer, inject, and re-send.
- **B. Custom ASGI static handler**: Implement a minimal static file handler that:
  - Serves files from `output_dir`
  - For `*.html`: read file, inject `LIVE_RELOAD_SCRIPT`, send
  - For others: stream file (or use sendfile if Pounce exposes it)
  - Uses `build_state.get_build_in_progress()` for rebuilding page
- **C. Pounce static + post-process**: Use `create_static_handler({"/": output_dir})` as inner app. Outer middleware: if response is HTML (by path or content-type), read body, inject script, send modified body. Simpler but may buffer large HTML.

**Recommendation**: **B** — full control, matches current behavior (build-aware, rebuilding page, 404). Can later optimize with Pounce's sendfile if we compose.

**Tasks**:

1. Implement `serve_static_asgi(scope, receive, send, output_dir, build_in_progress, active_palette)`:
  - Resolve path from `scope["path"]` (handle `/` → `index.html`, trailing slash)
  - If `build_in_progress()` and path looks like HTML → `get_rebuilding_page_html(path, palette)` → 200
  - Else: `pathlib.Path(output_dir) / path` → if file exists:
    - If HTML: read, `inject_live_reload_into_response(body)`, send
    - Else: stream file (Content-Type, Content-Length, body)
  - Else: 404 (use existing 404 logic from responses or simple "Not Found")
2. Add `inject_live_reload_into_response` (or reuse from `live_reload`) — pure function taking bytes, returning bytes.
3. Wire into `create_bengal_dev_app`: after SSE branch, call `serve_static_asgi(...)`.

### 1.3 Build-Aware Behavior

- **Rebuilding page**: When `build_in_progress()` is True and request is for an HTML path, return `get_rebuilding_page_html(path, active_palette)`.
- **Asset caching during build**: Current handler serves from cache during atomic rewrites. For ASGI, we can either (a) keep a small in-memory cache for CSS/JS during build, or (b) serve from disk and accept rare transient 404 during overwrite. **Recommendation**: Start with (b); add cache if needed.

---

## Phase 2: Pounce Backend

### 2.1 Add Pounce Dependency

```toml
# pyproject.toml
dependencies = [
    ...
    "bengal-pounce>=0.2.0",  # Requires 0.2.0 (shipped before this migration)
]
```

**Pre-requisite**: Ensure Pounce 0.2.0 is released and published to PyPI before merging.

### 2.2 Implement `PounceBackend`

```python
# bengal/server/backend.py

class PounceBackend:
    """Backend that runs the Bengal dev ASGI app via Pounce."""

    def __init__(self, server: "pounce.Server", port: int) -> None:
        self._server = server
        self._port = port

    def start(self) -> None:
        """Run Pounce (blocks until shutdown)."""
        self._server.run()

    def shutdown(self) -> None:
        """Trigger graceful shutdown."""
        self._server.shutdown()  # or equivalent

    @property
    def port(self) -> int:
        return self._port
```

**Note**: Pounce's `Server.run()` blocks. We need a way to trigger shutdown from another thread (e.g. signal handler, or `server.shutdown()`). Check Pounce's API for programmatic shutdown.

### 2.3 `create_pounce_backend`

```python
def create_pounce_backend(
    host: str,
    port: int,
    output_dir: Path,
    build_in_progress: Callable[[], bool],
    active_palette: str | None,
) -> PounceBackend:
    app = create_bengal_dev_app(
        output_dir=output_dir,
        build_in_progress=build_in_progress,
        active_palette=active_palette,
    )
    config = ServerConfig(host=host, port=port, ...)
    server = Server(config, app)
    return PounceBackend(server, port)
```

### 2.4 DevServer Integration

- `_create_server()`: Call `create_pounce_backend(...)` instead of `create_threading_tcp_backend(...)`.
- Pass `build_state.get_build_in_progress` and `build_state.get_active_palette` (or a lambda) into the backend.
- `backend.start()` and `backend.shutdown()` — same interface. ResourceManager already handles `ServerBackend` (has `start`, `port`; shutdown calls `backend.shutdown()`).
- **Serve-first**: Currently we start `backend.start()` in a thread. Pounce's `run()` blocks. Same pattern: `threading.Thread(target=backend.start, daemon=True)`.
- **Build-first**: `backend.start()` blocks. Same as today.

---

## Phase 3: Remove ThreadingTCPServer

### 3.1 Delete or Deprecate

- `create_threading_tcp_backend`
- `ThreadingTCPServerBackend`
- `BengalRequestHandler` (and `RequestLogger`, `LiveReloadMixin` if only used there)
- `request_handler.py` — after migrating all behavior to ASGI

### 3.2 Retain (Shared Logic)

- `live_reload.run_sse_loop` — used by ASGI via thread bridge
- `live_reload.LIVE_RELOAD_SCRIPT`, `inject_live_reload_into_response`
- `live_reload.notify_clients_reload`, `send_reload_payload`, etc. — used by BuildTrigger
- `responses.get_rebuilding_page_html`, `PALETTE_COLORS`
- `build_state`
- `resource_manager.register_sse_shutdown`

### 3.3 Update Tests

- `test_asgi_app.py`: Update expectations — SSE returns 200 with stream, static returns 200/404.
- `test_backend.py`: Add `PounceBackend` tests; remove or keep `ThreadingTCPServerBackend` tests if we keep it for a transition period.
- Integration: `bengal serve` with a test site, verify SSE, static, HTML injection, rebuilding page.

---

## Phase 4: Cleanup and Polish

- Remove `socketserver` usage from `backend.py`.
- Update `resource_manager.register_server` if Pounce backend has different shutdown semantics.
- CLI: Ensure `bengal serve` still works with `--port`, `--host`, `--no-watch`, etc.
- Documentation: Update dev server docs to mention Pounce.

---

## Dependency Order

```
Phase 1.1 (SSE in ASGI)     → 1.2 (static + injection)  → 1.3 (build-aware)
       ↓                              ↓
Phase 2.1 (add pounce)  →  2.2 (PounceBackend)  →  2.3 (create_pounce_backend)  →  2.4 (DevServer)
       ↓
Phase 3 (remove TCPServer)
       ↓
Phase 4 (cleanup)
```

---

## Risks and Mitigations


| Risk                      | Mitigation                                                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Pounce API changes        | Pin version, add integration test                                                                                 |
| SSE thread/async deadlock | Use queue with timeout, sentinel for shutdown                                                                     |
| Static file performance   | Start simple; add sendfile later if needed                                                                        |
| Regression in live reload | Parity tests: SSE connect, reload event, CSS hot reload                                                           |
| Port fallback             | DevServer already resolves `actual_port` before `_create_server`. Pass resolved port to Pounce; no change to flow |


---

## Out of Scope (Future)

- Pounce's `--reload` for code changes (we use our own watcher for content)
- HTTP/2, WebSocket (dev server is HTTP/1.1 + SSE)
- TLS (dev server is localhost only)

---

## Estimated Effort


| Phase     | Tasks                      | Estimate     |
| --------- | -------------------------- | ------------ |
| 1.1       | SSE in ASGI                | 0.5–1 day    |
| 1.2       | Static + HTML injection    | 1–1.5 days   |
| 1.3       | Build-aware                | 0.5 day      |
| 2         | Pounce backend + DevServer | 1 day        |
| 3         | Remove TCPServer           | 0.5 day      |
| 4         | Cleanup                    | 0.5 day      |
| **Total** |                            | **4–5 days** |


