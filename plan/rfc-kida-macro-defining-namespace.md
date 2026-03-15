# RFC: Kida Macro Defining-Namespace Injection

**Status**: Draft  
**Created**: 2026-03-14  
**Target**: Kida (template engine), Bengal (consumer)  
**Priority**: P1 (build-blocking bug class)  
**Source**: Code deep dive — `_Undefined object is not callable` in macro cross-template calls

---

## Executive Summary

Imported macros that call other macros (or use variables from their defining template) fail when invoked from a different template. The error `_Undefined object is not callable` occurs because macros resolve names in the **caller's context** instead of their **defining template's namespace**. This RFC proposes injecting the defining template's namespace into `MacroWrapper` so imported macros close over their dependencies regardless of caller.

| Aspect | Value |
|--------|-------|
| **Root cause** | MacroWrapper forwards calls without injecting defining namespace |
| **Fix location** | `kida/template/render_helpers.py` |
| **Estimated effort** | 2–4 hours |
| **Risk** | Low (localized change, no compiler changes) |

---

## Problem Statement

### Observed Failure

Bengal builds fail with 342 suppressed errors:

```
_Undefined object is not callable
```

Traceback points to macro calls inside imported macros, e.g.:

- `article_card` (in `partials/components/article.html`) calls `tag_list(article_tags, small=true)` at line 86
- When `article_card` is invoked from `tag.html`, `tag_list` resolves to `_Undefined`
- Same pattern for `pagination` (tag.html:22) and `newsletter_cta` (blog/single.html:44)

### Template Structure

```
tag.html
  {% from 'partials/components/article.html' import article_card %}
  {% from 'partials/components/tags.html' import tag_list %}
  {% from 'partials/navigation-components.html' import pagination %}
  ...
  {{ article_card(post, show_excerpt=true) }}   ← article_card runs in tag.html's context
  {{ pagination(current_page, total_pages, base_url) }}

article.html
  {% from 'partials/components/tags.html' import tag_list %}
  {% def article_card(article, show_excerpt=true, show_image=false) %}
    ...
    {{ tag_list(article_tags, small=true) }}   ← tag_list must be in scope
  {% end %}
```

When `article_card` runs, it looks up `tag_list` via `_lookup_scope(ctx, _scope_stack, name)`. The effective `ctx` is built from `_outer_ctx` passed to the macro. If the caller (tag.html) did not import `tag_list`, the macro sees `_Undefined`.

---

## Root Cause Analysis (Code Deep Dive)

### 1. Import Flow (`_import_macros`)

**File**: `kida/template/render_helpers.py:381–441`

```python
def _import_macros(template_name, with_context, context, names=None):
    ...
    import_ctx = {k: v for k, v in _env.globals.items() if v is not UNDEFINED}
    if with_context:
        import_ctx.update(context)
    imported._render_func(import_ctx, None)   # Run defining template
    ...
    for key, val in list(import_ctx.items()):
        if callable(val) and not isinstance(val, type):
            import_ctx[key] = _make_macro_wrapper(
                val, template_name, source_file, macro_source, macro_name=key
            )
    return import_ctx
```

- The defining template runs with `import_ctx`; macros and their dependencies populate it.
- Macros are wrapped with `MacroWrapper` for error attribution.
- The returned `import_ctx` is merged into the caller's context.

### 2. Macro Compilation (`_compile_def`)

**File**: `kida/compiler/statements/functions.py:114–299`

```python
# Generated signature:
def _def_article_card(article, *, _caller=None, _outer_ctx=ctx):
    ctx = {**_outer_ctx, 'article': article, ...}
    ...
    return _Markup(''.join(buf))
```

- Macros receive `_outer_ctx` (default: `ctx` from enclosing scope).
- Body uses `ctx = {**_outer_ctx, 'arg1': arg1, ...}`; lookups use `_lookup_scope(ctx, _scope_stack, name)`.

### 3. MacroWrapper Call Path

**File**: `kida/template/render_helpers.py:89–137`

```python
@dataclass(frozen=True, slots=True)
class MacroWrapper:
    _fn: Callable[..., object]
    ...

    def __call__(self, *args: object, **kwargs: object) -> object:
        ...
        return self._fn(*args, **kwargs)   # No _outer_ctx injection
```

- `MacroWrapper` forwards `*args, **kwargs` only.
- Call sites (e.g. `{{ article_card(post) }}`) do not pass `_outer_ctx` for imported macros.
- The macro falls back to its default `_outer_ctx=ctx`, which is captured from the **defining** template's scope at definition time.

### 4. Why the Closure Fails

In theory, the default `_outer_ctx=ctx` should capture the defining template's `import_ctx` (which includes `tag_list`) when the macro is defined. In practice:

1. **Extends flow**: With `{% extends %}`, the child's `_globals_setup` may not run before blocks execute (see `_make_render_extends_body` — it does not call `_globals_setup` before `_extends`).
2. **Caller context wins**: When the block runs, it receives the parent's `ctx`. The macro's closure may not reliably see the defining template's namespace across different render paths.
3. **Explicit is better**: Relying on closure capture is fragile; explicitly injecting the defining namespace is robust.

### 5. FuncCall Compilation

**File**: `kida/compiler/expressions.py:316–332`

- For regular macros (non-Region), the compiler does **not** add `_outer_ctx` to the call.
- Only Region callables get `_outer_ctx=ctx` and `_blocks` explicitly.
- So `{{ article_card(post) }}` compiles to `article_card(post, show_excerpt=True)` — no `_outer_ctx`.

---

## Proposed Solution

### Design: Defining-Namespace Injection in MacroWrapper

Extend `MacroWrapper` to capture and inject the defining template's namespace on each call.

**Principle**: Macros close over their **defining** template's namespace, not the caller's. The caller's context can override for explicit parameter passing, but dependencies (e.g. `tag_list`) come from the defining template.

### Implementation

#### 1. Extend MacroWrapper

**File**: `kida/template/render_helpers.py`

```python
@dataclass(frozen=True, slots=True)
class MacroWrapper:
    _fn: Callable[..., object]
    _defining_namespace: dict[str, Any]  # NEW: defining template's namespace
    _kida_source_template: str
    _kida_source_file: str | None
    _source: str | None
    _kida_macro_name: str | None

    def __call__(self, *args: object, **kwargs: object) -> object:
        from kida.render_context import get_render_context_required

        render_ctx = get_render_context_required()
        # ... existing template_stack / attribution logic ...

        # Inject defining namespace as _outer_ctx so macro sees its dependencies
        kwargs_with_ctx = dict(kwargs)
        kwargs_with_ctx["_outer_ctx"] = self._defining_namespace

        try:
            return self._fn(*args, **kwargs_with_ctx)
        finally:
            # ... existing cleanup ...
```

The macro receives `_outer_ctx=self._defining_namespace`, so variable lookups (e.g. `tag_list`) resolve from the defining template's namespace.

#### 2. Pass Defining Namespace in `_import_macros`

**File**: `kida/template/render_helpers.py`

```python
# After: imported._render_func(import_ctx, None)
defining_namespace = dict(import_ctx)  # Snapshot at import time

for key, val in list(import_ctx.items()):
    if callable(val) and not isinstance(val, type):
        import_ctx[key] = _make_macro_wrapper(
            val,
            template_name,
            source_file,
            macro_source,
            macro_name=key,
            defining_namespace=defining_namespace,  # NEW
        )
```

#### 3. Update `_make_macro_wrapper`

```python
def _make_macro_wrapper(
    macro_fn: Callable[..., object],
    source_template: str,
    source_file: str | None,
    source: str | None = None,
    macro_name: str | None = None,
    defining_namespace: dict[str, Any] | None = None,
) -> MacroWrapper:
    return MacroWrapper(
        _fn=macro_fn,
        _defining_namespace=defining_namespace or {},
        _kida_source_template=source_template,
        _kida_source_file=source_file,
        _source=source,
        _kida_macro_name=macro_name,
    )
```

### Edge Cases

| Case | Behavior |
|------|----------|
| Macro calls another macro | Defining namespace has both; works. |
| Macro uses `caller()` | `_caller` is passed by compiler; unchanged. |
| Caller passes `_outer_ctx` in kwargs | We overwrite with defining namespace; caller does not pass it for imported macros. |
| Empty defining namespace | `merged_ctx = kwargs`; no regression. |
| Frozen dataclass | `_defining_namespace` is a dict; mutable but not mutated. |

### Alternative: Run `_globals_setup` Before `_extends`

A complementary fix is to run the child's `_globals_setup(ctx)` before `_extends` in `_make_render_extends_body`, so the child's imports populate `ctx` before the parent runs. That ensures the block receives a context with `article_card`, `tag_list`, etc. This RFC focuses on MacroWrapper; the extends fix can be a separate change.

---

## Validation Plan

### 1. Unit Tests (Kida)

- Add test: imported macro that calls another macro from defining template; invoke from different template; assert no `_Undefined`.
- Add test: macro uses variable from defining template; invoke from template that doesn't have it; assert variable is found.
- Regression: macro called from same template still works.

### 2. Integration (Bengal)

- Revert the workaround: remove `{% from 'partials/components/tags.html' import tag_list %}` from `tag.html`.
- Run full build; assert zero `_Undefined object is not callable` errors.
- Fix remaining `pagination` and `newsletter_cta` import errors (likely same class of issue or additional missing globals).

### 3. Regression

- Run Kida test suite.
- Run Bengal test suite and build on lbliii (or equivalent site).

---

## Files to Modify

| File | Change |
|------|--------|
| `kida/src/kida/template/render_helpers.py` | Add `_defining_namespace` to MacroWrapper; inject in `__call__`; pass from `_import_macros`; update `_make_macro_wrapper` |
| `kida/tests/` | New tests for macro defining-namespace injection |
| `bengal/themes/default/templates/tag.html` | Revert workaround after fix (remove redundant `tag_list` import if no longer needed) |

---

## References

- **Evidence**: `kida/template/render_helpers.py:89–137` (MacroWrapper), `:381–441` (_import_macros)
- **Evidence**: `kida/compiler/statements/functions.py:114–299` (macro compilation, `_outer_ctx`)
- **Evidence**: `kida/compiler/expressions.py:316–332` (FuncCall, no `_outer_ctx` for regular macros)
- **Evidence**: `bengal/themes/default/templates/partials/components/article.html:86` (`tag_list` call)
- **Evidence**: `bengal/themes/default/templates/tag.html:21–24` (imports), `:73` (article_card call)
