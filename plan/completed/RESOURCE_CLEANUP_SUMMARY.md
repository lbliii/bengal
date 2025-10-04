# Bengal Resource Cleanup - Executive Summary

**Date**: October 4, 2025  
**Analysis Duration**: Deep dive complete  
**Documents Created**: 3 (Analysis, Best Solution, Summary)

---

## 🚨 What We Found

**You were right.** Bengal has a resource cleanup problem:

```bash
$ lsof -nP -iTCP:5173 -sTCP:LISTEN
Python  55191 ... PPID=1  # ← ORPHANED ZOMBIE PROCESS
```

### The Core Issue

Bengal's dev server **only cleans up on Ctrl+C**. It fails to cleanup on:
- ❌ SIGTERM (normal `kill` command)
- ❌ Parent process death (terminal crashes, SSH drops)
- ❌ SIGHUP (hangup signal)
- ❌ Uncaught exceptions (partially)

**Result**: Zombie processes that hold ports forever.

---

## 🔍 Root Cause

### Architectural Mismatch

Bengal was designed with **build-process semantics** (short-lived, exits naturally):
```python
with ThreadPoolExecutor() as executor:  # ✅ Context manager cleans up
    build_pages()
# Exits cleanly, OS releases resources
```

But the dev server is a **persistent daemon** (long-lived, killed externally):
```python
with TCPServer() as httpd:
    httpd.serve_forever()  # ← BLOCKS FOREVER, never exits naturally
                          # Context manager __exit__ only runs on exception/signal
```

**Problem**: Context managers only help if execution exits the `with` block. Servers that run forever need explicit lifecycle management.

### What's Missing

1. **No signal handlers**: SIGTERM/SIGHUP not caught
2. **No atexit handlers**: Cleanup doesn't run on abnormal exit
3. **No PID tracking**: Can't detect/kill stale processes
4. **No health checks**: Doesn't detect conflicts on startup

---

## 🏗️ The Best Solution: ResourceManager Pattern

After analyzing Bengal's architecture, the optimal solution is a **centralized resource lifecycle manager** that:

1. **Fits Bengal's architecture** (orchestrator pattern + context managers)
2. **Handles all failure scenarios** (signals, atexit, exceptions)
3. **Provides recovery tools** (PID files, cleanup command)
4. **Maintains code quality** (testable, extensible, minimal disruption)

### Core Components

```python
# 1. ResourceManager - Centralized lifecycle management
with ResourceManager() as rm:
    rm.register_server(httpd)      # Auto-cleanup on exit
    rm.register_observer(watcher)   # Auto-cleanup on exit
    httpd.serve_forever()
# Resources cleaned up regardless of how we exit

# 2. PIDManager - Track and recover from zombies
PIDManager.check_stale_pid(pid_file)
PIDManager.kill_stale_process(pid)

# 3. CLI command - User-friendly recovery
$ bengal cleanup  # Kills any stale processes
```

### Why This Is Best

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Handles all scenarios** | ⭐⭐⭐⭐⭐ | Signals, atexit, exceptions, zombies |
| **Fits architecture** | ⭐⭐⭐⭐⭐ | Uses orchestrator + context manager patterns |
| **Minimal disruption** | ⭐⭐⭐⭐⭐ | Isolated module, mostly additive changes |
| **User experience** | ⭐⭐⭐⭐⭐ | Automatic cleanup + manual recovery |
| **Testability** | ⭐⭐⭐⭐⭐ | Clear interfaces, deterministic behavior |
| **Extensibility** | ⭐⭐⭐⭐⭐ | Easy to add new resource types |

---

## 📊 Resources That Need Cleanup

### Critical (Currently Leaking)
1. ❌ **TCP Socket**: Port held by zombie process
2. ❌ **Watchdog Observer**: Background thread never stopped

### Working (Context Managers)
3. ✅ **ThreadPoolExecutor**: Render, asset, postprocess pools
4. ✅ **File handles**: All use `with open()` correctly
5. ✅ **Daemon threads**: Browser opener marked `daemon=True`

### Needs Improvement
6. ⚠️ **Thread-local storage**: Cleaned up when thread dies, but threads may not die gracefully

---

## 🎯 Recommended Implementation

### Phase 1: Core (Do First) - 2-3 hours
- [ ] Create `ResourceManager` class
- [ ] Create `PIDManager` class  
- [ ] Update `DevServer` to use ResourceManager
- [ ] Add signal handlers (SIGINT, SIGTERM, SIGHUP)
- [ ] Add atexit handler
- [ ] Add try/finally protection

### Phase 2: Recovery (Do Soon) - 1-2 hours
- [ ] Add PID file creation/cleanup
- [ ] Add stale process detection on startup
- [ ] Add `bengal cleanup` CLI command
- [ ] Add health check before port binding

### Phase 3: Testing (Essential) - 2-3 hours
- [ ] Test Ctrl+C cleanup
- [ ] Test SIGTERM cleanup
- [ ] Test orphaned process cleanup
- [ ] Test rapid restart
- [ ] Test `bengal cleanup` command
- [ ] Add automated integration tests

---

## 💡 Key Insights

### 1. Different Lifetime, Different Needs
**Build process**: Short-lived → Context managers sufficient  
**Dev server**: Long-lived → Need explicit lifecycle management

### 2. Python's Cleanup Hierarchy
```
Context manager (__exit__)     ← Only runs if execution exits with block
    ↓
Exception handler (except)     ← Only catches specific exceptions
    ↓  
Finally block                  ← Runs on normal/exception exit
    ↓
Signal handler                 ← Catches SIGTERM, SIGINT, SIGHUP
    ↓
atexit handler                 ← Last resort (parent death, sys.exit)
    ↓
OS cleanup                     ← Too late (resources leaked)
```

**Bengal needs layers 3-5**, not just layer 1.

### 3. Idempotent Cleanup Is Critical
```python
def _cleanup(self):
    if self._cleanup_done:  # ← ESSENTIAL
        return
    self._cleanup_done = True
    
    # ... cleanup code ...
```

Without this, cleanup gets called multiple times (atexit + signal + finally).

### 4. Timeouts Prevent Hangs
```python
observer.join(timeout=5)  # ← Don't wait forever
if not observer.is_alive():
    print("Warning: observer didn't stop")
```

Cleanup should never hang forever.

---

## 🧪 How To Verify

### Before Fix
```bash
$ bengal serve &
$ PID=$!
$ kill $PID
$ lsof -ti:5173
55191  # ← STILL LISTENING!
```

### After Fix
```bash
$ bengal serve &
$ PID=$!  
$ kill $PID
$ lsof -ti:5173
# ← EMPTY (port released)
```

---

## 📚 Comparison: How Other Tools Handle This

### Hugo (Go)
- Uses `context.Context` for cancellation
- Signal handlers with goroutines
- Graceful shutdown with timeout

### Vite (JavaScript)
- Process event handlers (`on('SIGTERM')`)
- Cleanup callbacks registry
- Unhandled rejection protection

### MkDocs (Python)
- Signal handlers for SIGINT/SIGTERM
- atexit registration
- try/finally blocks

**Commonality**: All production-ready servers use **signal handlers + atexit**.

Bengal is missing this layer.

---

## 🎬 Next Steps

### Immediate (Do Now)
1. ✅ Kill zombie process: `kill 55191`
2. ✅ Document findings (this summary)
3. ⏭️ Review with team

### Short-Term (This Week)
4. Implement ResourceManager pattern
5. Add signal handlers
6. Add PID file tracking
7. Add `bengal cleanup` command

### Long-Term (Next Sprint)
8. Add automated tests
9. Document troubleshooting
10. Monitor for cleanup failures
11. Consider health monitoring endpoint

---

## 📖 Documents Created

1. **RESOURCE_CLEANUP_ANALYSIS.md** (Detailed investigation)
   - Current problem analysis
   - Resource inventory
   - Failure scenarios
   - Cleanup architecture review
   - Research on other tools

2. **RESOURCE_CLEANUP_BEST_SOLUTION.md** (Design document)
   - Architectural thinking
   - Proposed ResourceManager pattern
   - Complete implementation design
   - Testing strategy
   - Benefits analysis

3. **RESOURCE_CLEANUP_SUMMARY.md** (This document)
   - Executive overview
   - Key findings
   - Recommendations
   - Next steps

---

## 🎯 Conclusion

**Your suspicion was 100% correct.**

Bengal's resource cleanup is **not robust**. It works for happy-path Ctrl+C, but fails for:
- Process signals (SIGTERM)
- Parent death (orphaning)
- Terminal crashes
- SSH disconnects

**The fix is well-defined and achievable:**
- 2-3 hours core implementation
- 1-2 hours recovery tools
- 2-3 hours testing
- **~6-8 hours total**

**The result will be production-ready cleanup that handles all scenarios gracefully.**

---

*Analysis complete. Zombie process killed. Ready for implementation.*

