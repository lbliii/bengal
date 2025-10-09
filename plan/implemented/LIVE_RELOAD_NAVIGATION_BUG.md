# Live Reload Navigation Bug

**Status**: Identified and Temporarily Disabled  
**Date**: 2025-10-09  
**Priority**: High

## Problem

After implementing live reload functionality, the dev server stopped being able to navigate across pages. Users would see:
- Requests being canceled (e.g., `tutorials/`, `docs/`)
- Connection timeouts (`net::ERR_CONNECTION_TIMED_OUT`)
- Pending requests that never complete

## Root Cause

The issue is in `/bengal/server/request_handler.py` in the `do_GET()` method:

```python
def do_GET(self) -> None:
    # Handle SSE endpoint for live reload
    if self.path == '/__bengal_reload__':
        self.handle_sse()
        return
    
    # For HTML files, inject live reload script
    if self.path.endswith('.html') or self.path.endswith('/'):
        try:
            handled = self.serve_html_with_live_reload()
            if handled:
                return
            # If not handled, fall through to default handling
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected while we were serving - this is normal
            return
    
    # Default handling for other files
    super().do_GET()
```

**The Problem**: The code intercepts ALL requests ending with `/` (like `/tutorials/`, `/docs/`, `/posts/`) to inject live reload. When `serve_html_with_live_reload()` is called, it:

1. Translates the path to a file system path
2. Checks if it's a directory and looks for `index.html`
3. Attempts to serve the HTML with injected live reload script

However, there are several potential failure modes:
- Path translation issues
- Directory without index.html (should return False but might not)
- Exception not caught (only catching BrokenPipeError and ConnectionResetError)
- Race conditions between file system operations and response writing
- Incomplete response headers or body causing browser to wait indefinitely

## Temporary Fix

Disabled live reload by commenting out the interception logic in `do_GET()`. This allows the server to use the default `SimpleHTTPRequestHandler.do_GET()` behavior, which is proven and stable.

Also updated the startup message to indicate live reload is temporarily disabled.

## Proper Fix Needed

To re-enable live reload properly, we need to:

1. **Add Better Error Handling**: Catch ALL exceptions in `serve_html_with_live_reload()`, not just BrokenPipeError
   ```python
   try:
       handled = self.serve_html_with_live_reload()
       if handled:
           return
   except Exception as e:
       logger.error("live_reload_injection_failed", error=str(e))
       # Fall through to default handling
   ```

2. **Fix Path Resolution**: Ensure `serve_html_with_live_reload()` correctly handles:
   - Directories without index.html (return False immediately)
   - Non-existent paths (return False, let default handler send 404)
   - Symbolic links and other edge cases

3. **Add Logging**: Add more detailed logging in `serve_html_with_live_reload()` to understand what's happening:
   - Log when function is called and with what path
   - Log when returning True vs False
   - Log any file system operations

4. **Test Edge Cases**: Test navigation to:
   - Existing directories with index.html (e.g., `/tutorials/`)
   - Non-existent directories (e.g., `/fake-page/`)
   - Files that exist but aren't HTML (should skip injection)
   - Root path `/`

5. **Consider Alternative Approach**: Instead of intercepting in `do_GET()`, consider:
   - Only injecting script when file is successfully read
   - Using a response wrapper/middleware pattern
   - Post-processing response after `super().do_GET()` completes

## Files Modified

- `/bengal/server/request_handler.py` - Commented out live reload logic
- `/bengal/server/dev_server.py` - Updated startup message

## Testing

To test the fix:
1. Restart dev server: `bengal serve`
2. Try navigating to different pages: `/`, `/tutorials/`, `/docs/`, `/posts/`
3. Verify all pages load correctly
4. Check browser console for errors
5. Check dev server logs

## Next Steps

1. ✅ Disable live reload (temporary fix)
2. ⬜ Investigate exact failure mode with detailed logging
3. ⬜ Implement proper error handling
4. ⬜ Test edge cases thoroughly
5. ⬜ Re-enable live reload with confidence

## Related Files

- `/bengal/server/request_handler.py` - Request handler with live reload
- `/bengal/server/live_reload.py` - Live reload implementation
- `/bengal/server/build_handler.py` - Triggers reload notifications
- `/bengal/server/dev_server.py` - Main dev server

