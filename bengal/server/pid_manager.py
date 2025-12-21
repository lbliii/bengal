"""
PID file management for Bengal dev server.

Tracks running server processes and provides recovery from stale processes.

Features:
- Automatic stale process detection
- Graceful process termination (SIGTERM then SIGKILL)
- PID file validation (ensures it's actually a Bengal process)
- Cross-platform support (psutil optional, falls back to os.kill)

Usage:

```python
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
```

The PID file (.bengal/server.pid) is created in the .bengal directory and
automatically cleaned up on normal server shutdown. If the server crashes or
is killed, the PID file remains and is detected on next startup.
"""

from __future__ import annotations

import contextlib
import os
import signal
import time
from pathlib import Path

from bengal.output.icons import get_icon_set
from bengal.utils.rich_console import should_use_emoji


class PIDManager:
    """
    Manage PID files for process tracking and recovery.

    Features:
    - Detect stale processes
    - Graceful process termination
    - PID file validation
    - Cross-platform support
    """

    @staticmethod
    def get_pid_file(project_root: Path) -> Path:
        """
        Get the PID file path for a project.

        Args:
            project_root: Root directory of Bengal project

        Returns:
            Path to PID file in .bengal/ directory
        """
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(project_root)
        paths.state_dir.mkdir(parents=True, exist_ok=True)
        return paths.server_pid

    @staticmethod
    def is_bengal_process(pid: int) -> bool:
        """
        Check if PID is actually a Bengal serve process.

        Uses psutil if available for accurate process name checking.
        Falls back to simple existence check if psutil is not installed.

        Args:
            pid: Process ID to check

        Returns:
            True if process is Bengal serve, False otherwise

        Example:
            if PIDManager.is_bengal_process(12345):
                print("Process 12345 is a Bengal server")
        """
        try:
            # Try to use psutil for better process info
            import psutil

            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline()).lower()
            return "bengal" in cmdline and "serve" in cmdline
        except ImportError:
            # psutil not available, assume valid if process exists
            try:
                os.kill(pid, 0)  # Check if process exists
                return True
            except (ProcessLookupError, PermissionError):
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    @staticmethod
    def check_stale_pid(pid_file: Path) -> int | None:
        """
        Check for stale PID file and return PID if found.

        A stale PID file indicates a previous server instance that didn't
        shut down cleanly (crash, kill -9, power loss, etc.).

        This method:
        1. Reads the PID file
        2. Checks if the process exists
        3. Verifies it's actually a Bengal process
        4. Returns the PID if stale, None otherwise

        Invalid or empty PID files are automatically cleaned up.

        Args:
            pid_file: Path to PID file

        Returns:
            PID of stale process, or None if no stale process

        Example:
            pid_file = Path(".bengal/server.pid")
            stale_pid = PIDManager.check_stale_pid(pid_file)

            if stale_pid:
                print(f"Found stale Bengal server (PID {stale_pid})")
                PIDManager.kill_stale_process(stale_pid)
        """
        if not pid_file.exists():
            return None

        try:
            pid_str = pid_file.read_text().strip()
            if not pid_str:
                # Empty PID file
                pid_file.unlink()
                return None

            pid = int(pid_str)

            # Check if process exists
            try:
                os.kill(pid, 0)  # Signal 0 checks existence without killing
            except ProcessLookupError:
                # Process doesn't exist, remove stale PID file
                pid_file.unlink()
                return None
            except PermissionError:
                # Process exists but we can't signal it
                # This shouldn't happen for our own process, might be different user
                pass

            # Process exists - check if it's actually Bengal
            if PIDManager.is_bengal_process(pid):
                return pid
            else:
                # PID file from non-Bengal process, safe to remove
                pid_file.unlink()
                return None

        except (ValueError, OSError):
            # Invalid PID file or read error
            with contextlib.suppress(OSError):
                pid_file.unlink()
            return None

    @staticmethod
    def kill_stale_process(pid: int, timeout: float = 5.0) -> bool:
        """
        Gracefully kill a stale process.

        Tries SIGTERM first (graceful), then SIGKILL if needed.

        Args:
            pid: Process ID to kill
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if process was killed, False otherwise
        """
        try:
            # Try SIGTERM first (graceful shutdown)
            os.kill(pid, signal.SIGTERM)

            # Wait for process to die
            start = time.time()
            while time.time() - start < timeout:
                try:
                    os.kill(pid, 0)  # Check if still alive
                    time.sleep(0.1)
                except ProcessLookupError:
                    return True  # Process died gracefully

            # Still alive after timeout? Use SIGKILL (force)
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.1)
                return True
            except ProcessLookupError:
                return True  # Already dead
            except PermissionError:
                return False

        except ProcessLookupError:
            return True  # Already dead
        except PermissionError:
            icons = get_icon_set(should_use_emoji())
            print(f"  {icons.warning} No permission to kill process {pid}")
            print(f"     Try manually: kill {pid}")
            return False
        except Exception as e:
            icons = get_icon_set(should_use_emoji())
            print(f"  {icons.warning} Error killing process {pid}: {e}")
            return False

    @staticmethod
    def write_pid_file(pid_file: Path) -> None:
        """
        Write current process PID to file.

        Uses atomic write to ensure the PID file is crash-safe.

        Args:
            pid_file: Path to PID file

        Example:
            pid_file = PIDManager.get_pid_file(Path.cwd())
            PIDManager.write_pid_file(pid_file)
            # Now .bengal/server.pid contains the current process ID
        """
        try:
            # Write PID file atomically (crash-safe)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(pid_file, str(os.getpid()))
        except OSError as e:
            icons = get_icon_set(should_use_emoji())
            print(f"  {icons.warning} Warning: Could not write PID file: {e}")

    @staticmethod
    def get_process_on_port(port: int) -> int | None:
        """
        Get the PID of process listening on a port.

        Uses lsof to find which process is listening on a port.
        This is useful for detecting port conflicts.

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise

        Example:
            port_pid = PIDManager.get_process_on_port(5173)

            if port_pid:
                print(f"Port 5173 is in use by PID {port_pid}")
                if PIDManager.is_bengal_process(port_pid):
                    print("It's a stale Bengal server!")

        Note:
            Requires lsof command (available on Unix/macOS)
        """
        try:
            import subprocess

            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], check=False, capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split()[0])
        except (subprocess.SubprocessError, ValueError, FileNotFoundError):
            pass
        return None
