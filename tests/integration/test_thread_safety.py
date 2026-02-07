"""
Thread-safety integration tests for key components under contention.

These tests verify that EffectTracer and BuildTaxonomyIndex behave correctly
when accessed concurrently from multiple threads, covering recording, querying,
persistence, and index updates.

Run with:
    pytest tests/integration/test_thread_safety.py -v -x

Run with GIL disabled (requires Python 3.14t):
    PYTHON_GIL=0 pytest tests/integration/test_thread_safety.py -v -x
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Event, Thread


class TestConcurrentEffectRecording:
    """Verify EffectTracer is safe under concurrent recording."""

    def test_concurrent_effect_recording(self) -> None:
        """8 threads x 100 effects each; total must be 800."""
        from bengal.effects.effect import Effect
        from bengal.effects.tracer import EffectTracer

        tracer = EffectTracer()

        def record_effects(thread_id: int) -> None:
            for i in range(100):
                effect = Effect.for_page_render(
                    source_path=Path(f"content/t{thread_id}/page{i}.md"),
                    output_path=Path(f"public/t{thread_id}/page{i}/index.html"),
                    template_name="default.html",
                    template_includes=frozenset(),
                    page_href=f"/t{thread_id}/page{i}/",
                )
                tracer.record(effect)

        threads = [Thread(target=record_effects, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        stats = tracer.get_statistics()
        assert stats["total_effects"] == 800, (
            f"Expected 800 effects (8 threads * 100), got {stats['total_effects']}"
        )

        # Indexes must also be consistent
        assert stats["unique_outputs"] == 800
        assert stats["by_operation"]["render_page"] == 800


class TestConcurrentTaxonomyUpdates:
    """Verify BuildTaxonomyIndex is safe under concurrent tag updates."""

    def test_concurrent_taxonomy_updates(self) -> None:
        """8 threads x 50 pages each; all 5 unique tag slugs must survive."""
        from bengal.cache.build_cache.taxonomy_index_mixin import BuildTaxonomyIndex

        index = BuildTaxonomyIndex()

        def update_tags(thread_id: int) -> None:
            for i in range(50):
                page = Path(f"content/page_{thread_id}_{i}.md")
                tags = {f"tag_{j}" for j in range(5)}
                index.update_page_tags(page, tags)

        threads = [Thread(target=update_tags, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # Verify consistency
        all_tags = index.get_all_tags()
        assert len(all_tags) == 5, f"Expected 5 unique tags, got {len(all_tags)}: {all_tags}"

        # Every page should be reachable via its tags
        for slug in all_tags:
            pages = index.get_pages_for_tag(slug)
            assert len(pages) == 400, (
                f"Tag '{slug}' should map to 400 pages (8*50), got {len(pages)}"
            )


class TestConcurrentRecordAndQuery:
    """Verify EffectTracer can be queried while recording (no deadlocks)."""

    def test_concurrent_record_and_query(self) -> None:
        """One thread records continuously while another queries; no crash or deadlock."""
        from bengal.effects.effect import Effect
        from bengal.effects.tracer import EffectTracer

        tracer = EffectTracer()
        stop_event = Event()
        errors: list[Exception] = []

        def record_loop() -> None:
            i = 0
            try:
                while not stop_event.is_set():
                    effect = Effect.for_page_render(
                        source_path=Path(f"content/loop/page{i}.md"),
                        output_path=Path(f"public/loop/page{i}/index.html"),
                        template_name="default.html",
                        template_includes=frozenset(),
                        page_href=f"/loop/page{i}/",
                    )
                    tracer.record(effect)
                    i += 1
            except Exception as exc:
                errors.append(exc)

        def query_loop() -> None:
            try:
                while not stop_event.is_set():
                    tracer.invalidated_by({Path("content/loop/page0.md")})
                    tracer.outputs_needing_rebuild({Path("content/loop/page0.md")})
                    tracer.get_statistics()
            except Exception as exc:
                errors.append(exc)

        recorder = Thread(target=record_loop)
        querier = Thread(target=query_loop)
        recorder.start()
        querier.start()

        time.sleep(0.5)  # Let them run under contention
        stop_event.set()

        recorder.join(timeout=10)
        querier.join(timeout=10)

        assert not errors, f"Concurrent record/query errors: {errors}"
        # At least some effects should have been recorded
        assert tracer.get_statistics()["total_effects"] > 0


class TestTracerPersistenceRoundtrip:
    """Verify EffectTracer save/load preserves all data."""

    def test_tracer_save_load_roundtrip(self, tmp_path: Path) -> None:
        """Record effects, save to disk, reload, and verify stats match."""
        from bengal.effects.effect import Effect
        from bengal.effects.tracer import EffectTracer

        tracer = EffectTracer()
        for i in range(10):
            tracer.record(
                Effect.for_page_render(
                    source_path=Path(f"content/page{i}.md"),
                    output_path=Path(f"public/page{i}/index.html"),
                    template_name="default.html",
                    template_includes=frozenset({"partials/nav.html"}),
                    page_href=f"/page{i}/",
                )
            )

        cache_path = tmp_path / "effects.json"
        tracer.save(cache_path)
        loaded = EffectTracer.load(cache_path)

        original_stats = tracer.get_statistics()
        loaded_stats = loaded.get_statistics()

        assert loaded_stats["total_effects"] == 10
        assert loaded_stats["total_effects"] == original_stats["total_effects"]
        assert loaded_stats["unique_outputs"] == original_stats["unique_outputs"]
        assert loaded_stats["by_operation"] == original_stats["by_operation"]

    def test_concurrent_save_does_not_corrupt(self, tmp_path: Path) -> None:
        """Multiple threads saving the same tracer should not produce corrupt files."""
        from bengal.effects.effect import Effect
        from bengal.effects.tracer import EffectTracer

        tracer = EffectTracer()
        for i in range(20):
            tracer.record(
                Effect.for_page_render(
                    source_path=Path(f"content/page{i}.md"),
                    output_path=Path(f"public/page{i}/index.html"),
                    template_name="default.html",
                    template_includes=frozenset(),
                    page_href=f"/page{i}/",
                )
            )

        errors: list[Exception] = []

        def save_worker(worker_id: int) -> None:
            try:
                path = tmp_path / f"effects_{worker_id}.json"
                tracer.save(path)
                # Verify the saved file can be loaded back
                loaded = EffectTracer.load(path)
                stats = loaded.get_statistics()
                assert stats["total_effects"] == 20
            except Exception as exc:
                errors.append(exc)

        threads = [Thread(target=save_worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Concurrent save errors: {errors}"
