# CLI Improvement Roadmap - Next Steps

**Date**: 2025-01-27  
**Status**: Phase 1 Complete, Phase 2 In Progress  
**Last Updated**: After initial improvements

---

## ✅ Completed (Phase 1)

1. ✅ **Standardized Error Handling** - Added `@handle_cli_errors` to:
   - `config.py` (all 4 commands)
   - `build.py`
   - `serve.py`
   - `health.py` (linkcheck)

2. ✅ **Extracted Large Command Logic**:
   - Created `helpers/config_validation.py` (80 lines)
   - Created `helpers/autodoc_build.py` (140 lines)
   - Reduced `config.py` from 684 → 470 lines
   - Reduced `build.py` from 561 → 420 lines

3. ✅ **Added Type Validation**:
   - Environment options now use `click.Choice` in:
     - `config.py` (show, doctor, diff)
     - `build.py`
     - `serve.py`

4. ✅ **Standardized Output**:
   - Replaced `print()` with `cli.console.print()` in:
     - `config.py` (show command)
     - `health.py` (linkcheck command)

---

## 🔴 High Priority (Do Next)

### 1. Complete Error Handling Standardization

**Status**: ~60% complete  
**Remaining Commands**:

- [ ] `new.py` - All subcommands (site, page, layout, partial, theme)
- [ ] `project.py` - All commands (profile, validate, info, config)
- [ ] `clean.py` - clean command
- [ ] `assets.py` - build command
- [ ] `autodoc.py` - autodoc and autodoc-cli commands
- [ ] `graph/` commands - analyze, suggest, pagerank, communities, bridges
- [ ] `theme.py` - theme commands
- [ ] `perf.py` - perf command

**Effort**: 1-2 hours  
**Impact**: High (consistency)

**Example**:
```python
@click.command()
@handle_cli_errors(show_art=False)  # Add this
def my_command():
    # Remove manual try/except blocks
    pass
```

---

### 2. Add Command Metadata to All Commands

**Status**: ~40% complete  
**Commands Missing Metadata**:

- [ ] `new.py` - page, layout, partial, theme subcommands
- [ ] `project.py` - profile, validate, info, config commands
- [ ] `clean.py` - clean command
- [ ] `assets.py` - build command
- [ ] `autodoc.py` - autodoc-cli command
- [ ] `graph/` - All graph commands
- [ ] `theme.py` - All theme commands
- [ ] `perf.py` - perf command

**Effort**: 2-3 hours  
**Impact**: Medium (discoverability, documentation)

**Example**:
```python
@click.command()
@command_metadata(
    category="content",
    description="Create a new page",
    examples=["bengal new page my-page", "bengal new page --section blog"],
    requires_site=True,
    tags=["content", "quick"],
)
def page():
    pass
```

---

### 3. Fix Main Command Docstring

**Issue**: `bengal/cli/__init__.py:28` has empty docstring `""" """`

**Fix**:
```python
def main(ctx) -> None:
    """
    Bengal Static Site Generator CLI.

    Build fast, modern static sites with Python.

    Quick Start:
        bengal new site my-site    Create a new site
        bengal site build          Build your site
        bengal site serve          Start dev server

    For more information, see: https://bengal.dev/docs
    """
```

**Effort**: 5 minutes  
**Impact**: Low (but easy win)

---

## 🟡 Medium Priority

### 4. Add Progress Feedback

**Commands Needing Progress Bars**:

- [ ] `config.py` - `show` command (for large configs)
- [ ] `new.py` - `site` command (file creation)
- [ ] `autodoc.py` - Documentation generation
- [ ] `assets.py` - Asset building (if slow)

**Effort**: 2-3 hours  
**Impact**: Medium (user experience)

**Example**:
```python
with cli_progress("Generating docs...", total=len(files), cli=cli) as update:
    for file in files:
        generate_doc(file)
        update(advance=1)
```

---

### 5. Improve Help Text Quality

**Commands Needing Better Help**:

- [ ] `clean.py` - Add more examples
- [ ] `assets.py` - Expand description
- [ ] `project.py` - Add "See also" sections
- [ ] `graph/` commands - Add usage examples

**Effort**: 1-2 hours  
**Impact**: Medium (discoverability)

**Template**:
```python
"""
📋 Command description.

Detailed explanation of what the command does and when to use it.

Examples:
    bengal command --option value
    bengal command --other-flag

See also:
    bengal related-command - Related functionality
    bengal other-command - Other related command
"""
```

---

### 6. Standardize CLIOutput Instantiation

**Current Issue**: Some commands create `CLIOutput()` multiple times

**Commands to Fix**:
- [ ] `new.py` - Multiple instantiations in helpers
- [ ] `project.py` - Some commands create new instances
- [ ] `clean.py` - Creates CLIOutput mid-function

**Pattern**:
```python
def my_command():
    cli = get_cli_output()  # Create once at start
    # Pass cli to helpers instead of creating new instances
    helper_function(cli=cli)
```

**Effort**: 1 hour  
**Impact**: Low (consistency polish)

---

## 🟢 Low Priority (Nice to Have)

### 7. Remove Compatibility Exports

**Location**: `bengal/cli/commands/site.py:24-27`

```python
# Remove these if no longer needed:
build_command = build
serve_command = serve
clean_command = clean
```

**Effort**: 5 minutes + verify no usage  
**Impact**: Low (cleanup)

---

### 8. Add Flag Conflict Validation Decorators

**Current**: Manual validation in some commands

**Example** (`serve.py:103-106`):
```python
# Replace manual check with decorator:
@validate_mutually_exclusive(("verbose", "debug"))
def serve():
    # Remove manual if statement
```

**Commands**:
- [ ] `serve.py` - verbose/debug conflict
- [ ] `build.py` - memory_optimized/perf_profile conflict (already has manual check)

**Effort**: 30 minutes  
**Impact**: Low (convenience)

---

### 9. Consider Lazy Command Loading

**Current**: All commands imported at startup

**Benefit**: Faster CLI startup (minimal impact)

**Effort**: Medium (2-3 hours)  
**Impact**: Low (performance)

---

## 📊 Progress Summary

### Error Handling
- **Current**: ~60% of commands use decorator
- **Target**: 100%
- **Remaining**: ~15 commands

### Command Metadata
- **Current**: ~40% of commands have metadata
- **Target**: 100%
- **Remaining**: ~20 commands

### Code Organization
- **Current**: ✅ Large files extracted
- **Status**: Complete

### Type Validation
- **Current**: ✅ Environment options validated
- **Status**: Complete

---

## Recommended Order

### Week 1: Consistency (High Priority)
1. Complete error handling standardization (1-2 hours)
2. Add command metadata to all commands (2-3 hours)
3. Fix main command docstring (5 minutes)

**Total**: ~4-5 hours

### Week 2: User Experience (Medium Priority)
4. Add progress feedback (2-3 hours)
5. Improve help text (1-2 hours)
6. Standardize CLIOutput usage (1 hour)

**Total**: ~4-6 hours

### Week 3: Polish (Low Priority)
7. Remove compatibility exports (5 minutes)
8. Add flag conflict decorators (30 minutes)
9. Consider lazy loading (if needed)

**Total**: ~1 hour (or 3-4 if doing lazy loading)

---

## Success Metrics

**Target State**:
- ✅ 100% of commands use `@handle_cli_errors`
- ✅ 100% of commands have `@command_metadata`
- ✅ All commands have comprehensive help text with examples
- ✅ Progress feedback for operations >1s
- ✅ Consistent CLIOutput usage patterns

**Current State**:
- ✅ ~60% error handling consistency
- ✅ ~40% command metadata coverage
- ✅ Mixed help text quality
- ⚠️ Progress feedback missing in some places
- ✅ Mostly consistent CLIOutput usage

---

## Quick Wins (Do First)

1. **Fix main command docstring** (5 min) ✅ Easy
2. **Add error handling to `clean.py`** (5 min) ✅ Easy
3. **Add error handling to `assets.py`** (5 min) ✅ Easy
4. **Add metadata to `clean.py`** (5 min) ✅ Easy

**Total Quick Wins**: ~20 minutes for 4 commands

---

## Related Documents

- `plan/active/cli-scrutiny-report.md` - Full analysis
- `plan/active/cli-refinement-analysis.md` - Original analysis
- `architecture/cli.md` - CLI architecture docs

---

**Next Action**: Start with Quick Wins, then proceed with High Priority items.
