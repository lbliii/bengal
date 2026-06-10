"""Dev-server palette-rebuild swallow must emit a diagnostic (issue #385, G10).

Regression for Finding 11: ``DevServer._set_active_palette`` used to ``pass`` on
failure, so dev-preview styling could be wrong with no signal -- even though the
sibling ``_clear_html_cache_after_build`` already logs the same failure class.
The palette path must now emit ``rebuilding_page_palette_failed``.
"""

from __future__ import annotations

from unittest.mock import Mock

from bengal.server.dev_server import DevServer


def _debug_events(logger_name: str = "bengal.server.dev_server"):
    from bengal.utils.observability.logger import _loggers

    if logger_name in _loggers:
        return _loggers[logger_name].get_events()
    return []


def test_palette_set_failure_emits_debug_breadcrumb() -> None:
    """A failure while setting the active palette must be logged, not swallowed."""
    from bengal.utils.observability.logger import LogLevel, configure_logging, reset_loggers

    reset_loggers()
    configure_logging(level=LogLevel.DEBUG)

    # Build a bare DevServer instance without running its heavy __init__.
    server = DevServer.__new__(DevServer)
    site = Mock()

    def boom(*args, **kwargs):
        raise RuntimeError("synthetic config failure")

    site.config.get = boom
    server.site = site

    # Must not raise -- the swallow keeps the dev server alive.
    server._set_active_palette()

    messages = [e.message for e in _debug_events()]
    assert "rebuilding_page_palette_failed" in messages

    reset_loggers()
