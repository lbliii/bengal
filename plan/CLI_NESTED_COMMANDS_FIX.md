# CLI Nested Command Groups Fix

**Date**: October 4, 2025  
**Status**: ✅ Complete

## Problem

The CLI autodoc was missing documentation pages for nested command groups and their subcommands. For example, `bengal new site` and `bengal new page` commands existed in the CLI but generated no documentation files, resulting in 404 errors when trying to access `/cli/commands/site`.

## Root Cause

The CLI extractor (`bengal/autodoc/extractors/cli.py`) had two bugs:

1. **Missing recursive flattening**: The `_extract_from_click()` method only added direct children of the main CLI group to the elements list, but didn't recursively add subcommands from nested command groups.

2. **Path collision**: The `get_output_path()` method returned `index.md` for ALL command groups, which would cause nested groups to overwrite the main index.

## Solution

### Code Changes

#### 1. Fixed `_extract_from_click()` to recursively flatten nested commands

```python:75:102:bengal/autodoc/extractors/cli.py
def _extract_from_click(self, cli: click.Group) -> List[DocElement]:
    """Extract documentation from Click command group."""
    elements = []
    
    # Main CLI/command group
    main_doc = self._extract_click_group(cli)
    elements.append(main_doc)
    
    # Add each command as a separate top-level element for individual pages
    # Recursively flatten nested command groups
    def flatten_commands(children: List[DocElement]):
        for child in children:
            elements.append(child)
            # If this is a nested command group, also flatten its children
            if child.element_type == 'command-group' and child.children:
                flatten_commands(child.children)
    
    flatten_commands(main_doc.children)
    
    return elements
```

#### 2. Fixed `get_output_path()` to handle nested groups

```python:387:415:bengal/autodoc/extractors/cli.py
def get_output_path(self, element: DocElement) -> Path:
    """Determine output path for CLI element."""
    if element.element_type == 'command-group':
        # Main CLI group gets index.md
        # Nested command groups (like 'new') get their own page in commands/
        if '.' not in element.qualified_name:
            return Path("index.md")
        else:
            return Path(f"commands/{element.name}.md")
    elif element.element_type == 'command':
        # bengal.build → commands/build.md
        # Just use the command name, not the full qualified name
        return Path(f"commands/{element.name}.md")
    else:
        # Shouldn't happen, but fallback
        return Path(f"{element.name}.md")
```

### Test Coverage

Added comprehensive test suite for nested command groups:

- Created a nested `manage` command group with `create` and `delete` subcommands in test fixtures
- Added 10 new tests in `TestNestedCommandGroups` class covering:
  - Nested group extraction
  - Qualified name generation
  - Subcommand flattening
  - Hierarchy preservation
  - Output path generation
  - Element counting

**Test Results**: ✅ 20 passed, 2 skipped

## Files Changed

1. `bengal/autodoc/extractors/cli.py` - Fixed extraction logic
2. `tests/unit/autodoc/test_cli_extractor.py` - Added/updated tests
3. `examples/showcase/content/cli/commands/` - Regenerated docs

## Generated Files

After regeneration, the following CLI documentation files now exist:

- `commands/new.md` - The `new` command group page
- `commands/site.md` - The `bengal new site` command
- `commands/page.md` - The `bengal new page` command

## Verification

```bash
# Regenerate CLI docs
cd examples/showcase
bengal autodoc-cli --app bengal.cli:main --output content/cli

# Output:
✅ CLI Documentation Generated!
   📊 Statistics:
      • Commands: 2
      • Options:  34
      • Pages:    10  # Previously was 7, now 10 (added 3 new pages)
```

URLs now working:
- ✅ http://localhost:5173/cli/commands/site
- ✅ http://localhost:5173/cli/commands/page
- ✅ http://localhost:5173/cli/commands/new

## Impact

This fix ensures that:
- All CLI commands (including nested ones) get proper documentation pages
- No 404 errors for nested command documentation
- Command group hierarchy is properly preserved
- Output paths don't conflict between main and nested groups

## Notes

- The fix handles arbitrary nesting depth (not just one level)
- Click normalizes command names to use dashes (e.g., `sample_cli` → `sample-cli`)
- Tests account for this normalization behavior

