
---
title: "logger"
type: "python-module"
source_file: "bengal/bengal/utils/logger.py"
line_number: 1
description: "Structured logging system for Bengal SSG. Provides phase-aware logging with context propagation, timing, and structured event emission. Designed for observability into the 22-phase build pipeline. Exa..."
---

# logger
**Type:** Module
**Source:** [View source](bengal/bengal/utils/logger.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›logger

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

## Classes




### `LogLevel`


**Inherits from:**`Enum`Log levels in order of severity.












### `LogEvent`


Structured log event with context.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `timestamp` | - | *No description provided.* |
| `level` | - | *No description provided.* |
| `logger_name` | - | *No description provided.* |
| `event_type` | - | *No description provided.* |
| `message` | - | *No description provided.* |
| `phase` | - | *No description provided.* |
| `phase_depth` | - | *No description provided.* |
| `duration_ms` | - | *No description provided.* |
| `memory_mb` | - | *No description provided.* |
| `peak_memory_mb` | - | *No description provided.* |
| `context` | - | *No description provided.* |







## Methods



#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```


Convert to dictionary for JSON serialization.



**Returns**


`dict[str, Any]`



#### `format_console`
```python
def format_console(self, verbose: bool = False) -> str
```


Format for console output using Rich markup.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `verbose` | `bool` | `False` | *No description provided.* |







**Returns**


`str`




### `BengalLogger`


Phase-aware structured logger for Bengal builds.

Tracks build phases, emits structured events, and provides
timing information. All logs are written to both console
and a build log file.









## Methods



#### `__init__`
```python
def __init__(self, name: str, level: LogLevel = LogLevel.INFO, log_file: Path | None = None, verbose: bool = False, quiet_console: bool = False)
```


Initialize logger.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Logger name (typically __name__) |
| `level` | `LogLevel` | `LogLevel.INFO` | Minimum log level to emit |
| `log_file` | `Path \| None` | - | Path to log file (optional) |
| `verbose` | `bool` | `False` | Whether to show verbose output |
| `quiet_console` | `bool` | `False` | Suppress console output (for live progress mode) |








#### `phase`
```python
def phase(self, name: str, **context)
```


Context manager for tracking build phases with timing and memory.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Phase name **context: Additional context to attach to all events in phase |





:::{rubric} Examples
:class: rubric-examples
:::


```python
with logger.phase("discovery", page_count=100):
        # ... work ...
        pass
```





#### `debug`
```python
def debug(self, message: str, **context)
```


Log debug event.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |








#### `info`
```python
def info(self, message: str, **context)
```


Log info event.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |








#### `warning`
```python
def warning(self, message: str, **context)
```


Log warning event.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |








#### `error`
```python
def error(self, message: str, **context)
```


Log error event.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |








#### `critical`
```python
def critical(self, message: str, **context)
```


Log critical event.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |








#### `get_events`
```python
def get_events(self) -> list[LogEvent]
```


Get all logged events.



**Returns**


`list[LogEvent]`



#### `get_phase_timings`
```python
def get_phase_timings(self) -> dict[str, float]
```


Extract phase timings from events.



**Returns**


`dict[str, float]` - Dict mapping phase names to duration in milliseconds



#### `print_summary`
```python
def print_summary(self)
```


Print timing summary of all phases.




#### `close`
```python
def close(self)
```


Close log file handle.




#### `__enter__`
```python
def __enter__(self)
```


Context manager entry.




#### `__exit__`
```python
def __exit__(self, exc_type, *args)
```


Context manager exit.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `exc_type` | - | - | *No description provided.* |

## Functions



### `truncate_str`


```python
def truncate_str(s: str, max_len: int = 500, suffix: str = ' ... (truncated)') -> str
```



Truncate a string if it exceeds max_len characters.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `s` | `str` | - | *No description provided.* |
| `max_len` | `int` | `500` | *No description provided.* |
| `suffix` | `str` | `' ... (truncated)'` | *No description provided.* |







**Returns**


`str`




### `truncate_error`


```python
def truncate_error(e: Exception, max_len: int = 500) -> str
```



Safely truncate an exception string representation.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `e` | `Exception` | - | *No description provided.* |
| `max_len` | `int` | `500` | *No description provided.* |







**Returns**


`str`




### `configure_logging`


```python
def configure_logging(level: LogLevel = LogLevel.INFO, log_file: Path | None = None, verbose: bool = False, track_memory: bool = False)
```



Configure global logging settings.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `level` | `LogLevel` | `LogLevel.INFO` | Minimum log level to emit |
| `log_file` | `Path \| None` | - | Path to log file |
| `verbose` | `bool` | `False` | Show verbose output |
| `track_memory` | `bool` | `False` | Enable memory profiling (adds overhead) |









### `get_logger`


```python
def get_logger(name: str) -> BengalLogger
```



Get or create a logger instance.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Logger name (typically __name__) |







**Returns**


`BengalLogger` - BengalLogger instance




### `set_console_quiet`


```python
def set_console_quiet(quiet: bool = True)
```



Enable or disable console output for all loggers.

Used by live progress manager to suppress structured log events
while preserving file logging for debugging.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `quiet` | `bool` | `True` | If True, suppress console output; if False, enable it |









### `close_all_loggers`


```python
def close_all_loggers()
```



Close all logger file handles.





### `reset_loggers`


```python
def reset_loggers()
```



Close all loggers and clear the registry (for testing).





### `print_all_summaries`


```python
def print_all_summaries()
```



Print timing and memory summaries from all loggers.



---
*Generated by Bengal autodoc from `bengal/bengal/utils/logger.py`*
