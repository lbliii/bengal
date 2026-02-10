"""Contracts for effect tracer persistence across build restarts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bengal.cache.paths import BengalPaths
from bengal.effects.effect import Effect
from bengal.effects.render_integration import BuildEffectTracer
from bengal.effects.tracer import EffectTracer
from bengal.orchestration.incremental.cache_manager import CacheManager


def _make_site(tmp_path: Path) -> SimpleNamespace:
    root_path = tmp_path / "site"
    root_path.mkdir(parents=True, exist_ok=True)
    output_dir = root_path / "public"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = BengalPaths(root_path)
    paths.ensure_dirs()

    return SimpleNamespace(
        root_path=root_path,
        output_dir=output_dir,
        paths=paths,
        theme=None,
        config={},
        config_hash="test_config_hash",
        assets=[],
    )


def test_effect_tracer_persists_and_reloads_with_same_invalidation_set(tmp_path: Path) -> None:
    site = _make_site(tmp_path)
    BuildEffectTracer.reset()

    manager_one = CacheManager(site)
    manager_one.initialize(enabled=True)
    tracer_one = manager_one.effect_tracer
    assert tracer_one is not None

    source_path = site.root_path / "content" / "page.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("# Page", encoding="utf-8")
    output_path = site.output_dir / "page" / "index.html"

    tracer_one.record(
        Effect.for_page_render(
            source_path=source_path,
            output_path=output_path,
            template_name="page.html",
            template_includes=frozenset(),
            page_href="/page/",
        )
    )
    expected_outputs = tracer_one.outputs_needing_rebuild({source_path})
    manager_one.save(pages_built=[], assets_processed=[])

    effects_path = site.paths.state_dir / "effects.json"
    assert effects_path.exists()

    manager_two = CacheManager(_make_site(tmp_path))
    manager_two.initialize(enabled=True)
    tracer_two = manager_two.effect_tracer
    assert tracer_two is not None
    actual_outputs = tracer_two.outputs_needing_rebuild({source_path})

    assert actual_outputs == expected_outputs
    assert BuildEffectTracer.get_instance().tracer is tracer_two


def test_effect_tracer_flushes_pending_fingerprints_on_save(tmp_path: Path) -> None:
    site = _make_site(tmp_path)
    BuildEffectTracer.reset()

    manager = CacheManager(site)
    manager.initialize(enabled=True)
    tracer = manager.effect_tracer
    assert tracer is not None

    tracked_file = site.root_path / "content" / "tracked.md"
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_file.write_text("tracked", encoding="utf-8")

    tracer.update_fingerprint(tracked_file)
    manager.save(pages_built=[], assets_processed=[])

    loaded_tracer = EffectTracer.load(site.paths.state_dir / "effects.json")
    assert str(tracked_file) in loaded_tracer.to_dict().get("fingerprints", {})
    assert not loaded_tracer.is_changed(tracked_file)
