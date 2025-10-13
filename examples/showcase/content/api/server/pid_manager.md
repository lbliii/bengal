
---
title: "server.pid_manager"
type: python-module
source_file: "bengal/server/pid_manager.py"
css_class: api-content
description: "PID file management for Bengal dev server.  Tracks running server processes and provides recovery from stale processes.  Features: - Automatic stale process detection - Graceful process termination..."
---

# server.pid_manager

PID file management for Bengal dev server.

Tracks running server processes and provides recovery from stale processes.

Features:
- Automatic stale process detection
- Graceful process termination (SIGTERM then SIGKILL)
- PID file validation (ensures it's actually a Bengal process)
- Cross-platform support (psutil optional, falls back to os.kill)

Usage:
    # Check for stale processes
    pid_file = PIDManager.get_pid_file(project_root)
    stale_pid = PIDManager.check_stale_pid(pid_file)

    if stale_pid:
        PIDManager.kill_stale_process(stale_pid)

    # Write current PID
    PIDManager.write_pid_file(pid_file)

    # Check port usage
    port_pid = PIDManager.get_process_on_port(5173)
    if port_pid:
        print(f"Port in use by PID {port_pid}")

The PID file (.bengal.pid) is created in the project root and automatically
cleaned up on normal server shutdown. If the server crashes or is killed,
the PID file remains and is detected on next startup.

---

## Classes

### `PIDManager`


Manage PID files for process tracking and recovery.

Features:
- Detect stale processes
- Graceful process termination
- PID file validation
- Cross-platform support




:::{rubric} Methods
:class: rubric-methods
:::
#### `get_pid_file` @staticmethod
```python
def get_pid_file(project_root: Path) -> Path
```

Get the PID file path for a project.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`project_root`** (`Path`) - Root directory of Bengal project

:::{rubric} Returns
:class: rubric-returns
:::
`Path` - Path to .bengal.pid file




---
#### `is_bengal_process` @staticmethod
```python
def is_bengal_process(pid: int) -> bool
```

Check if PID is actually a Bengal serve process.

Uses psutil if available for accurate process name checking.
Falls back to simple existence check if psutil is not installed.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`pid`** (`int`) - Process ID to check

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if process is Bengal serve, False otherwise




:::{rubric} Examples
:class: rubric-examples
:::
```python
if PIDManager.is_bengal_process(12345):
```


---
#### `check_stale_pid` @staticmethod
```python
def check_stale_pid(pid_file: Path) -> int | None
```

Check for stale PID file and return PID if found.

A stale PID file indicates a previous server instance that didn't
shut down cleanly (crash, kill -9, power loss, etc.).

This method:
1. Reads the PID file
2. Checks if the process exists
3. Verifies it's actually a Bengal process
4. Returns the PID if stale, None otherwise

Invalid or empty PID files are automatically cleaned up.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`pid_file`** (`Path`) - Path to PID file

:::{rubric} Returns
:class: rubric-returns
:::
`int | None` - PID of stale process, or None if no stale process




:::{rubric} Examples
:class: rubric-examples
:::
```python
pid_file = Path(".bengal.pid")
```


---
#### `kill_stale_process` @staticmethod
```python
def kill_stale_process(pid: int, timeout: float = 5.0) -> bool
```

Gracefully kill a stale process.

Tries SIGTERM first (graceful), then SIGKILL if needed.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`pid`** (`int`) - Process ID to kill
- **`timeout`** (`float`) = `5.0` - Seconds to wait for graceful shutdown

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if process was killed, False otherwise




---
#### `write_pid_file` @staticmethod
```python
def write_pid_file(pid_file: Path) -> None
```

Write current process PID to file.

Uses atomic write to ensure the PID file is crash-safe.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`pid_file`** (`Path`) - Path to PID file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
pid_file = PIDManager.get_pid_file(Path.cwd())
```


---
#### `get_process_on_port` @staticmethod
```python
def get_process_on_port(port: int) -> int | None
```

Get the PID of process listening on a port.

Uses lsof to find which process is listening on a port.
This is useful for detecting port conflicts.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`port`** (`int`) - Port number to check

:::{rubric} Returns
:class: rubric-returns
:::
`int | None` - PID if found, None otherwise


```{note}
Requires lsof command (available on Unix/macOS)
```




:::{rubric} Examples
:class: rubric-examples
:::
```python
port_pid = PIDManager.get_process_on_port(5173)
```


---
