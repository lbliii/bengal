# bengal serve: Verbose and Debug Modes

**Status:** ✅ Implemented  
**Date:** 2025-10-11

## Summary

Added `--verbose` and `--debug` flags to `bengal serve` for consistency with `bengal build`.

## Implementation

### CLI Flags

```bash
# Default mode (only warnings/errors)
bengal serve

# Verbose mode (INFO level)
bengal serve --verbose
bengal serve -v

# Debug mode (DEBUG level)
bengal serve --debug
```

### Logging Levels

| Mode | Log Level | What You See |
|------|-----------|--------------|
| **Default** | WARNING | Only errors and warnings |
| **Verbose** (`--verbose`) | INFO | Server activity, rebuilds, file watching |
| **Debug** (`--debug`) | DEBUG | Everything: port checks, PID files, observer setup, file changes |

### What Each Mode Shows

#### Default Mode (No Flags)
- Port conflicts and stale process warnings
- Rebuild errors
- HTTP request errors (4xx, 5xx)
- Server startup/shutdown messages

#### Verbose Mode (`--verbose`)
Shows everything in default mode, plus:
- File watcher initialization with watched directories
- Server started/stopped events
- Rebuild triggers with changed file list
- Rebuild completion with stats (pages built, duration)
- Port fallback information
- HTTP server creation details
- Stale process cleanup

#### Debug Mode (`--debug`)
Shows everything in verbose mode, plus:
- Server initialization parameters
- Initial build metrics (pages, duration)
- Browser auto-open URLs
- Directory watching details (recursive/non-recursive)
- Working directory changes
- Port availability checks
- File change detection (individual files)
- Debounce timer resets
- Build skip reasons (already in progress)
- Client disconnections
- Ephemeral state cleanup

### Log File

All modes also write structured JSON logs to `.bengal-serve.log` in the project root for debugging and analysis.

### Code Changes

**File:** `bengal/cli/commands/serve.py`

1. Added imports:
   ```python
   from bengal.utils.logger import configure_logging, LogLevel
   ```

2. Added CLI options:
   ```python
   @click.option('--verbose', '-v', is_flag=True, help='Show detailed server activity')
   @click.option('--debug', is_flag=True, help='Show debug output and full tracebacks')
   ```

3. Added logging configuration:
   ```python
   # Configure logging based on flags
   if debug:
       log_level = LogLevel.DEBUG
   elif verbose:
       log_level = LogLevel.INFO
   else:
       log_level = LogLevel.WARNING

   configure_logging(
       level=log_level,
       log_file=root_path / '.bengal-serve.log',
       verbose=verbose or debug,
       track_memory=False
   )
   ```

4. Added validation to prevent conflicting flags:
   ```python
   if verbose and debug:
       raise click.UsageError("--verbose and --debug cannot be used together")
   ```

## Benefits

1. **Consistency** - Matches `bengal build` interface
2. **Troubleshooting** - Easier to debug port conflicts, file watching issues, stale processes
3. **Transparency** - Shows what the server is doing (rebuilds, cache hits, etc.)
4. **Already instrumented** - The server code already had 41+ structured log calls
5. **Minimal overhead** - Logging only happens when needed

## Use Cases

### Verbose Mode
- **Theme development:** See when rebuilds happen and which files triggered them
- **Content authors:** Monitor file watching and rebuild status
- **Debugging slow rebuilds:** See timing information

### Debug Mode
- **Framework development:** Full observability into server internals
- **Troubleshooting issues:** Port conflicts, PID file problems, observer failures
- **Understanding behavior:** See exactly how file watching and debouncing work

## Example Output

### Default Mode
```
🚀 Bengal Dev Server
➜  Local:   http://localhost:5173/
➜  Serving: /path/to/public

  TIME     │ METHOD │ STATUS │ PATH
  ─────────┼────────┼────────┼───────────────────
  10:45:32 │ GET    │ 200 │ 📄 /
  10:45:35 │ GET    │ 404 │ ❌ /missing-page
```

### Verbose Mode (adds)
```
● file_watcher_started watch_dirs=[content/, assets/, templates/]
● dev_server_started host=localhost port=5173
● rebuild_triggered changed_file_count=1
● rebuild_complete duration_seconds=0.15 pages_built=24
```

### Debug Mode (adds even more)
```
● dev_server_starting host=localhost port=5173 watch_enabled=True
● initial_build_complete pages_built=24 duration_ms=245.3
● watching_directory path=content/ recursive=True
● watching_directory path=assets/ recursive=True
● file_change_detected file=content/docs/guide.md pending_count=1
● debounce_timer_reset delay_ms=300
```

## Testing

Verified that:
- ✅ Help text shows both flags
- ✅ Flags are mutually exclusive (validated)
- ✅ Logging levels are correctly configured
- ✅ Log file is written to `.bengal-serve.log`
- ✅ All existing log calls use appropriate levels
- ✅ No linting errors

## Notes

- The dev server code was already well-instrumented with structured logging
- This change simply exposes the existing logging via CLI flags
- Matches the pattern established by `bengal build --verbose` and `bengal build --debug`
- Log file always written regardless of console output level (good for post-mortem debugging)
