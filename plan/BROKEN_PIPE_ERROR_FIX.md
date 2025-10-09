# BrokenPipeError Fix - Dev Server

**Status:** ✅ Complete  
**Date:** October 9, 2025

## Problem

The dev server was logging noisy `BrokenPipeError` tracebacks when clients disconnected before the server finished sending data. This is normal HTTP behavior (clients can close connections at any time) but was cluttering the logs.

Example errors:
```
Exception occurred during processing of request from ('127.0.0.1', 62348)
Traceback (most recent call last):
  File "/bengal/server/dev_server.py", line 104, in _handle_sse
    self.wfile.write(b': keepalive\n\n')
BrokenPipeError: [Errno 32] Broken pipe
```

## Solution

Added three-layer error handling to gracefully handle client disconnections:

### 1. Main Request Handler (`do_GET`)
Wrapped the entire GET handler to catch and suppress BrokenPipeError:
```python
def do_GET(self) -> None:
    try:
        # Handle SSE, HTML, and other files
        ...
    except (BrokenPipeError, ConnectionResetError):
        # Client disconnected - this is normal, don't log it
        pass
```

### 2. HTML Live Reload Handler (`_serve_with_live_reload`)
Added specific error handling when injecting live reload scripts:
```python
def _serve_with_live_reload(self) -> None:
    try:
        # Read file, inject script, send response
        ...
    except (BrokenPipeError, ConnectionResetError):
        # Client disconnected - this is normal
        pass
```

### 3. Request Processing Override (`handle_one_request`)
Prevented socketserver from printing tracebacks for these expected errors:
```python
def handle_one_request(self) -> None:
    try:
        super().handle_one_request()
    except (BrokenPipeError, ConnectionResetError):
        # Client disconnected - don't print traceback
        pass
```

## Impact

- **Clean Logs:** No more BrokenPipeError tracebacks cluttering the dev server output
- **Normal Operation:** Legitimate errors are still logged; only expected network errors are suppressed
- **Better UX:** Developers see only relevant information when using `bengal serve`

## Technical Notes

`BrokenPipeError` occurs when:
- Browser cancels a request (e.g., navigating away)
- Browser closes connection before reading full response
- Network interruption during SSE keepalive
- Any scenario where the socket is closed by the client

These are all normal HTTP scenarios and shouldn't generate error logs.

## Files Modified

- `bengal/server/dev_server.py`:
  - Added try-except to `do_GET()` (lines 65-80)
  - Added try-except to `_serve_with_live_reload()` (lines 167-169)
  - Added `handle_one_request()` override (lines 315-324)

## Testing

Run the dev server and verify:
```bash
cd examples/showcase
bengal serve
```

Expected: Clean logs without BrokenPipeError tracebacks when:
- Refreshing pages quickly
- Closing browser tabs
- Network interruptions
- SSE connection timeouts

