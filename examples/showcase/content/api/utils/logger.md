
---
title: "utils.logger"
type: python-module
source_file: "bengal/utils/logger.py"
css_class: api-content
description: "Structured logging system for Bengal SSG.  Provides phase-aware logging with context propagation, timing, and structured event emission. Designed for observability into the 22-phase build pipeline...."
---

# utils.logger

Structured logging system for Bengal SSG.

Provides phase-aware logging with context propagation, timing,
and structured event emission. Designed for observability into
the 22-phase build pipeline.

Example:
    from bengal.utils.logger import get_logger

    logger = get_logger(__name__)

    with logger.phase("discovery", page_count=100):
        logger.info("discovered_content", files=len(files))
        logger.debug("parsed_frontmatter", page=page.path, keys=list(metadata.keys()))

---

## Classes

### `LogLevel`

**Inherits from:** `Enum`
Log levels in order of severity.





### `LogEvent`


Structured log event with context.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`timestamp`** (`str`)- **`level`** (`str`)- **`logger_name`** (`str`)- **`event_type`** (`str`)- **`message`** (`str`)- **`phase`** (`str | None`)- **`phase_depth`** (`int`)- **`duration_ms`** (`float | None`)- **`memory_mb`** (`float | None`)- **`peak_memory_mb`** (`float | None`)- **`context`** (`dict[str, Any]`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

Convert to dictionary for JSON serialization.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---
#### `format_console`
```python
def format_console(self, verbose: bool = False) -> str
```

Format for console output using Rich markup.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`verbose`** (`bool`) = `False`

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---

### `BengalLogger`


Phase-aware structured logger for Bengal builds.

Tracks build phases, emits structured events, and provides
timing information. All logs are written to both console
and a build log file.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, name: str, level: LogLevel = LogLevel.INFO, log_file: Path | None = None, verbose: bool = False, quiet_console: bool = False)
```

Initialize logger.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `name` | `str` | - | Logger name (typically __name__) |
| `level` | `LogLevel` | `LogLevel.INFO` | Minimum log level to emit |
| `log_file` | `Path | None` | `None` | Path to log file (optional) |
| `verbose` | `bool` | `False` | Whether to show verbose output |
| `quiet_console` | `bool` | `False` | Suppress console output (for live progress mode) |





---
#### `phase`
```python
def phase(self, name: str, **context)
```

Context manager for tracking build phases with timing and memory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`name`** (`str`) - Phase name **context: Additional context to attach to all events in phase





:::{rubric} Examples
:class: rubric-examples
:::
```python
with logger.phase("discovery", page_count=100):
```


---
#### `debug`
```python
def debug(self, message: str, **context)
```

Log debug event.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`message`** (`str`)





---
#### `info`
```python
def info(self, message: str, **context)
```

Log info event.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`message`** (`str`)





---
#### `warning`
```python
def warning(self, message: str, **context)
```

Log warning event.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`message`** (`str`)





---
#### `error`
```python
def error(self, message: str, **context)
```

Log error event.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`message`** (`str`)





---
#### `critical`
```python
def critical(self, message: str, **context)
```

Log critical event.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`message`** (`str`)





---
#### `get_events`
```python
def get_events(self) -> list[LogEvent]
```

Get all logged events.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[LogEvent]`




---
#### `get_phase_timings`
```python
def get_phase_timings(self) -> dict[str, float]
```

Extract phase timings from events.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, float]` - Dict mapping phase names to duration in milliseconds




---
#### `print_summary`
```python
def print_summary(self)
```

Print timing summary of all phases.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `close`
```python
def close(self)
```

Close log file handle.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `__enter__`
```python
def __enter__(self)
```

Context manager entry.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `__exit__`
```python
def __exit__(self, exc_type, exc_val, exc_tb)
```

Context manager exit.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`exc_type`**
- **`exc_val`**
- **`exc_tb`**





---


## Functions

### `configure_logging`
```python
def configure_logging(level: LogLevel = LogLevel.INFO, log_file: Path | None = None, verbose: bool = False, track_memory: bool = False)
```

Configure global logging settings.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`level`** (`LogLevel`) = `LogLevel.INFO` - Minimum log level to emit
- **`log_file`** (`Path | None`) = `None` - Path to log file
- **`verbose`** (`bool`) = `False` - Show verbose output
- **`track_memory`** (`bool`) = `False` - Enable memory profiling (adds overhead)





---
### `get_logger`
```python
def get_logger(name: str) -> BengalLogger
```

Get or create a logger instance.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`name`** (`str`) - Logger name (typically __name__)

:::{rubric} Returns
:class: rubric-returns
:::
`BengalLogger` - BengalLogger instance




---
### `set_console_quiet`
```python
def set_console_quiet(quiet: bool = True)
```

Enable or disable console output for all loggers.

Used by live progress manager to suppress structured log events
while preserving file logging for debugging.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`quiet`** (`bool`) = `True` - If True, suppress console output; if False, enable it





---
### `close_all_loggers`
```python
def close_all_loggers()
```

Close all logger file handles.







---
### `print_all_summaries`
```python
def print_all_summaries()
```

Print timing and memory summaries from all loggers.







---
