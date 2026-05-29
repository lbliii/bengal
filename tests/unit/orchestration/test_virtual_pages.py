from types import SimpleNamespace

from bengal.orchestration.utils.virtual_pages import VirtualPageSpec, create_virtual_page
from bengal.utils.paths.url_strategy import URLStrategy


def test_create_virtual_page_uses_source_record_adapter(tmp_path) -> None:
    site = SimpleNamespace(
        config_service=SimpleNamespace(paths=SimpleNamespace(generated_dir=tmp_path / "generated")),
        output_dir=tmp_path / "public",
        config={},
        url_registry=None,
    )
    output_path = tmp_path / "public" / "tags" / "python" / "index.html"

    page = create_virtual_page(
        site=site,
        url_strategy=URLStrategy(),
        spec=VirtualPageSpec(
            title="Python",
            template="tag.html",
            page_type="tag",
            metadata={"_tag": "python"},
            lang="en",
        ),
        path_segments=("tags", "python"),
        output_path=output_path,
    )

    assert page.source_path == tmp_path / "generated" / "tags" / "python" / "index.md"
    assert page.title == "Python"
    assert page.template_name == "tag.html"
    assert page.output_path == output_path
    assert page.lang == "en"
    assert page.virtual is True
    assert page._site is site
    assert page.metadata["_generated"] is True
    assert page.metadata["_virtual"] is True
