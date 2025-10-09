# Live Reload - Quick Implementation Guide

**TL;DR**: Use the Response Wrapper Pattern - let the base handler serve files, then intercept and modify HTML responses before sending to browser.

---

## The Problem (1 minute read)

```python
# ❌ CURRENT (BROKEN) - Intercepts request BEFORE serving
def do_GET(self):
    if self.path.endswith('/'):
        # Try to serve file ourselves → FAILS with edge cases
        handled = self.serve_html_with_live_reload()
        if handled:
            return
    super().do_GET()  # Only if above failed
```

**Issue**: We duplicate path resolution logic, miss edge cases, cause timeouts.

---

## The Solution (2 minute read)

```python
# ✅ RECOMMENDED - Let handler serve, THEN modify response
def do_GET(self):
    # Handle SSE
    if self.path == '/__bengal_reload__':
        self.handle_sse()
        return
    
    # Buffer response for potential modification
    if might_be_html(self.path):
        original_wfile = self.wfile
        buffer = ResponseBuffer(original_wfile)
        self.wfile = buffer
        
        try:
            super().do_GET()  # Let base handler do EVERYTHING
            
            # NOW check if it's HTML and inject script
            data = buffer.get_buffered_data()
            if is_html_response(data):
                data = inject_live_reload_script(data)
            
            original_wfile.write(data)
        finally:
            self.wfile = original_wfile
    else:
        super().do_GET()  # Definitely not HTML, serve normally
```

**Why it works**:
- ✅ Base handler validates paths, checks permissions, sends 404s
- ✅ We only modify SUCCESSFUL HTML responses
- ✅ No duplication of file system logic
- ✅ Errors in base handler are handled correctly
- ✅ If injection fails, send original response

---

## Implementation Checklist

### Step 1: Create ResponseBuffer Class (30 min)

```python
# bengal/server/response_wrapper.py
class ResponseBuffer:
    """Capture response for modification before sending."""
    
    def __init__(self, original_wfile):
        self.original_wfile = original_wfile
        self.buffer = []
        
    def write(self, data):
        """Buffer data instead of sending."""
        self.buffer.append(data)
        return len(data)
    
    def get_buffered_data(self):
        """Get all buffered data."""
        return b''.join(self.buffer)
    
    def send_buffered(self):
        """Send buffered data to original stream."""
        self.original_wfile.write(self.get_buffered_data())
        self.original_wfile.flush()
```

### Step 2: Add Helper Methods (45 min)

```python
# In BengalRequestHandler
def _might_be_html(self, path: str) -> bool:
    """Quick check if request might return HTML."""
    return (
        path.endswith('.html') or 
        path.endswith('.htm') or 
        path.endswith('/') or
        '.' not in path.split('/')[-1]  # No extension
    )

def _is_html_response(self, response_data: bytes) -> bool:
    """Check if response is HTML."""
    try:
        if b'\r\n\r\n' not in response_data:
            return False
        
        headers_end = response_data.index(b'\r\n\r\n')
        headers = response_data[:headers_end].decode('latin-1')
        
        # Check Content-Type
        if 'Content-Type: text/html' in headers:
            return True
        
        # Fallback: check body for HTML tags
        body = response_data[headers_end + 4:]
        return b'<html' in body.lower() or b'<!doctype' in body.lower()
    except:
        return False

def _inject_live_reload(self, response_data: bytes) -> bytes:
    """Inject live reload script into HTML."""
    try:
        # Split headers and body
        headers_end = response_data.index(b'\r\n\r\n')
        headers_bytes = response_data[:headers_end + 4]
        body = response_data[headers_end + 4:]
        
        # Inject script
        html = body.decode('utf-8', errors='replace')
        if '</body>' in html.lower():
            idx = html.lower().rfind('</body>')
            html = html[:idx] + LIVE_RELOAD_SCRIPT + html[idx:]
        else:
            html += LIVE_RELOAD_SCRIPT
        
        new_body = html.encode('utf-8')
        
        # Update Content-Length
        headers = headers_bytes.decode('latin-1')
        import re
        headers = re.sub(
            r'Content-Length: \d+',
            f'Content-Length: {len(new_body)}',
            headers
        )
        
        return headers.encode('latin-1') + new_body
    except Exception as e:
        logger.error("injection_failed", error=str(e))
        return response_data  # Return unmodified
```

### Step 3: Refactor do_GET() (30 min)

```python
def do_GET(self):
    """Handle GET with optional live reload injection."""
    # SSE endpoint
    if self.path == '/__bengal_reload__':
        self.handle_sse()
        return
    
    # Check if might be HTML
    if not self._might_be_html(self.path):
        super().do_GET()
        return
    
    # Buffer response
    original_wfile = self.wfile
    buffer = ResponseBuffer(original_wfile)
    self.wfile = buffer
    
    try:
        # Let parent do everything
        super().do_GET()
        
        # Check if HTML and inject
        data = buffer.get_buffered_data()
        if self._is_html_response(data):
            data = self._inject_live_reload(data)
        
        # Send final response
        original_wfile.write(data)
        original_wfile.flush()
    except Exception as e:
        logger.error("live_reload_wrapper_failed", error=str(e))
        # Don't retry - might be partially sent
    finally:
        self.wfile = original_wfile
```

### Step 4: Test (2-3 hours)

```python
# tests/unit/server/test_response_wrapper.py
def test_buffer_basic():
    buffer = ResponseBuffer(io.BytesIO())
    buffer.write(b'Hello')
    buffer.write(b' World')
    assert buffer.get_buffered_data() == b'Hello World'

def test_html_detection():
    handler = BengalRequestHandler()
    response = b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>'
    assert handler._is_html_response(response) is True

def test_injection():
    handler = BengalRequestHandler()
    response = b'HTTP/1.1 200 OK\r\n\r\n<html><body></body></html>'
    result = handler._inject_live_reload(response)
    assert b'__bengal_reload__' in result

# tests/integration/server/test_live_reload_navigation.py
def test_navigate_pages():
    """Test navigation across multiple pages."""
    # Start server, make requests, verify responses
    # ...
```

---

## Key Principles

1. **Let the base handler do its job** - Don't duplicate path resolution, security checks, etc.
2. **Modify responses, not requests** - Intercept after serving, not before
3. **Fail gracefully** - If injection fails, send original response
4. **Only buffer HTML** - Skip buffering for CSS/JS/images
5. **Update Content-Length** - Keep headers consistent with body

---

## Testing Checklist

Manual testing:
- [ ] Navigate from `/` to `/docs/` - loads immediately
- [ ] Navigate to `/posts/` - loads immediately  
- [ ] Navigate to `/fake-page/` - shows 404
- [ ] CSS files serve correctly
- [ ] Images serve correctly
- [ ] Large HTML files (>1MB) work
- [ ] Edit content file → browser reloads
- [ ] Multiple tabs reload together
- [ ] Server restart → SSE reconnects

---

## Troubleshooting

### Response buffer causing memory issues?
- Add max buffer size limit (default: 10MB)
- Only buffer responses that are likely HTML
- Stream large files instead of buffering

### Content-Length mismatch errors?
- Make sure you're updating the header after injection
- Use regex to find and replace: `Content-Length: \d+`

### Script not injecting?
- Check if `</body>` tag exists (case-insensitive)
- Fallback to appending at end of HTML
- Log when injection succeeds/fails

### SSE connection drops?
- Make sure SSE endpoint (`/__bengal_reload__`) isn't buffered
- Check keepalive interval (default: 30s)
- Verify client reconnects on disconnect

---

## Performance Impact

**Benchmarks** (expected):
- Buffering overhead: ~5-10ms per HTML request
- Memory overhead: ~2x page size while buffering (temporary)
- CSS/JS/images: 0ms overhead (no buffering)
- Total impact: <1% on dev server performance

**Optimization tips**:
- Skip buffering for paths that definitely aren't HTML (has file extension)
- Clear buffer after sending to free memory
- Consider streaming for very large files (>5MB)

---

## Next Steps

1. Review full proposal: `plan/LIVE_RELOAD_ARCHITECTURE_PROPOSAL.md`
2. Implement `ResponseBuffer` class
3. Add helper methods
4. Refactor `do_GET()`
5. Write tests
6. Test manually
7. Deploy behind feature flag
8. Monitor for issues
9. Remove old code once stable

---

**Questions?** See the full architectural proposal for detailed analysis, alternatives, and migration path.

