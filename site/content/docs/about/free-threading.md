---
title: Free-Threading
description: How Bengal uses Python 3.14t for parallel page rendering
weight: 25
icon: cpu
tags:
- free-threading
- performance
- architecture
keywords:
- free-threading
- PEP 703
- nogil
- parallel
- ThreadPoolExecutor
category: explanation
---

# Free-Threading

Bengal is designed for Python 3.14t (free-threaded Python). On free-threaded builds, page rendering achieves true parallelism — no GIL contention. The same code runs on standard Python; it just uses sequential rendering until you switch interpreters.

## Run It

```bash
uv python install 3.14t
uv run --python=3.14t bengal build
```

Bengal auto-detects free-threading at runtime and uses `ThreadPoolExecutor` when available.

## Key Patterns

### Runtime Detection

Bengal checks `sys._is_gil_enabled()` to decide whether threads provide real parallelism:

```python
def is_free_threaded() -> bool:
    if hasattr(sys, "_is_gil_enabled"):
        try:
            return not sys._is_gil_enabled()
        except (AttributeError, TypeError):
            pass
    # Fallback: sysconfig for Py_GIL_DISABLED
    ...
```

When `True`, Bengal spins up a `ThreadPoolExecutor` for page rendering.

### Immutable Snapshots (Lock-Free)

After content discovery, Bengal freezes the entire site into immutable dataclasses — `PageSnapshot`, `SectionSnapshot`, `SiteSnapshot`. During rendering, workers only read from snapshots. No locks in the hot path.

```python
@dataclass(frozen=True, slots=True)
class PageSnapshot:
    title: str
    href: str
    source_path: Path
    parsed_html: str
    content_hash: str
    section: SectionSnapshot | None = None
    next_page: PageSnapshot | None = None
    prev_page: PageSnapshot | None = None
    ...
```

### Context Propagation

`ThreadPoolExecutor.submit()` does not inherit `ContextVar` values. Bengal uses `contextvars.copy_context().run` so each worker gets the parent's context:

```python
ctx = contextvars.copy_context()
future_to_page = {
    executor.submit(ctx.run, process_page_with_pipeline, page): page
    for page in batch
}
```

### Thread-Local Pipelines

Each worker gets its own rendering pipeline via `threading.local()`, avoiding shared mutable state:

```python
def get_or_create_pipeline(current_gen, create_pipeline_fn):
    needs_new = (
        not hasattr(thread_local, "pipeline")
        or getattr(thread_local, "pipeline_generation", -1) != current_gen
    )
    if needs_new:
        thread_local.pipeline = create_pipeline_fn()
        thread_local.pipeline_generation = current_gen
    return thread_local.pipeline
```

## Performance

| Workers | Time (1K pages) | Speedup |
|---------|-----------------|---------|
| 1 | ~9.0 s | 1.0x |
| 4 | ~3.0 s | 3.0x |
| 8 | ~2.5 s | 3.6x |

On free-threaded Python, ~1.5–2x faster than GIL builds at the same worker count. Incremental builds: 35–80 ms for a single-page change on an 800-page site.

## Code References

| Pattern | File |
|---------|------|
| GIL detection | [bengal/utils/concurrency/gil.py](https://github.com/lbliii/bengal/blob/main/bengal/utils/concurrency/gil.py) |
| Parallel rendering, thread-local pipeline | [bengal/orchestration/render/parallel.py](https://github.com/lbliii/bengal/blob/main/bengal/orchestration/render/parallel.py) |
| Context propagation to workers | [bengal/utils/concurrency/context_propagation.py](https://github.com/lbliii/bengal/blob/main/bengal/utils/concurrency/context_propagation.py) |
| Immutable snapshots | [bengal/snapshots/types.py](https://github.com/lbliii/bengal/blob/main/bengal/snapshots/types.py) |
| Rendering (asset ContextVar) | [bengal/orchestration/build/rendering.py](https://github.com/lbliii/bengal/blob/main/bengal/orchestration/build/rendering.py) |

## See Also

- [[docs/building/performance/large-sites|Large Site Optimization]] — Free-threading notes and scaling
- [[docs/building/performance|Performance Overview]] — Incremental and parallel strategies
- [Bengal source](https://github.com/lbliii/bengal)
