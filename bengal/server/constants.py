"""
Server-level constants for Bengal dev server.

Centralizes configuration defaults and magic strings to ensure consistency
across all dev server components. Changes here propagate to documentation,
CLI defaults, and runtime behavior.

Constants:
    DEFAULT_DEV_HOST: Default hostname for the dev server (localhost)
    DEFAULT_DEV_PORT: Default port number (5173, matches Vite convention)
    LIVE_RELOAD_PATH: SSE endpoint path for live reload connections

Related:
    - bengal/server/dev_server.py: Uses these defaults for server initialization
    - bengal/server/live_reload.py: Uses LIVE_RELOAD_PATH for SSE endpoint
    - bengal/cli/serve.py: CLI exposes these as default argument values
"""

from __future__ import annotations

#: Default hostname for the dev server. Uses localhost for security.
DEFAULT_DEV_HOST: str = "localhost"

#: Default port number. Matches Vite's default for familiarity.
DEFAULT_DEV_PORT: int = 5173

#: Server-Sent Events endpoint path for live reload connections.
#: Prefixed with double underscores to avoid collisions with user routes.
LIVE_RELOAD_PATH: str = "/__bengal_reload__"
