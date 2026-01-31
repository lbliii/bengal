"""
Unit tests for EffectTracer and SnapshotEffectBuilder.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)
"""

from dataclasses import dataclass
from pathlib import Path

from bengal.effects import Effect, EffectTracer, SnapshotEffectBuilder


class TestEffectTracer:
    """Tests for EffectTracer class."""

    def test_record_effect(self) -> None:
        """Tracer records effects."""
        tracer = EffectTracer()
        effect = Effect(
            outputs=frozenset({Path("a.html")}),
            depends_on=frozenset({Path("a.md")}),
            invalidates=frozenset({"page:a"}),
        )
        tracer.record(effect)
        assert len(tracer.effects) == 1
        assert tracer.effects[0] == effect

    def test_record_batch(self) -> None:
        """Tracer records batch of effects."""
        tracer = EffectTracer()
        effects = [
            Effect(outputs=frozenset({Path("a.html")})),
            Effect(outputs=frozenset({Path("b.html")})),
        ]
        tracer.record_batch(effects)
        assert len(tracer.effects) == 2

    def test_invalidated_by(self) -> None:
        """Tracer computes invalidations for changed files."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                depends_on=frozenset({Path("content/page.md")}),
                invalidates=frozenset({"page:/page/"}),
            )
        )

        invalidated = tracer.invalidated_by({Path("content/page.md")})
        assert "page:/page/" in invalidated

    def test_outputs_needing_rebuild(self) -> None:
        """Tracer computes outputs needing rebuild."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/page.html")}),
                depends_on=frozenset({Path("content/page.md")}),
            )
        )

        outputs = tracer.outputs_needing_rebuild({Path("content/page.md")})
        assert Path("public/page.html") in outputs

    def test_transitive_outputs(self) -> None:
        """Tracer computes transitive outputs."""
        tracer = EffectTracer()
        # Page depends on template
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/page.html")}),
                depends_on=frozenset({Path("templates/page.html")}),
            )
        )
        # Template depends on base
        tracer.record(
            Effect(
                outputs=frozenset({Path("templates/page.html")}),
                depends_on=frozenset({Path("templates/base.html")}),
            )
        )

        # Changing base should rebuild page.html transitively
        outputs = tracer.outputs_needing_rebuild({Path("templates/base.html")})
        assert Path("templates/page.html") in outputs
        assert Path("public/page.html") in outputs

    def test_get_dependencies_for_output(self) -> None:
        """Tracer retrieves dependencies for specific output."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/page.html")}),
                depends_on=frozenset({Path("content/page.md"), "page.html"}),
            )
        )

        deps = tracer.get_dependencies_for_output(Path("public/page.html"))
        assert Path("content/page.md") in deps
        assert "page.html" in deps

    def test_get_effects_for_cache_key(self) -> None:
        """Tracer retrieves effects by cache key."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                invalidates=frozenset({"page:/page/"}),
                operation="render_page",
            )
        )

        effects = tracer.get_effects_for_cache_key("page:/page/")
        assert len(effects) == 1
        assert effects[0].operation == "render_page"

    def test_clear(self) -> None:
        """Tracer clears all effects."""
        tracer = EffectTracer()
        tracer.record(Effect(outputs=frozenset({Path("a.html")})))
        tracer.clear()
        assert len(tracer.effects) == 0

    def test_get_statistics(self) -> None:
        """Tracer provides statistics."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                outputs=frozenset({Path("a.html")}),
                depends_on=frozenset({Path("a.md")}),
                invalidates=frozenset({"page:a"}),
                operation="render_page",
            )
        )

        stats = tracer.get_statistics()
        assert stats["total_effects"] == 1
        assert stats["unique_outputs"] == 1
        assert stats["by_operation"]["render_page"] == 1

    def test_to_dependency_graph(self) -> None:
        """Tracer exports dependency graph."""
        tracer = EffectTracer()
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/page.html")}),
                depends_on=frozenset({Path("content/page.md"), "page.html"}),
            )
        )

        graph = tracer.to_dependency_graph()
        assert "public/page.html" in graph
        deps = graph["public/page.html"]
        assert "content/page.md" in deps
        assert "page.html" in deps


class TestEffectTracerThreadSafety:
    """Thread-safety tests for EffectTracer."""

    def test_concurrent_record(self) -> None:
        """Tracer is thread-safe for concurrent recording."""
        import threading

        tracer = EffectTracer()
        errors: list[Exception] = []

        def record_effects() -> None:
            try:
                for i in range(100):
                    tracer.record(
                        Effect(
                            outputs=frozenset(
                                {Path(f"out_{threading.current_thread().name}_{i}.html")}
                            ),
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_effects) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tracer.effects) == 400

    def test_concurrent_read_write(self) -> None:
        """Tracer is thread-safe for concurrent read/write."""
        import threading

        tracer = EffectTracer()
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(100):
                    tracer.record(
                        Effect(
                            outputs=frozenset({Path(f"out_{i}.html")}),
                            depends_on=frozenset({Path(f"src_{i}.md")}),
                        )
                    )
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    _ = tracer.effects
                    _ = tracer.get_statistics()
            except Exception as e:
                errors.append(e)

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)

        writer_thread.start()
        reader_thread.start()

        writer_thread.join()
        reader_thread.join()

        assert len(errors) == 0


# Mock snapshot types for SnapshotEffectBuilder tests
@dataclass
class MockPageSnapshot:
    """Mock PageSnapshot for testing."""

    source_path: Path
    output_path: Path
    template_name: str
    href: str


@dataclass
class MockTemplateSnapshot:
    """Mock TemplateSnapshot for testing."""

    all_dependencies: frozenset[str]


@dataclass
class MockSiteSnapshot:
    """Mock SiteSnapshot for testing."""

    pages: list[MockPageSnapshot]
    templates: dict[str, MockTemplateSnapshot]


class TestSnapshotEffectBuilder:
    """Tests for SnapshotEffectBuilder class."""

    def test_build_effects_empty_snapshot(self) -> None:
        """Builder handles empty snapshot."""
        snapshot = MockSiteSnapshot(pages=[], templates={})
        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        assert len(tracer.effects) == 0

    def test_build_effects_single_page(self) -> None:
        """Builder creates effect for single page."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    output_path=Path("public/page/index.html"),
                    template_name="page.html",
                    href="/page/",
                )
            ],
            templates={},
        )

        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        assert len(tracer.effects) == 1
        effect = tracer.effects[0]
        assert Path("public/page/index.html") in effect.outputs
        assert Path("content/page.md") in effect.depends_on
        assert "page.html" in effect.depends_on
        assert "page:/page/" in effect.invalidates
        assert effect.operation == "render_page"

    def test_build_effects_multiple_pages(self) -> None:
        """Builder creates effects for multiple pages."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/a.md"),
                    output_path=Path("public/a/index.html"),
                    template_name="page.html",
                    href="/a/",
                ),
                MockPageSnapshot(
                    source_path=Path("content/b.md"),
                    output_path=Path("public/b/index.html"),
                    template_name="page.html",
                    href="/b/",
                ),
            ],
            templates={},
        )

        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        assert len(tracer.effects) == 2
        output_paths = {next(iter(e.outputs)) for e in tracer.effects}
        assert Path("public/a/index.html") in output_paths
        assert Path("public/b/index.html") in output_paths

    def test_build_effects_includes_template_dependencies(self) -> None:
        """Builder includes template dependencies in effects."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    output_path=Path("public/page/index.html"),
                    template_name="page.html",
                    href="/page/",
                )
            ],
            templates={
                "page.html": MockTemplateSnapshot(
                    all_dependencies=frozenset({"base.html", "partials/nav.html"})
                )
            },
        )

        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        effect = tracer.effects[0]
        assert "base.html" in effect.depends_on
        assert "partials/nav.html" in effect.depends_on

    def test_build_effects_missing_template_in_registry(self) -> None:
        """Builder handles page with template not in registry."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    output_path=Path("public/page/index.html"),
                    template_name="missing.html",
                    href="/page/",
                )
            ],
            templates={},  # Template not registered
        )

        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        # Should still create effect, just without template dependencies
        assert len(tracer.effects) == 1
        effect = tracer.effects[0]
        assert "missing.html" in effect.depends_on

    def test_from_snapshot_convenience_method(self) -> None:
        """from_snapshot class method works correctly."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    output_path=Path("public/page/index.html"),
                    template_name="page.html",
                    href="/page/",
                )
            ],
            templates={},
        )

        tracer = SnapshotEffectBuilder.from_snapshot(snapshot)  # type: ignore[arg-type]

        assert isinstance(tracer, EffectTracer)
        assert len(tracer.effects) == 1

    def test_builder_instance_method(self) -> None:
        """Builder instance build_effects method works."""
        snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    output_path=Path("public/page/index.html"),
                    template_name="page.html",
                    href="/page/",
                )
            ],
            templates={},
        )

        builder = SnapshotEffectBuilder(snapshot)  # type: ignore[arg-type]
        tracer = builder.build_effects()

        assert isinstance(tracer, EffectTracer)
        assert len(tracer.effects) == 1
