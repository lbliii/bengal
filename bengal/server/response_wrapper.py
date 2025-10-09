"""
Response buffering for live reload injection.

Provides a file-like object that buffers HTTP response data so it can be
modified before sending to the client. This enables injecting the live reload
script into HTML responses without intercepting requests before they're served.
"""

from typing import BinaryIO
from io import BytesIO

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class ResponseBuffer:
    """
    Buffer HTTP response data for modification before sending.
    
    Acts as a file-like object that captures all writes to buffer them
    instead of sending immediately. This allows inspecting and modifying
    the response before it's sent to the client.
    
    Usage:
        original_wfile = handler.wfile
        buffer = ResponseBuffer(original_wfile)
        handler.wfile = buffer
        
        # Handler writes to buffer instead of socket
        handler.do_GET()
        
        # Now we can inspect/modify the response
        data = buffer.get_buffered_data()
        modified_data = inject_script(data)
        
        # Send modified response
        original_wfile.write(modified_data)
        original_wfile.flush()
    """
    
    def __init__(self, original_wfile: BinaryIO):
        """
        Initialize response buffer.
        
        Args:
            original_wfile: Original file object to send data to eventually
        """
        self.original_wfile = original_wfile
        self.buffer = BytesIO()
        
    def write(self, data: bytes) -> int:
        """
        Write data to buffer instead of sending immediately.
        
        Args:
            data: Bytes to buffer
            
        Returns:
            Number of bytes written
        """
        return self.buffer.write(data)
    
    def flush(self) -> None:
        """
        Flush does nothing - we control when data is sent.
        
        This is intentionally a no-op because we want to buffer the entire
        response before deciding whether to modify it.
        """
        pass
    
    def get_buffered_data(self) -> bytes:
        """
        Get all buffered data.
        
        Returns:
            All data that has been written to the buffer
        """
        return self.buffer.getvalue()
    
    def send_buffered(self) -> None:
        """
        Send buffered data to original stream unchanged.
        
        This is a convenience method for sending the response as-is
        without modification.
        """
        data = self.get_buffered_data()
        self.original_wfile.write(data)
        self.original_wfile.flush()
        
        logger.debug("response_sent_unmodified", 
                    size_bytes=len(data))
    
    def send_modified(self, modified_data: bytes) -> None:
        """
        Send modified data to original stream.
        
        Args:
            modified_data: Modified response data to send
        """
        original_size = len(self.get_buffered_data())
        modified_size = len(modified_data)
        
        self.original_wfile.write(modified_data)
        self.original_wfile.flush()
        
        logger.debug("response_sent_modified",
                    original_size_bytes=original_size,
                    modified_size_bytes=modified_size,
                    size_delta=modified_size - original_size)
    
    def clear(self) -> None:
        """
        Clear the buffer.
        
        Useful for freeing memory after the response has been sent.
        """
        self.buffer = BytesIO()

