"""Tests for include and literalinclude directives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from bengal.effects.render_integration import RenderEffectRecorder
from bengal.effects.tracer import EffectTracer
from bengal.parsing.backends.patitas.include_cache import clear_include_cache
from bengal.parsing.backends.patitas.render_session import page_render_session
from bengal.rendering.page_operations import get_content_dependencies, set_content_dependencies


@dataclass
class FakePage:
    source_path: Path
    output_path: Path = Path("public/page/index.html")
    href: str = "/page/"
    title: str = "Page"


@dataclass
class FakeSite:
    root_path: Path


def _render(
    markdown: str,
    *,
    site_root: Path,
    source_path: Path,
    effect_tracer: EffectTracer | None = None,
    track_content_deps: bool = True,
) -> str:
    from bengal.parsing.backends.patitas import create_markdown

    page = FakePage(source_path=source_path)
    site = FakeSite(root_path=site_root)
    md = create_markdown()

    def _run() -> str:
        return md(
            markdown,
            page_context=page,
            site=site,
        )

    if effect_tracer is not None:
        with RenderEffectRecorder(effect_tracer, page, "default.html"):
            return _run()

    if track_content_deps:
        with page_render_session() as session:
            html = _run()
        set_content_dependencies(page, session.content_dependencies)
        return html

    return _run()


@pytest.fixture(autouse=True)
def _clear_include_cache_between_tests() -> None:
    clear_include_cache()
    yield
    clear_include_cache()


def test_include_renders_markdown_snippet(temp_content_tree) -> None:
    temp_content_tree.create(
        "_snippets/hello.md",
        "```bash\nbengal new site mysite\n```\n\nYour site runs at `http://localhost:5173`.\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/hello.md\n:::\n")

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "bengal" in html
    assert "mysite" in html
    assert "<pre><code" in html
    assert "```bash" not in html
    assert "http://localhost:5173" in html


def test_include_resolves_from_content_root(temp_content_tree) -> None:
    temp_content_tree.create(
        "_snippets/install/uv.md",
        "```bash\nuv add bengal\n```\n",
    )
    source_path = temp_content_tree.content_dir / "docs/installation.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(":::{include} _snippets/install/uv.md\n:::\n")

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "uv" in html
    assert "bengal" in html
    assert "<pre><code" in html
    assert "```" not in html


def test_include_nested_directives(temp_content_tree) -> None:
    temp_content_tree.create(
        "_snippets/warning.md",
        ":::{warning}\nThis feature is in beta.\n:::\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/warning.md\n:::\n")

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "admonition warning" in html
    assert "This feature is in beta." in html


def test_include_detects_cycles(temp_content_tree) -> None:
    temp_content_tree.create(
        "_snippets/a.md",
        ":::{include} _snippets/b.md\n:::\n",
    )
    temp_content_tree.create(
        "_snippets/b.md",
        ":::{include} _snippets/a.md\n:::\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/a.md\n:::\n")

    with pytest.warns(UserWarning, match="Circular include detected"):
        html = _render(
            source_path.read_text(),
            site_root=temp_content_tree.root,
            source_path=source_path,
        )

    assert "include-error" in html
    assert "Circular include detected" in html


def test_literalinclude_renders_code_block(temp_content_tree) -> None:
    temp_content_tree.create(
        "examples/demo.py",
        "print('hello')\nprint('world')\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{literalinclude} examples/demo.py\n:::\n")

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "print(" in html
    assert "<pre><code" in html
    assert 'class="language-python"' in html


def test_include_records_extra_dependency(temp_content_tree) -> None:
    snippet = temp_content_tree.create(
        "_snippets/hello.md",
        "Included snippet.\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/hello.md\n:::\n")

    page = FakePage(source_path=source_path)
    with page_render_session() as session:
        _render(
            source_path.read_text(),
            site_root=temp_content_tree.root,
            source_path=source_path,
            track_content_deps=False,
        )
        set_content_dependencies(page, session.content_dependencies)

    assert snippet.resolve() in get_content_dependencies(page)


def test_include_parse_dependencies_merge_into_effect(temp_content_tree) -> None:
    snippet = temp_content_tree.create(
        "_snippets/hello.md",
        "Included snippet.\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/hello.md\n:::\n")

    page = FakePage(source_path=source_path)
    with page_render_session() as session:
        _render(
            source_path.read_text(),
            site_root=temp_content_tree.root,
            source_path=source_path,
            track_content_deps=False,
        )
        parse_deps = list(session.content_dependencies)
    set_content_dependencies(page, parse_deps)

    tracer = EffectTracer()
    with RenderEffectRecorder(
        tracer,
        page,
        "default.html",
        parse_dependencies=frozenset(get_content_dependencies(page)),
    ):
        pass

    assert len(tracer.effects) == 1
    effect = tracer.effects[0]
    assert snippet.resolve() in {Path(dep).resolve() for dep in effect.depends_on}


def test_include_cache_reuses_rendered_html(temp_content_tree, monkeypatch) -> None:
    snippet = temp_content_tree.create(
        "_snippets/hello.md",
        "Cached snippet.\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(
        ":::{include} _snippets/hello.md\n:::\n\n:::{include} _snippets/hello.md\n:::\n"
    )

    parse_calls = 0
    import bengal.parsing.backends.patitas as patitas_module

    original_parse_to_ast = patitas_module.Markdown.parse_to_ast

    def counting_parse_to_ast(self, source, text_transformer=None):  # type: ignore[no-untyped-def]
        nonlocal parse_calls
        if "Cached snippet." in source:
            parse_calls += 1
        return original_parse_to_ast(self, source, text_transformer=text_transformer)

    monkeypatch.setattr(patitas_module.Markdown, "parse_to_ast", counting_parse_to_ast)

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "Cached snippet." in html
    assert parse_calls == 1
    assert snippet.exists()


def test_include_reuses_bound_markdown_engine(temp_content_tree, monkeypatch) -> None:
    temp_content_tree.create(
        "_snippets/hello.md",
        "Included snippet.\n",
    )
    source_path = temp_content_tree.content_dir / "page.md"
    source_path.write_text(":::{include} _snippets/hello.md\n:::\n")

    create_calls = 0
    import bengal.parsing.backends.patitas as patitas_module

    original_create = patitas_module.create_markdown

    def counting_create(**kwargs: Any) -> Any:
        nonlocal create_calls
        create_calls += 1
        return original_create(**kwargs)

    monkeypatch.setattr(patitas_module, "create_markdown", counting_create)

    html = _render(
        source_path.read_text(),
        site_root=temp_content_tree.root,
        source_path=source_path,
    )

    assert "Included snippet." in html
    # One engine for the page; includes reuse it instead of constructing another.
    assert create_calls == 1
