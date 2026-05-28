from types import SimpleNamespace

from bengal.cache.parsed_output import apply_parsed_page_to_page
from bengal.core.records import ParsedPage


def test_apply_parsed_page_to_page_seeds_parse_fields() -> None:
    page = SimpleNamespace(
        html_content=None,
        toc=None,
        _toc_items_cache=None,
        links=[],
        _excerpt=None,
        _meta_description=None,
        _plain_text_cache=None,
        _ast_cache=None,
    )
    parsed_page = ParsedPage(
        html_content="<p>Hello</p>",
        toc="<nav>TOC</nav>",
        toc_items=({"id": "hello", "title": "Hello"},),
        excerpt="Hello",
        meta_description="Hello meta",
        plain_text="Hello",
        word_count=1,
        reading_time=1,
        links=("https://example.com",),
        ast_cache={"_type": "Document"},
    )

    apply_parsed_page_to_page(page, parsed_page, seed_ast=True)

    assert page.html_content == "<p>Hello</p>"
    assert page.toc == "<nav>TOC</nav>"
    assert page._toc_items_cache == [{"id": "hello", "title": "Hello"}]
    assert page.links == ["https://example.com"]
    assert page._excerpt == "Hello"
    assert page._meta_description == "Hello meta"
    assert page._plain_text_cache == "Hello"
    assert page._ast_cache == {"_type": "Document"}
    assert page.__dict__["word_count"] == 1
    assert page.__dict__["reading_time"] == 1


def test_apply_parsed_page_to_page_can_skip_optional_caches() -> None:
    page = SimpleNamespace(
        html_content=None,
        toc=None,
        _toc_items_cache=None,
        links=[],
        _excerpt=None,
        _meta_description=None,
        _plain_text_cache="old",
        _ast_cache="old-ast",
    )
    parsed_page = ParsedPage(
        html_content="<p>Hello</p>",
        toc="",
        toc_items=(),
        excerpt="",
        meta_description="",
        plain_text="new",
        word_count=1,
        reading_time=1,
        links=(),
        ast_cache={"new": True},
    )

    apply_parsed_page_to_page(
        page,
        parsed_page,
        seed_counts=False,
        seed_plain_text=False,
        seed_ast=False,
    )

    assert page._plain_text_cache == "old"
    assert page._ast_cache == "old-ast"
    assert "word_count" not in page.__dict__
    assert "reading_time" not in page.__dict__
