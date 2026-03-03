# Plan: Deferred Items (Kida Macro Hardening + Blog Template Parse Error)

**Status**: Implemented  
**Scope**: Kida repo (macro hardening), Bengal repo (blog template)  
**Related**: K-RUN-007, `tests/integration/test_blog_build.py` (uses docs variant until blog fixed)

---

## Overview

Two deferred items from the free-threading / blog work:

1. **Phase 4 – Kida macro hardening** (Kida repo): Validate macro imports at import time, add parallel tests, document parallel-safe patterns.
2. **Blog template parse error** (Bengal): `blog/single.html` line 68 has a Kida parse error; integration test uses docs until fixed.

---

## 1. Kida Macro Hardening (Kida Repo)

### 1.1 Validate at Import Time in `_import_macros`

**Location**: `kida/src/kida/template/core.py` lines 477–525

**Problem**: The compiler emits `ctx['alias'] = _imported['name']` without checking that the requested macro exists. If the imported template does not define the macro:

- `_imported['name']` raises `KeyError`, or
- If the value is `UNDEFINED`, calling it later yields `'_Undefined' object is not callable`.

**Solution**: In `_import_macros`, after `imported._render_func(import_ctx, None)` returns, validate that each requested macro name exists in `import_ctx` and is callable before returning. The compiler does not pass the requested names to `_import_macros`, so validation must happen in the compiler layer.

**Implementation options**:

| Option | Where | Pros | Cons |
|--------|-------|------|------|
| A | Compiler: add post-assign check | Keeps `_import_macros` generic | Compiler must emit validation code per name |
| B | `_import_macros` accepts optional `names: list[str]` | Single validation point | Changes `_import_macros` signature; compiler must pass names |
| C | `_import_macros` returns only requested keys | Clean separation | Requires compiler to pass names; changes return shape |

**Recommended**: Option B – extend `_import_macros` to accept optional `names: list[str]`. When provided, after `_render_func` returns, validate each name exists in `import_ctx` and is callable. Raise `TemplateRuntimeError` with clear message (template name, missing macro name) if validation fails. Compiler passes `[n for n, _ in node.names]` when compiling `FromImport`.

**Tasks**:

- [ ] Add optional `names: list[str] | None = None` to `_import_macros` signature
- [ ] After `imported._render_func(import_ctx, None)`, if `names` is not None, for each `name` in `names`:
  - Check `name in import_ctx`
  - Check `callable(import_ctx[name])` (or `import_ctx[name] is not UNDEFINED`)
  - Raise `TemplateRuntimeError` with `ErrorCode` (e.g. `MACRO_NOT_FOUND`) if validation fails
- [ ] Update compiler `_compile_from_import` to pass `[n for n, _ in node.names]` as third arg (or via new keyword)
- [ ] Add `MACRO_NOT_FOUND` (or similar) to `ErrorCode` if not present

### 1.2 Add Parallel Tests

**Location**: `kida/tests/test_kida_compiler_edge_cases.py`

**Existing**: `test_import_macros_parallel_rendering`, `test_import_macros_extends_parallel_rendering` (K-RUN-007 regression).

**Add**:

- [ ] `test_import_macros_missing_macro_raises`: `{% from "macros.html" import missing %}` when `macros.html` does not define `missing` → raises `TemplateRuntimeError` at render time (or compile time if we validate earlier)
- [ ] `test_import_macros_undefined_filtered_parallel`: Ensure that when a macro is correctly defined, no `UNDEFINED` leaks under parallel rendering (stress test with more workers/iterations if needed)

### 1.3 Document Parallel-Safe Patterns

**Location**: `kida/site/content/docs/about/thread-safety.md`

**Add section** (after "Best Practices" or in a new "Macro Import Patterns" subsection):

- [ ] **Macro imports**: Use `{% from "partials/x.html" import macro_name %}`; ensure the imported template defines the macro. If the macro is missing, Kida raises a clear error at import time (after 1.1).
- [ ] **Extends + import**: When using `{% extends %}` and `{% from %}`, each child gets an isolated `import_stack`; no shared mutable state. (Reference existing "Copy on fork" principle.)
- [ ] **Avoid importing non-macros**: `{% from "x" import y %}` expects `y` to be a macro (callable). Do not import filters or other globals this way.

---

## 2. Blog Template Parse Error (Bengal)

### 2.1 Problem

**File**: `bengal/bengal/themes/default/templates/blog/single.html` line 68

```kida
{% let author_data = (authors_registry.get(author_slug, {}) if author_slug and authors_registry is mapping) else {} %}
```

**Error**: `Parse Error: Expected block_end, got name` at position 108.

**Cause**: The `)` before `else` closes the conditional expression. The parser then sees `else` and treats it as a block keyword (e.g. `{% else %}`) instead of part of the ternary. In Python/Kida ternary form is `a if b else c`; the parentheses must include the full expression.

### 2.2 Fix Options

| Option | Repo | Change | Effort |
|--------|------|--------|--------|
| A | Bengal | Fix template: move `else {}` inside parentheses | Low |
| B | Kida | Fix parser: handle `else` in `{% let %}` expression context | Medium |

**Recommended**: Option A – fix the template. Correct form:

```kida
{% let author_data = (authors_registry.get(author_slug, {}) if author_slug and authors_registry is mapping else {}) %}
```

### 2.3 Tasks

- [ ] **Bengal**: In `blog/single.html` line 68, change `... mapping) else {}` to `... mapping else {})`
- [ ] **Bengal**: Update `tests/integration/test_blog_build.py` to use blog variant instead of docs (once template parses)
- [ ] **Optional – Kida**: If similar expressions appear elsewhere, consider parser fix so `(a if b) else c` is parsed as ternary. Low priority.

---

## 3. Implementation Order

1. **Blog template** (Bengal) – quick fix, unblocks integration test
2. **Kida macro validation** (Kida) – `_import_macros` + compiler changes
3. **Kida parallel tests** – missing macro + stress
4. **Kida docs** – thread-safety.md updates

---

## 4. Acceptance Criteria

- [ ] `blog/single.html` parses and renders without error
- [ ] `test_blog_build` uses blog variant and passes
- [ ] `{% from "x" import missing %}` with undefined macro raises clear `TemplateRuntimeError`
- [ ] Existing parallel macro tests pass; new missing-macro test added
- [ ] Thread-safety doc includes macro import patterns

---

## 5. References

| Item | Path |
|------|------|
| `_import_macros` | `kida/src/kida/template/core.py:477-525` |
| FromImport compiler | `kida/src/kida/compiler/statements/template_structure.py:324-372` |
| Blog template | `bengal/bengal/themes/default/templates/blog/single.html:68` |
| `_parse_let` | `kida/src/kida/parser/blocks/variables.py:244-256` |
| Parallel macro tests | `kida/tests/test_kida_compiler_edge_cases.py:541-593` |
| Thread-safety doc | `kida/site/content/docs/about/thread-safety.md` |
