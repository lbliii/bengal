# Fast Mode Ergonomics

**Status:** ✅ Implemented  
**Date:** 2025-10-13

## Overview

Added `--fast` mode to make it easy for users trying out Bengal to experience maximum build performance, especially with free-threaded Python 3.14t.

## Problem

Users testing Bengal with free-threaded Python 3.14t would see GIL warnings from third-party libraries (like watchdog) that haven't declared GIL-safety yet. While these warnings are harmless and don't affect build performance, they create noise and confusion for users trying to experience Bengal's speed.

## Solution

Implemented a fast mode that can be enabled via:

1. **CLI flag**: `bengal build --fast`
2. **Config option**: `fast_mode = true` in `[build]` section of `bengal.toml`

### What Fast Mode Does

When enabled, fast mode:
- Enables quiet output mode for minimal overhead
- Ensures parallel rendering is enabled
- Provides clean, focused build output

**Note:** To suppress GIL warnings, users must set `PYTHON_GIL=0` in their shell **before** running Python, as the warnings occur during module imports. Fast mode focuses on output ergonomics rather than warning suppression.

### Implementation Details

**CLI Flag:**
```bash
bengal build --fast       # Enable fast mode
bengal build --no-fast    # Explicitly disable
```

**Config Option:**
```toml
[build]
fast_mode = true  # Always use fast mode
```

**Precedence:**
- CLI flag takes priority over config
- Config is checked if no CLI flag provided
- Fast mode can be overridden with `--no-fast`

**Validations:**
- Fast mode conflicts with `--dev` and `--theme-dev` profiles (incompatible with verbose output)

## Files Changed

### Core Implementation
- `bengal/cli/commands/build.py`: Added `--fast` flag and logic

### Documentation
- `README.md`: Added fast mode to Quick Start and Commands sections
- `INSTALL_FREE_THREADED.md`: Added Fast Mode section with examples
- `bengal.toml.example`: Added `fast_mode` option with comments

## Benefits

1. **Ergonomic**: Single flag (`--fast`) is easy to remember and discover
2. **Flexible**: Can be one-time (CLI) or persistent (config)
3. **Future-proof**: As Python ecosystem matures with free-threading, we can gradually remove the GIL suppression while keeping the flag for other optimizations
4. **User-friendly**: Users trying Bengal get clean output and maximum speed

## Example Usage

```bash
# Try fast mode once
bengal build --fast

# Like it? Make it permanent
echo "[build]" >> bengal.toml
echo "fast_mode = true" >> bengal.toml

# Now just run normally
bengal build

# Override if needed
bengal build --no-fast
```

## Testing

Verified with:
```bash
# Help text shows flag
python -m bengal.cli build --help | grep fast

# Flag works in practice
cd examples/showcase && python -m bengal.cli build --fast
```

Output confirmed:
- Quiet mode active (minimal output)
- Build completes successfully
- No GIL warnings displayed

## Future Considerations

As the Python ecosystem matures with PEP 703 (free-threaded Python):
- More libraries will declare GIL-safety
- GIL warnings will naturally disappear
- We can keep `--fast` flag for other speed optimizations
- Eventually may become default behavior
