# RFC: Unified Config Resolution

**Status**: Draft  
**Created**: 2025-12-28  
**Author**: AI Assistant  
**Related**: rfc-path-to-200-pgs (discovered issue during Phase III)

---

## Executive Summary

Build option defaults are scattered across multiple locations: `defaults.py`, `BuildOptions` dataclass fields, and inline `config.get("key", default)` calls. While current behavior is correct, this DRY violation creates maintenance risk—changing a default requires updating multiple files. This RFC proposes a `resolve_build_options()` function to consolidate resolution logic with clear precedence: **CLI flag > config file > DEFAULTS**.

---

## Problem Statement

### Current State: It Works, But It's Fragile

The current implementation **does work correctly**—CLI flags override config, config overrides defaults. However, the resolution logic is duplicated across 11+ locations, creating maintenance burden and drift risk.

**1. Duplicated Resolution Pattern**

The same pattern appears throughout the codebase:

```python
# cli/commands/build.py:287-288
if parallel is None:
    parallel = site.config.get("parallel", True)

# server/build_trigger.py:251
use_parallel = config.get("parallel", True)

# health/validators/performance.py:80
parallel = site.config.get("parallel", True)

# health/validators/config.py:103
if config.get("incremental") and not config.get("parallel", True):
```

**Problem**: If the default for `parallel` changes from `True` to `False`, all 11 inline fallbacks must be updated manually.

**2. Defaults in Multiple Places**

| Location | Example | Issue |
|----------|---------|-------|
| `config/defaults.py:124` | `"parallel": True` | Source of truth ✅ |
| `orchestration/build/options.py:76` | `parallel: bool = True` | Hardcoded in dataclass |
| `cli/commands/build.py:288` | `config.get("parallel", True)` | Inline fallback |
| `server/build_trigger.py:251` | `config.get("parallel", True)` | Inline fallback |

**Problem**: `DEFAULTS` is the intended source of truth, but inline fallbacks bypass it.

**3. Inconsistent Config Path Access**

```python
# Flat path (correct after config flattening)
site.config.get("parallel", True)

# Nested path (incorrect—returns None after flattening)
site.config.get("build", {}).get("fast_mode", False)  # build.py:293
```

**Problem**: Some code uses nested paths that fail silently after config flattening.

### What's NOT Broken

To be clear, these work correctly today:

| Scenario | Status | Evidence |
|----------|--------|----------|
| CLI `--no-parallel` overrides config | ✅ Works | `build.py:50-52` uses `default=None` |
| Config `parallel: false` is respected | ✅ Works | `build.py:287-288` checks config |
| Dev server reads `parallel` from config | ✅ Works | `build_trigger.py:251` |

### Root Cause

No single resolution point. Each consumer reimplements `config.get(key, default)` with its own inline default, bypassing `DEFAULTS`.

---

## Proposed Solution

### 1. Create `resolve_build_options()`

A single function that handles all precedence logic:

```python
# bengal/config/build_options_resolver.py

from dataclasses import dataclass
from typing import Any

from bengal.config.defaults import DEFAULTS
from bengal.orchestration.build.options import BuildOptions


@dataclass
class CLIFlags:
    """Flags explicitly passed via CLI (None = not passed)."""
    parallel: bool | None = None
    incremental: bool | None = None
    quiet: bool | None = None
    verbose: bool | None = None
    strict: bool | None = None
    fast: bool | None = None
    memory_optimized: bool | None = None
    profile_templates: bool | None = None


def resolve_build_options(
    config: dict[str, Any],
    cli_flags: CLIFlags | None = None,
) -> BuildOptions:
    """
    Resolve build options with clear precedence.

    Precedence (highest to lowest):
        1. Special Modes (e.g., --fast overrides quiet/parallel)
        2. CLI flags (explicitly passed)
        3. Config file values
        4. DEFAULTS (single source of truth)

    Args:
        config: Site config dictionary (already flattened)
        cli_flags: CLI flags (None values = not passed)

    Returns:
        Fully resolved BuildOptions
    """
    cli = cli_flags or CLIFlags()

    def resolve(key: str, cli_value: Any) -> Any:
        """Resolve with CLI > config > DEFAULTS precedence."""
        if cli_value is not None:
            return cli_value
        if key in config:
            return config[key]
        return DEFAULTS.get(key)

    # Handle fast_mode (overrides parallel and quiet)
    fast_mode = resolve("fast_mode", cli.fast)

    # Resolve all options
    parallel = True if fast_mode else resolve("parallel", cli.parallel)
    quiet = True if fast_mode else resolve("quiet", cli.quiet)

    return BuildOptions(
        parallel=parallel,
        incremental=resolve("incremental", cli.incremental),
        quiet=quiet,
        verbose=resolve("verbose", cli.verbose),
        strict=resolve("strict_mode", cli.strict),
        memory_optimized=resolve("memory_optimized", cli.memory_optimized),
        profile_templates=resolve("profile_templates", cli.profile_templates),
    )
```

### 2. Update BuildOptions Dataclass

Remove hardcoded defaults—require explicit values:

```python
# bengal/orchestration/build/options.py

@dataclass
class BuildOptions:
    """Build options - all values must be explicitly set."""
    parallel: bool  # No default - must be resolved
    incremental: bool | None  # None = auto-detect
    quiet: bool
    verbose: bool
    strict: bool
    memory_optimized: bool
    profile_templates: bool
    # ... other fields
```

### 3. Update Consumers

**CLI Commands**:
```python
# bengal/cli/commands/build.py

def build(parallel: bool | None, incremental: bool | None, ...):
    site = load_site(...)

    cli_flags = CLIFlags(
        parallel=parallel,
        incremental=incremental,
        quiet=quiet,
        # ...
    )

    options = resolve_build_options(site.config, cli_flags)
    stats = site.build(options)
```

**Dev Server** (no CLI flags):
```python
# bengal/server/build_trigger.py

def _execute_build(self, ...):
    options = resolve_build_options(self.site.config)

    request = BuildRequest(
        site_root=str(self.site.root_path),
        parallel=options.parallel,
        incremental=options.incremental,
        # ...
    )
```

**Health Validators**:
```python
# bengal/health/validators/performance.py

def check_build_performance(site):
    options = resolve_build_options(site.config)
    parallel = options.parallel  # No inline fallback needed
```

---

## Implementation Plan

### Phase 1: Create Resolver (Low Risk)

- [ ] Create `bengal/config/build_options_resolver.py`
- [ ] Add `CLIFlags` dataclass with all build-related flags
- [ ] Add `resolve_build_options()` with DEFAULTS integration
- [ ] Add unit tests for precedence logic
- [ ] Add `--explain-config` debug flag to show resolution sources

**Deliverable**: New module with full test coverage, no behavior changes yet.

### Phase 2: Migrate Entry Points (Medium Risk)

- [ ] Update `bengal build` command to use resolver
- [ ] Update `bengal serve` startup build to use resolver
- [ ] Update `BuildTrigger` to use resolver
- [ ] Verify all CLI options use `default=None`

**Deliverable**: Main entry points use resolver; inline defaults still exist as fallback.

### Phase 3: Remove Inline Defaults (Low Risk)

- [ ] Remove inline fallbacks from health validators
- [ ] Remove inline fallbacks from analysis modules
- [ ] Update `BuildOptions` to require explicit values
- [ ] Remove redundant defaults from dataclass

**Deliverable**: Single source of truth for all defaults.

### Phase 4: Documentation (Low Risk)

- [ ] Add "Config Precedence" section to docs
- [ ] Document `--explain-config` debugging feature
- [ ] Update contributor guide with resolver pattern

---

## Testing Strategy

### Unit Tests

```python
class TestBuildOptionsResolver:
    def test_cli_wins_over_config(self):
        """CLI flag takes precedence over config."""
        config = {"parallel": True}
        cli = CLIFlags(parallel=False)

        options = resolve_build_options(config, cli)

        assert options.parallel is False

    def test_config_wins_over_defaults(self):
        """Config takes precedence over DEFAULTS."""
        config = {"parallel": False}

        options = resolve_build_options(config)

        assert options.parallel is False  # Config wins

    def test_defaults_used_when_not_set(self):
        """DEFAULTS used when neither CLI nor config sets value."""
        config = {}

        options = resolve_build_options(config)

        assert options.parallel == DEFAULTS["parallel"]

    def test_fast_mode_overrides_parallel_and_quiet(self):
        """Fast mode forces parallel=True and quiet=True."""
        config = {"parallel": False, "quiet": False}
        cli = CLIFlags(fast=True)

        options = resolve_build_options(config, cli)

        assert options.parallel is True
        assert options.quiet is True

    def test_none_cli_flag_means_not_passed(self):
        """None in CLIFlags means 'use config or default'."""
        config = {"parallel": False}
        cli = CLIFlags(parallel=None)  # Explicitly not passed

        options = resolve_build_options(config, cli)

        assert options.parallel is False  # From config
```

### Integration Tests

```python
class TestCLIConfigPrecedence:
    def test_build_respects_config_parallel(self, site_with_config):
        """bengal build respects parallel config when flag not passed."""
        # Set parallel: false in config
        site_with_config.config["parallel"] = False

        result = runner.invoke(build, [str(site_with_config.root)])

        # Should run in sequential mode
        assert result.exit_code == 0
        # Verify through build stats or log output

    def test_cli_flag_overrides_config(self, site_with_config):
        """CLI --parallel overrides config parallel: false."""
        site_with_config.config["parallel"] = False

        result = runner.invoke(
            build,
            ["--parallel", str(site_with_config.root)]
        )

        assert result.exit_code == 0
        # Should run in parallel mode despite config
```

---

## Migration Guide

### For Contributors

**Before** (scattered defaults):
```python
# Don't do this - inline fallback bypasses DEFAULTS
parallel = site.config.get("parallel", True)
parallel = site.config.get("build", {}).get("parallel", True)
```

**After** (use resolver):
```python
# Do this - single source of truth
from bengal.config.build_options_resolver import resolve_build_options

options = resolve_build_options(site.config, cli_flags)
parallel = options.parallel
```

### For Users

No changes required. Config files work exactly the same way. This refactor improves internal maintainability without changing external behavior.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Subtle behavior change | Low | Medium | Extensive unit + integration tests |
| Performance overhead | Very Low | Very Low | Resolver called once per build |
| Missing options in CLIFlags | Low | Low | Phase 0 audit identifies all flags |
| BuildOptions breaking change | Medium | Medium | Gradual migration, keep fallbacks initially |

---

## Success Criteria

- [ ] All build options resolved through `resolve_build_options()`
- [ ] `DEFAULTS` is the single source of truth for default values
- [ ] No inline `config.get(key, default)` patterns for build options
- [ ] `BuildOptions` dataclass has no hardcoded defaults
- [ ] Tests verify precedence: CLI > config > DEFAULTS
- [ ] `--explain-config` shows resolution source for debugging

---

## Appendix: Affected Locations

### Inline Defaults to Remove

| File | Line | Pattern |
|------|------|---------|
| `cli/commands/build.py` | 288 | `config.get("parallel", True)` |
| `server/build_trigger.py` | 251 | `config.get("parallel", True)` |
| `health/validators/performance.py` | 80 | `site.config.get("parallel", True)` |
| `health/validators/config.py` | 103 | `config.get("parallel", True)` |
| `analysis/graph_builder.py` | 95 | `site.config.get("parallel_graph")` |
| `autodoc/extractors/python/extractor.py` | 168 | `config.get("parallel_autodoc")` |

### Files to Create

- `bengal/config/build_options_resolver.py` - Resolver module
- `tests/unit/config/test_build_options_resolver.py` - Unit tests

### Files to Modify

- `bengal/orchestration/build/options.py` - Remove hardcoded defaults
- `bengal/cli/commands/build.py` - Use resolver
- `bengal/server/build_trigger.py` - Use resolver
