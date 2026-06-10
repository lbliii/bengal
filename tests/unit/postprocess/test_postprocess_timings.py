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
            "generate_rss": False,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)

    orchestrator.run(parallel=False, build_context=ctx, incremental=True)

    assert "special pages" in stats.postprocess_task_timings_ms


def test_postprocess_sequential_failure_emits_failed_line(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
            "generate_rss": False,
            "content_signals": {"enabled": False},
        },
    )
    orchestrator = PostprocessOrchestrator(site)
    emitted: list[tuple[str, str, float]] = []
    monkeypatch.setattr("bengal.orchestration.postprocess._emit_task_started", lambda _name: None)
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_task_finished",
        lambda name, duration: emitted.append(("finished", name, duration)),
    )
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_task_failed",
        lambda name, duration: emitted.append(("failed", name, duration)),
    )
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_postprocess_line", lambda _msg: None
    )
    monkeypatch.setattr(
        orchestrator,
        "_generate_special_pages",
        lambda _ctx=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    orchestrator.run(parallel=False, incremental=True)

    assert [(kind, name) for kind, name, _duration in emitted] == [("failed", "special pages")]


def test_postprocess_records_parallel_task_timings(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": True,
            "generate_rss": False,
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


def test_postprocess_parallel_failure_emits_failed_line(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": True,
            "generate_rss": False,
            "content_signals": {"enabled": False},
        },
    )
    orchestrator = PostprocessOrchestrator(site)
    emitted: list[tuple[str, str, float]] = []
    monkeypatch.setattr("bengal.orchestration.postprocess._emit_task_started", lambda _name: None)
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_task_finished",
        lambda name, duration: emitted.append(("finished", name, duration)),
    )
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_task_failed",
        lambda name, duration: emitted.append(("failed", name, duration)),
    )
    monkeypatch.setattr(
        "bengal.orchestration.postprocess._emit_postprocess_line", lambda _msg: None
    )
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)
    monkeypatch.setattr(
        orchestrator,
        "_generate_sitemap",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    orchestrator.run(parallel=True, incremental=True)

    emitted_kinds = {(kind, name) for kind, name, _duration in emitted}
    assert ("finished", "special pages") in emitted_kinds
    assert ("failed", "sitemap") in emitted_kinds
    assert ("finished", "sitemap") not in emitted_kinds


def test_postprocess_runs_rss_on_incremental(monkeypatch) -> None:
    """RSS regenerates on incremental builds (like sitemap), not just full builds.

    This locks in the artifact-repair / warm-build feed-freshness fix: previously
    RSS was gated behind ``if not incremental`` and was skipped on every incremental
    build, leaving feeds stale and un-repaired.
    """
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
            "generate_rss": True,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    ran: list[str] = []
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)
    monkeypatch.setattr(orchestrator, "_generate_rss", lambda: ran.append("rss"))

    orchestrator.run(parallel=False, build_context=ctx, incremental=True)

    assert ran == ["rss"], "RSS task should run on an incremental build"
    assert "rss" in stats.postprocess_task_timings_ms


def test_postprocess_skips_rss_when_disabled_on_incremental(monkeypatch) -> None:
    """generate_rss=False must keep RSS off even with the always-on-incremental rule."""
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
            "generate_rss": False,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    ran: list[str] = []
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)
    monkeypatch.setattr(orchestrator, "_generate_rss", lambda: ran.append("rss"))

    orchestrator.run(parallel=False, build_context=ctx, incremental=True)

    assert ran == []
    assert "rss" not in stats.postprocess_task_timings_ms


def test_postprocess_rss_excluded_by_serve_ready_allowlist(monkeypatch) -> None:
    """Serve-ready builds restrict tasks via enabled_task_names; RSS stays off there."""
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
            "generate_rss": True,
            "content_signals": {"enabled": False},
        },
    )
    stats = BuildStats()
    ctx = BuildContext(stats=stats)
    orchestrator = PostprocessOrchestrator(site)
    ran: list[str] = []
    monkeypatch.setattr(orchestrator, "_generate_special_pages", lambda _ctx=None: None)
    monkeypatch.setattr(orchestrator, "_generate_rss", lambda: ran.append("rss"))

    orchestrator.run(
        parallel=False,
        build_context=ctx,
        incremental=True,
        enabled_task_names={"special pages"},
    )

    assert ran == []
