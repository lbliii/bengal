# Live Reload Pipeline Review

Review of the live reload pipeline for bugs, subtle issues, and architectural improvements.

---

## Bugs Fixed

### Python 2-style exception syntax

The following used `except A, B` (Python 2) instead of `except (A, B)` (Python 3):

| File | Line | Fix |
|------|------|-----|
| `live_reload.py` | 511 | `except (FileNotFoundError, IsADirectoryError)` |
| `asgi_app.py` | 303, 339 | `except (BrokenPipeError, ConnectionResetError)` etc. |
| `reload_controller.py` | 536 | `except (FileNotFoundError, PermissionError)` |
| `utils.py` | 209 | `except (ValueError, TypeError)` |
| `build_trigger.py` | 862, 870 | `except (OSError, ValueError)` etc. |
| `pid_manager.py` | 106, 108, 173, 285 | Multiple exception tuples |

**Impact**: In Python 3, `except A, B` is parsed as `except A as B` (catch A, bind to variable B). This would catch only the first exception type and shadow the second as a variable name.

---

## Potential Bugs & Subtle Issues

### 1. **Global mutable state in `live_reload.py`**

```python
_reload_generation: int = 0
_last_action: str = "reload"
_reload_sent_count: int = 0
_reload_condition = threading.Condition()
_shutdown_requested: bool = False
```

**Issue**: Module-level globals are shared across all server instances. In tests or multi-server scenarios, state can leak.

**Recommendation**: Consider a `ReloadState` class (or `ContextVar` for free-threading) encapsulating these. Inject into `run_sse_loop` and `send_reload_payload` rather than using globals.

---

### 2. **`ReloadDecision` and `EnhancedReloadDecision` are mutable**

```python
@dataclass
class ReloadDecision:
    action: str
    reason: str
    changed_paths: list[str]  # Mutable!
```

**Issue**: Callers can mutate `changed_paths` after receiving a decision. Build trigger passes `decision.changed_paths` to `send_reload_payload`; if the controller or a caller mutates it, behavior is unclear.

**Recommendation**: Use frozen dataclasses with `tuple[str, ...]`:

```python
@dataclass(frozen=True, slots=True)
class ReloadDecision:
    action: str
    reason: str
    changed_paths: tuple[str, ...]
```

---

### 3. **`changed_outputs` tuple shape is implicit**

```python
changed_outputs: tuple[tuple[str, str, str], ...]  # (path, type, phase)
```

**Issue**: No type or validation. Invalid `type_val` (e.g. `"html"` vs `OutputType.HTML.value`) causes `ValueError` in a loop; records are skipped silently.

**Recommendation**: Introduce a frozen dataclass or `TypedDict`:

```python
@dataclass(frozen=True, slots=True)
class SerializedOutputRecord:
    path: str
    type_value: str  # OutputType.value
    phase: str
```

Validate at deserialization boundary; fail fast on invalid data.

---

### 4. **`reload_hint` has no type contract**

```python
reload_hint: str | None = None  # "css-only" | "full" | "none"?
```

**Issue**: Build, executor, and trigger all pass `reload_hint` without a shared literal type. Typos (e.g. `"no"` instead of `"none"`) would not be caught.

**Recommendation**: Use `Literal["css-only", "full", "none"]` or an enum:

```python
class ReloadHint(Enum):
    NONE = "none"
    CSS_ONLY = "css-only"
    FULL = "full"
```

---

### 5. **`set_reload_action` vs `send_reload_payload` — dual API**

- `notify_clients_reload()` increments generation, uses `_last_action` (set by `set_reload_action`)
- `send_reload_payload()` builds its own payload and sets `_last_action`

**Issue**: Build trigger and dev_server only use `send_reload_payload`. `notify_clients_reload` and `set_reload_action` appear to be legacy or for a different path. Docstring says "BuildTrigger → notify_clients_reload" but code uses `send_reload_payload`.

**Recommendation**: Either deprecate `notify_clients_reload`/`set_reload_action` and document that `send_reload_payload` is the single entry point, or clarify when each is used.

---

### 6. **Controller global singleton**

```python
controller = ReloadController(use_content_hashes=True)
```

**Issue**: Single global instance. Tests patch it; production always uses content hashes. No way to configure per-site (e.g. disable content hashes for small sites).

**Recommendation**: Inject controller into `BuildTrigger` (or pass as dependency). Allows per-site config and easier testing.

---

### 7. **`write_fn` called outside lock in `run_sse_loop`**

```python
with _reload_condition:
    last_seen_generation = _reload_generation
    if _reload_generation > 0:
        write_fn(f"data: {_last_action}\n\n".encode())  # I/O inside lock!
```

**Issue**: `write_fn` does I/O (network write). Holding the lock during I/O can block other SSE connections and the build thread calling `send_reload_payload`.

**Recommendation**: Copy `_last_action` and `_reload_generation` under the lock, then call `write_fn` outside the lock. Same pattern in the main loop.

---

### 8. **Cache eviction is FIFO, not LRU**

```python
if len(cls._html_cache) > cls._html_cache_max_size:
    first_key = next(iter(cls._html_cache))
    del cls._html_cache[first_key]
```

**Issue**: `dict` iteration order is insertion order (Python 3.7+), so this evicts the oldest entry. For HTML cache, that may be fine. For asset cache, frequently accessed assets could be evicted if they were cached early.

**Recommendation**: If asset cache hit rate matters, use `functools.lru_cache` or an LRU structure. Otherwise document that eviction is FIFO.

---

### 9. **Client script: `link.cloneNode()` without `true`**

```javascript
const newLink = link.cloneNode();
```

**Issue**: `cloneNode()` without `true` does a shallow clone. Child nodes (e.g. `@import` in a `<style>`) are not cloned. For `<link rel="stylesheet">` typically there are no children, so this is usually fine.

**Recommendation**: Use `cloneNode(true)` for consistency, or add a comment that shallow clone is intentional for link elements.

---

### 10. **`translate_path` can return `None`**

```python
path = self.translate_path(self.path)
if path is None:
    return False
```

**Issue**: `SimpleHTTPRequestHandler.translate_path` returns `str`, not `str | None`. The guard may be defensive for a custom subclass. If `translate_path` never returns `None`, the check is dead code.

**Recommendation**: Verify whether any handler overrides `translate_path` to return `None`. If not, remove the check or add a type: ignore with a comment.

---

## Architectural Recommendations

### 1. **Separate reload decision from notification**

Current: `BuildTrigger._handle_reload` does decision + notification in one method.

**Suggestion**: Extract a `ReloadDecisionService` that takes `(changed_files, changed_outputs, reload_hint)` and returns `ReloadDecision`. `BuildTrigger` would call the service and then `send_reload_payload(decision)`. Easier to test and reason about.

---

### 2. **Protocol for reload notification**

```python
class ReloadNotifier(Protocol):
    def send(self, action: str, reason: str, changed_paths: list[str]) -> None: ...
```

**Benefit**: `BuildTrigger` depends on an abstraction. Tests inject a mock; production uses `send_reload_payload`. Enables future backends (e.g. WebSocket).

---

### 3. **Modularize `live_reload.py`**

The file mixes:

- SSE loop logic
- Client script (JavaScript)
- HTML injection
- HTTP handler mixin (LiveReloadMixin)
- Global state and notification

**Suggestion**: Split into:

- `live_reload/sse.py` — `run_sse_loop`, condition/generation state
- `live_reload/script.py` — `LIVE_RELOAD_SCRIPT` constant
- `live_reload/injection.py` — `inject_live_reload_into_response`, `find_html_injection_point`
- `live_reload/notification.py` — `send_reload_payload`, `notify_clients_reload`
- `live_reload/mixin.py` — `LiveReloadMixin` (if still needed for non-ASGI)

---

### 4. **Frozen dataclasses for pipeline data**

| Current | Recommended |
|---------|-------------|
| `ReloadDecision` (mutable) | `@dataclass(frozen=True, slots=True)` with `tuple[str, ...]` |
| `EnhancedReloadDecision` (mutable) | Same |
| `changed_outputs` as `tuple[tuple[str,str,str],...]` | `SerializedOutputRecord` or `OutputRecord` |
| `SnapshotEntry` (already frozen) | Keep |
| `OutputSnapshot` (mutable `files` dict) | Consider immutable view or `Mapping` |

---

### 5. **Explicit contracts for build → trigger handoff**

Define a `BuildReloadInfo` dataclass that the build produces and the trigger consumes:

```python
@dataclass(frozen=True, slots=True)
class BuildReloadInfo:
    changed_files: tuple[str, ...]
    changed_outputs: tuple[SerializedOutputRecord, ...]
    reload_hint: ReloadHint | None
```

Ensures the build and trigger agree on the shape of data.

---

## Summary

| Category | Count |
|----------|-------|
| Bugs fixed (exception syntax) | 10 |
| Potential bugs / subtle issues | 10 |
| Architectural recommendations | 5 |

**Priority fixes**: Exception syntax (done), `run_sse_loop` I/O inside lock, frozen `ReloadDecision`/`EnhancedReloadDecision`.

**Lower priority**: Modularization, protocol extraction, `BuildReloadInfo` contract.
