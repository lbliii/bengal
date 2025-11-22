# pid_manager

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/server/pid_manager.py

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

*Note: Template has undefined variables. This is fallback content.*
