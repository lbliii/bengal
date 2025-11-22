# atomic_write

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/atomic_write.py

Atomic file writing utilities.

Provides crash-safe file writes using the write-to-temp-then-rename pattern.
This ensures files are never left in a partially written state.

If a process crashes during write, the original file (if any) remains intact.
Files are always either in their old complete state or new complete state,
never partially written.

Example:
    >>> from bengal.utils.atomic_write import atomic_write_text
    >>> atomic_write_text('output.html', '<html>...</html>')
    # If crash occurs during write:
    # - output.html is either old version (if existed) or missing
    # - Never partially written!

*Note: Template has undefined variables. This is fallback content.*
