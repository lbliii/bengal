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


def test_postprocess_sequential_failure_emits_failed_line(monkeypatch) -> None:
    site = SimpleNamespace(
        config={
            "output_formats": {"enabled": False},
            "generate_sitemap": False,
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
