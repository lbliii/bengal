# Graceful Shutdown Improvements

**Date**: October 4, 2025  
**Status**: ✅ Complete

## Problem

Users had to press Ctrl+C twice to shut down the dev server, but:
- It wasn't clear that a second press was even an option
- No indication of what was happening during shutdown
- No feedback on whether shutdown completed successfully
- No timeouts - could potentially hang forever
- Shutdown could take up to 7+ seconds (5s observer + server)

## Solution

### 1. Clear Messaging
**Before:**
```
👋 Received SIGINT, shutting down...
[hangs indefinitely?]
```

**After:**
```
👋 Shutting down gracefully... (press Ctrl+C again to force quit)
✅ Server stopped
```

### 2. Fast Timeouts
- HTTP server shutdown: **2 second timeout** (was: indefinite)
- File observer shutdown: **2 second timeout** (was: 5 seconds)
- Total expected shutdown time: **~0.2 seconds** in typical case

### 3. Timeout Handling
If a component doesn't shut down within its timeout:
```
⚠️  Server shutdown timed out (press Ctrl+C again to force quit)
```

### 4. Force Quit Support
- First Ctrl+C: Graceful shutdown (2-4 second max)
- Second Ctrl+C: Immediate force quit

### 5. Upfront Documentation
Startup message now shows:
```
╭──────────────────────────────────────────────────────────────────────────────╮
│ 🚀 Bengal Dev Server                                                         │
│                                                                              │
│   ➜  Local:   http://localhost:5173/                                        │
│   ➜  Serving: /path/to/output                                               │
│                                                                              │
│   Press Ctrl+C to stop (or twice to force quit)                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Technical Changes

### `resource_manager.py`

**Added timeouts to server cleanup:**
```python
def cleanup(s):
    # Shutdown in a thread with timeout to avoid hanging
    shutdown_thread = threading.Thread(target=s.shutdown)
    shutdown_thread.daemon = True
    shutdown_thread.start()
    shutdown_thread.join(timeout=2.0)
    
    if shutdown_thread.is_alive():
        print(f"  ⚠️  Server shutdown timed out (press Ctrl+C again to force quit)")
    
    s.server_close()
```

**Reduced observer timeout:**
```python
o.join(timeout=2.0)  # Was: 5 seconds
```

**Added completion feedback:**
```python
elapsed = time.time() - start_time
if signum and elapsed < 3.0:
    print(f"  ✅ Server stopped")
```

**Improved signal handler:**
```python
def _signal_handler(self, signum, frame):
    if not self._cleanup_done:
        # First interrupt - start graceful shutdown
        self.cleanup(signum=signum)
        sys.exit(0)
    else:
        # Second interrupt - force exit
        print("\n  ⚠️  Force shutdown")
        sys.exit(1)
```

### `dev_server.py`

**Updated startup message:**
```python
print(f"│   Press Ctrl+C to stop (or twice to force quit)   │")
```

## User Experience Flow

### Normal Shutdown (typical case)
```
[User presses Ctrl+C]

  👋 Shutting down gracefully... (press Ctrl+C again to force quit)
  ✅ Server stopped

[Process exits in ~0.2 seconds]
```

### Slow Shutdown (if something hangs)
```
[User presses Ctrl+C]

  👋 Shutting down gracefully... (press Ctrl+C again to force quit)
  ⚠️  Server shutdown timed out (press Ctrl+C again to force quit)

[User presses Ctrl+C again]

  ⚠️  Force shutdown

[Process exits immediately]
```

## Testing

```bash
# Test normal shutdown with mocked resources
python -c "
from bengal.server.resource_manager import ResourceManager
import time

rm = ResourceManager()

class MockServer:
    def shutdown(self): time.sleep(0.1)
    def server_close(self): pass

class MockObserver:
    def stop(self): pass
    def join(self, timeout): time.sleep(0.1)
    def is_alive(self): return False

server = rm.register_server(MockServer())
observer = rm.register_observer(MockObserver())

rm.cleanup(signum=2)  # SIGINT
"
```

Output:
```
  👋 Shutting down gracefully... (press Ctrl+C again to force quit)
  ✅ Server stopped
```

## Benefits

✅ **Clear expectations** - Users know they can press Ctrl+C twice  
✅ **Fast shutdown** - 2-4 seconds max instead of 5-7+ seconds  
✅ **Visual feedback** - See when shutdown completes successfully  
✅ **No hanging** - Timeouts prevent indefinite waits  
✅ **Force quit option** - Can always bail out immediately  
✅ **Familiar pattern** - Matches Docker, Node.js, and other dev servers

## Related

- Pattern used by: Docker, Node.js servers, webpack-dev-server, vite
- Follows Unix signal handling best practices
- Maintains backward compatibility (still shuts down on single Ctrl+C)

