Title: Expanding CLI Autodoc Support (argparse & Typer)

## Current State
- ✅ **Click**: Fully implemented and tested
- ✅ **Typer**: IMPLEMENTED (2025-10-12) - Converts to Click and reuses existing extraction
- ❌ **argparse**: Stub only (raises NotImplementedError)

## Difficulty Assessment

### 1. Typer Support - **EASY** (1-2 hours)

**Why It's Easy:**
- Typer is built on top of Click
- Typer apps expose a `.click()` method that returns a Click Group/Command
- Can largely reuse existing Click extraction logic

**Implementation Strategy:**
```python
def _extract_from_typer(self, app: Any) -> list[DocElement]:
    """Extract documentation from Typer app."""
    # Typer apps have a .click() method that returns Click objects
    try:
        click_app = app.click()
        return self._extract_from_click(click_app)
    except AttributeError:
        # Fallback: try to get the Click app directly
        if hasattr(app, 'registered_commands'):
            # Build Click group from Typer commands
            pass
    raise ValueError("Unable to extract Click app from Typer")
```

**Effort:** ~2 hours
- Convert Typer → Click
- Test with sample Typer apps
- Handle edge cases (type hints display)

---

### 2. argparse Support - **MODERATE** (4-8 hours)

**Why It's More Complex:**
- argparse uses a different introspection model
- No hierarchical command groups like Click (though subparsers exist)
- Less structured metadata

**What argparse Exposes:**

```python
parser = ArgumentParser()
parser.add_argument('--verbose', '-v', action='store_true')

# Available attributes:
parser._actions          # List of Action objects (arguments/options)
parser._subparsers       # Subparser actions (for command groups)
parser.description       # Help text
parser.epilog           # Footer text

# Each Action has:
action.dest             # Variable name
action.help             # Help text
action.default          # Default value
action.type             # Type converter
action.choices          # Valid choices
action.required         # Whether required
action.option_strings   # ['-v', '--verbose']
```

**Implementation Strategy:**

```python
def _extract_from_argparse(self, parser: Any) -> list[DocElement]:
    """Extract documentation from argparse ArgumentParser."""
    elements = []

    # Main parser becomes command-group
    main_doc = DocElement(
        name=parser.prog or "cli",
        qualified_name=parser.prog or "cli",
        description=parser.description or "",
        element_type="command-group",
        children=self._extract_argparse_actions(parser),
    )
    elements.append(main_doc)

    # Extract subparsers (if any)
    for action in parser._subparsers._actions if parser._subparsers else []:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                elements.extend(self._extract_argparse_subparser(subparser, name))

    return elements

def _extract_argparse_actions(self, parser) -> list[DocElement]:
    """Extract arguments/options from parser."""
    children = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue  # Skip --help

        element = DocElement(
            name=action.dest,
            qualified_name=f"{parser.prog}.{action.dest}",
            description=action.help or "",
            element_type="option" if action.option_strings else "argument",
            metadata={
                "type": action.type.__name__ if action.type else "str",
                "default": str(action.default) if action.default else None,
                "required": action.required,
                "opts": action.option_strings,
                "choices": action.choices,
            }
        )
        children.append(element)

    return children
```

**Challenges:**
1. **Subparser hierarchy**: argparse subparsers are less structured than Click groups
2. **Action types**: Many action types (store_true, store_const, append, etc.)
3. **Metavar/formatting**: argparse has different help formatting conventions
4. **Private API**: Uses `_actions`, `_subparsers` (private attributes)

**Effort:** ~6 hours
- 2 hours: Basic parser extraction
- 2 hours: Subparser/command group support
- 1 hour: Handle all Action types properly
- 1 hour: Testing and edge cases

---

### 3. Output Path Consistency

All frameworks need to work with our existing path structure:
- Root CLI → `_index.md`
- Command groups → `commands/group/_index.md`
- Commands → `commands/cmd.md`
- Nested → `commands/group/subcmd.md`

This is already handled by `get_output_path()`, so no changes needed there.

---

## Recommendation

**Phase 1: Typer (Quick Win)**
- Add Typer support first - it's trivial since it wraps Click
- Provides immediate value for Typer users
- Can ship in ~2 hours

**Phase 2: argparse (If Needed)**
- Only implement if there's demand
- More work for potentially less benefit (Click/Typer are more modern)
- argparse users might be better served by sphinx-argparse extensions

**Phase 3: Consider Other Frameworks**
- **docopt**: Very simple (just parse docstring), but less common
- **fire**: Google's framework, could be interesting
- **cleo**: Symfony-inspired, less common in Python

## Testing Strategy

For each framework:
1. Create fixture CLI apps in `tests/fixtures/cli_apps/`
2. Add test class in `test_cli_extractor.py`
3. Test command extraction, options, arguments, nested groups
4. Verify output paths match expected structure

## Estimated Total Effort

- **Typer only**: 2 hours (recommended)
- **Typer + argparse**: 8-10 hours
- **All three + docopt**: 12-15 hours

## Priority

Given that Bengal itself uses Click, and Typer is Click-based:
- ~~**High**: Typer support (helps users, easy to add)~~ **✅ COMPLETE**
- **Low**: argparse (older style, alternatives exist)
- **Very Low**: docopt, fire, cleo (uncommon)

---

## Implementation Complete: Typer Support (2025-10-12)

### What Was Implemented

Added full Typer framework support to the CLI autodoc system by converting Typer apps to Click and reusing the existing Click extraction logic.

**Files Modified:**
- `bengal/autodoc/extractors/cli.py`:
  - Implemented `_extract_from_typer()` method (previously raised NotImplementedError)
  - Added `_typer_to_click_group()` helper method
  - Uses Typer's built-in `typer.main.get_group()` conversion (Method 2, most reliable)
  - Falls back to manual construction and older APIs if needed

- `tests/unit/autodoc/test_cli_extractor.py`:
  - Added Typer availability check
  - Created sample Typer app with nested commands (mirroring Click test structure)
  - Added 9 new tests in `TestTyperExtractor` class:
    - `test_extract_typer_app`
    - `test_typer_commands_extracted`
    - `test_typer_nested_app_extracted`
    - `test_typer_subcommands_extracted`
    - `test_typer_command_with_arguments`
    - `test_typer_command_with_options`
    - `test_typer_qualified_names`
    - `test_typer_output_paths`
    - `test_typer_no_duplicate_files`

**Test Results:**
- All 30 CLI extractor tests pass (2 skipped)
- All 9 new Typer tests pass
- No linter errors
- Coverage increased from 73% to 77% in `cli.py`

**How It Works:**
1. User creates Typer app: `app = typer.Typer()`
2. Extractor receives framework="typer"
3. `_extract_from_typer()` calls `typer.main.get_group(app)` to convert to Click
4. Converted Click app is passed to existing `_extract_from_click()` logic
5. All output paths, qualified names, and structures work identically to Click

**Benefits:**
- Zero code duplication (reuses Click logic)
- Handles all Typer features (commands, groups, options, arguments)
- Nested Typer apps work correctly
- No duplicate file generation
- Same output structure as Click docs

**Time Taken:** ~2 hours (as estimated)
