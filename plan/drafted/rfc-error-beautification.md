# RFC: Error Beautification ("Delightful Errors")

**Status**: Implemented  
**Created**: 2025-12-24  
**Implemented**: 2025-12-24  
**Author**: AI Assistant  
**Confidence**: 92% 🟢  
**Priority**: P1 (High) — User-facing polish with low risk  

---

## Executive Summary

Bengal has a sophisticated error code system (`ErrorCode` enum with 54 codes across 10 categories) and rich exception hierarchy (`BengalError` subclasses with context, suggestions, and investigation helpers), but **none of it is used in the core build/config flows**. Users see raw Python tracebacks and generic error messages instead of helpful, actionable errors with codes.

This RFC proposes:
1. **Beautify CLI errors** — Update `@handle_cli_errors()` to detect and format `BengalError` instances
2. **Dog-food error codes** — Use `ErrorCode` in core flows (config, content, rendering)
3. **Handle ugly edge cases** — KeyboardInterrupt, import errors, common exceptions
4. **Add documentation links** — Auto-generate error pages at `/docs/errors/{code}/`

---

## Problem Statement

### Current State

Bengal has excellent error infrastructure that isn't being used:

**✅ Existing (Unused) Capabilities**:
- **Error codes**: 54 codes defined in `bengal/errors/codes.py` across 10 categories (C, N, R, D, A, S, T, P, X, G)
- **Rich exceptions**: `BengalError` hierarchy with `code`, `file_path`, `line_number`, `suggestion`, `related_files`, `debug_payload`
- **Investigation helpers**: `get_investigation_commands()`, `get_related_test_files()`, `get_docs_url()`
- **Traceback config**: Four styles (full/compact/minimal/off) via `BENGAL_TRACEBACK`
- **Error reporter**: `format_error_report()` and `format_error_summary()` for build output
- **CLI error handler**: `@handle_cli_errors()` decorator used in 30 CLI commands

**❌ Actual Usage**:

| Module | ErrorCode Uses | BengalError Raises | Gap |
|--------|---------------|-------------------|-----|
| `analysis/` | 25 | 25 | ✅ 100% |
| `errors/` (examples) | 11 | 9 | ✅ Docstrings |
| `config/` | **0** | 1 | ❌ 0% |
| `discovery/` | **0** | 4 | ❌ 0% |
| `rendering/` | **0** | 4 | ❌ 0% |
| `core/` | **0** | 2 | ❌ 0% |
| `orchestration/` | **0** | 5 | ❌ 0% |

**Total**: 97 `raise Bengal*Error(...)` statements across 45 files, but only 36 include `code=ErrorCode.XXX`.

### Root Cause: CLI Handler Ignores BengalError Fields

The current `@handle_cli_errors()` decorator doesn't detect `BengalError` instances:

```python
# bengal/cli/helpers/error_handling.py:68-71 (CURRENT)
except Exception as e:
    error_msg = str(e) or type(e).__name__
    show_error(f"Command failed: {error_msg}", show_art=show_art)
```

This means even when exceptions have error codes, file paths, and suggestions, **none of it is displayed**.

### Pain Points

1. **Ugly KeyboardInterrupt**: Pressing Ctrl+C during startup shows 40-line import traceback ~~(Sphinx vibes 😬)~~ ✅ FIXED
2. **Generic error messages**: "Command failed: Invalid YAML" instead of `[C001] Config file not found`
3. **No error codes visible**: Users never see the codes we spent time designing
4. **Missing suggestions**: Exceptions have `suggestion` field but it's rarely populated
5. **No docs links**: Error codes should link to troubleshooting pages
6. **Inconsistent formatting**: Some errors use Rich, others use plain text, others show raw tracebacks

### User Impact

**Before (Current)**:
```
$ bengal build
Traceback (most recent call last):
  File "/path/to/bengal/config/loader.py", line 45, in load
    data = yaml.safe_load(f)
yaml.scanner.ScannerError: while scanning a simple key
  in "bengal.toml", line 12, column 1
```

**After (Goal)**:
```
$ bengal build

  ✖ [C001] Configuration Error

  Invalid YAML syntax in bengal.toml

  File: bengal.toml:12

  Tip: Check for missing colons, incorrect indentation, or unquoted
       special characters. YAML requires consistent spacing.

  Docs: https://bengal.dev/docs/errors/c001/
```

---

## Goals & Non-Goals

**Goals**:
- ✅ **Beautiful CLI output** — Structured error display with codes, context, suggestions
- ✅ **Use error codes everywhere** — All `BengalError` raises should include codes
- ✅ **Graceful interrupts** — Clean exit on Ctrl+C at any point (import, build, serve)
- ✅ **Documentation links** — Each code links to troubleshooting page
- ✅ **Common exception beautification** — Pretty-print `FileNotFoundError`, `yaml.YAMLError`, etc.
- ✅ **Prevent regression** — Lint rule to enforce error codes on new raises

**Non-Goals**:
- ❌ Creating new error codes (existing 54 codes are sufficient)
- ❌ Changing exception hierarchy (already well-designed)
- ❌ Debug/trace mode changes (traceback config already exists)
- ❌ Adding error recovery (already exists in `recovery.py`)

---

## Proposed Changes

### Phase 1: Beautiful CLI Error Display (FOUNDATION)

> **Rationale**: Do this first so error codes are immediately visible once added in Phase 2.

#### 1a. Create `bengal/cli/helpers/error_display.py`

```python
"""Beautiful error display for CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.cli.output import CLIOutput
from bengal.cli.icons import get_icon_set, should_use_emoji

if TYPE_CHECKING:
    from bengal.errors import BengalError


def display_bengal_error(error: BengalError, console: CLIOutput) -> None:
    """Display a BengalError with beautiful, structured formatting.

    Args:
        error: The BengalError instance to display
        console: CLI output helper for formatted printing
    """
    icons = get_icon_set(should_use_emoji())

    # Header with code and category
    if error.code:
        code_str = f"[{error.code.name}]"
        category = error.code.category.replace("_", " ").title()
        console.console.print(f"\n  {icons.error} {code_str} {category} Error\n", style="bold red")
    else:
        console.console.print(f"\n  {icons.error} Error\n", style="bold red")

    # Main message
    console.console.print(f"  {error.message}\n")

    # File location (clickable in most terminals)
    if error.file_path:
        location = f"  File: {error.file_path}"
        if error.line_number:
            location += f":{error.line_number}"
        console.console.print(f"[dim]{location}[/dim]\n")

    # Related files (for debugging)
    if error.related_files:
        console.console.print("  [dim]Related:[/dim]")
        for rf in error.related_files[:3]:
            console.console.print(f"    [dim]• {rf}[/dim]")
        if len(error.related_files) > 3:
            console.console.print(f"    [dim]... and {len(error.related_files) - 3} more[/dim]")
        console.console.print()

    # Actionable suggestion
    if error.suggestion:
        console.console.print(f"  [bold cyan]Tip:[/bold cyan] {error.suggestion}\n")

    # Documentation link
    if error.code:
        docs_url = f"https://bengal.dev{error.code.docs_url}"
        console.console.print(f"  [dim]Docs: {docs_url}[/dim]\n")
```

#### 1b. Update `@handle_cli_errors()` decorator

```python
# In bengal/cli/helpers/error_handling.py

from bengal.errors import BengalError
from bengal.cli.helpers.error_display import display_bengal_error

def handle_cli_errors(...) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except click.Abort:
                raise
            except click.ClickException:
                raise
            except BengalError as e:
                # NEW: Beautiful display for Bengal errors
                from bengal.cli.output import CLIOutput
                cli = CLIOutput()
                display_bengal_error(e, cli)

                # Still show traceback if configured
                if show_traceback is None:
                    with contextlib.suppress(Exception):
                        config = TracebackConfig.from_environment()
                        renderer = config.get_renderer()
                        if renderer.style.value not in ("off", "minimal"):
                            renderer.display_exception(e)

                raise click.Abort() from e
            except Exception as e:
                # Existing generic handler for non-Bengal exceptions
                error_msg = str(e) or type(e).__name__
                show_error(f"Command failed: {error_msg}", show_art=show_art)
                # ... rest of existing logic
```

### Phase 2: Dog-food Error Codes (Core Flows)

Add `ErrorCode` to all exception raises in core modules.

#### Config Loading (`bengal/config/loader.py`)
```python
# Before:
raise BengalConfigError(f"Unsupported config format: {suffix}")

# After:
raise BengalConfigError(
    f"Unsupported config format: {suffix}",
    code=ErrorCode.C003,
    file_path=config_path,
    suggestion="Use .toml, .yaml, or .yml format. See: bengal init --help",
)
```

#### Content Parsing (`bengal/discovery/page_factory.py`)
```python
# Before:
raise BengalContentError(
    f"Page '{page.title}' has no output_path set..."
)

# After:  
raise BengalContentError(
    f"Page '{page.title}' has no output_path set.",
    code=ErrorCode.N004,
    file_path=page.source_path,
    suggestion="Ensure orchestrator computes output_path before calling ensure_initialized()",
)
```

#### Template Rendering (`bengal/rendering/engines/`)
```python
# Before:
raise BengalRenderingError(f"Template not found: {template_name}")

# After:
raise BengalRenderingError(
    f"Template not found: {template_name}",
    code=ErrorCode.R001,
    file_path=page.source_path,
    suggestion=f"Create {template_name} in templates/ or check theme template inheritance",
    related_files=similar_templates,  # Use fuzzy matching to suggest alternatives
)
```

**Files to Update** (priority order):

| File | Raises | Codes to Add |
|------|--------|--------------|
| `bengal/config/loader.py` | 1 | C001-C003 |
| `bengal/discovery/page_factory.py` | 3 | N001, N004 |
| `bengal/rendering/engines/__init__.py` | 3 | R001-R003 |
| `bengal/orchestration/build/*.py` | 5 | D001-D005 |
| `bengal/server/dev_server.py` | 2 | S001-S002 |
| `bengal/core/site/core.py` | 1 | D001 |
| `bengal/core/theme/config.py` | 1 | C004 |

### Phase 3: Graceful Interrupt Handling

#### Entry Point (`bengal/__main__.py`) ✅ ALREADY DONE
```python
def run() -> None:
    """Entry point wrapper that gracefully handles KeyboardInterrupt."""
    try:
        from bengal.cli import main
        main()
    except KeyboardInterrupt:
        print("\n\033[2m Interrupted.\033[0m")
        sys.exit(130)  # Standard exit code for SIGINT
```

#### Build Loop (NEW)
```python
# In bengal/orchestration/build/orchestrator.py
try:
    for page in pages:
        render_page(page)
except KeyboardInterrupt:
    cli.warning("Build interrupted")
    stats.interrupted = True
    stats.save()  # Preserve partial stats for debugging
    sys.exit(130)
```

### Phase 4: Common Exception Beautification

Create helpers to wrap common third-party exceptions with helpful context:

```python
# In bengal/cli/helpers/error_display.py

def beautify_common_exception(e: Exception) -> tuple[str, str | None] | None:
    """Return (message, suggestion) for common exceptions, or None.

    Handles exceptions from yaml, toml, jinja2, and filesystem operations
    to provide user-friendly error messages.
    """
    import yaml

    if isinstance(e, FileNotFoundError):
        return (
            f"File not found: {e.filename}",
            "Check the path exists and spelling is correct",
        )

    if isinstance(e, PermissionError):
        return (
            f"Permission denied: {e.filename}",
            "Check file permissions or run with appropriate access",
        )

    if isinstance(e, yaml.YAMLError):
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            return (
                f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}",
                "Check for missing colons, incorrect indentation, or unquoted special characters",
            )
        return ("Invalid YAML syntax", "Validate your YAML at https://yamlvalidator.com")

    try:
        import tomllib
        if isinstance(e, tomllib.TOMLDecodeError):
            return (f"TOML syntax error: {e}", "Check for unquoted strings or missing brackets")
    except ImportError:
        pass

    try:
        import jinja2
        if isinstance(e, jinja2.TemplateError):
            return (f"Template error: {e.message}", "Check template syntax and variable names")
    except ImportError:
        pass

    return None
```

### Phase 5: Error Documentation Pages (Auto-Generated)

Instead of manually writing 54 error pages, auto-generate them from the `ErrorCode` enum.

#### Generator Script (`scripts/generate_error_docs.py`)

```python
#!/usr/bin/env python3
"""Generate error documentation pages from ErrorCode enum."""

from pathlib import Path
from bengal.errors.codes import ErrorCode

TEMPLATE = '''---
title: "{code}: {title}"
description: "{description}"
error_code: "{code}"
category: "{category}"
---

## What This Means

{what_this_means}

## Common Causes

{common_causes}

## How to Fix

{how_to_fix}

## Example

{example}

## Related

- [Error Code Reference](/docs/errors/)
- [{category} Errors](/docs/errors/#{category_anchor})
'''

# Mapping of error codes to their documentation content
ERROR_DOCS = {
    "C001": {
        "title": "Config YAML Parse Error",
        "description": "Invalid YAML/TOML syntax in configuration file",
        "what_this_means": "The configuration file (`bengal.toml` or `bengal.yaml`) contains invalid syntax that cannot be parsed.",
        "common_causes": "- Missing colons after keys\\n- Incorrect indentation (YAML uses spaces, not tabs)\\n- Unquoted special characters (`:`, `#`, `@`)\\n- Unclosed quotes or brackets",
        "how_to_fix": "1. Check the line number in the error message\\n2. Look for the common issues above\\n3. Use a YAML validator: https://yamlvalidator.com",
        "example": "**❌ Invalid**:\\n```yaml\\ntitle My Site    # Missing colon\\n```\\n\\n**✅ Valid**:\\n```yaml\\ntitle: My Site\\n```",
    },
    # ... add entries for other codes
}

def generate_docs(output_dir: Path) -> None:
    """Generate error documentation pages."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for code in ErrorCode:
        doc_content = ERROR_DOCS.get(code.name)
        if doc_content:
            content = TEMPLATE.format(
                code=code.name,
                category=code.category.title(),
                category_anchor=code.category.lower(),
                **doc_content,
            )
        else:
            # Generate stub for codes without custom content
            content = f'''---
title: "{code.name}: {code.value.replace('_', ' ').title()}"
error_code: "{code.name}"
category: "{code.category}"
---

## What This Means

Error code `{code.name}` indicates a {code.category} error: **{code.value.replace('_', ' ')}**.

## How to Fix

Check the error message for specific details about what went wrong.

## Related

- [Error Code Reference](/docs/errors/)
'''

        output_path = output_dir / f"{code.name.lower()}.md"
        output_path.write_text(content)
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    generate_docs(Path("site/content/docs/errors"))
```

#### Index Page (`site/content/docs/errors/_index.md`)

```markdown
---
title: Error Code Reference
description: Complete reference for all Bengal error codes
---

## Error Categories

Bengal uses prefixed error codes for quick identification and searchability.

| Prefix | Category | Description |
|--------|----------|-------------|
| C | Config | Configuration loading and validation |
| N | Content | Frontmatter, markdown, taxonomy |
| R | Rendering | Template rendering and output |
| D | Discovery | Content and section discovery |
| A | Cache | Build cache operations |
| S | Server | Development server |
| T | Template | Template functions, shortcodes |
| P | Parsing | YAML, JSON, TOML, markdown |
| X | Asset | Static asset processing |
| G | Graph | Graph analysis |

## All Error Codes

{{< error-code-list >}}
```

### Phase 6: Lint Rule for Error Code Enforcement (Optional)

Add a pre-commit hook or test to ensure new `BengalError` raises include error codes:

```python
# tests/lint/test_error_codes.py

import ast
import re
from pathlib import Path

BENGAL_ROOT = Path("bengal")
EXEMPT_DIRS = {"errors", "tests"}  # Allow examples in errors/ without codes

def test_all_bengal_errors_have_codes():
    """Ensure all BengalError raises include code= parameter."""
    violations = []

    for py_file in BENGAL_ROOT.rglob("*.py"):
        if any(exempt in py_file.parts for exempt in EXEMPT_DIRS):
            continue

        content = py_file.read_text()

        # Find raises without code=
        pattern = r'raise\s+Bengal\w+Error\([^)]*\)'
        for match in re.finditer(pattern, content, re.DOTALL):
            if 'code=' not in match.group():
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                violations.append(f"{py_file}:{line_num}")

    if violations:
        msg = "BengalError raises missing code= parameter:\n"
        msg += "\n".join(f"  - {v}" for v in violations)
        raise AssertionError(msg)
```

---

## Implementation Plan

### Milestone 1: CLI Error Display (1-2 hours) — ✅ COMPLETE
- [x] Graceful KeyboardInterrupt in `__main__.py` ✅ DONE
- [x] Create `display_bengal_error()` helper in `bengal/cli/helpers/error_display.py`
- [x] Update `@handle_cli_errors()` to detect `BengalError`
- [x] Test with existing analysis/ errors (they already have codes)

### Milestone 2: Core Error Codes (2-3 hours) — ✅ COMPLETE
- [x] Add codes to `bengal/config/loader.py` (C003)
- [x] Add codes to `bengal/discovery/page_factory.py` (N004, D002, N010)
- [x] Add codes to `bengal/rendering/engines/` (C003)
- [x] Add codes to `bengal/orchestration/build/` (D003, R002)
- [x] Add codes to `bengal/core/site/core.py` (D005)
- [x] Add codes to `bengal/core/theme/config.py` (C003)
- [x] Add codes to `bengal/core/menu.py` (C007)
- [x] Add codes to `bengal/themes/config.py` (C001, C003)
- [x] Add codes to `bengal/directives/` (T004, T005)

### Milestone 3: Common Exceptions (1 hour) — ✅ COMPLETE
- [x] Create `beautify_common_exception()` helper in `error_display.py`
- [x] Handle YAML/TOML/Jinja2 errors specifically
- [x] Handle file system errors (not found, permission)
- [x] Integrate into CLI error handler

### Milestone 4: Documentation (1 hour) — ✅ COMPLETE
- [x] Create `scripts/generate_error_docs.py`
- [x] Write detailed content for top 10 most common codes
- [x] Generate stubs for remaining codes (72 total)
- [x] Create error code index page

### Milestone 5: Testing & Enforcement (1 hour) — ✅ COMPLETE
- [x] Create `tests/lint/test_error_codes.py` for enforcement
- [x] Test error display for each code category
- [x] Test common exception beautification

### Remaining Work (26 files still need error codes)
The lint rule identifies 26 remaining files in autodoc/, content_layer/, and utility modules
that need error codes. These are lower priority than core flows but should be addressed.

---

## Metrics & Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| ErrorCode in core raises | 0% (0/61) | 100% |
| Errors with suggestions | ~10% | 80%+ |
| Errors linking to docs | 0% | 100% |
| Ugly tracebacks on interrupt | No (fixed) | No |

**User Experience Test**:

A new user encountering an error should be able to:
1. ✅ Understand what went wrong (clear message with code)
2. ✅ Know where to look (file + line, clickable in terminal)
3. ✅ Know how to fix it (actionable suggestion)
4. ✅ Find more help (docs link)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing error handling | Low | Medium | Preserve exception chaining, additive changes only |
| Too verbose for experienced users | Medium | Low | Respect `BENGAL_TRACEBACK=minimal`, hide docs link in minimal mode |
| Stale documentation links | Low | Low | Build-time check for dead links, auto-generate from code |
| Scope creep on docs | Medium | Low | Auto-generate stubs, only write detailed docs for top 10 codes |

---

## Alternatives Considered

### 1. Keep error codes internal-only
**Rejected**: We already invested in building them; not using them is waste.

### 2. Auto-generate codes at runtime  
**Rejected**: Stable codes are better for documentation, searchability, and support.

### 3. Full Rust-style error formatting
**Deferred**: Rich error display with code snippets and caret pointers (like rustc) is nice-to-have but not MVP. Could add in Phase 7.

### 4. AI-generated suggestions
**Deferred**: Static suggestions are sufficient for MVP. Could integrate later for complex errors.

---

## Open Questions

1. **Should we show codes in non-TTY output?**
   - **Answer**: Yes — codes are useful for searching, logging, and bug reports.

2. **Should we track which errors users hit most?**
   - **Deferred**: Nice analytics but not necessary for MVP. Could add opt-in telemetry later.

3. **Should related_files use fuzzy matching?**
   - **Answer**: Yes for template errors — suggest similar template names when R001 (template not found) occurs.

---

## Related Work

- `bengal/errors/codes.py` — 54 error code definitions
- `bengal/errors/exceptions.py` — Exception hierarchy with full context support
- `bengal/errors/suggestions.py` — Suggestion system (underutilized)
- `bengal/errors/traceback/` — Traceback configuration (BENGAL_TRACEBACK)
- `bengal/cli/helpers/error_handling.py` — CLI error decorator (needs update)
- `bengal/__main__.py` — Entry point with KeyboardInterrupt handling ✅

---

## Appendix: Error Code Reference

### Category Overview

| Category | Prefix | Count | Subsystem |
|----------|--------|-------|-----------|
| Config | C | 8 | `bengal.config` |
| Content | N | 10 | `bengal.core`, `bengal.discovery` |
| Rendering | R | 10 | `bengal.rendering` |
| Discovery | D | 7 | `bengal.discovery` |
| Cache | A | 6 | `bengal.cache` |
| Server | S | 5 | `bengal.server` |
| Template Function | T | 9 | `bengal.rendering` |
| Parsing | P | 6 | `bengal.core` |
| Asset | X | 6 | `bengal.assets` |
| Graph | G | 5 | `bengal.analysis` |

### Config Errors (C001-C008)

| Code | Name | Description |
|------|------|-------------|
| C001 | config_yaml_parse_error | Invalid YAML/TOML syntax |
| C002 | config_key_missing | Required key not found |
| C003 | config_invalid_value | Value failed validation |
| C004 | config_type_mismatch | Wrong type for field |
| C005 | config_defaults_missing | defaults.yaml not found |
| C006 | config_environment_unknown | Unknown environment name |
| C007 | config_circular_reference | Circular config inheritance |
| C008 | config_deprecated_key | Using deprecated option |

### Content Errors (N001-N010)

| Code | Name | Description |
|------|------|-------------|
| N001 | frontmatter_invalid | Can't parse frontmatter |
| N002 | frontmatter_date_invalid | Bad date format |
| N003 | content_file_encoding | Non-UTF8 content |
| N004 | content_file_not_found | Content file missing |
| N005 | content_markdown_error | Markdown parsing failed |
| N006 | content_shortcode_error | Shortcode execution failed |
| N007 | content_toc_extraction_error | TOC extraction failed |
| N008 | content_taxonomy_invalid | Invalid taxonomy value |
| N009 | content_weight_invalid | Invalid weight value |
| N010 | content_slug_invalid | Invalid slug format |

### Rendering Errors (R001-R010)

| Code | Name | Description |
|------|------|-------------|
| R001 | template_not_found | Template file missing |
| R002 | template_syntax_error | Jinja2 syntax error |
| R003 | template_undefined_variable | Undefined variable in template |
| R004 | template_filter_error | Filter execution failed |
| R005 | template_include_error | Include/import failed |
| R006 | template_macro_error | Macro execution failed |
| R007 | template_block_error | Block definition error |
| R008 | template_context_error | Context building failed |
| R009 | template_inheritance_error | Template inheritance failed |
| R010 | render_output_error | Output write failed |

*(Full list: 54 codes in `bengal/errors/codes.py`)*

---

## Verification Checklist

Before marking this RFC as complete:

- [ ] `bengal build` on invalid YAML shows `[C001]` with suggestion
- [ ] `bengal build` on missing template shows `[R001]` with similar templates
- [ ] `Ctrl+C` during build shows "Build interrupted" (no traceback)
- [ ] `BENGAL_TRACEBACK=off` hides all tracebacks
- [ ] `BENGAL_TRACEBACK=full` shows full traceback after beautiful error
- [ ] Error docs pages accessible at `/docs/errors/c001/`
- [ ] Lint rule catches new raises without `code=` (optional)
