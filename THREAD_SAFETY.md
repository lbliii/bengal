# Thread Safety Guide

Bengal supports Python 3.14 free-threading (PEP 703) with protected shared state for safe concurrent execution during parallel rendering.

## Protected Modules

| Module | Lock | Pattern | Purpose |
|--------|------|---------|---------|
| `directives/cache.py` | `DirectiveCache._lock` | Lock per cache op | LRU cache for parsed directives |
| `icons/resolver.py` | `_icon_lock` | Lock per cache op | Icon SVG loading and caching |
| `rendering/context/__init__.py` | `_context_lock` | Double-check | Global context wrapper cache |
| `directives/registry.py` | `_registry_lock` | Double-check | Lazy directive class loading |
| `server/live_reload.py` | `_reload_condition` | Condition var | SSE reload coordination |
| `rendering/pygments_cache.py` | `_cache_lock` | Lock per cache op | Lexer instance caching |
| `directives/factory.py` | `_INSTANCE_LOCK` | Double-check | Directive instance creation |

## Lock Acquisition Order

When holding multiple locks, always acquire in this order to prevent deadlocks:

1. `_icon_lock` (icons/resolver.py)
2. `DirectiveCache._lock` (directives/cache.py)
3. `_cache_lock` (rendering/pygments_cache.py)
4. `_context_lock` (rendering/context/__init__.py)
5. `_registry_lock` (directives/registry.py)
6. `_reload_condition` (server/live_reload.py)

**No code path should acquire these in reverse order.**

## Patterns

### Pattern 1: Simple Lock Protection

Use for caches with atomic operations:

```python
import threading

_cache: dict[str, Any] = {}
_lock = threading.Lock()

def get_cached(key: str) -> Any | None:
    with _lock:
        return _cache.get(key)

def set_cached(key: str, value: Any) -> None:
    with _lock:
        _cache[key] = value
```

### Pattern 2: Lock with Expensive Computation Outside

Use when cache miss requires expensive I/O or computation:

```python
def get_or_compute(key: str) -> Any:
    # Check cache under lock
    with _lock:
        if key in _cache:
            return _cache[key]

    # Expensive work OUTSIDE lock (allows parallelism)
    value = expensive_computation(key)

    # Store under lock
    with _lock:
        _cache[key] = value
    return value
```

### Pattern 3: Double-Check Locking

Use for one-time initialization of singletons:

```python
_value: Any | None = None
_lock = threading.Lock()

def get_value() -> Any:
    global _value

    # Fast path: already initialized
    if _value is not None:
        return _value

    with _lock:
        # Double-check after acquiring lock
        if _value is not None:
            return _value
        _value = compute_once()
        return _value
```

### Pattern 4: Condition Variable

Use for signaling between threads:

```python
_condition = threading.Condition()
_state = initial_state

def wait_for_change(current_value):
    with _condition:
        while _state == current_value:
            _condition.wait(timeout=1.0)
        return _state

def notify_change(new_value):
    global _state
    with _condition:
        _state = new_value
        _condition.notify_all()
```

## When NOT to Lock

### CLI-Only Globals

CLI commands run in a single-threaded context. No lock needed:

```python
# bengal/output/globals.py
# Note: CLI commands are single-threaded; no lock needed.
_cli_output: CLIOutput | None = None
```

### Thread-Local Storage

Use `threading.local()` for per-thread state:

```python
from bengal.utils.thread_local import ThreadLocalCache

# One parser instance per thread - no locking needed
_parser_cache = ThreadLocalCache(create_parser)
parser = _parser_cache.get()
```

### Immutable Data

Constants and frozen data don't need protection:

```python
# Read-only after initialization - safe
DIRECTIVE_MAP: frozenset[str] = frozenset({...})
```

## Lock Choice Guidelines

| Scenario | Use |
|----------|-----|
| Simple mutex | `threading.Lock()` |
| Re-entrant (nested calls) | `threading.RLock()` |
| Signal between threads | `threading.Condition()` |
| Per-key serialization | `PerKeyLockManager` |
| Per-thread isolation | `ThreadLocalCache` |

## Existing Utilities

Bengal provides thread-safety utilities in `bengal/utils/`:

### PerKeyLockManager

Serialize work for the SAME resource while allowing parallelism for DIFFERENT resources:

```python
from bengal.utils.concurrent_locks import PerKeyLockManager

locks = PerKeyLockManager()

with locks.get_lock(page.url):
    # Only one thread can process this URL at a time
    compile_template(page)
```

### ThreadLocalCache

One instance per thread, no locking needed:

```python
from bengal.utils.thread_local import ThreadLocalCache

_pipeline_cache = ThreadLocalCache(RenderPipeline)
pipeline = _pipeline_cache.get()  # Thread-specific instance
```

### ThreadSafeSet

Thread-safe set for tracking unique items:

```python
from bengal.utils.thread_local import ThreadSafeSet

_created_dirs = ThreadSafeSet()

if _created_dirs.add_if_new(dir_path):
    # Only one thread will create this directory
    os.makedirs(dir_path)
```

## Testing

Run thread safety tests:

```bash
uv run pytest tests/test_thread_safety.py -v
```

The test suite includes:

- Concurrent cache access tests
- Race condition detection
- Lock ordering documentation
- Stress tests for parallel rendering

## References

- [PEP 703 – Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- [Python 3.14 Free-Threading Build](https://docs.python.org/3.14/howto/free-threading-python.html)
- `plan/drafted/rfc-thread-safety-sweep.md` — Thread safety RFC with full audit
- `plan/drafted/rfc-concurrent-compilation-locks.md` — Original lock design rationale
