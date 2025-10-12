Title: Autodoc CLI nesting for subcommands (theme new) - COMPLETE

Context
- The CLI autodoc output flattened commands by simple name, causing collisions (e.g., theme new rendered at cli/commands/new/).
- This made subcommands appear as top-level commands in docs and overwrote similarly named groups.
- **Additional issue discovered 2025-10-12**: Nested command groups were generating BOTH `commands/assets.md` AND `commands/assets/_index.md`, causing race conditions during parallel builds and FileNotFoundError when atomic writes failed.

Changes Made
1. Updated `bengal/autodoc/extractors/cli.py:get_output_path` to namespace by `qualified_name`:
   - Root command-group → `_index.md` (unchanged)
   - Nested command-group → `commands/<qualified path minus root>/_index.md`
   - Command → `commands/<qualified path minus root>.md`

2. **Fixed duplicate file generation (2025-10-12)**:
   - Modified `_extract_from_click` method's `flatten_commands` function
   - Command groups now only generate their `_index.md` file (not duplicate `.md` files)
   - Commands in nested groups properly generate individual pages in the group's directory

Impact
- `theme new` becomes `cli/commands/theme/new/`.
- The top-level `new` command-group index becomes `cli/commands/new/` (index), avoiding collision.
- CLI reference templates already handle subsections, so nested groups appear under "Command Groups" with their commands listed on their group page.
- **No more race conditions**: Each command group generates exactly one index file, preventing FileNotFoundError during parallel rendering

Notes
- No linter issues introduced.
- No template changes required.
- Tested with `bengal autodoc-cli --app bengal.cli:main --output content/cli --clean`
- Build completes successfully without file conflicts

Status: COMPLETE

Tests:
- Updated existing tests in `tests/unit/autodoc/test_cli_extractor.py`
- Fixed `test_nested_group_output_path` to expect `_index.md` for nested groups
- Fixed `test_nested_subcommand_output_path` to expect proper namespacing (e.g., `commands/manage/create.md`)
- Added `test_no_duplicate_files_for_nested_groups` to verify no duplicate path generation
- All 21 tests pass (2 skipped) ✓

Date Completed: 2025-10-12
