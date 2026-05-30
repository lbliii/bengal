import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from bengal.content.discovery.page_adapter import page_from_source_page
from bengal.core.records import build_source_page, create_virtual_source_page


def test_page_adapter_import_does_not_expose_page_class() -> None:
    code = """
import importlib.util
import sys
import bengal.content.discovery.page_adapter
import bengal.core.page
print("legacy_module", importlib.util.find_spec("bengal.core.page.legacy"))
print("legacy_loaded", "bengal.core.page.legacy" in sys.modules)
print("exports_page", hasattr(bengal.core.page, "Page"))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "legacy_module None",
        "legacy_loaded False",
        "exports_page False",
    ]


def test_page_from_source_page_preserves_source_record_fields() -> None:
    source_page = build_source_page(
        source_path="docs/guide.md",
        raw_content="# Guide",
        metadata={"title": "Guide", "tags": ["docs"], "translation_key": "guide"},
        lang="en",
        section_path="docs",
        content_hash="abc123",
    )

    page = cast("Any", page_from_source_page(source_page))

    assert page.source_path == Path("docs/guide.md")
    assert page._raw_content == "# Guide"
    assert page.title == "Guide"
    assert page.tags == ["docs"]
    assert page.lang == "en"
    assert page.translation_key == "guide"
    assert page.section_path == "docs"
    assert page.virtual is False


def test_page_from_source_page_can_seed_cache_core() -> None:
    source_page = build_source_page(
        source_path="docs/cached.md",
        raw_content="",
        metadata={"title": "Cached"},
    )

    page = cast("Any", page_from_source_page(source_page, from_cache=True))

    assert page.core is source_page.core
    assert page.title == "Cached"


def test_page_from_source_page_preserves_virtual_rendering_fields(tmp_path) -> None:
    source_page = create_virtual_source_page(
        source_id="__virtual__/tags/python.md",
        title="Python",
        metadata={"template": "tag.html", "type": "tag"},
    )
    site = SimpleNamespace()
    section = SimpleNamespace(path=Path("tags"), name="tags")
    output_path = tmp_path / "tags" / "python" / "index.html"

    page = cast(
        "Any",
        page_from_source_page(
            source_page,
            site=site,
            section=section,
            output_path=output_path,
            rendered_html="<main>Python</main>",
            template_name="tag.html",
        ),
    )

    assert page.virtual is True
    assert page._site is site
    assert page.section_path == "tags"
    assert page.output_path == output_path
    assert page.rendered_html == "<main>Python</main>"
    assert page.prerendered_html == "<main>Python</main>"
    assert page.template_name == "tag.html"
