"""Regression guard for the live cache-save path passing ``build_context``.

The orchestrator's ``_save_main_cache`` closure must call
``incremental.save_cache(..., build_context=ctx)`` so the persisted cache stays
consistent with the build it describes. A previous, dead ``phase_cache_save``
helper diverged by calling ``save_cache`` *without* ``build_context``; this test
exercises the real build path and asserts the live behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


def _make_tiny_site(tmp_path: Path) -> Path:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "bengal.toml").write_text(
        """
[site]
title = "Cache Save Context Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
""",
        encoding="utf-8",
    )
    content_dir = site_dir / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n\nHello.\n",
        encoding="utf-8",
    )
    return site_dir


def test_live_cache_save_passes_build_context(tmp_path: Path, monkeypatch) -> None:
    """The live build path saves the main cache WITH a non-None build_context."""
    site_dir = _make_tiny_site(tmp_path)
    site = Site.from_config(site_dir)

    real_save_cache = IncrementalOrchestrator.save_cache
    captured: list[dict] = []

    def _recording_save_cache(self, *args, **kwargs):
        captured.append(dict(kwargs))
        return real_save_cache(self, *args, **kwargs)

    monkeypatch.setattr(IncrementalOrchestrator, "save_cache", _recording_save_cache)

    site.build(BuildOptions(incremental=False))

    assert captured, "Expected incremental.save_cache to be called during the build"
    # The main-cache save is the call that carries build_context.
    context_calls = [c for c in captured if c.get("build_context") is not None]
    assert context_calls, (
        "Live cache save must pass a non-None build_context; "
        f"observed save_cache kwargs were: {captured}"
    )
