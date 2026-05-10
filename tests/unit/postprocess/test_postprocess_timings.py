from __future__ import annotations

from types import SimpleNamespace

from bengal.orchestration.build_context import BuildContext
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.stats import BuildStats


def test_postprocess_records_sequential_task_timings(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)

    orchestrator.run(parallel=False, build_context=ctx, incremental=True)

    assert "special pages" in stats.postprocess_task_timings_ms


def test_postprocess_records_parallel_task_timings(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": True,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)
    monkeypatch.setattr(orchestrator, "_generate_sitemap", lambda: None)

    orchestrator.run(parallel=True, build_context=ctx, incremental=True)

    assert set(stats.postprocess_task_timings_ms) == {"special pages", "sitemap"}
