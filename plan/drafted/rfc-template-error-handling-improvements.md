# RFC: Template Error Handling & Developer Experience Improvements

**Status**: Draft → Ready for Review  
**Created**: 2025-12-27  
**Updated**: 2025-12-27  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High)  
**Estimated Effort**: ~4 hours  
**Related**: `bengal/rendering/pipeline/autodoc_renderer.py`, `bengal/rendering/kida/`, `bengal/cli/`  
**Confidence**: 95% 🟢

---

## Executive Summary

During template development, **syntax errors in templates were silently swallowed** and reported as "template not found" errors. This led to hours of debugging cache invalidation when the actual issue was parse errors in the templates themselves.

This RFC proposes improvements to both **Bengal** (error surfacing, validation tooling) and **Kida** (better error messages, new filters) to make template debugging significantly faster.

**Key Problems Identified**:
1. Parse errors conflated with "not found" errors
2. Errors logged at `warning` level, easily missed
3. No CLI access to existing template validation
4. Jinja2 → Kida migration has undocumented gotchas

**Proposed Solutions**:
1. Distinguish error types in autodoc renderer
2. Extend `bengal validate` with `--templates` flag (leveraging existing infrastructure)
3. Add `get()` filter to Kida for safe dict access
4. Improve error messages for common Jinja2 migration issues

---

## Problem Statement

### The Debugging Session That Prompted This RFC

```
autodoc_template_not_found template=autodoc/openapi/list
error=Template 'autodoc/openapi/list' not found in: ...
```

**What we thought**: Template caching issue, templates not being discovered  
**What it actually was**: Templates had Kida syntax errors (Jinja2 incompatibilities)

The actual error was buried in the `error=` field:
```
Parse Error: Expected 'context' after 'with'
  --> autodoc/openapi/list.html:139:78
```

### Root Cause Analysis

**Evidence**: `bengal/rendering/pipeline/autodoc_renderer.py:177-188`

```python
try:
    template = self.template_engine.env.get_template(f"{template_name}.html")
except Exception:  # ← Catches ALL exceptions
    try:
        template = self.template_engine.env.get_template(template_name)
    except Exception as e:
        logger.warning(
            "autodoc_template_not_found",  # ← Misleading event name
            template=template_name,
            error=str(e),  # ← Real error buried here
        )
```

**Issues**:
1. All exceptions treated as "not found"
2. `warning` level easily missed in build output
3. Event name doesn't match actual error type
4. No stack trace or source location in log

---

## Prior Art: Existing Infrastructure

Before implementing, note that Bengal/Kida already provides:

| Component | Location | Status |
|-----------|----------|--------|
| `TemplateSyntaxError` | `kida/environment/exceptions.py:60` | ✅ Exists with `lineno`, `name`, `filename` |
| `TemplateNotFoundError` | `kida/environment/exceptions.py:46` | ✅ Exists |
| `TemplateRuntimeError` | `kida/environment/exceptions.py:88` | ✅ Exists with `suggestion` field |
| `KidaTemplateEngine.validate()` | `rendering/engines/kida.py:554` | ✅ Exists, validates all templates |
| `bengal validate` command | `cli/commands/validate.py` | ✅ Exists for health checks |

**Key insight**: Template validation infrastructure exists but isn't exposed properly.

---

## Proposed Changes

### 1. Bengal: Distinguish Error Types in Autodoc Renderer

**File**: `bengal/rendering/pipeline/autodoc_renderer.py`

**Before** (current):
```python
try:
    template = self.template_engine.env.get_template(f"{template_name}.html")
except Exception:
    # ... fallback ...
```

**After** (proposed):
```python
from bengal.rendering.kida import TemplateSyntaxError, TemplateNotFoundError

def _load_autodoc_template(self, template_name: str) -> Template:
    """Load autodoc template with proper error handling.

    Raises:
        TemplateSyntaxError: Template has parse errors (fail fast)
        TemplateNotFoundError: Template doesn't exist (use fallback)
    """
    names_to_try = [f"{template_name}.html", template_name]
    last_error: TemplateNotFoundError | None = None

    for name in names_to_try:
        try:
            return self.template_engine.env.get_template(name)
        except TemplateSyntaxError as e:
            # Syntax error = fail fast, don't try fallback
            logger.error(
                "autodoc_template_syntax_error",
                template=name,
                error=str(e),
                line=e.lineno,
                file=e.filename,
            )
            raise  # Don't silently continue
        except TemplateNotFoundError as e:
            last_error = e
            continue  # Try next name

    # All names exhausted - actually not found
    logger.warning(
        "autodoc_template_not_found",
        template=template_name,
        tried=names_to_try,
    )
    if last_error:
        raise last_error
    raise TemplateNotFoundError(f"Template '{template_name}' not found")
```

**Log Output Improvement**:

```
# Before (misleading):
⚠️ Warning: autodoc_template_not_found template=autodoc/openapi/list

# After (clear):
❌ Error: autodoc_template_syntax_error
   Template: autodoc/openapi/list.html
   Line: 139

   Parse Error: Expected 'context' after 'with'

   139 |  {% include 'partial.html' with param=value %}
                                         ^

   💡 Hint: Kida uses {% let param=value %} before {% include %}
            instead of Jinja2's "with" syntax.
```

---

### 2. Bengal: Extend `validate` Command with `--templates` Flag

**File**: `bengal/cli/commands/validate.py` (extend existing)

Rather than creating a new command, extend the existing `bengal validate` to support template validation via `KidaTemplateEngine.validate()`.

**Implementation**:
```python
@click.command("validate")
@click.option(
    "--templates",
    is_flag=True,
    help="Validate template syntax (Kida/Jinja2 templates)",
)
@click.option(
    "--templates-pattern",
    default=None,
    help="Glob pattern for templates (e.g., 'autodoc/**/*.html')",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Show migration hints for template errors",
)
# ... existing options ...
def validate(
    templates: bool,
    templates_pattern: str | None,
    fix: bool,
    # ... existing params ...
):
    """
    Validate site health and content quality.

    Examples:
        bengal validate                              # Health checks
        bengal validate --templates                  # Template syntax
        bengal validate --templates --fix            # With migration hints
        bengal validate --templates-pattern "autodoc/**/*.html"
    """
    if templates:
        _validate_templates(site, templates_pattern, fix, cli)
        return

    # ... existing health check logic ...


def _validate_templates(
    site: Site,
    pattern: str | None,
    show_hints: bool,
    cli: CLIOutput,
) -> None:
    """Validate templates using existing engine.validate() method."""
    from bengal.rendering.engines import create_engine

    engine = create_engine(site)
    patterns = [pattern] if pattern else None
    errors = engine.validate(patterns)

    if not errors:
        cli.success("✓ All templates valid")
        return

    cli.error(f"✗ Found {len(errors)} template error(s):")

    for error in errors:
        cli.blank()
        cli.warning(f"  {error.template}")
        cli.info(f"    Line {error.line}: {error.message}")

        if show_hints and error.suggestion:
            cli.info(f"    💡 {error.suggestion}")

    raise click.ClickException(f"Template validation failed: {len(errors)} error(s)")
```

**Usage**:
```bash
# Validate all templates
bengal validate --templates

# Validate only autodoc templates
bengal validate --templates --templates-pattern "autodoc/**/*.html"

# Show migration hints
bengal validate --templates --fix

# Combined with content validation
bengal validate --templates && bengal validate
```

**Optional: Add to build command**:
```python
# bengal/cli/commands/build.py
@click.option(
    "--validate-templates/--no-validate-templates",
    default=False,  # Opt-in, not default (builds should be fast)
    help="Validate templates before building",
)
def build(validate_templates: bool, ...):
    if validate_templates:
        errors = engine.validate()
        if errors:
            # Show errors and exit before wasting time on full build
            ...
```

---

### 3. Kida: Fix Strict Mode for Attribute/Key Access (BUG)

**File**: `bengal/rendering/kida/compiler/expressions.py`

**Problem**: Strict mode only catches undefined *variables*, not undefined *attributes* or *keys*.

```python
# Current behavior (WRONG):
{{ undefined_var }}       # → UndefinedError ✓
{{ obj.undefined_attr }}  # → '' (silent!) ✗
{{ dict.missing_key }}    # → '' (silent!) ✗
```

**Impact**: Templates with typos like `{{ section.url }}` (should be `section.href`) silently render empty strings instead of failing.

**Expected behavior (strict=True)**:
```python
{{ obj.undefined_attr }}  # → UndefinedError
{{ dict.missing_key }}    # → UndefinedError
```

**Root Cause**: The attribute resolver catches `AttributeError` and `KeyError` and returns `None`/empty string instead of checking strict mode.

**Fix**: In the attribute/key access compiler, check strict mode and raise `UndefinedError`:

```python
def _resolve_attr(obj, attr, strict=False):
    """Resolve attribute with strict mode support."""
    # Try attribute access
    try:
        return getattr(obj, attr)
    except AttributeError:
        pass

    # Try item access
    try:
        return obj[attr]
    except (KeyError, TypeError, IndexError):
        pass

    # Both failed - check strict mode
    if strict:
        raise UndefinedError(f"Undefined attribute '{attr}' on {type(obj).__name__}")

    return None  # Non-strict: return None (becomes '')
```

---

### 4. Kida: Add `get()` Filter for Safe Dict Access (Optional after #3)

**File**: `bengal/rendering/kida/environment/filters.py`

> Note: After fixing #3, this becomes optional since strict mode will catch typos.
> Still useful for intentionally optional attributes.

**Problem**: Python dict methods (`.items`, `.keys`, `.get`) conflict with dict key access.

```jinja
{# This fails - .items is the method, not the key #}
{{ schema.items }}

{# This works but is verbose #}
{{ schema['items'] }}

{# Proposed - cleaner syntax #}
{{ schema | get('items') }}
{{ schema | get('items', default_value) }}
```

**Implementation** (simplified):
```python
def _filter_get(value: Any, key: str, default: Any = None) -> Any:
    """Safe dictionary/object access.

    Avoids conflicts with Python method names like 'items', 'keys', 'values'.
    Falls back to default if key doesn't exist or value is None.

    Examples:
        {{ user | get('name') }}
        {{ config | get('timeout', 30) }}
        {{ schema | get('items') }}  # Safe access to 'items' key

    Args:
        value: Dict, object, or None
        key: Key to access
        default: Value to return if key doesn't exist (default: None)

    Returns:
        value[key] if exists, else default
    """
    if value is None:
        return default

    # Dict access (handles method name conflicts)
    if isinstance(value, dict):
        return value.get(key, default)

    # Object attribute access
    return getattr(value, key, default)


# Register in DEFAULT_FILTERS
DEFAULT_FILTERS = {
    # ... existing filters ...
    "get": _filter_get,
}
```

---

### 5. Kida: Better Error Messages for Jinja2 Migration

**File**: `bengal/rendering/kida/parser/blocks/template_structure.py`

**Current Error** (line 78):
```
Parse Error: Expected 'context' after 'with'
```

**Proposed Error**:
```
Parse Error: Jinja2's "include with var=value" syntax is not supported.

  --> autodoc/openapi/list.html:139
   |
139|  {% include 'partial.html' with param=value %}
   |                                 ^^^^^^^^^^^^
   |
   = help: In Kida, set variables before the include:
   |
   |  {% let param = value %}
   |  {% include 'partial.html' %}
```

**Implementation**:
```python
def _parse_include(self) -> Include:
    """Parse {% include "partial.html" [with context] [ignore missing] %}."""
    start = self._advance()  # consume 'include'
    template = self._parse_expression()

    with_context = True
    ignore_missing = False

    # Parse optional modifiers
    while self._current.type == TokenType.NAME:
        keyword = self._current.value
        if keyword == "with":
            self._advance()  # consume 'with'
            if self._current.type == TokenType.NAME and self._current.value == "context":
                self._advance()  # consume 'context'
                with_context = True
            elif self._current.type == TokenType.NAME:
                # Detected Jinja2 "with var=value" pattern
                raise self._error(
                    'Jinja2\'s "include with var=value" syntax is not supported',
                    suggestion=(
                        "In Kida, set variables before the include:\n"
                        "  {% let var = value %}\n"
                        "  {% include 'template.html' %}"
                    ),
                )
            else:
                raise self._error(
                    "Expected 'context' after 'with'",
                    suggestion="Use '{% include \"template.html\" with context %}' or just '{% include \"template.html\" %}'"
                )
        # ... rest of parsing unchanged
```

---

### 6. Documentation: Migration Guide

**File**: `site/reference/kida/migration-from-jinja2.md` (new)

```markdown
---
title: Migrating from Jinja2 to Kida
description: Common gotchas and syntax differences when migrating templates
---

# Migrating from Jinja2 to Kida

## Syntax Differences

### Include with Variables

**Jinja2**:
```jinja
{% include 'partial.html' with context %}
{% include 'partial.html' with param=value %}
```

**Kida**:
```jinja
{% include 'partial.html' %}                    {# inherits context #}
{% include 'partial.html' with context %}       {# explicit #}
{% let param = value %}                         {# set before include #}
{% include 'partial.html' %}
```

### Dict Key Access (Method Name Conflicts)

Python dict methods (`items`, `keys`, `values`, `get`) conflict with key access.

**Problem**:
```jinja
{{ schema.items }}    {# Returns the method, not the key! #}
```

**Solutions**:
```jinja
{{ schema['items'] }}        {# Bracket notation #}
{{ schema | get('items') }}  {# get() filter #}
```

### Slice Filter vs Python Slicing

Kida's `slice` filter groups items (like Jinja2), it doesn't do string slicing.

```jinja
{# Wrong - this groups into slices #}
{{ items | slice(3) }}

{# Correct for string/list slicing #}
{{ status[:1] }}
```

### Nil-Coalescing with Undefined Variables

In strict mode, use `??` to handle undefined variables:

```jinja
{# May error if 'schemas' is undefined #}
{% let schema = schemas[name] if schemas else none %}

{# Safe - ?? handles undefined #}
{% let schemas_dict = schemas ?? {} %}
{% let schema = schemas_dict | get(name) %}
```

## Validation

Run template validation before building:

```bash
bengal validate --templates
bengal validate --templates --fix  # Show migration hints
```
```

---

## Implementation Plan

### Phase 1: Error Handling (Bengal) - 1 hour
- [ ] Refactor `autodoc_renderer.py` to distinguish error types
- [ ] Import specific exception types from `bengal.rendering.kida`
- [ ] Update log levels (syntax errors → ERROR)

### Phase 2: CLI Integration (Bengal) - 1 hour
- [ ] Add `--templates` flag to existing `validate` command
- [ ] Add `--templates-pattern` for filtering
- [ ] Add `--fix` flag for migration hints
- [ ] Wire up `engine.validate()` to CLI output

### Phase 3: Kida Strict Mode Fix (CRITICAL) - 2 hours
- [ ] Fix attribute resolver to check strict mode
- [ ] Fix key resolver to check strict mode  
- [ ] Raise `UndefinedError` for undefined attrs/keys in strict mode
- [ ] Add comprehensive tests for strict mode behavior
- [ ] Verify backwards compatibility for non-strict mode

### Phase 4: Kida Filters - 30 minutes
- [ ] Add `get(key, default)` filter
- [ ] Add tests for dict method name conflicts

### Phase 5: Kida Error Messages - 30 minutes
- [ ] Improve `include with` error detection
- [ ] Add `suggestion` parameter to parser errors
- [ ] Add migration hints to common errors

### Phase 6: Documentation - 1 hour
- [ ] Create migration guide at `site/reference/kida/`
- [ ] Document common gotchas
- [ ] Add examples to filter docs

**Total**: ~6 hours

---

## Success Criteria

1. **Parse errors immediately visible**: Syntax errors show at ERROR level with source location
2. **Clear error messages**: Developers understand what's wrong and how to fix it
3. **Pre-build validation**: `bengal validate --templates` catches errors before slow build
4. **Migration path**: Jinja2 users get helpful hints when using unsupported syntax
5. **Safe dict access**: `| get('items')` provides clean alternative to bracket notation

---

## Alternatives Considered

### 1. Support Jinja2's `include with var=val` Syntax

**Pros**: Full Jinja2 compatibility, easier migration  
**Cons**: Adds complexity, conflicts with Kida's explicit `{% let %}` philosophy  
**Decision**: Rejected - better to provide clear migration path than muddied syntax

### 2. Auto-Fallback to String Rendering on Template Errors

**Pros**: Build never fails  
**Cons**: Silently produces broken output, harder to debug  
**Decision**: Rejected - fail fast is better for development

### 3. Create New `validate-templates` Command

**Pros**: Clear separation of concerns  
**Cons**: Duplicates infrastructure, `engine.validate()` already exists  
**Decision**: Rejected - extend existing `validate` command instead

### 4. Runtime Template Validation Only

**Pros**: Simpler implementation  
**Cons**: Slow builds waste time before showing errors  
**Decision**: Add CLI validation AND better runtime errors

---

## Appendix: Error Examples

### Before (Current)
```
⚠️ Warning: autodoc_template_not_found template=autodoc/openapi/list
error=Template 'autodoc/openapi/list' not found in: /path/to/templates
```

### After (Proposed)
```
❌ Error: Template Syntax Error

   File: autodoc/openapi/list.html
   Line: 139

   Parse Error: Jinja2's "include with var=value" syntax is not supported.

   139 |  {% include 'autodoc/openapi/partials/param-row.html' with param=param %}
       |                                                            ^^^^^^^^^^^^

   💡 Hint: In Kida, set variables before the include:

      {% let param = param %}
      {% include 'autodoc/openapi/partials/param-row.html' %}

   See: https://bengal.dev/reference/kida/migration-from-jinja2
```

---

## References

- **Kida Exception Hierarchy**: `bengal/rendering/kida/environment/exceptions.py`
- **Existing Validation**: `bengal/rendering/engines/kida.py:554`
- **Current Validate Command**: `bengal/cli/commands/validate.py`
- **Include Parser**: `bengal/rendering/kida/parser/blocks/template_structure.py:61-104`
- **Incident**: Template Cache Debugging Session (2025-12-27)
