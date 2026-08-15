"""Index-first expand path for provenance invalidation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.build.contracts import DependencyIndexEntry, DependencyReadIndex
from bengal.build.provenance.invalidation import expand_forced_changed
from bengal.build.provenance.lookups import (
    FALLBACK_INDEX_INCOMPLETE,
    FALLBACK_TEMPLATE_DEPS_MISSING,
    consult_dependency_index,
    dependency_key_candidates,
)
from bengal.cache import BuildCache
from bengal.utils.observability.logger import reset_loggers


def _index(*entries: tuple[str, str, str]) -> DependencyReadIndex:
    """Build a read index from ``(kind, key, page)`` triples."""
    return DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind=kind,
                dependency_key=key,
                page_keys=(page,),
                invalidation_reason=f"{kind}_dependency_changed",
                producer="provenance",
            )
            for kind, key, page in entries
        ]
    )


def test_dependency_key_candidates_include_content_and_generated_relatives(
    tmp_path: Path,
) -> None:
    cache = BuildCache(site_root=tmp_path)
    track_item = tmp_path / "content" / "guides" / "step1.md"
    generated = tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md"
    track_item.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    track_item.write_text("# Step\n")
    generated.write_text("# Python\n")

    track_keys = dependency_key_candidates(cache, track_item)
    assert "guides/step1.md" in track_keys
    assert "content/guides/step1.md" in track_keys

    generated_keys = dependency_key_candidates(cache, generated)
    assert "tags/python" in generated_keys


def test_consult_dependency_index_hits_all_five_kinds(tmp_path: Path) -> None:
    cache = BuildCache(site_root=tmp_path)
    generated = tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md"
    track_item = tmp_path / "content" / "guides" / "step1.md"
    asset = tmp_path / "assets" / "css" / "style.css"
    template = tmp_path / "templates" / "page.html"
    data_file = tmp_path / "data" / "team.yaml"
    for path in (generated, track_item, asset, template, data_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n")

    index = _index(
        ("generated", "tags/python", "content/tags/python.md"),
        ("track", "guides/step1.md", "content/tracks/intro.md"),
        ("asset", "assets/css/style.css", "content/about.md"),
        ("template", "page.html", "content/about.md"),
        ("data", "data/team.yaml", "content/about.md"),
    )

    pages_by_kind, resolved = consult_dependency_index(
        cache,
        (generated, track_item, asset, template, data_file),
        index,
    )

    assert set(pages_by_kind) == {"generated", "track", "asset", "template", "data"}
    assert pages_by_kind["generated"] == {Path("content/tags/python.md")}
    assert pages_by_kind["track"] == {Path("content/tracks/intro.md")}
    assert pages_by_kind["asset"] == {Path("content/about.md")}
    assert ("generated", "tags/python") in resolved
    assert ("track", "guides/step1.md") in resolved
    assert ("asset", "assets/css/style.css") in resolved


def test_expand_consults_index_before_scans_for_all_kinds(tmp_path: Path, monkeypatch) -> None:
    """Forced paths + index hits expand pages without running fallback scans."""
    generated = tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md"
    track_item = tmp_path / "content" / "guides" / "step1.md"
    asset = tmp_path / "assets" / "css" / "style.css"
    template = tmp_path / "templates" / "page.html"
    data_file = tmp_path / "data" / "team.yaml"
    for path in (generated, track_item, asset, template, data_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n")

    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    index = _index(
        ("generated", "tags/python", "content/tags/python.md"),
        ("track", "guides/step1.md", "content/tracks/intro.md"),
        ("asset", "assets/css/style.css", "content/about.md"),
        ("template", "page.html", "content/docs.md"),
        ("data", "data/team.yaml", "content/team.md"),
    )

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_data_files", lambda *_a, **_k: set())
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: set())
    monkeypatch.setattr(
        inv,
        "get_pages_for_data_file",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("data scan ran")),
    )

    expanded, reasons = expand_forced_changed(
        {generated, track_item, asset, template, data_file},
        cache,
        site,
        [],
        index,
    )

    assert Path("content/tags/python.md") in expanded
    assert Path("content/tracks/intro.md") in expanded
    assert Path("content/about.md") in expanded
    assert Path("content/docs.md") in expanded
    assert Path("content/team.md") in expanded
    assert reasons["content/tags/python.md"] == ["generated_changed:index.md"]
    assert reasons["content/tracks/intro.md"] == ["track_changed:step1.md"]
    assert reasons["content/about.md"] == ["asset_changed:style.css"]
    assert reasons["content/docs.md"] == ["template_changed:page.html"]
    assert reasons["content/team.md"] == ["data_file:team.yaml"]


def test_expand_skips_data_page_scan_when_index_hits(tmp_path: Path, monkeypatch) -> None:
    data_file = tmp_path / "data" / "team.yaml"
    data_file.parent.mkdir()
    data_file.write_text("team: docs\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    index = _index(("data", "data/team.yaml", "content/about.md"))

    from bengal.build.provenance import invalidation as inv

    scan_calls: list[str] = []

    def _detect(cache_: object, site_: object) -> set[Path]:
        scan_calls.append("detect")
        return {data_file}

    def _pages(*_a: object, **_k: object) -> set[Path]:
        scan_calls.append("scan")
        raise AssertionError("data page-finding scan should be skipped on index hit")

    monkeypatch.setattr(inv, "detect_changed_data_files", _detect)
    monkeypatch.setattr(inv, "get_pages_for_data_file", _pages)
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: set())

    expanded, reasons = expand_forced_changed({data_file}, cache, site, [], index)

    assert expanded >= {data_file, Path("content/about.md")}
    assert reasons["content/about.md"] == ["data_file:team.yaml"]
    assert scan_calls == ["detect"]


def test_expand_skips_template_fallback_scan_when_index_hits(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "templates" / "page.html"
    template.parent.mkdir()
    template.write_text("{{ page.title }}\n")
    cache = BuildCache(site_root=tmp_path)
    cache.get_pages_for_template = lambda _name: (_ for _ in ()).throw(
        AssertionError("template cache scan should be skipped on index hit")
    )
    site = SimpleNamespace(root_path=tmp_path)
    pages = [
        SimpleNamespace(source_path=Path("content/about.md")),
        SimpleNamespace(source_path=Path("content/other.md")),
    ]
    index = _index(("template", "page.html", "content/about.md"))

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_data_files", lambda *_a, **_k: set())
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: {template})
    monkeypatch.setattr(inv, "iter_template_files", lambda _site: (template,))
    monkeypatch.setattr(inv, "resolve_template_dirs", lambda _site: [template.parent])

    expanded, reasons = expand_forced_changed({template}, cache, site, pages, index)

    assert Path("content/about.md") in expanded
    assert Path("content/other.md") not in expanded
    assert reasons["content/about.md"] == ["template_changed:page.html"]


def test_expand_keeps_data_scan_when_index_misses(tmp_path: Path, monkeypatch) -> None:
    from bengal.effects.render_integration import BuildEffectTracer

    BuildEffectTracer.reset()
    data_file = tmp_path / "data" / "team.yaml"
    content_file = tmp_path / "content" / "about.md"
    data_file.parent.mkdir()
    content_file.parent.mkdir()
    data_file.write_text("team: docs\n")
    content_file.write_text("# About\n")
    cache = BuildCache(site_root=tmp_path)
    cache.add_dependency(content_file, data_file)
    site = SimpleNamespace(root_path=tmp_path)

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: set())

    expanded, reasons = expand_forced_changed(set(), cache, site, [], DependencyReadIndex())

    assert Path("content/about.md") in expanded
    assert reasons["content/about.md"] == ["data_file:team.yaml"]


def test_expand_keeps_template_full_rebuild_when_index_misses(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "templates" / "page.html"
    template.parent.mkdir()
    template.write_text("{{ page.title }}\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    pages = [
        SimpleNamespace(source_path=Path("content/about.md")),
        SimpleNamespace(source_path=Path("content/other.md")),
    ]

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_data_files", lambda *_a, **_k: set())
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: {template})
    monkeypatch.setattr(inv, "iter_template_files", lambda _site: (template,))
    monkeypatch.setattr(inv, "resolve_template_dirs", lambda _site: [template.parent])

    expanded, reasons = expand_forced_changed(set(), cache, site, pages, DependencyReadIndex())

    assert Path("content/about.md") in expanded
    assert Path("content/other.md") in expanded
    assert "template_changed:page.html" in reasons["content/about.md"]


def test_expand_generated_miss_does_not_invent_a_scan(tmp_path: Path, monkeypatch) -> None:
    generated = tmp_path / ".bengal" / "generated" / "tags" / "python" / "index.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("# Python\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_data_files", lambda *_a, **_k: set())
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: set())

    expanded, reasons = expand_forced_changed({generated}, cache, site, [], DependencyReadIndex())

    assert expanded == {generated}
    assert reasons == {}


def _info_fallback_reasons() -> list[str]:
    """Collect stable ``reason`` tokens from live-filter INFO logs."""
    from bengal.utils.observability.logger import _loggers

    reasons: list[str] = []
    for name in (
        "bengal.build.provenance.lookups",
        "bengal.build.provenance.invalidation",
    ):
        logger = _loggers.get(name)
        if logger is None:
            continue
        for event in logger.get_events():
            if event.level != "INFO":
                continue
            reason = event.context.get("reason")
            if isinstance(reason, str):
                reasons.append(reason)
    return reasons


def test_data_scan_fallback_logs_index_incomplete(tmp_path: Path, monkeypatch) -> None:
    """Index miss on a data file logs ``index_incomplete`` before the scan."""
    from bengal.effects.render_integration import BuildEffectTracer

    reset_loggers()
    BuildEffectTracer.reset()
    data_file = tmp_path / "data" / "team.yaml"
    content_file = tmp_path / "content" / "about.md"
    data_file.parent.mkdir()
    content_file.parent.mkdir()
    data_file.write_text("team: docs\n")
    content_file.write_text("# About\n")
    cache = BuildCache(site_root=tmp_path)
    cache.add_dependency(content_file, data_file)
    site = SimpleNamespace(root_path=tmp_path)

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: set())

    try:
        expanded, reasons = expand_forced_changed(set(), cache, site, [], DependencyReadIndex())

        assert Path("content/about.md") in expanded
        assert reasons["content/about.md"] == ["data_file:team.yaml"]
        assert FALLBACK_INDEX_INCOMPLETE in _info_fallback_reasons()
    finally:
        reset_loggers()


def test_template_full_rebuild_fallback_logs_template_deps_missing(
    tmp_path: Path, monkeypatch
) -> None:
    """Missing template dependency data logs ``template_deps_missing``."""
    reset_loggers()
    template = tmp_path / "templates" / "page.html"
    template.parent.mkdir()
    template.write_text("{{ page.title }}\n")
    cache = BuildCache(site_root=tmp_path)
    site = SimpleNamespace(root_path=tmp_path)
    pages = [
        SimpleNamespace(source_path=Path("content/about.md")),
        SimpleNamespace(source_path=Path("content/other.md")),
    ]

    from bengal.build.provenance import invalidation as inv

    monkeypatch.setattr(inv, "detect_changed_data_files", lambda *_a, **_k: set())
    monkeypatch.setattr(inv, "detect_changed_templates", lambda *_a, **_k: {template})
    monkeypatch.setattr(inv, "iter_template_files", lambda _site: (template,))
    monkeypatch.setattr(inv, "resolve_template_dirs", lambda _site: [template.parent])

    try:
        expanded, reasons = expand_forced_changed(set(), cache, site, pages, DependencyReadIndex())

        assert Path("content/about.md") in expanded
        assert Path("content/other.md") in expanded
        assert "template_changed:page.html" in reasons["content/about.md"]
        assert FALLBACK_TEMPLATE_DEPS_MISSING in _info_fallback_reasons()
    finally:
        reset_loggers()
