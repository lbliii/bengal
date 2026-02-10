"""Unit tests for provenance filter recovery paths."""

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bengal.build.provenance.filter import ProvenanceFilterResult
from bengal.orchestration.build import provenance_filter as provenance_filter_module
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
    cache = SimpleNamespace(
        file_fingerprints={},
        dependencies={},
        reverse_dependencies={},
        output_sources={},
        taxonomy_index=taxonomy_index,
    )
    def _add_dependency(source: Path, dependency: Path) -> None:
        source_key = str(source)
        dep_key = str(dependency)
        deps = cache.dependencies.setdefault(source_key, set())
        deps.add(dep_key)
        reverse = cache.reverse_dependencies.setdefault(dep_key, set())
        reverse.add(source_key)

    cache.add_dependency = _add_dependency
    return cache


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


def test_detect_changed_data_files_skips_hash_when_stat_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_file = data_dir / "payload.json"
    data_file.write_text('{"ok": true}', encoding="utf-8")
    stat = data_file.stat()

    cache = _make_cache_stub()
    cache.file_fingerprints[str(data_file)] = {
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "hash": "unchanged",
    }
    site = SimpleNamespace(root_path=tmp_path)

    def _hash_should_not_run(path: Path) -> str:
        raise AssertionError(f"hash_file should not be called for unchanged file: {path}")

    monkeypatch.setattr(provenance_filter_module, "hash_file", _hash_should_not_run)

    changed = provenance_filter_module._detect_changed_data_files(cache, site)
    assert changed == set()


def test_detect_changed_templates_skips_hash_when_stat_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_file = templates_dir / "base.html"
    template_file.write_text("<html></html>", encoding="utf-8")
    stat = template_file.stat()

    cache = _make_cache_stub()
    cache.file_fingerprints[str(template_file)] = {
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "hash": "unchanged",
    }
    site = SimpleNamespace(root_path=tmp_path, theme_path=None)

    def _hash_should_not_run(path: Path) -> str:
        raise AssertionError(f"hash_file should not be called for unchanged template: {path}")

    monkeypatch.setattr(provenance_filter_module, "hash_file", _hash_should_not_run)

    changed = provenance_filter_module._detect_changed_templates(cache, site)
    assert changed == set()


def test_expand_forced_changed_uses_template_dependency_index(
    tmp_path: Path,
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    page_template = templates_dir / "page.html"
    list_template = templates_dir / "list.html"
    page_template.write_text("<main>{{ content }}</main>", encoding="utf-8")
    list_template.write_text("<ul>{{ content }}</ul>", encoding="utf-8")

    page_source = tmp_path / "content" / "page.md"
    list_source = tmp_path / "content" / "list.md"
    page_source.parent.mkdir(parents=True, exist_ok=True)
    page_source.write_text("# Page", encoding="utf-8")
    list_source.write_text("# List", encoding="utf-8")

    pages = [
        SimpleNamespace(source_path=page_source, metadata={"template": "page.html"}),
        SimpleNamespace(source_path=list_source, metadata={"template": "list.html"}),
    ]
    site = SimpleNamespace(root_path=tmp_path, theme_path=None)
    cache = _make_cache_stub()

    # Prime fingerprints, then mutate page.html so only that template is "changed".
    page_stat_before = page_template.stat()
    list_stat_before = list_template.stat()
    cache.file_fingerprints[str(page_template)] = {
        "mtime": page_stat_before.st_mtime,
        "size": page_stat_before.st_size,
        "hash": provenance_filter_module.hash_file(page_template),
    }
    cache.file_fingerprints[str(list_template)] = {
        "mtime": list_stat_before.st_mtime,
        "size": list_stat_before.st_size,
        "hash": provenance_filter_module.hash_file(list_template),
    }
    page_template.write_text("<main class='changed'>{{ content }}</main>", encoding="utf-8")

    expanded, reasons = provenance_filter_module._expand_forced_changed(
        forced_changed=set(),
        cache=cache,
        site=site,
        pages=pages,
    )

    assert page_source in expanded
    assert list_source not in expanded
    assert reasons[str(page_source)] == ["template:page.html"]


def test_get_pages_for_template_prefers_reverse_dependencies() -> None:
    class _NoItemsDict(dict):
        def items(self):  # pragma: no cover - executed on regression only
            raise AssertionError("forward dependency scan should not run")

    template_path = Path("/tmp/templates/page.html")
    page_path = Path("/tmp/content/page.md")
    cache = _make_cache_stub()
    cache.reverse_dependencies = {str(template_path): {str(page_path)}}
    cache.dependencies = _NoItemsDict()

    pages = provenance_filter_module._get_pages_for_template(cache, template_path)
    assert pages == {page_path}


def test_get_pages_for_data_file_prefers_reverse_dependencies() -> None:
    class _NoItemsDict(dict):
        def items(self):  # pragma: no cover - executed on regression only
            raise AssertionError("forward dependency scan should not run")

    data_path = Path("/tmp/data/products.yaml")
    page_path = Path("/tmp/content/catalog.md")
    cache = _make_cache_stub()
    cache.reverse_dependencies = {f"data:{data_path}": {str(page_path)}}
    cache.dependencies = _NoItemsDict()

    pages = provenance_filter_module._get_pages_for_data_file(cache, data_path)
    assert pages == {page_path}
