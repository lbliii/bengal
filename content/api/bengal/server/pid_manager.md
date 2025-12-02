
---
title: "pid_manager"
type: "python-module"
source_file: "bengal/bengal/server/pid_manager.py"
line_number: 1
description: "PID file management for Bengal dev server. Tracks running server processes and provides recovery from stale processes. Features: - Automatic stale process detection - Graceful process termination (SIG..."
---

# pid_manager
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/server/pid_manager.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[server](/api/bengal/server/) ›pid_manager

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

The PID file (.bengal/server.pid) is created in the .bengal directory and
automatically cleaned up on normal server shutdown. If the server crashes or
is killed, the PID file remains and is detected on next startup.

## Classes




### `PIDManager`


Manage PID files for process tracking and recovery.

Features:
- Detect stale processes
- Graceful process termination
- PID file validation
- Cross-platform support









## Methods



#### `get_pid_file` @staticmethod
```python
def get_pid_file(project_root: Path) -> Path
```


Get the PID file path for a project.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `project_root` | `Path` | - | Root directory of Bengal project |







**Returns**


`Path` - Path to PID file in .bengal/ directory



#### `is_bengal_process` @staticmethod
```python
def is_bengal_process(pid: int) -> bool
```


Check if PID is actually a Bengal serve process.

Uses psutil if available for accurate process name checking.
Falls back to simple existence check if psutil is not installed.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pid` | `int` | - | Process ID to check |







**Returns**


`bool` - True if process is Bengal serve, False otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
if PIDManager.is_bengal_process(12345):
        print("Process 12345 is a Bengal server")
```




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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pid_file` | `Path` | - | Path to PID file |







**Returns**


`int | None` - PID of stale process, or None if no stale process
:::{rubric} Examples
:class: rubric-examples
:::


```python
pid_file = Path(".bengal/server.pid")
    stale_pid = PIDManager.check_stale_pid(pid_file)

    if stale_pid:
        print(f"Found stale Bengal server (PID {stale_pid})")
        PIDManager.kill_stale_process(stale_pid)
```




#### `kill_stale_process` @staticmethod
```python
def kill_stale_process(pid: int, timeout: float = 5.0) -> bool
```


Gracefully kill a stale process.

Tries SIGTERM first (graceful), then SIGKILL if needed.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pid` | `int` | - | Process ID to kill |
| `timeout` | `float` | `5.0` | Seconds to wait for graceful shutdown |







**Returns**


`bool` - True if process was killed, False otherwise



#### `write_pid_file` @staticmethod
```python
def write_pid_file(pid_file: Path) -> None
```


Write current process PID to file.

Uses atomic write to ensure the PID file is crash-safe.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pid_file` | `Path` | - | Path to PID file |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
pid_file = PIDManager.get_pid_file(Path.cwd())
    PIDManager.write_pid_file(pid_file)
    # Now .bengal/server.pid contains the current process ID
```




#### `get_process_on_port` @staticmethod
```python
def get_process_on_port(port: int) -> int | None
```


Get the PID of process listening on a port.

Uses lsof to find which process is listening on a port.
This is useful for detecting port conflicts.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `port` | `int` | - | Port number to check |







**Returns**


`int | None` - PID if found, None otherwise
:::{rubric} Examples
:class: rubric-examples
:::


```python
port_pid = PIDManager.get_process_on_port(5173)

    if port_pid:
        print(f"Port 5173 is in use by PID {port_pid}")
        if PIDManager.is_bengal_process(port_pid):
            print("It's a stale Bengal server!")
```

:::{note}Requires lsof command (available on Unix/macOS):::



---
*Generated by Bengal autodoc from `bengal/bengal/server/pid_manager.py`*

