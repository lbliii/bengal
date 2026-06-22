"""Integration tests for include dependency invalidation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.effects.effect import Effect
from bengal.effects.tracer import EffectTracer
from bengal.parsing.backends.patitas import create_markdown
from bengal.parsing.backends.patitas.render_session import page_render_session
from bengal.rendering.page_operations import get_content_dependencies, set_content_dependencies

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FakePage:
    source_path: Path
    output_path: Path
    href: str
    title: str


@dataclass
class FakeSite:
    root_path: Path


def test_snippet_change_invalidates_dependent_page_via_effect_tracer(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    snippet = content_dir / "_snippets" / "note.md"
    snippet.parent.mkdir(parents=True)
    snippet.write_text("Original snippet.\n")

    page_path = content_dir / "docs" / "page.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(":::{include} _snippets/note.md\n:::\n")

    page = FakePage(
        source_path=page_path,
        output_path=tmp_path / "public" / "docs" / "page" / "index.html",
        href="/docs/page/",
        title="Page",
    )
    site = FakeSite(root_path=tmp_path)
    md = create_markdown()

    with page_render_session(page_context=page, site=site) as session:
        md(
            page_path.read_text(),
            page_context=page,
            site=site,
        )
    set_content_dependencies(page, session.content_dependencies)

    tracer = EffectTracer()
    include_deps = frozenset(get_content_dependencies(page))
    assert snippet.resolve() in include_deps

    tracer.record(
        Effect(
            outputs=frozenset({page.output_path}),
            depends_on=frozenset({page.source_path, *include_deps}),
            invalidates=frozenset({f"page:{page.href}"}),
            operation="render_page",
            metadata={"include_dependencies": sorted(str(p) for p in include_deps)},
        )
    )

    outputs = tracer.outputs_needing_rebuild({snippet.resolve()})
    assert page.output_path in outputs

    unrelated = content_dir / "other.md"
    unrelated.write_text("# Other\n")
    assert page.output_path not in tracer.outputs_needing_rebuild({unrelated.resolve()})


def test_effect_metadata_tags_include_dependencies(tmp_path: Path) -> None:
    from bengal.effects.render_integration import RenderEffectRecorder

    content_dir = tmp_path / "content"
    snippet = content_dir / "_snippets" / "note.md"
    snippet.parent.mkdir(parents=True)
    snippet.write_text("Snippet.\n")
    page_path = content_dir / "page.md"
    page_path.write_text(":::{include} _snippets/note.md\n:::\n")

    page = FakePage(
        source_path=page_path,
        output_path=tmp_path / "public" / "page" / "index.html",
        href="/page/",
        title="Page",
    )
    site = FakeSite(root_path=tmp_path)
    md = create_markdown()

    with page_render_session(page_context=page, site=site) as session:
        md(page_path.read_text(), page_context=page, site=site)
    set_content_dependencies(page, session.content_dependencies)

    tracer = EffectTracer()
    with RenderEffectRecorder(
        tracer,
        page,  # type: ignore[arg-type]
        "default.html",
        parse_dependencies=frozenset(get_content_dependencies(page)),
    ):
        pass

    effect = tracer.effects[0]
    assert "include_dependencies" in effect.metadata
    assert str(snippet.resolve()) in effect.metadata["include_dependencies"]


def test_snippet_change_invalidates_dependent_page_via_effect_detector(tmp_path: Path) -> None:
    """End-to-end invalidation through EffectBasedDetector, not just EffectTracer."""
    from unittest.mock import Mock

    from bengal.effects.render_integration import RenderEffectRecorder
    from bengal.orchestration.incremental.effect_detector import EffectBasedDetector

    content_dir = tmp_path / "content"
    content_dir.mkdir()
    snippet = content_dir / "_snippets" / "note.md"
    snippet.parent.mkdir(parents=True)
    snippet.write_text("Original snippet.\n")

    page_path = content_dir / "docs" / "page.md"
    page_path.parent.mkdir(parents=True)
    page_path.write_text(":::{include} _snippets/note.md\n:::\n")

    page = FakePage(
        source_path=page_path,
        output_path=tmp_path / "public" / "docs" / "page" / "index.html",
        href="/docs/page/",
        title="Page",
    )
    site = FakeSite(root_path=tmp_path)
    md = create_markdown()

    with page_render_session(page_context=page, site=site) as session:
        md(page_path.read_text(), page_context=page, site=site)
    set_content_dependencies(page, session.content_dependencies)

    tracer = EffectTracer()
    include_deps = frozenset(get_content_dependencies(page))
    with RenderEffectRecorder(
        tracer,
        page,  # type: ignore[arg-type]
        "default.html",
        parse_dependencies=include_deps,
    ):
        pass

    mock_site = Mock()
    mock_site.pages = [page]
    mock_site.root_path = tmp_path

    detector = EffectBasedDetector(site=mock_site, tracer=tracer)
    pages = detector.detect_changes({snippet.resolve()})

    assert page.source_path in pages
    assert page.source_path not in detector.detect_changes({content_dir / "other.md"})
