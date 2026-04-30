"""Rendering-side helpers for page bundle resources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.page.bundle import PageResource, PageResources


_TYPE_EXTENSIONS: dict[str, set[str]] = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif", ".ico", ".bmp", ".tiff"},
    "video": {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
    "data": {".json", ".yaml", ".yml", ".csv", ".xml", ".toml"},
    "code": {".js", ".ts", ".css", ".scss", ".less", ".py", ".rb", ".go"},
    "archive": {".zip", ".tar", ".gz", ".rar", ".7z"},
}
_CONTENT_EXTENSIONS: set[str] = {".md", ".markdown", ".rst", ".txt"}


def resource_type(resource: PageResource) -> str | None:
    """Get resource type category based on file extension."""
    suffix_lower = resource.suffix.lower()
    for category, extensions in _TYPE_EXTENSIONS.items():
        if suffix_lower in extensions:
            return category
    return None


def as_image(resource: PageResource) -> Any | None:
    """Convert an image page resource to an ImageResource when possible."""
    if resource.suffix.lower() not in _TYPE_EXTENSIONS.get("image", set()):
        return None

    try:
        from bengal.core.resources.image import ImageResource
    except ImportError:
        return None

    return ImageResource(source_path=resource.path, site=None)


def resource_exists(resource: PageResource) -> bool:
    """Return True when the resource file exists."""
    return resource.path.exists()


def resource_size(resource: PageResource) -> int:
    """Return resource file size in bytes, or zero when unavailable."""
    try:
        return resource.path.stat().st_size
    except OSError:
        return 0


def read_text(resource: PageResource, encoding: str = "utf-8") -> str:
    """Read a page bundle resource as text."""
    return resource.path.read_text(encoding=encoding)


def read_bytes(resource: PageResource) -> bytes:
    """Read a page bundle resource as bytes."""
    return resource.path.read_bytes()


def read_json(resource: PageResource) -> Any:
    """Read and parse a page bundle resource as JSON."""
    return json.loads(read_text(resource))


def read_yaml(resource: PageResource) -> Any:
    """Read and parse a page bundle resource as YAML."""
    return yaml.safe_load(read_text(resource))


def by_type(resources: PageResources, resource_type_name: str) -> list[PageResource]:
    """Get resources by MIME-like type category."""
    extensions = _TYPE_EXTENSIONS.get(resource_type_name, set())
    return [resource for resource in resources if resource.suffix.lower() in extensions]


def images(resources: PageResources) -> list[PageResource]:
    """Get all image resources."""
    return by_type(resources, "image")


def data(resources: PageResources) -> list[PageResource]:
    """Get all data resources."""
    return by_type(resources, "data")


def get_resources(source_path: Path, url: str) -> PageResources:
    """Get resources co-located with a page leaf bundle."""
    from bengal.core.page.bundle import PageResource, PageResources, is_leaf_bundle

    if not is_leaf_bundle(source_path):
        return PageResources([])

    bundle_dir = source_path.parent
    if not bundle_dir.exists() or not bundle_dir.is_dir():
        return PageResources([])

    resources: list[PageResource] = []
    for path in bundle_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in _CONTENT_EXTENSIONS:
            continue
        resources.append(PageResource(path=path, page_url=url))

    resources.sort(key=lambda resource: resource.name)
    return PageResources(resources)
