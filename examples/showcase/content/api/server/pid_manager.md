---
title: "server.pid_manager"
layout: api-reference
type: python-module
source_file: "../../bengal/server/pid_manager.py"
---

# server.pid_manager

PID file management for Bengal dev server.

Tracks running server processes and provides recovery from stale processes.

**Source:** `../../bengal/server/pid_manager.py`

---

## Classes

### PIDManager


Manage PID files for process tracking and recovery.

Features:
- Detect stale processes
- Graceful process termination
- PID file validation
- Cross-platform support




**Methods:**

#### get_pid_file

```python
def get_pid_file(project_root: Path) -> Path
```

Get the PID file path for a project.

**Parameters:**

- **project_root** (`Path`) - Root directory of Bengal project

**Returns:** `Path` - Path to .bengal.pid file






---
#### is_bengal_process

```python
def is_bengal_process(pid: int) -> bool
```

Check if PID is actually a Bengal serve process.

**Parameters:**

- **pid** (`int`) - Process ID to check

**Returns:** `bool` - True if process is Bengal serve, False otherwise






---
#### check_stale_pid

```python
def check_stale_pid(pid_file: Path) -> Optional[int]
```

Check for stale PID file and return PID if found.

**Parameters:**

- **pid_file** (`Path`) - Path to PID file

**Returns:** `Optional[int]` - PID of stale process, or None if no stale process






---
#### kill_stale_process

```python
def kill_stale_process(pid: int, timeout: float = 5.0) -> bool
```

Gracefully kill a stale process.

Tries SIGTERM first (graceful), then SIGKILL if needed.

**Parameters:**

- **pid** (`int`) - Process ID to kill
- **timeout** (`float`) = `5.0` - Seconds to wait for graceful shutdown

**Returns:** `bool` - True if process was killed, False otherwise






---
#### write_pid_file

```python
def write_pid_file(pid_file: Path) -> None
```

Write current process PID to file.

**Parameters:**

- **pid_file** (`Path`) - Path to PID file

**Returns:** `None`






---
#### get_process_on_port

```python
def get_process_on_port(port: int) -> Optional[int]
```

Get the PID of process listening on a port.

**Parameters:**

- **port** (`int`) - Port number to check

**Returns:** `Optional[int]` - PID if found, None otherwise






---


