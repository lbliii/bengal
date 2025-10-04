# Bengal Resource Cleanup Deep Dive Analysis

**Date**: October 4, 2025  
**Status**: 🔍 Investigation in Progress  
**Trigger**: Found zombie process (PID 55191) holding port 5173 with PPID=1 (orphaned)

---

## 🚨 Current Problem

```bash
$ lsof -nP -iTCP:5173 -sTCP:LISTEN
COMMAND   PID  USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  55191 llane   19u  IPv4 0x9a95cc6f01d208e3      0t0  TCP 127.0.0.1:5173 (LISTEN)

$ ps -p 55191 -o pid,ppid,command
  PID  PPID COMMAND
55191     1 /Library/Frameworks/Python.framework/Versions/3.10/bin/bengal serve --port 5173
```

**Key finding**: PPID=1 means the process has been **orphaned** (parent died, adopted by init/launchd).

---

## 📊 Resources That Need Cleanup

### 1. **Network Resources**
- **TCP Socket (Port 5173)**: `socketserver.TCPServer`
- **Status**: ❌ Not cleaned up in orphan scenario
- **Location**: `bengal/server/dev_server.py:322`

### 2. **File System Observers**
- **Watchdog Observer Thread**: Monitors content/assets/templates directories
- **Status**: ❌ Not cleaned up in orphan scenario  
- **Location**: `bengal/server/dev_server.py:233-246`

### 3. **Thread Pool Resources**
- **ThreadPoolExecutor** (rendering): Used via context manager ✅
- **ThreadPoolExecutor** (assets): Used via context manager ✅
- **ThreadPoolExecutor** (postprocess): Used via context manager ✅
- **Status**: ✅ These are properly cleaned up due to `with` statement

### 4. **Thread-Local Storage**
- **_thread_local.pipeline**: Jinja2 environments and parsers
- **Status**: ⚠️ Cleaned up when thread dies, but threads may not die gracefully

### 5. **File Handles**
- **Content Files**: Opened via context managers ✅
- **Template Files**: Jinja2 manages these ✅
- **Output Files**: Opened via context managers ✅
- **Status**: ✅ Generally safe

### 6. **Background Threads**
- **Browser opener thread**: `daemon=True` ✅
- **Status**: ✅ Daemon threads die with main thread

---

## 🔍 Current Cleanup Architecture

### What Happens on Clean Exit (Ctrl+C)

```python
# bengal/server/dev_server.py:343-354
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print(f"\n\n  \033[90m{'─' * 78}\033[0m")
    print(f"  👋 Shutting down server...")
    # Explicitly shutdown the server to close the socket
    httpd.shutdown()        # Stop accepting connections
    httpd.server_close()    # Release port ✅
    if self.observer:
        self.observer.stop()   # Stop watching ✅
        self.observer.join()   # Wait for thread ✅
    print(f"  ✅ Server stopped\n")
```

**Status**: ✅ Good cleanup on KeyboardInterrupt

### What's Missing

1. **No signal handlers**: SIGTERM, SIGHUP, SIGQUIT not handled
2. **No atexit handlers**: Cleanup doesn't run if process killed/crashes
3. **No finally block**: Only catches KeyboardInterrupt
4. **Context manager not used**: Server lifecycle not properly scoped
5. **Observer always created**: Even if watch=False initially creates it

---

## 🐛 Failure Scenarios

### Scenario 1: Parent Process Dies
```bash
# User runs: bengal serve
# Terminal crashes or SSH session drops
# Result: Bengal becomes orphaned (PPID=1)
# Cleanup: ❌ NONE - KeyboardInterrupt never raised
```

### Scenario 2: SIGTERM/SIGKILL
```bash
# User runs: kill <PID>
# Result: Process receives SIGTERM
# Cleanup: ❌ NONE - No signal handler registered
```

### Scenario 3: Uncaught Exception
```python
# Error in rebuild logic, template rendering, etc.
# Exception escapes to dev_server.py
# Result: Server crashes
# Cleanup: ❌ PARTIAL - Context manager exits, but observer not stopped
```

### Scenario 4: Python Crash
```bash
# Segfault, memory error, etc.
# Result: Hard crash
# Cleanup: ❌ NONE - No opportunity for cleanup
```

---

## 🏗️ Bengal's Current Architecture

### Process Model
```
bengal CLI (cli.py)
    └─→ Site.serve()
         └─→ DevServer.start()
              ├─→ Initial build
              ├─→ Observer.start() [if watch=True]
              └─→ TCPServer.serve_forever()  [BLOCKS HERE]
```

### Thread Model
```
Main Thread
    ├─→ HTTP Server (serve_forever loop)
    ├─→ Watchdog Observer (background thread)
    │    └─→ Event Handler (triggers rebuilds)
    └─→ Browser Opener (daemon thread)

Build Threads (created per rebuild)
    ├─→ RenderOrchestrator ThreadPool (ephemeral)
    ├─→ AssetOrchestrator ThreadPool (ephemeral)  
    └─→ PostprocessOrchestrator ThreadPool (ephemeral)
```

**Key Insight**: Build threads are ephemeral (created and destroyed per build), but:
- HTTP server is persistent
- Observer is persistent  
- Both need explicit cleanup

---

## 📚 Research: How Other Tools Handle This

### Hugo
```go
// Uses context.Context for cancellation
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

// Signal handling
sigint := make(chan os.Signal, 1)
signal.Notify(sigint, os.Interrupt, syscall.SIGTERM)

go func() {
    <-sigint
    cancel()
}()
```

### Vite (JavaScript)
```javascript
// Uses process event handlers
process.on('SIGTERM', cleanup)
process.on('SIGHUP', cleanup)
process.on('exit', cleanup)
process.on('uncaughtException', (err) => {
    cleanup()
    throw err
})
```

### MkDocs (Python)
```python
# Uses try/finally with signal handlers
import signal
import atexit

def shutdown_handler(signum, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
atexit.register(cleanup)

try:
    server.serve_forever()
finally:
    cleanup()
```

---

## 🎯 Root Cause Analysis

### Why the Zombie Process Exists

1. **Orphaning**: Parent terminal/shell died without sending signal
2. **No signal handler**: Bengal didn't catch SIGHUP/SIGTERM
3. **No atexit**: No cleanup registered for abnormal exit
4. **Blocking call**: `serve_forever()` never returns naturally

### Why `allow_reuse_address = True` Isn't Enough

```python
socketserver.TCPServer.allow_reuse_address = True  # Line 320
```

This only helps with **TIME_WAIT** state after normal close. It doesn't help if:
- Socket is still open in another process
- Process is still listening on port
- Process never called `server_close()`

---

## 💡 Proposed Solutions

### Solution 1: Comprehensive Signal Handling ⭐ RECOMMENDED
**Complexity**: Medium  
**Robustness**: High  
**Compatibility**: Cross-platform

```python
import signal
import atexit

class DevServer:
    def __init__(self, ...):
        self.httpd = None
        self.observer = None
        self._cleanup_done = False
        
    def _cleanup(self):
        """Cleanup resources (idempotent)."""
        if self._cleanup_done:
            return
        self._cleanup_done = True
        
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except:
                pass
                
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=5)
            except:
                pass
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        print(f"\n  👋 Received signal {signum}, shutting down...")
        self._cleanup()
        sys.exit(0)
    
    def start(self):
        # Register cleanup handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGHUP'):  # Unix only
            signal.signal(signal.SIGHUP, self._signal_handler)
        atexit.register(self._cleanup)
        
        try:
            # ... existing setup code ...
            self.httpd.serve_forever()
        finally:
            self._cleanup()
```

**Pros**:
- Handles all termination scenarios
- Idempotent cleanup (safe to call multiple times)
- Works with Ctrl+C, kill, parent death, crashes
- Standard Python approach

**Cons**:
- Signal handlers have limitations (can't do much work)
- Need to be careful with threading

---

### Solution 2: Context Manager Pattern
**Complexity**: Low  
**Robustness**: Medium  
**Compatibility**: High

```python
class DevServer:
    def __enter__(self):
        self._start_watcher()
        self._start_http_server()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        return False
        
    def start(self):
        with self:
            try:
                self.httpd.serve_forever()
            except KeyboardInterrupt:
                pass
```

**Pros**:
- Pythonic and clean
- Guaranteed cleanup via `__exit__`
- Works with exceptions

**Cons**:
- Doesn't handle signals (SIGTERM, etc.)
- Parent death still orphans
- Requires code restructuring

---

### Solution 3: PID File + Cleanup Script
**Complexity**: Low  
**Robustness**: Low  
**Compatibility**: Unix-only

```python
def start(self):
    # Write PID file
    pid_file = self.site.root_path / '.bengal.pid'
    pid_file.write_text(str(os.getpid()))
    
    try:
        # ... server code ...
    finally:
        pid_file.unlink(missing_ok=True)
```

Plus cleanup command:
```bash
bengal cleanup  # Kills any process in .bengal.pid
```

**Pros**:
- Simple to implement
- User-friendly recovery option

**Cons**:
- Doesn't prevent zombies
- Requires manual intervention
- PID file can go stale

---

## 🎯 RECOMMENDATION: Hybrid Approach

Combine **Solution 1** (signal handling) + **Solution 3** (PID file for recovery):

### Implementation Plan

1. **Core cleanup infrastructure**:
   - Centralized `_cleanup()` method (idempotent)
   - Track all resources in instance variables
   - Timeout-based joins (don't hang forever)

2. **Register all handlers**:
   - Signal handlers (SIGINT, SIGTERM, SIGHUP)
   - atexit handler
   - try/finally block
   - Exception handler

3. **PID file for recovery**:
   - Write PID on start
   - Clean up PID on exit
   - Add `bengal cleanup` command to kill stale processes

4. **Health checks**:
   - Check for stale PID before starting
   - Offer to kill stale process if port in use
   - Validate PID is actually Bengal

### Benefits
- ✅ Handles all termination scenarios
- ✅ Graceful degradation
- ✅ User-friendly recovery
- ✅ Doesn't prevent normal operation
- ✅ Works cross-platform (with graceful fallback)

---

## 📝 Additional Improvements

### 1. Health Check on Startup
```python
def _check_port_health(self):
    """Check if port is in use and offer to clean up."""
    if not self._is_port_available(self.port):
        pid = self._get_process_on_port(self.port)
        if pid and self._is_bengal_process(pid):
            if click.confirm(f"Found stale Bengal process {pid}. Kill it?"):
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
```

### 2. Graceful Observer Shutdown
```python
def _cleanup(self):
    if self.observer:
        try:
            self.observer.stop()
            if not self.observer.join(timeout=5):  # Wait max 5 seconds
                print("  ⚠️  Watchdog observer did not stop cleanly")
        except Exception as e:
            print(f"  ⚠️  Error stopping observer: {e}")
```

### 3. Resource Tracking
```python
class DevServer:
    def __init__(self, ...):
        self._resources = {
            'httpd': None,
            'observer': None,
            'temp_files': [],
        }
```

---

## 🧪 Testing Strategy

### Test Cases
1. **Normal exit (Ctrl+C)**: Should clean up all resources
2. **SIGTERM**: Should clean up all resources
3. **SIGHUP**: Should clean up all resources  
4. **Parent process death**: Should clean up all resources (via atexit)
5. **Exception during startup**: Should clean up partial resources
6. **Exception during rebuild**: Should not terminate server
7. **Rapid restart**: Should not get "port in use" error
8. **Multiple servers**: Should not interfere with each other

### Validation
```bash
# Start server
bengal serve &
PID=$!

# Kill with SIGTERM
kill $PID

# Check cleanup
lsof -ti:5173  # Should be empty
ps -p $PID     # Should be dead
```

---

## 🚀 Implementation Priority

### Phase 1: Critical (Do First)
1. Add signal handlers (SIGINT, SIGTERM)
2. Add atexit handler  
3. Wrap in try/finally
4. Make `_cleanup()` idempotent

### Phase 2: Important (Do Soon)
5. Add PID file tracking
6. Add `bengal cleanup` command
7. Add startup health check
8. Add timeout to observer.join()

### Phase 3: Nice-to-Have
9. Convert to context manager
10. Add resource tracking dictionary
11. Add telemetry for cleanup failures
12. Add automatic stale process detection

---

## 📚 Related Issues

- Port reuse after crashes
- Watchdog threads not terminating
- File handles in crashed builds
- Thread pool cleanup in exceptions

---

## 🎬 Next Steps

1. **Kill the zombie**: `kill 55191`
2. **Implement Phase 1**: Signal handling
3. **Test all scenarios**: See testing strategy above
4. **Document for users**: Add to troubleshooting guide
5. **Monitor in production**: Watch for cleanup failures

---

*Analysis complete. Ready for implementation.*

