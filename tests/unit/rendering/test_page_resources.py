"""Tests for rendering-side page resource helpers."""

from __future__ import annotations

from pathlib import Path

from bengal.core.page.bundle import PageResource, PageResources
from bengal.rendering.page_resources import (
    as_image,
    by_type,
    get_resources,
    read_json,
    read_text,
    resource_type,
)


def test_get_resources_discovers_leaf_bundle_resources(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "posts" / "entry"
    bundle_dir.mkdir(parents=True)
    source_path = bundle_dir / "index.md"
    source_path.write_text("# Entry")
    (bundle_dir / "hero.jpg").write_bytes(b"image")
    (bundle_dir / "data.json").write_text('{"name": "entry"}')
    (bundle_dir / "notes.txt").write_text("content note")

    resources = get_resources(source_path, "/posts/entry/")

    assert [resource.name for resource in resources] == ["data.json", "hero.jpg"]
    hero = resources.get("hero.jpg")
    assert hero is not None
    assert hero.rel_permalink == "/posts/entry/hero.jpg"


def test_page_resource_read_shims_delegate_to_rendering_helpers(tmp_path: Path) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_text('{"count": 3}')
    resource = PageResource(path=data_path, page_url="/")

    assert read_text(resource) == '{"count": 3}'
    assert resource.read_text() == '{"count": 3}'
    assert read_json(resource) == {"count": 3}
    assert resource.read_json() == {"count": 3}
    assert resource.exists is True
    assert resource.size == len('{"count": 3}')


def test_resource_type_and_collection_filters_delegate_to_rendering_helpers() -> None:
    image = PageResource(path=Path("/hero.jpg"), page_url="/")
    data = PageResource(path=Path("/data.json"), page_url="/")
    unknown = PageResource(path=Path("/notes.xyz"), page_url="/")
    resources = PageResources([image, data, unknown])

    assert resource_type(image) == "image"
    assert image.resource_type == "image"
    assert unknown.resource_type is None
    assert by_type(resources, "data") == [data]
    assert resources.images() == [image]
    assert resources.data() == [data]
    assert as_image(data) is None
