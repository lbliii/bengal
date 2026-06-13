"""
End-to-end render test for the autodoc "View source" link (regression for #441).

The autodoc header partial (``autodoc/partials/header.html``) used to read a
``source_url`` key that nothing ever writes to ``element.metadata`` and fell
back to ``#``. As a result, every "View source" link rendered as ``#`` even
when ``github_repo`` was configured.

These tests render the partial through the real template engine with a
configured ``github_repo`` and assert a *real* blob URL is produced. They pass
the live ``Site.config`` object (exactly what the autodoc renderer hands the
template), so the positive assertion fails if the partial regresses to the
``#`` fallback -- this is what makes the test discriminating.
"""

from __future__ import annotations

from pathlib import Path

from bengal.autodoc.base import DocElement
from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine

# Render the partial exactly as the page templates do (it inherits `element` and
# `config` from the surrounding template context, matching production).
HEADER_INCLUDE = "{% include 'autodoc/partials/header.html' %}"


def _make_site(tmp_path: Path, *, github_repo: str | None, branch: str | None = None) -> Site:
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    autodoc_lines = []
    if github_repo is not None:
        autodoc_lines.append(f'github_repo = "{github_repo}"')
    if branch is not None:
        autodoc_lines.append(f'github_branch = "{branch}"')
    autodoc_block = "[autodoc]\n" + "\n".join(autodoc_lines) if autodoc_lines else ""

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        f"""
[site]
title = "Test"

[build]
output_dir = "public"

{autodoc_block}
        """,
        encoding="utf-8",
    )
    (site_dir / "content" / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n", encoding="utf-8"
    )
    return Site.from_config(site_dir)


def _make_element() -> DocElement:
    element = DocElement(
        name="MyClass",
        qualified_name="mypackage.core.MyClass",
        description="A documented class.",
        element_type="class",
        source_file=Path("/repo/mypackage/core.py"),
        line_number=42,
        metadata={"type": "autodoc/python"},
        children=[],
        examples=[],
        see_also=[],
        deprecated=None,
    )
    # page_builders.py sets this repo-relative display path on the element
    # before rendering; mirror that here.
    element.display_source_file = "mypackage/core.py"
    return element


def _render(site: Site, element: DocElement) -> str:
    engine = TemplateEngine(site)
    # Pass the live Site.config object, mirroring AutodocRenderer's render() call.
    return engine.render_string(HEADER_INCLUDE, {"element": element, "config": site.config})


def test_view_source_renders_real_blob_url_when_github_repo_configured(tmp_path: Path) -> None:
    """A configured github_repo (in [autodoc]) produces a real blob URL, not '#'."""
    site = _make_site(tmp_path, github_repo="myorg/myproject")
    html = _render(site, _make_element())

    expected = "https://github.com/myorg/myproject/blob/main/mypackage/core.py#L42"
    assert f'href="{expected}"' in html, (
        f"View source link should point at the GitHub blob URL.\nGot:\n{html}"
    )
    # Discriminating guard: the old bug rendered href="#". If the partial
    # regresses to that fallback, this fails.
    assert 'href="#"' not in html
    assert "View source" in html


def test_view_source_honors_custom_branch(tmp_path: Path) -> None:
    """github_branch from [autodoc] is reflected in the blob URL."""
    site = _make_site(tmp_path, github_repo="myorg/myproject", branch="develop")
    html = _render(site, _make_element())

    assert 'href="https://github.com/myorg/myproject/blob/develop/mypackage/core.py#L42"' in html
    assert 'href="#"' not in html


def test_view_source_accepts_full_url_repo(tmp_path: Path) -> None:
    """A repo already given as a full URL is not double-prefixed."""
    site = _make_site(tmp_path, github_repo="https://github.com/myorg/myproject")
    html = _render(site, _make_element())

    assert 'href="https://github.com/myorg/myproject/blob/main/mypackage/core.py#L42"' in html
    assert "https://github.com/https://" not in html


def test_view_source_omitted_when_no_github_repo(tmp_path: Path) -> None:
    """Without a configured repo, no 'View source' link (and no '#' leak) renders."""
    site = _make_site(tmp_path, github_repo=None)
    html = _render(site, _make_element())

    # No repo configured -> the source link block is skipped entirely.
    assert "View source" not in html
    assert 'href="#"' not in html


def test_view_source_omitted_when_element_has_no_source_file(tmp_path: Path) -> None:
    """Elements without a source file (e.g. some CLI commands) get no link."""
    site = _make_site(tmp_path, github_repo="myorg/myproject")
    element = DocElement(
        name="build",
        qualified_name="cli.build",
        description="Build command.",
        element_type="command",
        source_file=None,
        line_number=None,
        metadata={"type": "autodoc/cli"},
        children=[],
        examples=[],
        see_also=[],
        deprecated=None,
    )
    html = _render(site, element)

    assert "View source" not in html
