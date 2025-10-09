# Live Reload Architecture - Long-Term Solution Proposal

**Status**: Architectural Analysis  
**Date**: 2025-10-09  
**Priority**: High  
**Author**: Architecture Review

## Executive Summary

The current live reload implementation has a critical flaw: it intercepts all directory requests (`/`) in the `do_GET()` method, causing navigation failures. This document proposes three architectural solutions, recommends the **Response Wrapper Pattern** as the optimal approach, and provides a detailed implementation plan.

**Recommended Solution**: Response Wrapper Pattern with post-processing hook  
**Estimated Effort**: 4-6 hours  
**Risk**: Low (fallback to default handler on any error)  

---

## 1. Problem Analysis

### Root Cause

The bug occurs in `bengal/server/request_handler.py`:

```python
def do_GET(self) -> None:
    # Handle SSE endpoint for live reload
    if self.path == '/__bengal_reload__':
        self.handle_sse()
        return
    
    # PROBLEM: Intercepts ALL requests ending with '/'
    if self.path.endswith('.html') or self.path.endswith('/'):
        try:
            handled = self.serve_html_with_live_reload()
            if handled:
                return  # Success - script injected
            # Fall through if not handled
        except (BrokenPipeError, ConnectionResetError):
            return
    
    super().do_GET()  # Only reached if above failed
```

**The Issue**: When `serve_html_with_live_reload()` is called:

1. Path translation may fail (`translate_path()` edge cases)
2. Directory without `index.html` returns `False` but may not fall through correctly
3. File system race conditions during read
4. Response already partially sent, causing browser to wait indefinitely
5. Only catching 2 exception types (BrokenPipeError, ConnectionResetError) - not catching all errors

**Result**: Browser receives incomplete response → request canceled/timeout → navigation failure

### Failure Modes Observed

1. **Requests canceled** - Browser gives up waiting
2. **Connection timeouts** - No response received within timeout window
3. **Pending requests** - Browser waiting indefinitely for response
4. **Navigation blocked** - User cannot navigate to any page ending with `/`

---

## 2. Current Architecture Review

### Component Structure

```
bengal/server/
├── dev_server.py          # Main server orchestration
├── request_handler.py     # HTTP request handling (BROKEN HERE)
├── request_logger.py      # Request logging mixin
├── live_reload.py         # SSE + HTML injection (LiveReloadMixin)
├── build_handler.py       # File watcher + rebuild trigger
├── resource_manager.py    # Cleanup on exit
└── pid_manager.py         # Stale process detection
```

### Class Hierarchy (Multiple Inheritance)

```python
class BengalRequestHandler(
    RequestLogger,           # Mixin: Beautiful logging
    LiveReloadMixin,         # Mixin: SSE + HTML injection
    SimpleHTTPRequestHandler # Base: Standard HTTP file serving
):
    pass
```

**Problem**: The `LiveReloadMixin` tries to **intercept** requests before `SimpleHTTPRequestHandler` processes them. This is fragile because:
- We're duplicating path resolution logic
- We're manually checking file existence (race conditions)
- We're sending responses before the base handler has a chance to validate

### Why Multiple Inheritance is Risky Here

Multiple inheritance with method overriding (like `do_GET()`) creates a fragile Method Resolution Order (MRO):

```
RequestLogger.do_GET()? No
  ↓
LiveReloadMixin.do_GET()? No
  ↓
BengalRequestHandler.do_GET()? Yes → Intercepts everything
  ↓
SimpleHTTPRequestHandler.do_GET()? Only if we call super()
```

**The core issue**: We're trying to **modify the response** by **intercepting the request**. This is backwards.

---

## 3. Research Findings: Industry Patterns

### Pattern 1: Response Wrapper (WSGI Middleware Pattern)

**Used by**: Flask, Django, Werkzeug

**Concept**: Let the handler complete normally, then wrap/modify the response.

```python
class ResponseCapture:
    """Capture response, modify it, send modified version."""
    
    def __init__(self, handler):
        self.handler = handler
        self.captured_response = []
        
    def write(self, data):
        """Intercept all writes."""
        self.captured_response.append(data)
        
    def get_modified_response(self):
        """Get response with modifications."""
        html = b''.join(self.captured_response).decode('utf-8')
        if '</body>' in html:
            html = html.replace('</body>', LIVE_RELOAD_SCRIPT + '</body>')
        return html.encode('utf-8')
```

**Advantages**:
- ✅ Let base handler do all the hard work (path resolution, file serving)
- ✅ Only modify successful HTML responses
- ✅ No duplication of file system logic
- ✅ Errors in base handler are handled correctly

**Disadvantages**:
- Need to buffer entire response (memory overhead for large files)
- Requires careful handling of Content-Length header

### Pattern 2: Streaming Injection (Nginx/Proxy Pattern)

**Used by**: Browser-sync, live-server (Node.js)

**Concept**: Stream response and inject script on-the-fly.

```python
def do_GET(self):
    # Let parent handle everything
    super().do_GET()  # This writes to self.wfile
    
# Override wfile to inject during streaming
class InjectionStream:
    def write(self, data):
        if b'</body>' in data:
            data = data.replace(b'</body>', 
                               LIVE_RELOAD_SCRIPT.encode() + b'</body>')
        return self.original_wfile.write(data)
```

**Advantages**:
- ✅ No buffering needed - constant memory usage
- ✅ Works with very large files
- ✅ Minimal overhead

**Disadvantages**:
- Complex to implement correctly
- Need to handle chunked encoding
- Script might be split across writes

### Pattern 3: Process-Level Hot Reload (Gunicorn/Uvicorn Pattern)

**Used by**: Gunicorn, Uvicorn, Huey

**Concept**: Restart entire server process on file change.

```python
def watch_and_reload():
    """Watch files and restart process."""
    for changes in watch('./project'):
        subprocess.run(['pkill', '-TERM', 'bengal'])
        subprocess.Popen(['bengal', 'serve'])
```

**Advantages**:
- ✅ Simplest implementation
- ✅ No live reload script needed (browser reconnects)
- ✅ No response modification required

**Disadvantages**:
- ❌ Slower (full server restart)
- ❌ Loses SSE connections
- ❌ Browser doesn't auto-reload (user must refresh)
- ❌ Not true "live reload" from user perspective

### Pattern 4: Post-Processing Hook (Template Engine Pattern)

**Used by**: Jinja2, Mako (template caching)

**Concept**: Let handler complete, check if HTML, modify before final send.

```python
def do_GET(self):
    """Process request and optionally post-process response."""
    # Capture the response path before calling parent
    request_path = self.path
    
    # Let parent do everything (path resolution, security checks, file serving)
    # But DON'T send response yet
    response_data = self._get_response_from_parent()
    
    # Post-process if it's HTML
    if self._is_html_response(request_path):
        response_data = self._inject_live_reload_script(response_data)
    
    # Now send the final response
    self._send_response(response_data)
```

**Advantages**:
- ✅ Clean separation of concerns
- ✅ Only modify successful responses
- ✅ Easy to test and debug
- ✅ Can be disabled with a simple flag

**Disadvantages**:
- Requires refactoring do_GET() significantly
- Need to capture response before it's sent (tricky with SimpleHTTPRequestHandler)

---

## 4. Proposed Solutions

### Solution A: Fix Current Implementation (Quick Fix) ⚠️

**Approach**: Improve error handling in existing `serve_html_with_live_reload()`.

**Changes**:
```python
def do_GET(self):
    # Handle SSE
    if self.path == '/__bengal_reload__':
        self.handle_sse()
        return
    
    # Try live reload injection with COMPREHENSIVE error handling
    if self.path.endswith('.html') or self.path.endswith('/'):
        try:
            handled = self.serve_html_with_live_reload()
            if handled:
                return
        except Exception as e:  # Catch ALL exceptions
            logger.error("live_reload_failed", path=self.path, error=str(e))
            # Fall through to default handler
    
    super().do_GET()
```

**In `serve_html_with_live_reload()`**:
```python
def serve_html_with_live_reload(self) -> bool:
    try:
        path = self.translate_path(self.path)
        
        # Check if directory first
        if os.path.isdir(path):
            for index in ['index.html', 'index.htm']:
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
            else:
                # No index.html found - let default handler deal with it
                return False
        
        # Check if HTML file exists
        if not os.path.exists(path):
            return False  # File doesn't exist - let default handler send 404
            
        if not (path.endswith('.html') or path.endswith('.htm')):
            return False  # Not HTML - let default handler serve it
        
        # Read and inject
        with open(path, 'rb') as f:
            content = f.read()
        
        html_str = content.decode('utf-8', errors='replace')  # Handle encoding errors
        
        # Inject script
        if '</body>' in html_str.lower():
            idx = html_str.lower().rfind('</body>')
            html_str = html_str[:idx] + LIVE_RELOAD_SCRIPT + html_str[idx:]
        elif '</html>' in html_str.lower():
            idx = html_str.lower().rfind('</html>')
            html_str = html_str[:idx] + LIVE_RELOAD_SCRIPT + html_str[idx:]
        else:
            html_str += LIVE_RELOAD_SCRIPT
        
        # Send response
        modified_content = html_str.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(modified_content)))
        self.send_header('Cache-Control', 'no-cache')  # Prevent caching during dev
        self.end_headers()
        self.wfile.write(modified_content)
        return True
        
    except Exception as e:
        logger.error("serve_html_failed", error=str(e), error_type=type(e).__name__)
        return False  # Let default handler take over
```

**Pros**:
- ✅ Minimal changes
- ✅ Quick to implement (30 minutes)
- ✅ Better error handling

**Cons**:
- ❌ Still fragile (duplicating logic)
- ❌ Race conditions still possible
- ❌ Not addressing root architectural issue

**Verdict**: 🔴 **Not Recommended** - Band-aid solution

---

### Solution B: Response Wrapper Pattern (Recommended) ✅

**Approach**: Let `SimpleHTTPRequestHandler` do everything, then intercept and modify the response.

**Implementation**:

```python
class ResponseBuffer:
    """Buffer to capture response data."""
    
    def __init__(self, original_wfile):
        self.original_wfile = original_wfile
        self.buffer = []
        self.headers_sent = False
        
    def write(self, data):
        """Buffer writes instead of sending immediately."""
        self.buffer.append(data)
        return len(data)
    
    def flush(self):
        """Flush does nothing - we control when to send."""
        pass
    
    def get_buffered_data(self):
        """Get all buffered data."""
        return b''.join(self.buffer)
    
    def send_buffered(self):
        """Send buffered data to original stream."""
        data = self.get_buffered_data()
        self.original_wfile.write(data)
        self.original_wfile.flush()


class BengalRequestHandler(RequestLogger, http.server.SimpleHTTPRequestHandler):
    """Request handler with live reload via response wrapping."""
    
    server_version = "Bengal/1.0"
    sys_version = ""
    
    def do_GET(self):
        """Handle GET requests with optional live reload injection."""
        # Handle SSE endpoint
        if self.path == '/__bengal_reload__':
            self.handle_sse()  # From mixin
            return
        
        # Check if this might be an HTML request
        might_be_html = (
            self.path.endswith('.html') or 
            self.path.endswith('.htm') or 
            self.path.endswith('/') or
            '.' not in self.path.split('/')[-1]  # No extension = might be directory
        )
        
        if not might_be_html:
            # Definitely not HTML - use default handler
            super().do_GET()
            return
        
        # Buffer the response so we can modify it
        original_wfile = self.wfile
        response_buffer = ResponseBuffer(original_wfile)
        self.wfile = response_buffer
        
        try:
            # Let parent handler do ALL the work (path resolution, security, serving)
            super().do_GET()
            
            # Now check if we got an HTML response
            buffered_data = response_buffer.get_buffered_data()
            
            # Parse response to check if it's HTML
            if self._is_html_response(buffered_data):
                # Inject live reload script
                modified_data = self._inject_live_reload(buffered_data)
                
                # Send modified response
                original_wfile.write(modified_data)
                original_wfile.flush()
            else:
                # Not HTML - send as-is
                response_buffer.send_buffered()
                
        except Exception as e:
            # If anything goes wrong, restore wfile and let default handler try again
            logger.error("response_wrapper_failed", error=str(e))
            self.wfile = original_wfile
            # Don't retry - response might be partially sent
            # Just log and let it fail naturally
        finally:
            # Always restore original wfile
            self.wfile = original_wfile
    
    def _is_html_response(self, response_data: bytes) -> bool:
        """Check if response is HTML by inspecting headers and content."""
        try:
            # Look for HTTP response headers
            if b'\r\n\r\n' not in response_data:
                return False
            
            headers_end = response_data.index(b'\r\n\r\n')
            headers = response_data[:headers_end].decode('latin-1', errors='ignore')
            body = response_data[headers_end + 4:]
            
            # Check Content-Type header
            if 'Content-Type: text/html' in headers:
                return True
            
            # Check for HTML content (as fallback)
            if b'<html' in body.lower() or b'<!doctype html' in body.lower():
                return True
                
            return False
        except Exception:
            return False
    
    def _inject_live_reload(self, response_data: bytes) -> bytes:
        """Inject live reload script into HTML response."""
        try:
            # Split headers and body
            headers_end = response_data.index(b'\r\n\r\n')
            headers_bytes = response_data[:headers_end + 4]
            body = response_data[headers_end + 4:]
            
            # Decode body
            html = body.decode('utf-8', errors='replace')
            
            # Inject script before </body> (case-insensitive)
            html_lower = html.lower()
            if '</body>' in html_lower:
                idx = html_lower.rfind('</body>')
                html = html[:idx] + LIVE_RELOAD_SCRIPT + html[idx:]
            elif '</html>' in html_lower:
                idx = html_lower.rfind('</html>')
                html = html[:idx] + LIVE_RELOAD_SCRIPT + html[idx:]
            else:
                html += LIVE_RELOAD_SCRIPT
            
            # Re-encode
            new_body = html.encode('utf-8')
            
            # Update Content-Length header
            headers = headers_bytes.decode('latin-1', errors='ignore')
            if 'Content-Length:' in headers:
                # Find and replace Content-Length
                import re
                headers = re.sub(
                    r'Content-Length: \d+',
                    f'Content-Length: {len(new_body)}',
                    headers
                )
            
            new_headers = headers.encode('latin-1')
            return new_headers + new_body
            
        except Exception as e:
            logger.error("injection_failed", error=str(e))
            return response_data  # Return unmodified on error
    
    def handle_sse(self):
        """Handle SSE endpoint (from LiveReloadMixin)."""
        # Keep existing SSE implementation from live_reload.py
        pass
```

**Pros**:
- ✅ **Robust**: Let base handler do all validation and security checks
- ✅ **No duplication**: Don't reimplement path resolution
- ✅ **Error-safe**: If injection fails, send original response
- ✅ **Testable**: Can test injection logic separately
- ✅ **Clean separation**: Handler logic vs. modification logic

**Cons**:
- ❌ Memory overhead: Buffer entire response (not an issue for HTML pages)
- ❌ Requires parsing HTTP response format
- ❌ Need to update Content-Length header

**Verdict**: 🟢 **Recommended** - Proper architectural solution

**Estimated Effort**: 4-6 hours (implementation + testing)

---

### Solution C: Subprocess Pattern (Alternative) 🟡

**Approach**: Use `livereload` library - restart server process on file change.

**Implementation**:

```python
# Option 1: Use livereload library
from livereload import Server

def serve_with_livereload(site):
    """Serve site with process-level live reload."""
    server = Server(site.output_dir)
    
    # Watch content directories
    server.watch('content/', site.build)
    server.watch('assets/', site.build)
    server.watch('templates/', site.build)
    server.watch('bengal.toml', site.build)
    
    server.serve(port=5173, host='localhost')


# Option 2: Custom subprocess management
import subprocess
import sys
from watchdog.observers import Observer

class ProcessReloader:
    """Restart server process on file changes."""
    
    def __init__(self, watch_dirs):
        self.watch_dirs = watch_dirs
        self.process = None
        
    def start(self):
        """Start server process."""
        self.process = subprocess.Popen([sys.executable, '-m', 'bengal.server.dev_server'])
        
    def restart(self):
        """Restart server process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.start()
        
    def on_change(self, event):
        """Handle file change event."""
        print(f"File changed: {event.src_path}")
        print("Restarting server...")
        self.restart()
```

**Pros**:
- ✅ Simple implementation
- ✅ No response modification needed
- ✅ Clean process state on each reload
- ✅ Battle-tested (used by many frameworks)

**Cons**:
- ❌ Slower (full restart)
- ❌ Not true "live reload" (browser doesn't auto-refresh)
- ❌ Loses SSE connections
- ❌ UX degradation (users must manually refresh)

**Verdict**: 🟡 **Not Recommended for Bengal** - We want true live reload with auto-refresh

---

## 5. Recommended Solution: Response Wrapper Pattern

### Why This is the Best Approach

1. **Architectural Soundness**
   - Follows Single Responsibility Principle
   - Separates concerns: serving vs. modification
   - No duplication of file system logic
   - Easy to test and debug

2. **Robustness**
   - Base handler does ALL validation
   - Security checks happen before modification
   - Errors in injection don't break serving
   - Graceful degradation (serve without injection)

3. **Maintainability**
   - Clear code structure
   - Easy to understand flow
   - Can be disabled with a simple flag
   - Future-proof (works with any improvements to SimpleHTTPRequestHandler)

4. **Performance**
   - Minimal overhead (only buffer HTML responses)
   - No streaming complexity
   - No process restart overhead

### Implementation Plan

**Phase 1: Core Implementation** (3-4 hours)

1. Create `ResponseBuffer` class
2. Refactor `do_GET()` to use response buffering
3. Implement `_is_html_response()` helper
4. Implement `_inject_live_reload()` helper
5. Keep SSE endpoint handling (already works)

**Phase 2: Testing** (2-3 hours)

1. Unit tests for `ResponseBuffer`
2. Unit tests for HTML detection
3. Unit tests for script injection
4. Integration tests:
   - Regular HTML pages
   - Directory with index.html
   - Directory without index.html (should 404)
   - Non-HTML files (CSS, JS, images)
   - Very large HTML files
   - Malformed HTML
   - Binary files incorrectly named .html
5. Manual testing:
   - Navigate across multiple pages
   - Verify live reload works
   - Test with slow connections
   - Test with large pages

**Phase 3: Configuration & Documentation** (1 hour)

1. Add `live_reload` config option to `bengal.toml`:
   ```toml
   [server]
   live_reload = true  # Can be disabled if needed
   ```

2. Update documentation
3. Add logging for debugging

**Total Estimated Effort**: 6-8 hours

---

## 6. Testing Strategy

### Unit Tests

```python
# tests/unit/server/test_response_buffer.py
def test_response_buffer_basic():
    """Test basic buffering."""
    import io
    original = io.BytesIO()
    buffer = ResponseBuffer(original)
    
    buffer.write(b'Hello ')
    buffer.write(b'World')
    
    assert buffer.get_buffered_data() == b'Hello World'
    assert original.getvalue() == b''  # Not sent yet
    
    buffer.send_buffered()
    assert original.getvalue() == b'Hello World'


# tests/unit/server/test_html_detection.py
def test_is_html_response_with_content_type():
    """Test HTML detection via Content-Type header."""
    response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>'
    handler = BengalRequestHandler()
    assert handler._is_html_response(response) is True


def test_is_html_response_no_html():
    """Test non-HTML detection."""
    response = b'HTTP/1.1 200 OK\r\nContent-Type: text/css\r\n\r\nbody { }'
    handler = BengalRequestHandler()
    assert handler._is_html_response(response) is False


# tests/unit/server/test_script_injection.py
def test_inject_before_body_tag():
    """Test script injection before </body>."""
    response = b'HTTP/1.1 200 OK\r\n\r\n<html><body>Content</body></html>'
    handler = BengalRequestHandler()
    result = handler._inject_live_reload(response)
    
    assert b'<script>' in result
    assert b'__bengal_reload__' in result
    assert result.index(b'<script>') < result.index(b'</body>')
```

### Integration Tests

```python
# tests/integration/server/test_live_reload_navigation.py
def test_navigate_across_pages(tmp_site):
    """Test navigation works with live reload enabled."""
    # Create test site with multiple pages
    (tmp_site / 'public' / 'index.html').write_text('<html><body>Home</body></html>')
    (tmp_site / 'public' / 'about.html').write_text('<html><body>About</body></html>')
    (tmp_site / 'public' / 'contact' / 'index.html').write_text('<html><body>Contact</body></html>')
    
    # Start server
    server = DevServer(site, port=0)  # Random port
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1)
    
    # Test navigation
    import requests
    base_url = f'http://localhost:{server.port}'
    
    # Navigate to pages
    r1 = requests.get(f'{base_url}/')
    assert r1.status_code == 200
    assert b'__bengal_reload__' in r1.content
    
    r2 = requests.get(f'{base_url}/about.html')
    assert r2.status_code == 200
    assert b'__bengal_reload__' in r2.content
    
    r3 = requests.get(f'{base_url}/contact/')
    assert r3.status_code == 200
    assert b'__bengal_reload__' in r3.content
    
    # Verify live reload script is present
    assert b'EventSource' in r1.content
    assert b'EventSource' in r2.content
    assert b'EventSource' in r3.content


def test_non_existent_page_404(tmp_site):
    """Test 404 handling with live reload enabled."""
    server = DevServer(site, port=0)
    # ... test that 404 pages work correctly


def test_binary_files_not_modified(tmp_site):
    """Test that binary files are served unchanged."""
    # Create an image file
    import base64
    img_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    (tmp_site / 'public' / 'test.png').write_bytes(img_data)
    
    # Request image
    r = requests.get(f'{base_url}/test.png')
    assert r.status_code == 200
    assert r.content == img_data  # Unchanged
    assert b'__bengal_reload__' not in r.content
```

### Manual Testing Checklist

- [ ] Navigate from `/` to `/docs/` - should load immediately
- [ ] Navigate from `/docs/` to `/tutorials/` - should load immediately
- [ ] Navigate to non-existent page - should show 404
- [ ] Edit a content file - browser should auto-reload
- [ ] Edit a CSS file - browser should auto-reload
- [ ] Server restart - browser should reconnect SSE automatically
- [ ] Multiple browser tabs - all should reload together
- [ ] Slow connection (throttle network) - should not timeout
- [ ] Very large HTML page (>1MB) - should inject correctly

---

## 7. Migration Path

### Step 1: Implement Response Wrapper (Week 1)

1. Create new `ResponseWrapper` class in `bengal/server/response_wrapper.py`
2. Write unit tests
3. Refactor `BengalRequestHandler.do_GET()` to use wrapper
4. Keep old code commented out as fallback

### Step 2: Test Extensively (Week 1-2)

1. Run all integration tests
2. Manual testing with real sites
3. Performance benchmarking
4. Memory profiling (ensure buffering doesn't cause issues)

### Step 3: Deploy with Feature Flag (Week 2)

```toml
[server]
live_reload = true  # Enable new implementation
live_reload_method = "response_wrapper"  # or "old" for fallback
```

### Step 4: Monitor & Fix Issues (Week 2-3)

1. Gather user feedback
2. Fix any edge cases
3. Improve logging

### Step 5: Remove Old Code (Week 4)

1. Once stable, remove commented-out old implementation
2. Remove feature flags
3. Update documentation

---

## 8. Alternative Considerations

### Why Not Use `livereload` Library?

The `livereload` library is great for simple projects, but:

1. **Less control**: Black box - harder to customize
2. **Process restart**: Slower than SSE-based reload
3. **UX**: Requires manual browser refresh (no auto-reload)
4. **Dependencies**: Adds another dependency
5. **Integration**: Harder to integrate with Bengal's build system

**Our SSE approach is better** because:
- ✅ True live reload (auto-refresh)
- ✅ Instant feedback (no process restart)
- ✅ Full control over behavior
- ✅ Works with existing build system
- ✅ Better UX

### Why Not Streaming Injection?

Streaming injection (modifying data as it's sent) is complex:

1. Need to handle chunked encoding
2. Script might be split across multiple writes
3. Hard to update Content-Length
4. More edge cases to handle

**Buffering is simpler and sufficient** because:
- HTML pages are typically small (<1MB)
- Memory overhead is negligible
- Implementation is much simpler
- Fewer bugs

---

## 9. Success Criteria

### Must Have
- ✅ Navigation works perfectly (no timeouts/cancels)
- ✅ Live reload script injected into all HTML pages
- ✅ SSE endpoint working correctly
- ✅ Browser auto-reloads on file changes
- ✅ No performance degradation
- ✅ Works with all content types (HTML, CSS, JS, images)

### Nice to Have
- ⭐ Configurable (can be disabled)
- ⭐ Selective reload (only reload changed assets, not full page)
- ⭐ Smart reload (preserve scroll position, form state)
- ⭐ Multi-device sync (reload all connected devices)

### Quality Metrics
- Code coverage: >85%
- Integration tests: >10 scenarios
- Manual test checklist: 100% passed
- Performance overhead: <50ms per HTML request
- Memory overhead: <10MB additional usage

---

## 10. Conclusion

**Recommended Implementation**: Response Wrapper Pattern

**Timeline**: 1-2 weeks
- Week 1: Implementation + Testing
- Week 2: Deploy + Monitor + Fix

**Risk**: Low (fallback to default handler on any error)

**Impact**: High (fixes critical navigation bug, enables true live reload)

**Next Steps**:
1. Review this document with team
2. Get approval for approach
3. Create implementation tasks
4. Begin Phase 1 implementation

---

## Appendix A: Code Snippets

### Full Response Wrapper Implementation

See full implementation in the main document above (Solution B).

### Configuration Schema

```toml
# bengal.toml
[server]
# Enable/disable live reload
live_reload = true

# SSE keepalive interval (seconds)
sse_keepalive = 30

# Maximum response buffer size (MB)
max_buffer_size = 10

# Paths to exclude from live reload injection
exclude_paths = [
    "/_internal/",
    "/admin/",
]
```

---

## Appendix B: References

### Industry Examples

1. **Flask + Werkzeug**: Uses process restart with `watchdog`
   - https://flask.palletsprojects.com/en/latest/cli/#reloader

2. **Django**: Uses autoreload with file monitoring
   - https://docs.djangoproject.com/en/stable/ref/utils/#module-django.utils.autoreload

3. **Browser-Sync**: Uses streaming injection
   - https://browsersync.io/docs

4. **live-server** (Node.js): Uses HTML injection + SSE
   - https://github.com/tapio/live-server

### Python Patterns

1. **WSGI Middleware**: Response wrapping pattern
   - https://peps.python.org/pep-3333/

2. **Watchdog**: File system monitoring
   - https://python-watchdog.readthedocs.io/

3. **Server-Sent Events**: Real-time communication
   - https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-09  
**Status**: Awaiting Review

