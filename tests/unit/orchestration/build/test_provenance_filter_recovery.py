"""Unit tests for provenance filter recovery paths."""

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bengal.build.provenance.filter import ProvenanceFilterResult
from bengal.orchestration.build.provenance_filter import phase_incremental_filter_provenance


def _make_page(source_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        source_path=source_path,
        metadata={},
        tags=[],
        section=None,
        output_path=None,
    )


def _make_orchestrator(tmp_path: Path, pages: list[SimpleNamespace]) -> SimpleNamespace:
    output_dir = tmp_path / "public"
    (output_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (output_dir / "assets" / "css" / "style.css").write_text("body {}", encoding="utf-8")

    site = SimpleNamespace(
        root_path=tmp_path,
        output_dir=output_dir,
        pages=pages,
        assets=[],
        sections=[],
        cascade={},
        config={},
    )

    logger = MagicMock()
    logger.phase.return_value = nullcontext()
    stats = SimpleNamespace(
        skipped=False,
        build_time_ms=0.0,
        cache_hits=0,
        cache_misses=0,
        time_saved_ms=0.0,
        incremental_decision=None,
    )

    return SimpleNamespace(site=site, logger=logger, stats=stats)


def _make_cache_stub() -> SimpleNamespace:
    taxonomy_index = SimpleNamespace(page_tags={})
    return SimpleNamespace(
        file_fingerprints={},
        dependencies={},
        reverse_dependencies={},
        output_sources={},
        taxonomy_index=taxonomy_index,
    )


def test_recovery_success_uses_recovered_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    page = _make_page(tmp_path / "content" / "about.md")
    page.source_path.parent.mkdir(parents=True, exist_ok=True)
    page.source_path.write_text("# About", encoding="utf-8")
    orchestrator = _make_orchestrator(tmp_path, pages=[])
    cache = _make_cache_stub()
    cli = MagicMock()

    from bengal.orchestration.build import initialization

    def _recover_pages(*args, **kwargs) -> None:
        _ = args, kwargs
        orchestrator.site.pages = [page]

    monkeypatch.setattr(initialization, "phase_discovery", _recover_pages)

    created_filters: list[object] = []

    class _FakeProvenanceCache:
        def __init__(self, cache_dir: Path) -> None:
            self.cache_dir = cache_dir
            self._index = {"dummy_key": "dummy_hash"}
            self._loaded = False

        def _ensure_loaded(self) -> None:
            self._loaded = True

    class _FakeProvenanceFilter:
        def __init__(self, site: object, cache_obj: _FakeProvenanceCache) -> None:
            _ = site
            self.cache = cache_obj
            self._asset_hashes = {}
            created_filters.append(self)

        def _get_page_key(self, page_obj: SimpleNamespace) -> str:
            _ = page_obj
            return "dummy_key"

        def _compute_provenance(self, page_obj: SimpleNamespace) -> SimpleNamespace:
            _ = page_obj
            return SimpleNamespace(combined_hash="dummy_hash")

        def filter(
            self,
            pages: list[SimpleNamespace],
            assets: list[object],
            incremental: bool = True,
            forced_changed: set[Path] | None = None,
            trust_unchanged: bool = False,
        ) -> ProvenanceFilterResult:
            _ = assets, incremental, forced_changed, trust_unchanged
            return ProvenanceFilterResult(
                pages_to_build=list(pages),
                assets_to_process=[],
                pages_skipped=[],
                total_pages=len(pages),
                cache_hits=0,
                cache_misses=len(pages),
                changed_page_paths={p.source_path for p in pages},
            )

    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceCache", _FakeProvenanceCache
    )
    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceFilter", _FakeProvenanceFilter
    )

    result = phase_incremental_filter_provenance(
        orchestrator=orchestrator,
        cli=cli,
        cache=cache,
        incremental=True,
        verbose=False,
        build_start=0.0,
    )

    assert result is not None
    assert [p.source_path for p in result.pages_to_build] == [page.source_path]
    cli.success.assert_called()
    assert created_filters


def test_recovery_failure_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path, pages=[])
    cache = _make_cache_stub()
    cli = MagicMock()

    from bengal.orchestration.build import initialization

    def _no_recovery(*args, **kwargs) -> None:
        _ = args, kwargs
        orchestrator.site.pages = []

    monkeypatch.setattr(initialization, "phase_discovery", _no_recovery)

    class _FakeProvenanceCache:
        def __init__(self, cache_dir: Path) -> None:
            self.cache_dir = cache_dir
            self._index = {}
            self._loaded = False

        def _ensure_loaded(self) -> None:
            self._loaded = True

    class _FakeProvenanceFilter:
        def __init__(self, site: object, cache_obj: _FakeProvenanceCache) -> None:
            _ = site, cache_obj
            self._asset_hashes = {}

        def filter(self, *args, **kwargs) -> ProvenanceFilterResult:
            raise AssertionError("filter() should not be called when recovery fails")

    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceCache", _FakeProvenanceCache
    )
    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceFilter", _FakeProvenanceFilter
    )

    result = phase_incremental_filter_provenance(
        orchestrator=orchestrator,
        cli=cli,
        cache=cache,
        incremental=True,
        verbose=False,
        build_start=0.0,
    )

    assert result is None
    cli.error.assert_called()


def test_recovery_mismatch_clears_provenance_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    page = _make_page(tmp_path / "content" / "about.md")
    page.source_path.parent.mkdir(parents=True, exist_ok=True)
    page.source_path.write_text("# About", encoding="utf-8")
    orchestrator = _make_orchestrator(tmp_path, pages=[])
    cache = _make_cache_stub()
    cli = MagicMock()

    from bengal.orchestration.build import initialization

    def _recover_pages(*args, **kwargs) -> None:
        _ = args, kwargs
        orchestrator.site.pages = [page]

    monkeypatch.setattr(initialization, "phase_discovery", _recover_pages)

    cache_instances: list[object] = []
    filter_instances: list[object] = []

    class _FakeProvenanceCache:
        def __init__(self, cache_dir: Path) -> None:
            self.cache_dir = cache_dir
            self._index = {"dummy_key": "old_hash"}
            self._loaded = False
            cache_instances.append(self)

        def _ensure_loaded(self) -> None:
            self._loaded = True

    class _FakeProvenanceFilter:
        def __init__(self, site: object, cache_obj: _FakeProvenanceCache) -> None:
            _ = site, cache_obj
            self._asset_hashes = {"old": "value"}
            filter_instances.append(self)

        def _get_page_key(self, page_obj: SimpleNamespace) -> str:
            _ = page_obj
            return "dummy_key"

        def _compute_provenance(self, page_obj: SimpleNamespace) -> SimpleNamespace:
            _ = page_obj
            return SimpleNamespace(combined_hash="new_hash")

        def filter(
            self,
            pages: list[SimpleNamespace],
            assets: list[object],
            incremental: bool = True,
            forced_changed: set[Path] | None = None,
            trust_unchanged: bool = False,
        ) -> ProvenanceFilterResult:
            _ = assets, incremental, forced_changed, trust_unchanged
            return ProvenanceFilterResult(
                pages_to_build=list(pages),
                assets_to_process=[],
                pages_skipped=[],
                total_pages=len(pages),
                cache_hits=0,
                cache_misses=len(pages),
                changed_page_paths={p.source_path for p in pages},
            )

    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceCache", _FakeProvenanceCache
    )
    monkeypatch.setattr(
        "bengal.orchestration.build.provenance_filter.ProvenanceFilter", _FakeProvenanceFilter
    )

    result = phase_incremental_filter_provenance(
        orchestrator=orchestrator,
        cli=cli,
        cache=cache,
        incremental=True,
        verbose=False,
        build_start=0.0,
    )

    assert result is not None
    assert cache_instances
    assert filter_instances
    assert cache_instances[0]._index == {}
    assert cache_instances[0]._loaded is False
    assert filter_instances[0]._asset_hashes == {}
