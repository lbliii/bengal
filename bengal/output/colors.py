"""
Color utilities for CLI output.

Provides Rich style names and ANSI escape codes for HTTP status codes
and request methods. Used by the dev server output for colorized
request logging.

Color Mapping:
Status codes are colorized by category:
- 2xx Success: Green
- 304 Not Modified: Gray (dimmed)
- 3xx Redirect: Cyan
- 4xx Client Error: Yellow
- 5xx Server Error: Red

HTTP methods are colorized by semantic meaning:
- GET: Cyan (read operation)
- POST: Yellow (create operation)
- PUT/PATCH: Magenta (update operation)
- DELETE: Red (destructive operation)

Note:
    This module re-exports functions from bengal.output.utils for backward
    compatibility. The unified color mappings are defined in utils.py.

Related:
- bengal/output/utils.py: Single source of truth for color mappings
- bengal/output/dev_server.py: Consumes these color functions
- bengal/utils/rich_console.py: Rich console configuration

"""

from __future__ import annotations

# Re-export from utils for backward compatibility
# Old names mapped to new names
from bengal.output.utils import get_method_ansi as get_method_color_code
from bengal.output.utils import get_method_style, get_status_ansi as get_status_color_code
from bengal.output.utils import get_status_style

__all__ = [
    "get_status_color_code",
    "get_status_style",
    "get_method_color_code",
    "get_method_style",
]
