# CLI Refinement Opportunities Analysis

**Date**: 2025-01-27  
**Status**: Phase 1 Implementation Complete  
**Scope**: `bengal/cli/` directory and related utilities

## Implementation Status

### ✅ Phase 1: Foundation (Completed)
- ✅ Created `bengal/cli/helpers/` directory structure
- ✅ Implemented unified error handling (`error_handling.py`)
- ✅ Created site loading helper (`site_loader.py`)
- ✅ Created traceback configuration helper (`traceback.py`)
- ✅ Extracted duplicate help text sanitization to module-level function
- ✅ Refactored `serve.py` to use new helpers
- ✅ Refactored `health.py` to use new helpers
- ✅ Created CLI testing utilities (`tests/_testing/cli_helpers.py`)

### 🔄 Phase 2: Consistency (Pending)
- ⏳ Refactor `build.py` to use new helpers
- ⏳ Standardize CLIOutput usage across all commands
- ⏳ Add progress feedback to long-running operations
- ⏳ Improve help text across all commands

### 📋 Phase 3: Polish (Pending)
- ⏳ Extract remaining duplicate code
- ⏳ Add command metadata
- ⏳ Implement lazy loading
- ⏳ Add validation decorators

## Executive Summary

The Bengal CLI is well-structured with good separation of concerns, but there are several opportunities for refinement across code organization, error handling, consistency, and user experience. This analysis identifies 8 major categories of improvements with specific, actionable recommendations.

---

## 1. Code Organization & Structure

### 1.1 Command Registration Inconsistency

**Issue**: Commands are registered in multiple places with inconsistent patterns.

**Current State**:
- `bengal/cli/__init__.py` registers top-level commands
- `bengal/cli/commands/site.py` registers subcommands (`build`, `serve`, `clean`)
- `bengal/cli/commands/utils.py` registers utility commands
- Some commands have compatibility exports (`build_command`, `serve_command`)

**Problems**:
- Hard to discover all commands
- Inconsistent grouping logic
- Compatibility exports suggest refactoring needed

**Recommendation**:
```python
# Create bengal/cli/registry.py
class CommandRegistry:
    """Centralized command registration with metadata."""

    def register_group(self, name: str, commands: list[click.Command]):
        """Register a command group."""
        pass

    def get_all_commands(self) -> dict[str, click.Command]:
        """Get all registered commands for discovery."""
        pass
```

**Impact**: Medium  
**Effort**: Low  
**Priority**: Medium

---

### 1.2 Duplicate Help Text Sanitization

**Issue**: `_sanitize_help_text()` function is duplicated in `BengalCommand` and `BengalGroup`.

**Location**: `bengal/cli/base.py:17-36` and `118-135`

**Recommendation**:
```python
# Extract to module-level function or utility class
def sanitize_help_text(text: str) -> str:
    """Remove Commands section from help text to avoid duplication."""
    # ... existing logic ...
```

**Impact**: Low  
**Effort**: Very Low  
**Priority**: Low

---

### 1.3 Command File Size

**Issue**: Some command files are very large (e.g., `build.py` is 567 lines, `new.py` is 1012 lines).

**Problems**:
- Hard to maintain
- Multiple responsibilities per file
- Difficult to test in isolation

**Recommendation**:
- Extract helper functions to separate modules
- Split `new.py` into `new/site.py`, `new/page.py`, `new/layout.py`, etc.
- Extract autodoc logic from `build.py` to `bengal/cli/helpers/autodoc.py`

**Impact**: High  
**Effort**: Medium  
**Priority**: Medium

---

## 2. Error Handling Patterns

### 2.1 Inconsistent Error Handling

**Issue**: Commands use different error handling patterns:

**Pattern A** (most common):
```python
try:
    # ... command logic ...
except Exception as e:
    show_error(f"Failed: {e}", show_art=False)
    raise click.Abort() from e
```

**Pattern B** (some commands):
```python
except ConfigLoadError as e:
    show_error(f"Config load failed: {e}", show_art=False)
    raise click.Abort()
except Exception as e:
    show_error(f"Error: {e}", show_art=False)
    raise click.Abort()
```

**Pattern C** (health.py):
```python
except click.Abort:
    raise
except Exception as e:
    cli.error(f"Link check failed: {e}")
    with contextlib.suppress(Exception):
        TracebackConfig.from_environment().get_renderer().display_exception(e)
    raise click.Abort() from e
```

**Problems**:
- No consistent pattern for different error types
- Some preserve exception chain (`from e`), others don't
- Traceback handling is inconsistent

**Recommendation**: Create a decorator or context manager:

```python
# bengal/cli/helpers/error_handling.py
@click.command()
@handle_cli_errors
def my_command():
    """Command with automatic error handling."""
    pass

# Or context manager:
def my_command():
    with cli_error_handler():
        # ... command logic ...
        pass
```

**Impact**: High  
**Effort**: Medium  
**Priority**: High

---

### 2.2 Missing Error Context

**Issue**: Many error messages lack context about what was being done when the error occurred.

**Example** (current):
```python
show_error(f"Failed to create site: {e}", show_art=False)
```

**Better**:
```python
show_error(f"Failed to create site '{site_name}': {e}", show_art=False)
```

**Recommendation**: Standardize error messages to include:
- What operation was being performed
- Key parameters/context
- Actionable next steps when possible

**Impact**: Medium  
**Effort**: Low  
**Priority**: Medium

---

## 3. CLI Output Consistency

### 3.1 CLIOutput Instantiation

**Issue**: `CLIOutput()` is instantiated multiple times per command, sometimes with different parameters.

**Examples**:
- `build.py`: Creates `CLIOutput()` 8+ times
- `config.py`: Creates `CLIOutput()` in each command function
- Some commands pass `quiet` parameter, others don't

**Problems**:
- Inconsistent output formatting
- Potential performance overhead (though minimal)
- Hard to maintain consistent state

**Recommendation**:
```python
# Option 1: Pass CLIOutput as context
@click.command()
@click.pass_context
def my_command(ctx):
    cli = ctx.ensure_object(CLIOutput)
    # ... use cli ...

# Option 2: Create CLIOutput at command start, reuse
def my_command(...):
    cli = CLIOutput(quiet=quiet, verbose=verbose)
    # ... reuse cli throughout ...
```

**Impact**: Medium  
**Effort**: Low  
**Priority**: Medium

---

### 3.2 Inconsistent Message Formatting

**Issue**: Commands use different methods for similar output:

- Some use `cli.header()`, others use `cli.info()` with manual formatting
- Some use `cli.success()`, others print directly
- Inconsistent use of emojis/icons

**Recommendation**: Create a style guide and helper methods:

```python
class CLIOutput:
    def operation_start(self, name: str):
        """Standard format for starting an operation."""
        self.header(f"🔄 {name}...")

    def operation_complete(self, name: str, duration_ms: int | None = None):
        """Standard format for completing an operation."""
        if duration_ms:
            self.success(f"✅ {name} completed in {duration_ms}ms")
        else:
            self.success(f"✅ {name} completed")
```

**Impact**: Low  
**Effort**: Low  
**Priority**: Low

---

## 4. Configuration & Context Management

### 4.1 Site Loading Duplication

**Issue**: Many commands duplicate the site loading logic:

```python
root_path = Path(source).resolve()
config_path = Path(config).resolve() if config else None
site = Site.from_config(root_path, config_path, environment=environment, profile=profile)
```

**Location**: Found in `build.py`, `serve.py`, `health.py`, `config.py`, etc.

**Recommendation**: Create a shared helper:

```python
# bengal/cli/helpers/site_loader.py
def load_site_from_cli(
    source: str,
    config: str | None,
    environment: str | None,
    profile: str | None,
) -> Site:
    """Load site with consistent error handling."""
    root_path = Path(source).resolve()
    config_path = Path(config).resolve() if config else None

    try:
        return Site.from_config(root_path, config_path, environment=environment, profile=profile)
    except Exception as e:
        cli = CLIOutput()
        cli.error(f"Failed to load site from {root_path}: {e}")
        raise click.Abort() from e
```

**Impact**: High  
**Effort**: Low  
**Priority**: High

---

### 4.2 Traceback Configuration Duplication

**Issue**: Traceback configuration is duplicated across commands:

```python
# Repeated in build.py, serve.py, health.py, etc.
map_debug_flag_to_traceback(debug, traceback)
set_effective_style_from_cli(traceback)
TracebackConfig.from_environment().install()

# Then later:
try:
    from bengal.utils.traceback_config import apply_file_traceback_to_env
    apply_file_traceback_to_env(site.config)
    TracebackConfig.from_environment().install()
except Exception:
    pass
```

**Recommendation**: Create a decorator or helper:

```python
# bengal/cli/helpers/traceback.py
def configure_traceback(debug: bool, traceback: str | None, site: Site | None = None):
    """Configure traceback handling with proper precedence."""
    map_debug_flag_to_traceback(debug, traceback)
    set_effective_style_from_cli(traceback)
    TracebackConfig.from_environment().install()

    if site:
        try:
            apply_file_traceback_to_env(site.config)
            TracebackConfig.from_environment().install()
        except Exception:
            pass
```

**Impact**: Medium  
**Effort**: Low  
**Priority**: Medium

---

## 5. Option & Argument Validation

### 5.1 Flag Conflict Detection

**Issue**: Flag conflicts are detected manually in each command:

```python
# build.py
if fast and (use_dev or use_theme_dev):
    raise click.UsageError("--fast cannot be used with --dev or --theme-dev profiles")
if quiet and verbose:
    raise click.UsageError("--quiet and --verbose cannot be used together")
```

**Recommendation**: Create a validation decorator:

```python
# bengal/cli/helpers/validation.py
@validate_flags(
    conflicts=[
        ("fast", ["use_dev", "use_theme_dev"]),
        ("quiet", ["verbose"]),
    ]
)
@click.command()
def build(...):
    pass
```

**Impact**: Low  
**Effort**: Medium  
**Priority**: Low

---

### 5.2 Missing Type Validation

**Issue**: Some options accept strings that should be validated (e.g., environment names, profile names).

**Current**:
```python
@click.option("--environment", "-e", type=str, help="Environment name")
```

**Better**:
```python
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment name",
)
```

**Impact**: Low  
**Effort**: Low  
**Priority**: Low

---

## 6. User Experience Improvements

### 6.1 Progress Feedback

**Issue**: Some long-running operations lack progress feedback.

**Examples**:
- `config doctor` doesn't show progress while checking multiple environments
- `health linkcheck` could show progress for large sites
- `autodoc` generation could show file-by-file progress

**Recommendation**: Use Rich progress bars consistently:

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
) as progress:
    task = progress.add_task("Checking environments...", total=len(environments))
    for env in environments:
        # ... check env ...
        progress.update(task, advance=1)
```

**Impact**: Medium  
**Effort**: Medium  
**Priority**: Medium

---

### 6.2 Interactive Prompts

**Issue**: Inconsistent use of interactive prompts.

**Current**: `new.py` uses `questionary` for some prompts, `cli.prompt()` for others.

**Recommendation**: Standardize on a single approach or create a wrapper:

```python
# bengal/cli/helpers/prompts.py
def prompt_user(
    message: str,
    type: type = str,
    default: Any = None,
    choices: list[str] | None = None,
) -> Any:
    """Unified prompt interface with fallback."""
    if choices:
        return questionary.select(message, choices=choices).ask()
    else:
        return CLIOutput().prompt(message, default=default, type=type)
```

**Impact**: Low  
**Effort**: Low  
**Priority**: Low

---

### 6.3 Help Text Quality

**Issue**: Some commands have minimal or unclear help text.

**Examples**:
- `bengal/cli/__init__.py:28`: Main command has empty docstring `""" """`
- Some commands lack examples in help text
- Help text doesn't always explain when to use which option

**Recommendation**:
- Add comprehensive docstrings to all commands
- Include examples in help text
- Add "See also" references to related commands

**Impact**: Medium  
**Effort**: Low  
**Priority**: Medium

---

## 7. Testing & Maintainability

### 7.1 Command Testing Infrastructure

**Issue**: No clear pattern for testing CLI commands.

**Recommendation**: Create test utilities:

```python
# tests/_testing/cli_helpers.py
def run_command(cmd: click.Command, args: list[str]) -> click.testing.Result:
    """Run a command and return result."""
    runner = click.testing.CliRunner()
    return runner.invoke(cmd, args)

def assert_command_success(result: click.testing.Result):
    """Assert command succeeded."""
    assert result.exit_code == 0, f"Command failed: {result.output}"

def assert_command_error(result: click.testing.Result, expected_error: str):
    """Assert command failed with expected error."""
    assert result.exit_code != 0
    assert expected_error in result.output
```

**Impact**: High  
**Effort**: Medium  
**Priority**: High

---

### 7.2 Command Discovery

**Issue**: No easy way to discover all available commands programmatically.

**Recommendation**: Add command metadata:

```python
# bengal/cli/base.py
class BengalCommand(click.Command):
    """Custom command with metadata."""

    def __init__(self, *args, category: str = "general", **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category  # "build", "dev", "content", etc.
        self.experimental = kwargs.pop("experimental", False)
```

**Impact**: Low  
**Effort**: Low  
**Priority**: Low

---

## 8. Performance Optimizations

### 8.1 Lazy Imports

**Issue**: Some commands import heavy modules at module level.

**Example**: `build.py` imports many modules that may not be needed if command isn't run.

**Recommendation**: Use lazy imports in command functions:

```python
@click.command()
def build(...):
    # Import only when command is actually invoked
    from bengal.core.site import Site
    from bengal.utils.build_stats import display_build_stats
    # ... rest of command ...
```

**Impact**: Low  
**Effort**: Low  
**Priority**: Low

---

### 8.2 Command Grouping

**Issue**: All commands are loaded even when only one is needed.

**Current**: `bengal/cli/__init__.py` imports all command modules at startup.

**Recommendation**: Use lazy loading for command groups:

```python
class LazyGroup(click.Group):
    """Group that loads commands on demand."""

    def __init__(self, *args, loader: Callable[[], dict[str, click.Command]], **kwargs):
        super().__init__(*args, **kwargs)
        self._loader = loader
        self._loaded = False

    def list_commands(self, ctx):
        if not self._loaded:
            commands = self._loader()
            for name, cmd in commands.items():
                self.add_command(cmd, name)
            self._loaded = True
        return super().list_commands(ctx)
```

**Impact**: Low  
**Effort**: Medium  
**Priority**: Low

---

## Priority Matrix

### High Priority (Do First)
1. **Error Handling Patterns** (Section 2.1) - Affects all commands
2. **Site Loading Duplication** (Section 4.1) - Reduces code duplication significantly
3. **Command Testing Infrastructure** (Section 7.1) - Enables better testing

### Medium Priority (Do Next)
4. **Command File Size** (Section 1.3) - Improves maintainability
5. **CLIOutput Instantiation** (Section 3.1) - Improves consistency
6. **Traceback Configuration** (Section 4.2) - Reduces duplication
7. **Progress Feedback** (Section 6.1) - Improves UX
8. **Help Text Quality** (Section 6.3) - Improves discoverability

### Low Priority (Nice to Have)
9. **Command Registration** (Section 1.1) - Organizational improvement
10. **Duplicate Help Text** (Section 1.2) - Minor cleanup
11. **Message Formatting** (Section 3.2) - Consistency polish
12. **Flag Conflict Detection** (Section 5.1) - Convenience feature
13. **Type Validation** (Section 5.2) - Better error messages
14. **Interactive Prompts** (Section 6.2) - UX polish
15. **Command Discovery** (Section 7.2) - Developer convenience
16. **Lazy Imports** (Section 8.1) - Minor performance
17. **Command Grouping** (Section 8.2) - Minor performance

---

## Implementation Strategy

### Phase 1: Foundation (High Priority)
1. Create `bengal/cli/helpers/` directory structure
2. Implement error handling decorator/context manager
3. Create site loading helper
4. Create traceback configuration helper
5. Add CLI testing utilities

### Phase 2: Consistency (Medium Priority)
1. Refactor large command files (`new.py`, `build.py`)
2. Standardize CLIOutput usage
3. Add progress feedback to long-running operations
4. Improve help text across all commands

### Phase 3: Polish (Low Priority)
1. Extract duplicate code
2. Add command metadata
3. Implement lazy loading
4. Add validation decorators

---

## Metrics for Success

- **Code Duplication**: Reduce duplicate code by 30%+
- **Error Handling**: 100% of commands use consistent error handling
- **Test Coverage**: 80%+ coverage for CLI commands
- **Help Quality**: All commands have comprehensive help text with examples
- **User Feedback**: Commands provide progress feedback for operations >1s

---

## Related Files

- `bengal/cli/base.py` - Base command classes
- `bengal/cli/commands/` - All command implementations
- `bengal/utils/cli_output.py` - CLI output utilities
- `architecture/cli.md` - CLI architecture documentation

---

## Notes

- This analysis is based on code review of `bengal/cli/` directory
- Recommendations prioritize maintainability and user experience
- Some improvements may require breaking changes (document separately)
- Consider creating RFCs for major refactorings (e.g., command registration system)
