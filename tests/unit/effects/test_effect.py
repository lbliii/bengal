"""
Unit tests for Effect dataclass.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 1)
"""

from pathlib import Path

import pytest

from bengal.effects import Effect


class TestEffect:
    """Tests for Effect dataclass."""

    def test_create_empty_effect(self) -> None:
        """Effect can be created with defaults."""
        effect = Effect()
        assert effect.outputs == frozenset()
        assert effect.depends_on == frozenset()
        assert effect.invalidates == frozenset()
        assert effect.operation == ""
        assert effect.metadata == {}

    def test_create_effect_with_values(self) -> None:
        """Effect can be created with explicit values."""
        effect = Effect(
            outputs=frozenset({Path("public/page.html")}),
            depends_on=frozenset({Path("content/page.md"), "page.html"}),
            invalidates=frozenset({"page:/page/"}),
            operation="render_page",
            metadata={"href": "/page/"},
        )
        assert len(effect.outputs) == 1
        assert len(effect.depends_on) == 2
        assert len(effect.invalidates) == 1
        assert effect.operation == "render_page"
        assert effect.metadata["href"] == "/page/"

    def test_effect_is_frozen(self) -> None:
        """Effect is immutable (frozen dataclass)."""
        effect = Effect()
        with pytest.raises(AttributeError):
            effect.operation = "new_value"  # type: ignore[misc]

    def test_effect_merge(self) -> None:
        """Effects can be merged."""
        effect1 = Effect(
            outputs=frozenset({Path("a.html")}),
            depends_on=frozenset({Path("a.md")}),
            invalidates=frozenset({"page:a"}),
            operation="op1",
        )
        effect2 = Effect(
            outputs=frozenset({Path("b.html")}),
            depends_on=frozenset({Path("b.md")}),
            invalidates=frozenset({"page:b"}),
            operation="op2",
        )
        merged = effect1.merge_with(effect2)
        assert len(merged.outputs) == 2
        assert len(merged.depends_on) == 2
        assert len(merged.invalidates) == 2
        assert merged.operation == "op1+op2"


class TestEffectFactories:
    """Tests for Effect factory methods."""

    def test_for_page_render(self) -> None:
        """Effect.for_page_render creates correct effect."""
        effect = Effect.for_page_render(
            source_path=Path("content/docs/guide.md"),
            output_path=Path("public/docs/guide/index.html"),
            template_name="doc.html",
            template_includes=frozenset({"base.html", "partials/nav.html"}),
            page_href="/docs/guide/",
        )
        assert effect.operation == "render_page"
        assert Path("public/docs/guide/index.html") in effect.outputs
        assert Path("content/docs/guide.md") in effect.depends_on
        assert "doc.html" in effect.depends_on
        assert "base.html" in effect.depends_on
        assert "page:/docs/guide/" in effect.invalidates

    def test_for_page_render_with_cascade(self) -> None:
        """Effect.for_page_render includes cascade sources."""
        effect = Effect.for_page_render(
            source_path=Path("content/docs/guide.md"),
            output_path=Path("public/docs/guide/index.html"),
            template_name="doc.html",
            template_includes=frozenset(),
            page_href="/docs/guide/",
            cascade_sources=frozenset({Path("content/docs/_index.md")}),
        )
        assert Path("content/docs/_index.md") in effect.depends_on

    def test_for_asset_copy(self) -> None:
        """Effect.for_asset_copy creates correct effect."""
        effect = Effect.for_asset_copy(
            source_path=Path("assets/style.css"),
            output_path=Path("public/assets/style.abc123.css"),
            fingerprinted=True,
        )
        assert effect.operation == "fingerprint_asset"
        assert Path("assets/style.css") in effect.depends_on
        assert Path("public/assets/style.abc123.css") in effect.outputs
        assert "asset:assets/style.css" in effect.invalidates

    def test_for_index_generation(self) -> None:
        """Effect.for_index_generation creates correct effect."""
        source_pages = frozenset(
            {
                Path("content/page1.md"),
                Path("content/page2.md"),
            }
        )
        effect = Effect.for_index_generation(
            output_path=Path("public/sitemap.xml"),
            source_pages=source_pages,
            index_type="sitemap",
        )
        assert effect.operation == "generate_sitemap"
        assert Path("public/sitemap.xml") in effect.outputs
        assert Path("content/page1.md") in effect.depends_on
        assert "index:sitemap" in effect.invalidates

    def test_for_taxonomy_page(self) -> None:
        """Effect.for_taxonomy_page creates correct effect."""
        members = frozenset(
            {
                Path("content/post1.md"),
                Path("content/post2.md"),
            }
        )
        effect = Effect.for_taxonomy_page(
            output_path=Path("public/tags/python/index.html"),
            taxonomy_name="tags",
            term="python",
            member_pages=members,
        )
        assert effect.operation == "generate_taxonomy_page"
        assert Path("content/post1.md") in effect.depends_on
        assert "taxonomy:tags:python" in effect.invalidates
