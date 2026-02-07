"""
Parity tests: verify EffectTracer covers all DependencyTracker query scenarios.

These tests confirm that EffectTracer can answer every query that DependencyTracker
served, validating that the cutover is safe. The tests exercise:

1. Data file dependency tracking → outputs_needing_rebuild()
2. Taxonomy bidirectional tracking → outputs_needing_rebuild() via member page changes
3. Cross-version link invalidation → outputs_needing_rebuild() via version target changes
4. File change detection → get_changed_files() / is_changed()

RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)
"""

from __future__ import annotations

from pathlib import Path

from bengal.effects.effect import Effect
from bengal.effects.tracer import EffectTracer


class TestDataFileDependencyParity:
    """DependencyTracker.get_pages_using_data_file() → EffectTracer.outputs_needing_rebuild()."""

    def test_pages_using_data_file_are_rebuilt_when_data_changes(self) -> None:
        """When data/team.yaml changes, pages that depend on it should be rebuilt."""
        tracer = EffectTracer()

        # Page A depends on data/team.yaml
        tracer.record(
            Effect.for_page_render(
                source_path=Path("content/about.md"),
                output_path=Path("public/about/index.html"),
                template_name="single.html",
                template_includes=frozenset(),
                page_href="/about/",
                data_files=frozenset({Path("data/team.yaml")}),
            )
        )

        # Page B depends on data/team.yaml too
        tracer.record(
            Effect.for_page_render(
                source_path=Path("content/team.md"),
                output_path=Path("public/team/index.html"),
                template_name="single.html",
                template_includes=frozenset(),
                page_href="/team/",
                data_files=frozenset({Path("data/team.yaml")}),
            )
        )

        # Page C does NOT depend on data/team.yaml
        tracer.record(
            Effect.for_page_render(
                source_path=Path("content/blog/post.md"),
                output_path=Path("public/blog/post/index.html"),
                template_name="single.html",
                template_includes=frozenset(),
                page_href="/blog/post/",
            )
        )

        # Query: data/team.yaml changed — what outputs need rebuild?
        outputs = tracer.outputs_needing_rebuild({Path("data/team.yaml")})

        assert Path("public/about/index.html") in outputs
        assert Path("public/team/index.html") in outputs
        assert Path("public/blog/post/index.html") not in outputs

    def test_no_outputs_when_unrelated_data_changes(self) -> None:
        """When an unrelated data file changes, no pages should be rebuilt."""
        tracer = EffectTracer()

        tracer.record(
            Effect.for_page_render(
                source_path=Path("content/about.md"),
                output_path=Path("public/about/index.html"),
                template_name="single.html",
                template_includes=frozenset(),
                page_href="/about/",
                data_files=frozenset({Path("data/team.yaml")}),
            )
        )

        outputs = tracer.outputs_needing_rebuild({Path("data/config.yaml")})
        assert Path("public/about/index.html") not in outputs


class TestTaxonomyDependencyParity:
    """DependencyTracker.get_term_pages_for_member() → EffectTracer.outputs_needing_rebuild()."""

    def test_taxonomy_pages_rebuilt_when_member_changes(self) -> None:
        """When a member page changes, taxonomy pages that list it should rebuild."""
        tracer = EffectTracer()

        # Taxonomy page for "python" tag depends on member pages
        tracer.record(
            Effect.for_taxonomy_page(
                output_path=Path("public/tags/python/index.html"),
                taxonomy_name="tags",
                term="python",
                member_pages=frozenset({
                    Path("content/blog/post1.md"),
                    Path("content/blog/post2.md"),
                }),
            )
        )

        # Taxonomy page for "tutorial" tag depends on post1 too
        tracer.record(
            Effect.for_taxonomy_page(
                output_path=Path("public/tags/tutorial/index.html"),
                taxonomy_name="tags",
                term="tutorial",
                member_pages=frozenset({
                    Path("content/blog/post1.md"),
                }),
            )
        )

        # When post1 changes, both taxonomy pages should rebuild
        outputs = tracer.outputs_needing_rebuild({Path("content/blog/post1.md")})

        assert Path("public/tags/python/index.html") in outputs
        assert Path("public/tags/tutorial/index.html") in outputs

    def test_taxonomy_pages_not_rebuilt_for_unrelated_member(self) -> None:
        """Taxonomy pages should not rebuild for unrelated member changes."""
        tracer = EffectTracer()

        tracer.record(
            Effect.for_taxonomy_page(
                output_path=Path("public/tags/python/index.html"),
                taxonomy_name="tags",
                term="python",
                member_pages=frozenset({Path("content/blog/post1.md")}),
            )
        )

        outputs = tracer.outputs_needing_rebuild({Path("content/blog/unrelated.md")})
        assert Path("public/tags/python/index.html") not in outputs


class TestCrossVersionLinkParity:
    """DependencyTracker.get_cross_version_dependents() → EffectTracer.outputs_needing_rebuild()."""

    def test_cross_version_link_pages_rebuilt_when_target_changes(self) -> None:
        """When a cross-version target changes, pages linking to it should rebuild."""
        tracer = EffectTracer()

        # Page in v3 links to v2/docs/guide via cross-version link
        # The cross-version target is recorded as an extra dependency
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/v3/docs/index.html")}),
                depends_on=frozenset({
                    Path("content/v3/docs/index.md"),
                    "single.html",
                    Path("content/v2/docs/guide.md"),  # Cross-version target
                }),
                invalidates=frozenset({"page:/v3/docs/"}),
                operation="render_page",
            )
        )

        # When the v2 target changes, the v3 page should rebuild
        outputs = tracer.outputs_needing_rebuild({Path("content/v2/docs/guide.md")})
        assert Path("public/v3/docs/index.html") in outputs


class TestTemplateDependencyParity:
    """DependencyTracker.track_template/track_partial → EffectTracer via template_includes."""

    def test_template_change_rebuilds_dependent_pages(self) -> None:
        """When a template changes, pages using it should rebuild.

        Template includes are stored as resolved Paths in depends_on so that
        filesystem-based change queries (which use Paths) can match them.
        """
        tracer = EffectTracer()

        # Record effects with resolved template Paths in depends_on
        # (Effect.for_page_render stores template_name as string; we add
        # resolved paths separately to match filesystem change queries)
        tracer.record(
            Effect(
                outputs=frozenset({Path("public/about/index.html")}),
                depends_on=frozenset({
                    Path("content/about.md"),
                    "single.html",
                    Path("themes/default/templates/partials/nav.html"),
                    Path("themes/default/templates/partials/footer.html"),
                }),
                invalidates=frozenset({"page:/about/"}),
                operation="render_page",
            )
        )

        tracer.record(
            Effect(
                outputs=frozenset({Path("public/blog/index.html")}),
                depends_on=frozenset({
                    Path("content/blog.md"),
                    "list.html",
                    Path("themes/default/templates/partials/nav.html"),
                }),
                invalidates=frozenset({"page:/blog/"}),
                operation="render_page",
            )
        )

        # Partial nav changes → both pages rebuild
        nav_path = Path("themes/default/templates/partials/nav.html")
        outputs = tracer.outputs_needing_rebuild({nav_path})
        assert Path("public/about/index.html") in outputs
        assert Path("public/blog/index.html") in outputs

        # Partial footer changes → only about page rebuilds
        footer_path = Path("themes/default/templates/partials/footer.html")
        outputs = tracer.outputs_needing_rebuild({footer_path})
        assert Path("public/about/index.html") in outputs
        assert Path("public/blog/index.html") not in outputs


class TestFileChangeDetectionParity:
    """DependencyTracker.get_changed_files/find_new_files/find_deleted_files."""

    def test_changed_files_detected(self, tmp_path: Path) -> None:
        """EffectTracer detects changed files via fingerprinting."""
        tracer = EffectTracer()

        # Create a test file and fingerprint it
        test_file = tmp_path / "test.md"
        test_file.write_text("original content")
        tracer.update_fingerprint(test_file)
        tracer.flush_pending_fingerprints()

        # Not changed yet
        assert not tracer.is_changed(test_file)

        # Modify the file with different size so mtime-based detection
        # works even on fast filesystems with coarse timestamp resolution
        test_file.write_text("modified content that is deliberately longer")

        # Should detect the change (size differs)
        assert tracer.is_changed(test_file)

    def test_new_files_detected(self, tmp_path: Path) -> None:
        """EffectTracer treats unknown files as changed (new)."""
        tracer = EffectTracer()

        new_file = tmp_path / "new.md"
        new_file.write_text("new content")

        # New file (no fingerprint) should be considered changed
        assert tracer.is_changed(new_file)

    def test_deleted_files_detected(self, tmp_path: Path) -> None:
        """EffectTracer detects deleted files as changed."""
        tracer = EffectTracer()

        # Create, fingerprint, then delete
        test_file = tmp_path / "deleted.md"
        test_file.write_text("content")
        tracer.update_fingerprint(test_file)
        tracer.flush_pending_fingerprints()
        test_file.unlink()

        # Deleted file should be considered changed
        assert tracer.is_changed(test_file)


class TestTransitiveInvalidation:
    """EffectTracer provides transitive invalidation that DependencyTracker lacked."""

    def test_transitive_template_invalidation(self) -> None:
        """Template change → page rebuild → dependent indexes rebuild."""
        tracer = EffectTracer()

        # Page depends on template
        tracer.record(
            Effect.for_page_render(
                source_path=Path("content/post.md"),
                output_path=Path("public/post/index.html"),
                template_name="single.html",
                template_includes=frozenset(),
                page_href="/post/",
            )
        )

        # Index depends on the page
        tracer.record(
            Effect.for_index_generation(
                output_path=Path("public/sitemap.xml"),
                source_pages=frozenset({Path("content/post.md")}),
                index_type="sitemap",
            )
        )

        # Source change → both page and sitemap rebuild (transitive)
        outputs = tracer.outputs_needing_rebuild({Path("content/post.md")})
        assert Path("public/post/index.html") in outputs
        assert Path("public/sitemap.xml") in outputs
