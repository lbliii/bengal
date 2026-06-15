"""
Atomic-write guards for three non-atomic writers (issue #471).

Three subsystems previously wrote files with a direct
``open(...)`` / ``write_text(...)`` and would leave a truncated or
partially written file behind on a SIGINT/crash/OOM mid-write:

- external-ref index cache  (``ExternalRefResolver._fetch``)
- performance ``latest.json`` (``PerformanceCollector.save``)
- versioning ``bengal.yaml`` (``_update_config_with_version``)

These tests pin each write through the crash-safe helpers in
``bengal.utils.io.atomic_write``. Each test wraps the *canonical* helper
(which always exists) with a spy and asserts the producer invokes it. A
regression to a direct ``open()``/``write_text()`` would bypass the helper
entirely, leaving ``calls`` empty and failing the target assertion (not an
import error).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

import bengal.utils.io.atomic_write as atomic_mod


def test_external_ref_cache_writes_through_atomic_helper(tmp_path, monkeypatch):
    """``ExternalRefResolver._fetch`` must cache via ``atomic_write_text``.

    Discriminating: a regression to ``cache_file.write_text(...)`` never calls
    the atomic helper, so ``calls`` stays empty.
    """
    from bengal.rendering.external_refs.resolver import IndexCache

    cache = IndexCache(cache_dir=tmp_path / "cache")
    cache_file = cache.cache_dir / "python.json"

    payload = {"entries": {"pathlib.Path": {"path": "/x"}}}

    calls: list[tuple[Path, str]] = []
    real = atomic_mod.atomic_write_text

    def spy(path, content, *args, **kwargs):
        calls.append((Path(path), content))
        return real(path, content, *args, **kwargs)

    monkeypatch.setattr(atomic_mod, "atomic_write_text", spy)

    # Stub the network so _fetch reaches its caching branch deterministically.
    fake_response = MagicMock()
    fake_response.status = 200
    fake_response.read.return_value = json.dumps(payload).encode("utf-8")
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_cm):
        result = cache._fetch("python", "https://example.com/xref.json", cache_file)

    assert result == payload
    cache_calls = [c for c in calls if c[0] == cache_file]
    assert len(cache_calls) == 1, "external-ref cache must write via atomic_write_text"
    written_content = cache_calls[0][1]
    assert json.loads(written_content) == payload
    assert cache_file.read_text(encoding="utf-8") == written_content


def test_performance_latest_json_writes_through_atomic_helper(tmp_path, monkeypatch):
    """``PerformanceCollector.save`` must write ``latest.json`` atomically.

    Discriminating: a regression to ``open(latest_file, "w")`` never calls the
    atomic helper, so ``calls`` stays empty.
    """
    from bengal.utils.observability.performance_collector import PerformanceCollector

    collector = PerformanceCollector(metrics_dir=tmp_path / "metrics")
    latest_file = collector.metrics_dir / "latest.json"

    calls: list[tuple[Path, str]] = []
    real = atomic_mod.atomic_write_text

    def spy(path, content, *args, **kwargs):
        calls.append((Path(path), content))
        return real(path, content, *args, **kwargs)

    monkeypatch.setattr(atomic_mod, "atomic_write_text", spy)

    stats = MagicMock()
    stats.to_dict.return_value = {"total_pages": 3, "build_time_ms": 1234.0}

    collector.save(stats)

    latest_calls = [c for c in calls if c[0] == latest_file]
    assert len(latest_calls) == 1, "latest.json must be written via atomic_write_text"
    written_content = latest_calls[0][1]
    data = json.loads(written_content)
    assert data["total_pages"] == 3
    assert latest_file.read_text(encoding="utf-8") == written_content


def test_version_config_writes_through_atomic_file(tmp_path, monkeypatch):
    """``_update_config_with_version`` must rewrite ``bengal.yaml`` atomically.

    Discriminating: a regression to ``open(config_file, "w")`` never
    instantiates the atomic ``AtomicFile``, so ``calls`` stays empty.
    """
    import bengal.cli.milo_commands.version as version_mod

    config_file = tmp_path / "bengal.yaml"
    config_file.write_text(
        yaml.dump({"site": {"title": "Demo"}}, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    dest_dir = tmp_path / "versions" / "v1"
    dest_dir.mkdir(parents=True, exist_ok=True)

    real_cls = atomic_mod.AtomicFile
    calls: list[Path] = []

    class SpyAtomicFile(real_cls):
        def __init__(self, path, *args, **kwargs):
            calls.append(Path(path))
            super().__init__(path, *args, **kwargs)

    monkeypatch.setattr(atomic_mod, "AtomicFile", SpyAtomicFile)

    cli = MagicMock()
    version_mod._update_config_with_version(
        root_path=tmp_path,
        version_id="v1",
        dest_dir=dest_dir,
        label="v1",
        cli=cli,
    )

    assert calls == [config_file], "bengal.yaml must be rewritten via AtomicFile"
    updated = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert updated["versioning"]["enabled"] is True
    assert updated["versioning"]["versions"][0]["id"] == "v1"
