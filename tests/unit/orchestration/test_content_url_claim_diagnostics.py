"""Diagnostics for URLRegistry claim failures in content output-path wiring.

Regression for issue #385 (Finding 9): ``ContentOrchestrator._set_output_paths``
used to swallow any ``url_registry.claim()`` failure with a bare ``pass`` and no
trace. Detection is not lost (URLCollisionValidator backstops post-hoc), so this
is purely an observability fix: the claim site must now emit a ``url_claim_failed``
debug breadcrumb while the build still completes.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.core.site import Site
from bengal.orchestration.content import ContentOrchestrator


@pytest.fixture
def discovered_site():
    """A minimal discovered site with at least one regular page."""
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        content_dir = root / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "post.md").write_text("---\ntitle: Post\n---\n# Post")

        site = Site(root_path=root, config={})
        orchestrator = ContentOrchestrator(site)
        orchestrator.discover()
        yield site, orchestrator


def _debug_events(logger_name: str = "bengal.orchestration.content"):
    from bengal.utils.observability.logger import _loggers

    if logger_name in _loggers:
        return _loggers[logger_name].get_events()
    return []


def test_claim_failure_emits_debug_breadcrumb(discovered_site) -> None:
    """A claim that raises must produce a url_claim_failed debug record."""
    from bengal.utils.observability.logger import LogLevel, configure_logging, reset_loggers

    site, orchestrator = discovered_site

    reset_loggers()
    configure_logging(level=LogLevel.DEBUG)

    # Force claim() to raise for every page.
    def boom(*args, **kwargs):
        raise RuntimeError("synthetic claim failure")

    site.url_registry.claim = boom  # type: ignore[method-assign]

    # Re-run output-path assignment: clear any output_path set during discovery.
    for page in site.pages:
        page.output_path = None

    # Must not raise -- the swallow keeps the build alive.
    orchestrator._set_output_paths()

    events = _debug_events()
    failed = [e for e in events if e.message == "url_claim_failed"]
    assert failed, "expected a url_claim_failed debug record"
    assert failed[0].context.get("owner") == "content"
    assert failed[0].context.get("error_type") == "RuntimeError"

    # Output paths are still assigned despite the claim failure.
    assert all(p.output_path is not None for p in site.pages)

    reset_loggers()
