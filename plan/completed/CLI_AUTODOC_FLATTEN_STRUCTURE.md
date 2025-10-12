# CLI Autodoc: Flatten Directory Structure

**Date:** 2025-10-12  
**Status:** ✅ Complete

## Problem

The CLI autodoc system was generating documentation with an unnecessary `/commands/` directory nesting:

```
content/cli/
  _index.md          (root: bengal CLI)
  commands/          ← UNNECESSARY NESTING
    build.md
    serve.md
    theme/
      _index.md
      new.md
      swizzle.md
```

This created a "Commands" folder in the navigation tree where **every single page** was buried, making the navigation unnecessarily deep.

## Analysis

**Question:** Are there scenarios where CLI docs would have other top-level buckets besides commands?

**Answer:** No. The CLI autodoc element types are:
- `command-group` (main CLI + nested groups like `theme`, `new`)
- `command` (individual commands)
- `option` (flags/options - always children of commands)
- `argument` (positional args - always children of commands)

Options and arguments never get their own pages. There's **no scenario** where you'd have anything besides commands at the top level.

**Industry Standard:** Other CLI documentation systems (Docker, kubectl, git) all place commands directly under the root without a `/commands/` folder.

## Solution

Flattened the structure by removing the `/commands/` prefix from output paths:

```
content/cli/
  _index.md          (root: bengal CLI)
  build.md           ← Direct children
  serve.md
  theme/             ← Nested groups
    _index.md
    new.md
    swizzle.md
```

## Changes Made

### 1. Updated `bengal/autodoc/extractors/cli.py`
Modified `get_output_path()` method:
- `command-group` (main) → `_index.md` (unchanged)
- `command-group` (nested) → `{name}/_index.md` (was `commands/{name}/_index.md`)
- `command` → `{name}.md` (was `commands/{name}.md`)

### 2. Updated Tests
Updated path expectations in `tests/unit/autodoc/test_cli_extractor.py`:
- `test_nested_group_output_path()`
- `test_nested_subcommand_output_path()`
- `test_no_duplicate_files_for_nested_groups()`
- `test_typer_output_paths()`

All tests pass: ✅ 30 passed, 2 skipped

### 3. Updated CLI Reference Template
Simplified `bengal/themes/default/templates/cli-reference/list.html`:
- Removed obsolete logic that flattened `/commands/` subdirectory (lines 56-69)
- Now directly renders `posts` (commands) and `subsections` (command groups)
- Cleaner, simpler template that matches the new flat structure

### 4. Left Navigation
No changes needed to `partials/docs-nav.html` - it's generic and automatically adapts to the new structure. Custom nav templates are **not required**.

## Benefits

1. **Cleaner Navigation:** Commands appear directly under the CLI root instead of buried under "Commands"
2. **Industry Standard:** Matches how other CLI tools document their commands
3. **Better UX:** Fewer clicks to reach command documentation
4. **Simpler Structure:** More intuitive organization

## Breaking Change

This is a **breaking change** for existing CLI autodoc users:
- Generated file paths will change
- Links to CLI documentation will need updating
- Custom navigation templates may need adjustment

## Migration

Projects using CLI autodoc should:
1. Regenerate CLI documentation with `bengal autodoc-cli`
2. Update any hardcoded links to CLI docs
3. Update custom navigation templates if using them

## Related

- Issue raised during theme improvements work
- Part of the broader documentation UX improvements
