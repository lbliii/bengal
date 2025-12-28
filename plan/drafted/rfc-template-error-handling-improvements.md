# RFC: Template Error Handling & Developer Experience Improvements

**Status**: Draft  
**Created**: 2025-12-27  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High)  
**Related**: `bengal/rendering/pipeline/autodoc_renderer.py`, `bengal/rendering/kida/`, `bengal/cli/`  
**Confidence**: 95% 🟢

---

## Executive Summary

During template development, **syntax errors in templates were silently swallowed** and reported as "template not found" errors. This led to hours of debugging cache invalidation when the actual issue was parse errors in the templates themselves.

This RFC proposes improvements to both **Bengal** (error surfacing, validation tooling) and **Kida** (better error messages, new filters) to make template debugging significantly faster.

**Key Problems Identified**:
1. Parse errors conflated with "not found" errors
2. Errors logged at `warning` level, easily missed
3. No pre-build template validation
4. Jinja2 → Kida migration has undocumented gotchas

**Proposed Solutions**:
1. Distinguish error types in autodoc renderer
2. Add `bengal validate-templates` CLI command
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

```python
# bengal/rendering/pipeline/autodoc_renderer.py:177-188
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
from bengal.rendering.kida.environment import (
    TemplateNotFoundError,
    TemplateSyntaxError,
)

def _load_autodoc_template(self, template_name: str) -> Template:
    """Load autodoc template with proper error handling.

    Raises:
        TemplateSyntaxError: Template has parse errors (fail fast)
        TemplateNotFoundError: Template doesn't exist (use fallback)
    """
    names_to_try = [f"{template_name}.html", template_name]
    last_error = None

    for name in names_to_try:
        try:
            return self.template_engine.env.get_template(name)
        except TemplateSyntaxError as e:
            # Syntax error = fail fast, don't try fallback
            logger.error(
                "autodoc_template_syntax_error",
                template=name,
                error=str(e),
                line=getattr(e, 'lineno', None),
                source_snippet=self._extract_source_snippet(name, e),
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
        search_paths=self.template_engine.template_dirs,
    )
    raise last_error
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

### 2. Bengal: Add `bengal validate-templates` CLI Command

**File**: `bengal/cli/commands/validate.py` (new)

```python
"""Template validation command for pre-build syntax checking."""

import click
from pathlib import Path
from bengal.core import Site
from bengal.rendering.engines import create_engine


@click.command("validate-templates")
@click.option("--fix", is_flag=True, help="Suggest fixes for common issues")
@click.option("--pattern", default="**/*.html", help="Glob pattern for templates")
@click.pass_context
def validate_templates(ctx, fix: bool, pattern: str):
    """Validate all templates for syntax errors before building.

    Examples:
        bengal validate-templates
        bengal validate-templates --pattern "autodoc/**/*.html"
        bengal validate-templates --fix
    """
    site = Site.from_config(Path.cwd())
    engine = create_engine(site)

    errors = engine.validate(patterns=[pattern] if pattern != "**/*.html" else None)

    if not errors:
        click.secho("✓ All templates valid", fg="green")
        return

    click.secho(f"✗ Found {len(errors)} template errors:", fg="red")

    for error in errors:
        click.echo()
        click.secho(f"  {error.template}", fg="yellow")
        click.echo(f"    Line {error.line}: {error.message}")

        if fix and error.suggestion:
            click.secho(f"    💡 {error.suggestion}", fg="cyan")

    ctx.exit(1)
```

**Usage**:
```bash
# Validate all templates
bengal validate-templates

# Validate only autodoc templates
bengal validate-templates --pattern "autodoc/**/*.html"

# Show migration hints
bengal validate-templates --fix
```

**Integration with Build**:
```python
# bengal/cli/commands/build.py
@click.option("--validate/--no-validate", default=True,
              help="Validate templates before building")
def build(validate: bool, ...):
    if validate:
        errors = engine.validate()
        if errors:
            # Show errors and exit before wasting time on full build
            ...
```

---

### 3. Kida: Add `get()` Filter for Safe Dict Access

**File**: `bengal/rendering/kida/environment/filters.py`

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

**Implementation**:
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

    # Try dict-style access first
    if isinstance(value, dict):
        return value.get(key, default)

    # Try attribute access for objects
    try:
        result = getattr(value, key, None)
        # Don't return bound methods - that's a key conflict
        if callable(result) and hasattr(value, '__getitem__'):
            try:
                return value[key]
            except (KeyError, TypeError):
                return default
        return result if result is not None else default
    except Exception:
        return default


# Register in DEFAULT_FILTERS
DEFAULT_FILTERS = {
    # ... existing filters ...
    "get": _filter_get,
}
```

---

### 4. Kida: Better Error Messages for Jinja2 Migration

**File**: `bengal/rendering/kida/parser/blocks/template_structure.py`

**Current Error**:
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
    start = self._advance()
    template = self._parse_expression()

    with_context = True
    ignore_missing = False

    while self._current.type == TokenType.NAME:
        keyword = self._current.value
        if keyword == "with":
            self._advance()
            if self._current.type == TokenType.NAME and self._current.value == "context":
                self._advance()
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
                raise self._error("Expected 'context' after 'with'")
        # ... rest of parsing
```

---

### 5. Kida: Document Common Gotchas

**File**: `docs/kida/migration-from-jinja2.md` (new)

```markdown
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
{# Wrong - this groups into 0 slices (error!) #}
{{ status | slice(0, 1) }}

{# Correct - Python slice syntax #}
{{ status[:1] }}
```

### Nil-Coalescing with Undefined Variables

In strict mode, use `??` to handle undefined variables:

```jinja
{# May error if 'schemas' is undefined #}
{% let schema = schemas[name] if schemas else none %}

{# Safe - ?? handles undefined #}
{% let schemas_dict = schemas ?? {} %}
{% let schema = schemas_dict.get(name) %}
```
```

---

## Implementation Plan

### Phase 1: Error Handling (Bengal) - 2 hours
- [ ] Refactor `autodoc_renderer.py` to distinguish error types
- [ ] Add source snippet extraction for syntax errors
- [ ] Update log levels (syntax errors → ERROR)
- [ ] Add error codes for programmatic handling

### Phase 2: CLI Validation (Bengal) - 2 hours
- [ ] Create `validate-templates` command
- [ ] Add `--validate` flag to build command
- [ ] Output structured errors with suggestions

### Phase 3: Kida Filters - 1 hour
- [ ] Add `get(key, default)` filter
- [ ] Add comprehensive tests

### Phase 4: Kida Error Messages - 1 hour
- [ ] Improve `include with` error message
- [ ] Add migration hints to common errors
- [ ] Add `suggestion` field to `TemplateSyntaxError`

### Phase 5: Documentation - 1 hour
- [ ] Create migration guide
- [ ] Document common gotchas
- [ ] Add examples to filter docs

---

## Success Criteria

1. **Parse errors immediately visible**: Syntax errors show at ERROR level with source snippets
2. **Clear error messages**: Developers understand what's wrong and how to fix it
3. **Pre-build validation**: `bengal validate-templates` catches errors before slow build
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

### 3. Runtime Template Validation Only

**Pros**: Simpler implementation  
**Cons**: Slow builds waste time before showing errors  
**Decision**: Add both CLI validation AND better runtime errors

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

   See: https://bengal.dev/docs/kida/migration-from-jinja2
```

---

## References

- [Kida Template Engine Documentation](../docs/kida/)
- [Bengal Rendering Pipeline](../bengal/rendering/pipeline/)
- [Incident: Template Cache Debugging Session](./incidents/2025-12-27-template-cache-confusion.md)
