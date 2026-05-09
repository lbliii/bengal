from __future__ import annotations

from types import SimpleNamespace

from bengal.orchestration.content import ContentOrchestrator


def test_library_javascript_bundle_inserts_statement_boundary(tmp_path) -> None:
    first = tmp_path / "first.js"
    second = tmp_path / "second.js"
    bundle = tmp_path / "bundle.js"
    first.write_text("window.first = true", encoding="utf-8")
    second.write_text("(function () { window.second = true })();", encoding="utf-8")

    orchestrator = ContentOrchestrator.__new__(ContentOrchestrator)
    orchestrator._write_library_asset_bundle(
        bundle,
        [
            SimpleNamespace(source_path=first),
            SimpleNamespace(source_path=second),
        ],
        "javascript",
    )

    output = bundle.read_text(encoding="utf-8")
    assert "\n;\n// second.js" in output
