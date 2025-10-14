from __future__ import annotations

from types import SimpleNamespace

from bengal.orchestration.streaming import StreamingRenderOrchestrator


def test_streaming_suppresses_stdout_in_quiet_mode(tmp_path, capsys):
    site = SimpleNamespace(config={}, root_path=tmp_path, output_dir=tmp_path / "public")

    # Minimal pages list (empty is fine; focus is on emitted messages)
    orch = StreamingRenderOrchestrator(site)

    # No reporter, quiet=True -> should not print anything
    orch.process(pages=[], parallel=False, quiet=True)

    captured = capsys.readouterr()
    assert captured.out == ""
