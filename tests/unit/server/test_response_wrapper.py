"""
Tests for response buffering functionality.

Tests the ResponseBuffer class used for capturing and modifying
HTTP responses before sending them to clients.
"""

import io
import pytest

from bengal.server.response_wrapper import ResponseBuffer


class TestResponseBuffer:
    """Test ResponseBuffer class."""
    
    def test_buffer_initialization(self):
        """Test basic buffer initialization."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        assert buffer.original_wfile is original
        assert buffer.get_buffered_data() == b''
    
    def test_write_buffers_data(self):
        """Test that write() buffers data instead of sending."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Write data
        bytes_written = buffer.write(b'Hello ')
        assert bytes_written == 6
        
        bytes_written = buffer.write(b'World')
        assert bytes_written == 5
        
        # Data should be buffered, not sent
        assert original.getvalue() == b''
        assert buffer.get_buffered_data() == b'Hello World'
    
    def test_flush_is_noop(self):
        """Test that flush() does nothing."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        buffer.write(b'Test data')
        buffer.flush()
        
        # Data should still be buffered, not sent
        assert original.getvalue() == b''
        assert buffer.get_buffered_data() == b'Test data'
    
    def test_send_buffered(self):
        """Test sending buffered data unchanged."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        buffer.write(b'HTTP/1.1 200 OK\r\n')
        buffer.write(b'Content-Type: text/html\r\n\r\n')
        buffer.write(b'<html><body>Test</body></html>')
        
        # Send buffered data
        buffer.send_buffered()
        
        # Now data should be in original stream
        sent_data = original.getvalue()
        assert sent_data == b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body>Test</body></html>'
    
    def test_send_modified(self):
        """Test sending modified data."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Buffer original data
        buffer.write(b'Original data')
        
        # Send modified data
        modified_data = b'Modified data'
        buffer.send_modified(modified_data)
        
        # Modified data should be sent
        assert original.getvalue() == modified_data
    
    def test_clear_buffer(self):
        """Test clearing the buffer."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        buffer.write(b'Test data')
        assert buffer.get_buffered_data() == b'Test data'
        
        # Clear buffer
        buffer.clear()
        assert buffer.get_buffered_data() == b''
    
    def test_multiple_writes(self):
        """Test multiple write operations."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Simulate HTTP response being written in chunks
        chunks = [
            b'HTTP/1.1 200 OK\r\n',
            b'Content-Type: text/html\r\n',
            b'Content-Length: 30\r\n',
            b'\r\n',
            b'<html><body>',
            b'Test',
            b'</body></html>',
        ]
        
        for chunk in chunks:
            buffer.write(chunk)
        
        # All chunks should be buffered together
        expected = b''.join(chunks)
        assert buffer.get_buffered_data() == expected
    
    def test_large_response(self):
        """Test buffering large response."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Create a large response (1MB)
        large_body = b'x' * (1024 * 1024)
        headers = b'HTTP/1.1 200 OK\r\n\r\n'
        
        buffer.write(headers)
        buffer.write(large_body)
        
        buffered = buffer.get_buffered_data()
        assert len(buffered) == len(headers) + len(large_body)
        assert buffered == headers + large_body
    
    def test_binary_data(self):
        """Test buffering binary data (like images)."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Simulate binary image data
        headers = b'HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n'
        binary_data = bytes(range(256))  # All possible byte values
        
        buffer.write(headers)
        buffer.write(binary_data)
        
        buffered = buffer.get_buffered_data()
        assert buffered == headers + binary_data
        
        # Send unchanged
        buffer.send_buffered()
        assert original.getvalue() == headers + binary_data
    
    def test_empty_buffer_send(self):
        """Test sending empty buffer."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Send empty buffer
        buffer.send_buffered()
        
        assert original.getvalue() == b''
    
    def test_buffer_reuse_after_clear(self):
        """Test reusing buffer after clearing."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # First use
        buffer.write(b'First data')
        buffer.send_buffered()
        
        # Clear and reuse
        buffer.clear()
        buffer.write(b'Second data')
        
        assert buffer.get_buffered_data() == b'Second data'


class TestResponseBufferEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_unicode_in_binary_stream(self):
        """Test handling unicode that gets encoded."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Write UTF-8 encoded unicode
        unicode_text = "Hello 世界 🌍"
        buffer.write(unicode_text.encode('utf-8'))
        
        buffered = buffer.get_buffered_data()
        assert buffered == unicode_text.encode('utf-8')
        assert buffered.decode('utf-8') == unicode_text
    
    def test_partial_writes(self):
        """Test partial writes (simulating network conditions)."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        # Write one byte at a time
        data = b'Test'
        for byte in data:
            buffer.write(bytes([byte]))
        
        assert buffer.get_buffered_data() == data
    
    def test_write_returns_correct_length(self):
        """Test that write() returns number of bytes written."""
        original = io.BytesIO()
        buffer = ResponseBuffer(original)
        
        assert buffer.write(b'') == 0
        assert buffer.write(b'a') == 1
        assert buffer.write(b'hello') == 5
        assert buffer.write(b'\x00\x01\x02') == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

