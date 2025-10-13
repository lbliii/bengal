"""Server-level constants used across dev server components.

Keeping these in one module ensures docs and defaults stay consistent.
"""

DEFAULT_DEV_HOST: str = "localhost"
DEFAULT_DEV_PORT: int = 5173

# Server-Sent Events endpoint path for live reload
LIVE_RELOAD_PATH: str = "/__bengal_reload__"
