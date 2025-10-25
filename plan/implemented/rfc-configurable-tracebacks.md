# RFC: Configurable Traceback System

**Status**: Draft  
**Created**: 2025-10-23  
**Author**: Bengal OS  
**Confidence**: 88% 🟢

---

## Problem Statement

Bengal currently has **fragmented and partially configurable** error display across the codebase:

1. **Rich traceback settings are hardcoded** (`show_locals=True`, `max_frames=20`) in `bengal/cli/__init__.py:35-41`
2. **Debug mode is scattered** across commands (`build.py:207`, `serve.py:44`, `renderer.py:205-228`) with inconsistent behavior
3. **No user control** over traceback verbosity beyond binary `--debug` flag
4. **Context-unaware** - same traceback format for template errors, import errors, and runtime errors
5. **No environment-based configuration** - users can't set preferences per-environment (dev/CI/prod)

### Real-World Example

```python
# Current: User gets this on ImportError
Traceback (most recent call last):
  File ".../venv-3.14t/bin/bengal", line 4, in <module>
    from bengal.cli import main
  File ".../bengal/cli/__init__.py", line 10, in <module>
    from bengal.cli.commands.health import health_cli
  File ".../bengal/cli/commands/health.py", line 16, in <module>
    from bengal.cli.click_extensions import verbosity_option
ImportError: cannot import name 'verbosity_option' from 'bengal.cli.click_extensions'
```

**Users want**:
- Minimal output for simple errors (just the fix suggestion)
- Context-aware details (what's available in the module)
- Control over verbosity (compact, full, or none)
- Per-environment defaults (CI vs local dev)

---

## Current State (Evidence)

### 1. Rich Traceback Installation
**Location**: `bengal/cli/__init__.py:26-44`

```python
install(
    console=get_console(),
    show_locals=True,          # ❌ Hardcoded
    suppress=[click],          # ✅ Good
    max_frames=20,             # ❌ Hardcoded
    width=None,                # ✅ Auto-detect
)
```

**Issues**:
- Always shows locals (verbose, can leak sensitive data)
- Always shows 20 frames (overwhelming for simple errors)
- Only disabled in CI (`if not os.getenv("CI")`)

### 2. Debug Mode Usage
**Scattered across codebase**:

```python
# bengal/rendering/renderer.py:204-228
debug_mode = self.site.config.get("debug", False)
if debug_mode:
    import traceback
    traceback.print_exc()  # ❌ Standard Python traceback, loses Rich formatting
```

**Issues**:
- Inconsistent: sometimes uses Rich, sometimes uses `traceback.print_exc()`
- No granular control (all or nothing)
- Duplicates Rich traceback (shows both Rich and standard)

### 3. Template Error Display
**Location**: `bengal/rendering/errors.py:272-381`

```python
# ✅ EXCELLENT: Context-aware, structured, helpful
def _display_template_error_rich(error: TemplateRenderError) -> None:
    # Shows: template context, suggestions, alternatives, chain, docs
```

**Strengths**:
- Beautiful Rich formatting
- Context-specific suggestions
- Links to documentation
- Shows template chain

**Limitation**: Only for template errors, not generalized

### 4. CLI Error Display
**Location**: `bengal/utils/build_stats.py:507-512`

```python
def show_error(message: str, show_art: bool = True) -> None:
    cli.error_header(message, mouse=show_art)  # ✅ Themed
```

**Strengths**: Consistent branding (mouse emoji 🐭)  
**Limitation**: No traceback control

### 5. Configuration Support
**Location**: `bengal/config/loader.py:397`

```python
"debug": False,  # Show verbose debug output and tracebacks
```

**Issues**:
- Boolean only (no granularity)
- Not documented what "tracebacks" means
- Doesn't control Rich settings

---

## Goals

### Primary Goals
1. **User Control**: Allow users to configure traceback verbosity per-environment
2. **Context-Aware**: Different error types get appropriate display depth
3. **Consistency**: Centralize traceback configuration and display
4. **Discoverability**: Make configuration obvious and well-documented

### Non-Goals
- ❌ Change template error display (already excellent)
- ❌ Add AI-powered error suggestions (future enhancement)
- ❌ Implement custom traceback parser (use Rich)
- ❌ Support Python 2.7 or legacy environments

---

## Design Options

### Option 1: Environment Variable + Config File (Recommended)

**Configuration Hierarchy** (highest precedence first):
1. CLI flag: `--traceback=full|compact|minimal|off`
2. Environment variable: `BENGAL_TRACEBACK=full|compact|minimal|off`
3. Config file: `[dev.traceback]` section in `bengal.toml`
4. Auto-detection: CI → minimal, TTY → compact, non-TTY → off

**Config Schema**:
```toml
[dev.traceback]
style = "compact"              # full | compact | minimal | off
show_locals = false            # Show local variables
max_frames = 10                # Max stack frames to show
suppress = ["click", "jinja2"] # Libraries to suppress
context_aware = true           # Use smart defaults per error type

# Context-aware overrides
[dev.traceback.overrides]
template_error = "full"        # Always show full for template errors
import_error = "compact"       # Compact for import errors
runtime_error = "compact"      # Compact for runtime errors
```

**CLI Flags**:
```bash
# Global traceback control
bengal site build --traceback=full
bengal site build --traceback=minimal
bengal site build --traceback=off

# Legacy flags still work (map to traceback styles)
bengal site build --debug      # Maps to --traceback=full
bengal site build --verbose    # Maps to --traceback=compact
```

**Traceback Styles**:

#### 1. `full` (Developer Mode)
- All stack frames
- Local variables shown
- Rich syntax highlighting
- Full template context
- **Use case**: Deep debugging, development

**Example**:
```python
╭─────────────────────────────────── Traceback ────────────────────────────────────╮
│ /Users/.../bengal/cli/commands/health.py:16 in <module>                          │
│                                                                                   │
│   13 │                                                                            │
│   14 │ import click                                                               │
│   15 │                                                                            │
│ ❱ 16 │ from bengal.cli.click_extensions import verbosity_option                  │
│   17 │ from bengal.cli.base import BengalGroup                                   │
│   18 │                                                                            │
│                                                                                   │
│ ImportError: cannot import name 'verbosity_option' from 'bengal.cli.click_exte…  │
╰───────────────────────────────────────────────────────────────────────────────────╯
```

#### 2. `compact` (Default for Development)
- Key frames only (user code + error location)
- No locals
- Suppressed framework internals
- **Use case**: Daily development, quick fixes

**Example**:
```python
❌ ImportError in bengal/cli/commands/health.py:16

  Cannot import 'verbosity_option' from bengal.cli.click_extensions

📦 Available in click_extensions:
   • BengalGroup
   • BengalCommand

💡 Quick fix: Remove unused import or define verbosity_option
```

#### 3. `minimal` (CI/Production)
- Error type + message only
- File and line number
- One-line suggestion
- **Use case**: CI logs, production errors

**Example**:
```
ERROR: ImportError at bengal/cli/commands/health.py:16 - 'verbosity_option' not found in click_extensions
```

#### 4. `off` (Standard Python)
- Standard Python traceback
- No Rich formatting
- **Use case**: Piping to files, legacy tools

**Example**: (standard Python format)

---

**Pros**:
- ✅ Flexible: Users choose verbosity per-environment
- ✅ Backward compatible: `--debug` still works
- ✅ Context-aware: Can override per error type
- ✅ Discoverable: Config file + env var + CLI flag
- ✅ Powerful: Supports all use cases (dev, CI, prod)

**Cons**:
- ⚠️ Complexity: 3-layer config hierarchy
- ⚠️ Implementation: Moderate effort (2-3 days)
- ⚠️ Testing: Need to test all style combinations

**Confidence**: 92% 🟢

---

### Option 2: CLI Flags Only (Simpler)

**No config file**, only:
```bash
--traceback=full|compact|minimal|off
--show-locals
--max-frames=N
```

**Pros**:
- ✅ Simple implementation (1 day)
- ✅ Explicit: Always visible in command
- ✅ No config parsing needed

**Cons**:
- ❌ Repetitive: Must specify every time
- ❌ No per-environment defaults
- ❌ Not context-aware

**Confidence**: 78% 🟡

---

### Option 3: Smart Auto-Detection Only

**No configuration**, just intelligent defaults:
- ImportError → Show available exports
- Template error → Full template context
- Runtime error → Compact with suggestion
- CI environment → Always minimal

**Pros**:
- ✅ Zero configuration
- ✅ Always appropriate for error type
- ✅ Users never think about it

**Cons**:
- ❌ No user control (some users want full always)
- ❌ Hard to debug when auto-detection wrong
- ❌ Can't reproduce same output on different machines

**Confidence**: 65% 🟠

---

## Recommended Approach

**Option 1: Environment Variable + Config File**

### Why?
1. **Flexibility**: Covers all use cases (dev, CI, team preferences)
2. **Context-Aware**: Smart defaults with manual overrides
3. **Backward Compatible**: Existing `--debug` flags still work
4. **Industry Standard**: Matches patterns from pytest, mypy, black

### Implementation Strategy

#### Phase 1: Core Infrastructure (Day 1)
1. Create `TracebackConfig` dataclass
2. Implement config hierarchy (CLI → env → file → defaults)
3. Update Rich traceback installation to use config
4. Add `--traceback` flag to all commands

#### Phase 2: Style Renderers (Day 2)
1. Implement `FullTracebackRenderer`
2. Implement `CompactTracebackRenderer` (context-aware)
3. Implement `MinimalTracebackRenderer`
4. Wire up to global exception handler

#### Phase 3: Context-Aware Enhancement (Day 3)
1. Add `ImportErrorHandler` (show available exports)
2. Add `AttributeErrorHandler` (show available attributes)
3. Add `TypeErrorHandler` (show type mismatches)
4. Keep `TemplateRenderError` as-is (already excellent)

#### Phase 4: Config File Support (Day 4)
1. Add `[dev.traceback]` schema to config loader
2. Update documentation
3. Add examples to `bengal.toml.example`

---

## Architecture Impact

### Affected Subsystems

| Subsystem | Impact | Risk |
|-----------|--------|------|
| **CLI** | Medium - Add flags to all commands | Low |
| **Config** | Low - Add new section | Low |
| **Rendering** | Low - Keep existing template errors | None |
| **Utils** | High - New traceback module | Low |

### New Files
```
bengal/utils/traceback_config.py   # Config dataclass + hierarchy
bengal/utils/traceback_renderer.py # Style renderers
bengal/utils/error_handlers.py     # Context-aware handlers
```

### Modified Files
```
bengal/cli/__init__.py              # Use TracebackConfig
bengal/cli/commands/*.py            # Add --traceback flag
bengal/config/loader.py             # Add [dev.traceback] schema
bengal/rendering/renderer.py        # Remove duplicate traceback.print_exc()
```

### API Changes
**New Public API**:
```python
from bengal.utils.traceback_config import TracebackConfig, TracebackStyle

# Get current config
config = TracebackConfig.from_environment()

# Install with config
config.install()

# Render error with specific style
renderer = config.get_renderer()
renderer.display(exception)
```

**Backward Compatibility**:
- All existing `--debug`, `--verbose` flags continue to work
- No breaking changes to public API
- Template error display unchanged

---

## Risks & Mitigations

### Risk 1: Config Complexity
**Concern**: Users confused by 3-layer hierarchy  
**Mitigation**:
- Clear documentation with examples
- `bengal project config --show-traceback` to show active config
- Validation errors if config invalid

### Risk 2: Rich Library Limitations
**Concern**: Rich may not support all features  
**Mitigation**:
- Fallback to standard traceback if Rich fails
- Test on all platforms (macOS, Linux, Windows)
- Support `NO_COLOR` env var

### Risk 3: Breaking Changes
**Concern**: Users rely on current behavior  
**Mitigation**:
- Keep defaults same as current behavior (compact)
- Gradual rollout: add config first, deprecate old flags later
- Version in config: `traceback_version = 2`

### Risk 4: Performance
**Concern**: Context-aware detection adds overhead  
**Mitigation**:
- Only run on exceptions (not hot path)
- Cache module introspection results
- Skip if `--traceback=off`

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_traceback_config.py
def test_config_hierarchy():
    """CLI flag overrides env var overrides file."""

def test_style_detection():
    """Context-aware style per error type."""

def test_import_error_handler():
    """ImportError shows available exports."""
```

### Integration Tests
```python
# tests/integration/test_traceback_cli.py
def test_build_with_traceback_full():
    """Build with --traceback=full shows all frames."""

def test_ci_mode_minimal():
    """CI=1 uses minimal traceback."""
```

### Manual Tests
- [ ] Trigger ImportError and verify compact display
- [ ] Trigger template error and verify unchanged
- [ ] Test in CI environment (GitHub Actions)
- [ ] Test with `NO_COLOR=1`
- [ ] Test in non-TTY (piped output)

---

## Documentation

### User-Facing Docs

**Update `docs/cli/troubleshooting.md`**:
```markdown
## Controlling Error Display

Bengal provides flexible traceback control:

### Quick Start

```bash
# Full tracebacks (for debugging)
bengal site build --traceback=full

# Compact (default, balanced)
bengal site build --traceback=compact

# Minimal (CI/production)
bengal site build --traceback=minimal
```

### Configuration File

Add to `bengal.toml`:

```toml
[dev.traceback]
style = "compact"
show_locals = false
max_frames = 10
```

### Environment Variable

```bash
export BENGAL_TRACEBACK=full
bengal site build  # Uses full tracebacks
```
```

**Update `bengal.toml.example`**:
```toml
[dev.traceback]
# Traceback display style
# - full: All frames, locals, full context (debugging)
# - compact: Key frames only, suggestions (default)
# - minimal: Error message + location (CI)
# - off: Standard Python traceback
style = "compact"

# Show local variables in tracebacks
show_locals = false

# Maximum stack frames to display
max_frames = 10

# Libraries to suppress in tracebacks
suppress = ["click", "jinja2"]

# Context-aware overrides per error type
[dev.traceback.overrides]
template_error = "full"   # Always verbose for templates
import_error = "compact"  # Balanced for imports
```

---

## Migration Path

### Version 0.1.4 (Current)
- `--debug` shows Rich traceback with hardcoded settings
- Template errors use rich display
- All other errors use standard Python traceback

### Version 0.2.0 (Phase 1)
- Add `--traceback` flag to all commands
- Add `BENGAL_TRACEBACK` env var support
- Keep `--debug` as alias for `--traceback=full`
- **No breaking changes**

### Version 0.2.1 (Phase 2)
- Add `[dev.traceback]` config file support
- Add context-aware error handlers
- Deprecation warning: `--debug` → `--traceback=full`

### Version 0.3.0 (Phase 3)
- Remove `--debug` flag (breaking change)
- All config stable and documented
- Full context-aware support

---

## Success Metrics

### Quantitative
- [ ] Users can set traceback style in ≤ 3 ways (CLI, env, config)
- [ ] ImportError shows available exports 100% of time
- [ ] Config parsing adds < 10ms to startup time
- [ ] Test coverage ≥ 90% for new code

### Qualitative
- [ ] Users report "helpful" error messages
- [ ] CI logs are clean and actionable
- [ ] Developers can debug deep issues with `--traceback=full`
- [ ] New contributors understand errors without asking

---

## Alternatives Considered

### Alt 1: Extend Template Error System
**Idea**: Generalize `TemplateRenderError` for all error types  
**Rejected**: Too complex, template errors have unique requirements

### Alt 2: Use `logging` Module Formatters
**Idea**: Use Python's logging formatters for tracebacks  
**Rejected**: Less flexible than Rich, poor UX

### Alt 3: Custom Traceback Parser
**Idea**: Parse tracebacks and enhance with AST analysis  
**Rejected**: Over-engineered, Rich is sufficient

---

## Open Questions

1. **Should we support JSON output for tracebacks?**
   - Use case: Structured logging, log aggregation
   - Decision: Defer to v0.3.0 (not critical for MVP)

2. **Should compact mode show locals for user code?**
   - Pro: Helpful for debugging
   - Con: Can be noisy
   - Decision: No, use `--traceback=full` if needed

3. **Should we add `--traceback=interactive` for live debugging?**
   - Opens IPython/pdb on error
   - Decision: Defer to future (nice-to-have)

---

## References

### Internal
- `bengal/cli/__init__.py:26-44` - Current Rich installation
- `bengal/rendering/errors.py:272-381` - Template error display (excellent)
- `bengal/utils/build_stats.py:507-512` - Error display function
- `architecture/cli.md` - CLI architecture

### External
- [Rich Traceback Documentation](https://rich.readthedocs.io/en/latest/traceback.html)
- [pytest Traceback Modes](https://docs.pytest.org/en/stable/how-to/output.html#modifying-python-traceback-printing)
- [mypy Error Reporting](https://mypy.readthedocs.io/en/stable/command_line.html#report-generation)

---

## Implementation Checklist

### Phase 1: Core (Required for MVP)
- [ ] Create `bengal/utils/traceback_config.py`
- [ ] Implement config hierarchy (CLI → env → defaults)
- [ ] Add `--traceback` flag to `build`, `serve`, `health` commands
- [ ] Update Rich installation in `cli/__init__.py`
- [ ] Add unit tests for config hierarchy

### Phase 2: Styles (Required for MVP)
- [ ] Implement `CompactTracebackRenderer` with context detection
- [ ] Implement `MinimalTracebackRenderer`
- [ ] Implement `FullTracebackRenderer` (wrap Rich)
- [ ] Add tests for each style

### Phase 3: Context Handlers (Nice-to-have)
- [ ] Add `ImportErrorHandler` (show available exports)
- [ ] Add `AttributeErrorHandler` (show available attributes)
- [ ] Add `TypeErrorHandler` (show type hints)
- [ ] Add tests for each handler

### Phase 4: Config File (Nice-to-have)
- [ ] Add `[dev.traceback]` schema to config loader
- [ ] Add validation for traceback config
- [ ] Update `bengal.toml.example`
- [ ] Add integration tests

### Phase 5: Documentation (Required for release)
- [ ] Update CLI reference
- [ ] Add troubleshooting guide
- [ ] Add examples to cookbook
- [ ] Update changelog

---

## Timeline

**Total Estimate**: 3-4 days

| Phase | Time | Blockers |
|-------|------|----------|
| Phase 1: Core | 1 day | None |
| Phase 2: Styles | 1 day | Phase 1 |
| Phase 3: Handlers | 1 day | Phase 2 (optional) |
| Phase 4: Config | 0.5 day | Phase 1 (optional) |
| Phase 5: Docs | 0.5 day | Phase 2 |

**MVP** (Phases 1-2): 2 days  
**Full** (Phases 1-5): 4 days

---

## Appendix: Config Schema

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class TracebackStyle(Enum):
    FULL = "full"          # All frames, locals, rich formatting
    COMPACT = "compact"    # Key frames, context-aware
    MINIMAL = "minimal"    # Error message + location only
    OFF = "off"            # Standard Python traceback

@dataclass
class TracebackConfig:
    """Configuration for traceback display."""

    style: TracebackStyle = TracebackStyle.COMPACT
    show_locals: bool = False
    max_frames: int = 10
    suppress: list[str] = None
    context_aware: bool = True

    # Per-error-type overrides
    overrides: dict[str, TracebackStyle] = None

    @classmethod
    def from_environment(cls) -> "TracebackConfig":
        """Load config from CLI flags → env var → config file → defaults."""
        ...

    def install(self) -> None:
        """Install Rich traceback handler with this config."""
        ...

    def get_renderer(self) -> "TracebackRenderer":
        """Get renderer for this config."""
        ...
```

---

**End of RFC**

**Recommendation**: **Approve Option 1** and implement Phases 1-2 (MVP) immediately.

**Next Steps**:
1. Review RFC with team
2. Create implementation plan (detailed task breakdown)
3. Implement Phase 1 (core infrastructure)
4. Implement Phase 2 (style renderers)
5. Write documentation
6. Ship in v0.2.0

**Confidence**: 88% 🟢
- ✅ Problem is well-understood
- ✅ Evidence is comprehensive
- ✅ Design is battle-tested (similar to pytest, mypy)
- ⚠️ Implementation complexity moderate
- ⚠️ Need to validate with users
