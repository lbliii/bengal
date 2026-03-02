# Research Report: K-RUN-007 '_Undefined' object is not callable on Full Rebuild

**Date:** 2025-03-02  
**Error:** `TypeError: '_Undefined' object is not callable` (K-RUN-007)  
**Location:** `blog/single.html:44` — `{% from 'partials/components/newsletter-cta.html' import newsletter_cta %}`  
**Reproduction:** Full rebuild (parallel rendering); does not occur on incremental builds

---

## Executive Summary

The error occurs when `newsletter_cta` resolves to the `_Undefined` sentinel instead of the macro function, then is invoked as `newsletter_cta()`. The failure is **only on full rebuilds** because parallel rendering is enabled (35+ pages). Incremental builds use sequential rendering (below `parallel_threshold`), so the error does not appear.

**Root cause hypothesis:** A concurrency or race condition during parallel template rendering when resolving `{% from 'X' import y %}` macros, or when the imported macro is used in a context where the lookup returns `UNDEFINED` instead of the macro.

---

## 1. Compiler: `{% from 'X' import y %}` Code Generation

**File:** `kida/src/kida/compiler/statements/template_structure.py:324-372`

```python
def _compile_from_import(self, node: FromImport) -> list[ast.stmt]:
    # Generates:
    #   _imported = _import_macros(template_name, with_context, ctx)
    #   ctx['name'] = _imported['name'] for each imported name
```

- Uses direct subscript: `ctx['newsletter_cta'] = _imported['newsletter_cta']`
- If `newsletter_cta` is missing from `_imported`, this raises **KeyError**, not `TypeError`
- So `UNDEFINED` must come from somewhere else (e.g. `_getattr` path or `env.globals`)

---

## 2. `_import_macros` Flow

**File:** `kida/src/kida/template/core.py:474-521`

1. `get_render_context_required()` → current `RenderContext` from `ContextVar`
2. Circular import check via `render_ctx.import_stack`
3. `render_ctx.import_stack.append(template_name)`
4. `child_ctx = render_ctx.child_context(template_name)`
5. `set_render_context(child_ctx)` → set `ContextVar` to child
6. `import_ctx = dict(_env.globals)` (new dict per call)
7. `import_ctx.update(context)` if `with_context`
8. `imported._render_func(import_ctx, None)` → template mutates `import_ctx` with macros
9. `return import_ctx`
10. `render_ctx.import_stack.pop()`

---

## 3. Shared State and Thread Safety

| Component | Location | Thread Safety |
|-----------|----------|---------------|
| `RenderContext` | `kida/render_context.py:245-250` | `ContextVar` — thread-local |
| `import_stack` | `kida/render_context.py:86-88, 212` | Shared between parent and child within one render; each thread has its own `RenderContext` |
| `import_ctx` | `kida/template/core.py:512-516` | New dict per `_import_macros` call; not shared |
| `cached_blocks` | `kida/render_context.py:210-211` | Shared in child_context; each top-level render has its own |
| `_env` (Environment) | Shared across threads | LRU cache uses RLock; thread-safe |

---

## 4. How `{% def %}` Adds Macros

**File:** `kida/src/kida/compiler/statements/functions.py:286-296`

```python
# Assign to context: ctx['name'] = _def_name
assign = ast.Assign(
    targets=[ast.Subscript(value=ast.Name(id="ctx"), slice=ast.Constant(value=def_name), ctx=ast.Store())],
    value=ast.Name(id=func_name, ctx=ast.Load()),
)
```

The macro is stored in the context dict passed to `_render_func`. For imports, that dict is `import_ctx`, which is mutated in place and returned.

---

## 5. Where `_Undefined` Comes From

**File:** `kida/src/kida/template/helpers.py:33-66`

- `UNDEFINED` is a singleton `_Undefined` instance
- Returned by `_safe_getattr` on failed attribute/key lookup (e.g. `obj.missing_attr`)

**File:** `kida/src/kida/template/core.py:1157-1201`

- `_safe_getattr` returns `UNDEFINED` when attribute/key not found
- Used for `Getattr` nodes (e.g. `{{ obj.newsletter_cta() }}`), not direct `Name` lookups

**File:** `kida/src/kida/template/helpers.py:175-213`

- `lookup_scope` raises `UndefinedError` if name not found — does **not** return `UNDEFINED`
- Used for direct names like `{{ newsletter_cta() }}`

So `_Undefined` would only appear if:

1. The call goes through `_getattr` (e.g. `{{ obj.newsletter_cta() }}` where `obj` has no `newsletter_cta`), or
2. `newsletter_cta` is explicitly set to `UNDEFINED` in the context (e.g. via `env.globals` or another shared source).

---

## 6. Template Structure

**newsletter-cta.html** — only defines the macro:

```html
{% def newsletter_cta() %}
<div class="newsletter-cta">...</div>
{% end %}
```

**blog/single.html** — imports and uses:

```html
{% from 'partials/components/newsletter-cta.html' import newsletter_cta %}
...
{{ newsletter_cta() }}  {# line 149, inside {% if show_newsletter %} #}
```

---

## 7. Parallel vs Sequential Rendering

**File:** `bengal/orchestration/build/rendering.py:523-528`

```python
use_parallel = not force_sequential and should_parallelize(
    len(pages_to_build), workload_type=WorkloadType.MIXED
)
```

**File:** `bengal/utils/concurrency/workers.py:278`

- `should_parallelize(3)` → False (below threshold)
- `should_parallelize(35)` → True (full rebuild)

---

## 8. Findings Summary

| Area | Finding |
|------|---------|
| Compiler | `_compile_from_import` emits `ctx['name'] = _imported['name']` |
| `_import_macros` | Uses `import_ctx = dict(_env.globals)`, runs `_render_func(import_ctx, None)`, returns `import_ctx` |
| `import_stack` | Shared between parent and child within one render; thread-local via `ContextVar` |
| `import_ctx` | New dict per call; not shared across threads |
| `{% def %}` | Emits `ctx['name'] = _def_name`; mutates the passed context dict |
| `RenderContext` | Stored in `ContextVar`; thread-local |
| `_Undefined` | Returned by `_safe_getattr` on failed attribute access |
| Tests | No tests for parallel rendering with import macros |

---

## 9. Hypotheses for K-RUN-007

1. **`env.globals`**  
   If `newsletter_cta` exists in `env.globals` and is set to `UNDEFINED`, it would be copied into `import_ctx` before `_render_func` runs. The `{% def %}` would overwrite it, so this is unlikely unless the macro is never executed.

2. **`_getattr` path**  
   If the call is compiled as `_getattr(obj, 'newsletter_cta')()` (e.g. `{{ obj.newsletter_cta() }}`), a missing attribute would yield `UNDEFINED` and cause the error. The default blog template uses `{{ newsletter_cta() }}`, which should use `_lookup_scope`, but other templates or dynamic constructs might use `_getattr`.

3. **Shared `import_stack` under free-threading**  
   In free-threaded Python, `ContextVar` behavior can differ. If `import_stack` were ever shared across threads (e.g. due to context propagation), concurrent `append`/`pop` could corrupt state.

4. **Template cache / Environment sharing**  
   Bengal uses a shared `Environment` across threads. If template compilation or cache population has a race, one thread could get a partially-initialized template or wrong context.

5. **Block/extends scope**  
   When `blog/single` extends `blog/shell`, the block content is rendered in a specific scope. If the scope or `_scope_stack` is misconfigured or shared incorrectly during parallel execution, lookups could fail or return `UNDEFINED`.

---

## 10. Recommendations

1. **Immediate workaround:** Run `bengal build --no-parallel` to force sequential rendering and confirm the failure disappears.
2. **Add regression test:** Run `{% from X import y %}` and `{{ y() }}` under `ThreadPoolExecutor` with multiple concurrent renders.
3. **Isolate import_stack:** Use a copy of `import_stack` per `_import_macros` call instead of sharing the parent's list.
4. **Add assertions:** In `_import_macros`, verify `import_ctx` contains the expected macro before returning.
5. **Improve error handling:** Map `'_Undefined' object is not callable` to a clearer K-RUN-007 message with a hint about the import macro and parallel rendering.

---

## 11. References

| File | Lines |
|------|-------|
| `kida/compiler/statements/template_structure.py` | 324-372 |
| `kida/template/core.py` | 474-521, 1157-1201 |
| `kida/template/helpers.py` | 33-66, 175-213 |
| `kida/render_context.py` | 86-88, 210-212, 245-250 |
| `bengal/orchestration/build/rendering.py` | 523-528 |
| `bengal/utils/concurrency/workers.py` | 278 |
