# Bengal Resource Cleanup: Best Long-Term Solution

**Date**: October 4, 2025  
**Status**: 🎯 Design Recommendation  
**Context**: See `RESOURCE_CLEANUP_ANALYSIS.md` for detailed investigation

---

## 🧠 Architectural Thinking Process

### Understanding Bengal's Design Philosophy

Looking at Bengal's codebase, I observe:

1. **Modular Orchestration Pattern**: Bengal separates concerns into orchestrators
   - `RenderOrchestrator` - page rendering
   - `AssetOrchestrator` - asset processing  
   - `PostprocessOrchestrator` - post-build tasks
   - Each orchestrator manages its own resources

2. **Context Manager Heavy**: Thread pools use `with` statements extensively
   ```python
   with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
       # Resources automatically cleaned up
   ```

3. **Thread-Local Optimization**: Smart reuse of expensive resources
   ```python
   _thread_local = threading.local()  # Jinja2 environments
   ```

4. **Graceful Degradation**: Falls back to sequential if parallel fails

5. **User-Friendly Output**: Beautiful, informative messages throughout

### The Core Problem

**Bengal's dev server is a long-running persistent process, but was designed with short-lived build-process cleanup semantics.**

The build process (CLI → build) works perfectly:
- Runs once
- Uses context managers
- Exits cleanly
- Resources released by OS

The dev server (CLI → serve → blocks forever) breaks this model:
- Never returns naturally
- Killed externally (Ctrl+C, SIGTERM, parent death)
- **Context managers only help if execution exits the `with` block**

---

## 🎯 The Best Long-Term Solution

### Core Principle: **"Resource Lifecycle Management as First-Class Concern"**

Not just "cleanup when we remember," but **explicit lifecycle management** throughout.

### Design: ResourceManager Pattern

Create a `ResourceManager` class that:
1. Tracks all resources
2. Provides registration interface
3. Handles all cleanup scenarios
4. Integrates with orchestrators
5. Works with existing architecture

---

## 🏗️ Proposed Architecture

### 1. Core ResourceManager Class

```python
# bengal/server/resource_manager.py

import signal
import atexit
import threading
from typing import Callable, List, Optional, Any
from contextlib import contextmanager


class ResourceManager:
    """
    Centralized resource lifecycle management for Bengal.
    
    Handles cleanup for all scenarios:
    - Normal exit (context manager)
    - Ctrl+C (KeyboardInterrupt)
    - kill/SIGTERM (signal handler)
    - Parent death (atexit)
    - Exceptions (finally block)
    
    Usage:
        with ResourceManager() as rm:
            server = rm.register_server(httpd)
            observer = rm.register_observer(watcher)
            rm.run()  # Blocks until cleanup needed
    """
    
    def __init__(self):
        self._resources: List[tuple[str, Any, Callable]] = []
        self._cleanup_done = False
        self._lock = threading.Lock()
        self._original_signals = {}
        
    def register(self, name: str, resource: Any, cleanup_fn: Callable) -> Any:
        """
        Register a resource with its cleanup function.
        
        Args:
            name: Human-readable name for debugging
            resource: The resource object
            cleanup_fn: Function to call to clean up (takes resource as arg)
            
        Returns:
            The resource (for chaining)
        """
        with self._lock:
            self._resources.append((name, resource, cleanup_fn))
        return resource
        
    def register_server(self, server) -> Any:
        """Register HTTP server."""
        def cleanup(s):
            try:
                s.shutdown()
                s.server_close()
            except Exception as e:
                print(f"  ⚠️  Error closing server: {e}")
        return self.register("HTTP Server", server, cleanup)
        
    def register_observer(self, observer) -> Any:
        """Register file system observer."""
        def cleanup(o):
            try:
                o.stop()
                # Don't hang forever waiting for observer
                if not o.join(timeout=5):
                    print(f"  ⚠️  Observer did not stop cleanly")
            except Exception as e:
                print(f"  ⚠️  Error stopping observer: {e}")
        return self.register("File Observer", observer, cleanup)
        
    def register_pidfile(self, pidfile_path) -> Any:
        """Register PID file for cleanup."""
        def cleanup(path):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        return self.register("PID File", pidfile_path, cleanup)
    
    def cleanup(self, signum: Optional[int] = None) -> None:
        """
        Clean up all resources (idempotent).
        
        Args:
            signum: Signal number if cleanup triggered by signal
        """
        with self._lock:
            if self._cleanup_done:
                return
            self._cleanup_done = True
            
        if signum:
            print(f"\n  👋 Received signal {signum}, shutting down...")
        
        # Clean up in reverse order (LIFO - like context managers)
        for name, resource, cleanup_fn in reversed(self._resources):
            try:
                cleanup_fn(resource)
            except Exception as e:
                print(f"  ⚠️  Error cleaning up {name}: {e}")
        
        self._restore_signals()
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.cleanup(signum=signum)
        import sys
        sys.exit(0)
    
    def _register_signal_handlers(self):
        """Register signal handlers for cleanup."""
        # Store original handlers so we can restore them
        signals_to_catch = [signal.SIGINT, signal.SIGTERM]
        
        # SIGHUP only exists on Unix
        if hasattr(signal, 'SIGHUP'):
            signals_to_catch.append(signal.SIGHUP)
        
        for sig in signals_to_catch:
            try:
                self._original_signals[sig] = signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                # Some signals can't be caught (e.g., in threads)
                pass
    
    def _restore_signals(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_signals.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass
    
    def __enter__(self):
        """Context manager entry."""
        self._register_signal_handlers()
        atexit.register(self.cleanup)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False  # Don't suppress exceptions
```

### 2. Integrate with DevServer

```python
# bengal/server/dev_server.py (UPDATED)

from bengal.server.resource_manager import ResourceManager
import os
from pathlib import Path


class DevServer:
    """Development server with robust resource management."""
    
    def __init__(self, site, host="localhost", port=5173, watch=True, 
                 auto_port=True, open_browser=False):
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.auto_port = auto_port
        self.open_browser = open_browser
    
    def start(self) -> None:
        """Start the development server with robust cleanup."""
        
        # Use ResourceManager for lifecycle management
        with ResourceManager() as rm:
            # Initial build
            show_building_indicator("Initial build")
            stats = self.site.build()
            display_build_stats(stats, show_art=False, output_dir=str(self.site.output_dir))
            
            # Create PID file for recovery
            pid_file = self.site.root_path / '.bengal.pid'
            pid_file.write_text(str(os.getpid()))
            rm.register_pidfile(pid_file)
            
            # Start observer if watching
            observer = None
            if self.watch:
                observer = self._create_observer()
                rm.register_observer(observer)
                observer.start()
            
            # Create and register HTTP server
            httpd = self._create_server()
            rm.register_server(httpd)
            
            # Open browser if requested
            if self.open_browser:
                self._open_browser_delayed()
            
            # Print startup message
            self._print_startup_message(httpd.server_address[1])
            
            # Run until signal/exception
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n  👋 Shutting down server...")
            # ResourceManager cleanup happens automatically via __exit__
    
    def _create_observer(self):
        """Create file system observer."""
        event_handler = BuildHandler(self.site)
        observer = Observer()
        
        watch_dirs = [
            self.site.root_path / "content",
            self.site.root_path / "assets",
            self.site.root_path / "templates",
        ]
        
        for watch_dir in watch_dirs:
            if watch_dir.exists():
                observer.schedule(event_handler, str(watch_dir), recursive=True)
        
        return observer
    
    def _create_server(self):
        """Create HTTP server with port management."""
        os.chdir(self.site.output_dir)
        
        actual_port = self._find_available_port()
        
        socketserver.TCPServer.allow_reuse_address = True
        return socketserver.TCPServer((self.host, actual_port), QuietHTTPRequestHandler)
    
    # ... rest of methods ...
```

### 3. Add PID-Based Recovery

```python
# bengal/server/pid_manager.py

from pathlib import Path
import os
import signal
import psutil  # Optional: for better process checking


class PIDManager:
    """
    Manage PID files for process tracking and recovery.
    """
    
    @staticmethod
    def is_bengal_process(pid: int) -> bool:
        """Check if PID is actually a Bengal process."""
        try:
            import psutil
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())
            return 'bengal' in cmdline and 'serve' in cmdline
        except (psutil.NoSuchProcess, ImportError):
            # Fallback if psutil not available
            return True  # Assume it's valid
    
    @staticmethod
    def check_stale_pid(pid_file: Path, port: int) -> Optional[int]:
        """
        Check for stale PID file and return PID if found.
        
        Returns:
            PID of stale process, or None if no stale process
        """
        if not pid_file.exists():
            return None
        
        try:
            pid = int(pid_file.read_text().strip())
            
            # Check if process exists
            os.kill(pid, 0)  # Signal 0 checks existence without killing
            
            # Check if it's actually Bengal
            if PIDManager.is_bengal_process(pid):
                return pid
            else:
                # Stale PID file from non-Bengal process
                pid_file.unlink()
                return None
                
        except (ValueError, ProcessLookupError):
            # Invalid PID or process doesn't exist
            pid_file.unlink()
            return None
        except OSError:
            # Permission denied or other error
            return None
    
    @staticmethod
    def kill_stale_process(pid: int, timeout: float = 5.0) -> bool:
        """
        Gracefully kill a stale process.
        
        Args:
            pid: Process ID to kill
            timeout: Seconds to wait for graceful shutdown
            
        Returns:
            True if process was killed, False otherwise
        """
        try:
            # Try SIGTERM first (graceful)
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to die
            import time
            start = time.time()
            while time.time() - start < timeout:
                try:
                    os.kill(pid, 0)  # Check if still alive
                    time.sleep(0.1)
                except ProcessLookupError:
                    return True  # Process died
            
            # Still alive? Use SIGKILL (force)
            os.kill(pid, signal.SIGKILL)
            return True
            
        except ProcessLookupError:
            return True  # Already dead
        except PermissionError:
            print(f"  ⚠️  No permission to kill process {pid}")
            return False
```

### 4. Add Health Check on Startup

```python
# In DevServer.start(), before creating server:

def start(self) -> None:
    """Start the development server with health checks."""
    
    # Check for stale processes
    pid_file = self.site.root_path / '.bengal.pid'
    stale_pid = PIDManager.check_stale_pid(pid_file, self.port)
    
    if stale_pid:
        print(f"⚠️  Found stale Bengal process (PID {stale_pid})")
        print(f"   This process may be holding port {self.port}")
        
        if click.confirm("  Kill stale process?", default=True):
            if PIDManager.kill_stale_process(stale_pid):
                print("  ✅ Stale process killed")
                time.sleep(1)  # Give OS time to release port
            else:
                print("  ❌ Failed to kill stale process")
                print(f"     Try manually: kill {stale_pid}")
                raise click.Abort()
    
    # Continue with normal startup...
    with ResourceManager() as rm:
        # ... existing code ...
```

### 5. Add Cleanup Command

```python
# bengal/cli.py - Add new command

@main.command()
@click.option('--force', '-f', is_flag=True, help='Kill without confirmation')
@click.argument('source', type=click.Path(exists=True), default='.')
def cleanup(force: bool, source: str) -> None:
    """
    🧹 Clean up stale Bengal processes.
    
    Finds and kills any stale 'bengal serve' processes that may be
    holding ports or preventing new servers from starting.
    """
    try:
        root_path = Path(source).resolve()
        pid_file = root_path / '.bengal.pid'
        
        stale_pid = PIDManager.check_stale_pid(pid_file, port=None)
        
        if not stale_pid:
            click.echo(click.style("✅ No stale processes found", fg='green'))
            return
        
        click.echo(click.style(f"Found stale process: PID {stale_pid}", fg='yellow'))
        
        if not force:
            if not click.confirm("Kill this process?"):
                click.echo("Cancelled")
                return
        
        if PIDManager.kill_stale_process(stale_pid):
            click.echo(click.style("✅ Process killed successfully", fg='green'))
        else:
            click.echo(click.style(f"❌ Failed to kill process", fg='red'))
            click.echo(f"Try manually: kill {stale_pid}")
            raise click.Abort()
            
    except Exception as e:
        show_error(f"Cleanup failed: {e}", show_art=False)
        raise click.Abort()
```

---

## 🎯 Why This Is The Best Solution

### 1. **Aligns with Bengal's Architecture**
- Uses orchestrator pattern (ResourceManager is an orchestrator for cleanup)
- Leverages context managers (Bengal's preferred pattern)
- Maintains separation of concerns
- Fits existing code structure

### 2. **Handles All Failure Scenarios**
- ✅ Normal exit (context manager `__exit__`)
- ✅ Ctrl+C (KeyboardInterrupt + signal handler)
- ✅ SIGTERM/kill (signal handlers)
- ✅ Parent death (atexit handler)
- ✅ Exceptions (try/finally via context manager)
- ✅ Orphaned processes (PID file + cleanup command)

### 3. **Graceful Degradation**
- Signal handlers are optional (work without them)
- PID file is optional (work without it)
- psutil is optional (work without it)
- Each component can fail independently

### 4. **User-Friendly**
- Automatic cleanup in most cases
- Manual recovery option (`bengal cleanup`)
- Clear messages about what's happening
- Proactive stale process detection

### 5. **Minimal Disruption**
- ResourceManager is isolated module
- DevServer changes are mostly additive
- No changes to build/orchestration logic
- Backward compatible

### 6. **Extensible**
- Easy to add new resource types
- Can register custom cleanup functions
- Works with future features (WebSocket server, etc.)
- Supports resource dependencies (cleanup order)

---

## 📋 Implementation Plan

### Phase 1: Core Infrastructure (1-2 hours)
1. Create `bengal/server/resource_manager.py`
2. Create `bengal/server/pid_manager.py`
3. Add tests for ResourceManager
4. Add tests for PIDManager

### Phase 2: Integration (1 hour)
5. Update `bengal/server/dev_server.py`
6. Add PID file creation/cleanup
7. Add stale process detection on startup

### Phase 3: CLI Commands (30 mins)
8. Add `bengal cleanup` command
9. Update `bengal serve` help text

### Phase 4: Testing (1-2 hours)
10. Test KeyboardInterrupt cleanup
11. Test SIGTERM cleanup
12. Test orphaned process scenario
13. Test `bengal cleanup` command
14. Test rapid restart scenario
15. Test multiple concurrent servers

### Phase 5: Documentation (30 mins)
16. Update README troubleshooting section
17. Add comments to code
18. Update CONTRIBUTING.md with cleanup info

---

## 🧪 Testing Strategy

### Manual Tests
```bash
# Test 1: Normal Ctrl+C
bengal serve
# Press Ctrl+C
lsof -ti:5173  # Should be empty

# Test 2: SIGTERM
bengal serve &
PID=$!
kill $PID
lsof -ti:5173  # Should be empty

# Test 3: Orphaned process (simulated)
# Terminal 1:
bengal serve

# Terminal 2:
PPID=$(ps -o ppid= -p $(lsof -ti:5173))
kill $PPID  # Kill parent

# Verify process is orphaned:
ps -p $(lsof -ti:5173) -o ppid=  # Should be 1

# Test cleanup:
cd <project> && bengal cleanup

# Test 4: Rapid restart
bengal serve &
PID=$!
kill $PID
sleep 0.5
bengal serve  # Should start immediately

# Test 5: Stale process detection
# (Leave zombie from test 3)
bengal serve  # Should offer to kill stale process
```

### Automated Tests
```python
# tests/integration/test_resource_cleanup.py

def test_cleanup_on_keyboard_interrupt():
    """Test resources cleaned up on Ctrl+C."""
    # Start server in subprocess
    # Send SIGINT
    # Verify port released
    
def test_cleanup_on_sigterm():
    """Test resources cleaned up on SIGTERM."""
    # Start server in subprocess
    # Send SIGTERM
    # Verify port released
    
def test_pid_file_creation():
    """Test PID file created and removed."""
    # Start server
    # Verify PID file exists
    # Stop server
    # Verify PID file removed
    
def test_stale_process_detection():
    """Test detection of stale processes."""
    # Create fake PID file
    # Start server
    # Should detect and offer to clean
```

---

## 📊 Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Ctrl+C cleanup** | ✅ Works | ✅ Works (improved) |
| **SIGTERM cleanup** | ❌ No | ✅ Yes |
| **Orphan cleanup** | ❌ No | ✅ Yes (atexit) |
| **Stale detection** | ❌ No | ✅ Yes (automatic) |
| **Manual recovery** | ⚠️ `kill -9` | ✅ `bengal cleanup` |
| **Port conflicts** | ⚠️ Common | ✅ Rare |
| **Code complexity** | Low | Medium (justified) |
| **User experience** | Good | Excellent |

---

## 🚀 Future Enhancements

### Post-V1 (Optional)
1. **Resource telemetry**: Track cleanup success rates
2. **Graceful reload**: SIGHUP triggers config reload instead of exit
3. **Health endpoint**: HTTP endpoint for monitoring
4. **Multi-instance coordination**: Support multiple servers via port in PID filename
5. **Resource limits**: Track memory/file handles, warn on leaks

---

## 🎬 Conclusion

**The ResourceManager pattern is the best solution because:**

1. ✅ **Comprehensive**: Handles all failure scenarios
2. ✅ **Architectural fit**: Matches Bengal's design patterns
3. ✅ **Pragmatic**: Solves real problems without over-engineering
4. ✅ **Extensible**: Supports future needs
5. ✅ **Testable**: Clear interfaces for testing
6. ✅ **User-friendly**: Automatic + manual recovery

**This is not just a fix—it's an architectural improvement that makes Bengal more robust and production-ready.**

---

*Ready to implement? See RESOURCE_CLEANUP_IMPLEMENTATION.md for detailed code.*

