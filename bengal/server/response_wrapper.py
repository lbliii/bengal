"""
Deprecated: ResponseBuffer is no longer used.

Kept temporarily to avoid import errors while tests are updated.
"""

class ResponseBuffer:  # pragma: no cover - slated for removal
    def __init__(self, *args, **kwargs):
        pass
    def write(self, data):
        return len(data)
    def flush(self):
        pass
    def get_buffered_data(self):
        return b""
    def send_buffered(self):
        pass
    def send_modified(self, modified_data: bytes):
        pass
    def clear(self):
        pass

