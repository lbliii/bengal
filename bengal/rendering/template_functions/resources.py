"""Hugo-style resource functions for templates.

RFC: hugo-inspired-features

Provides Hugo-style resource access in templates:
- resources.get(path): Get single image resource
- resources.match(pattern): Get all resources matching pattern

Example:
    {% let hero = resources.get("images/hero.jpg") %}
    {% if hero %}
        <img src="{{ hero.fill('1200x630 webp q85') }}">
    {% end %}

    {% for img in resources.match("gallery/*.jpg") %}
        <img src="{{ img.fit('400x300 webp') }}" loading="lazy">
    {% end %}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment

logger = get_logger(__name__)


class ResourcesProxy:
    """Proxy object for resources.get() and resources.match() in templates.

    Provides Hugo-style resource access syntax:
        resources.get("images/hero.jpg")
        resources.match("gallery/*.jpg")
    """

    def __init__(self, site: Site):
        self._site = site
        self._assets_dir = site.root_path / "assets"

    def get(self, path: str) -> Any | None:
        """Get an image resource by path.

        Args:
            path: Path relative to assets/ directory

        Returns:
            ImageResource or None if file doesn't exist

        Example:
            {% let hero = resources.get("images/hero.jpg") %}
            {{ hero.fill("800x600 webp") }}
        """
        from bengal.core.resources.image import ImageResource

        full_path = self._assets_dir / path

        if not full_path.exists():
            logger.debug(
                "resource_not_found",
                path=path,
                searched=str(full_path),
            )
            return None

        # Only return for image files
        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".avif",
            ".bmp",
            ".tiff",
        }
        if full_path.suffix.lower() not in image_extensions:
            logger.debug(
                "resource_not_image",
                path=path,
                suffix=full_path.suffix,
            )
            return None

        return ImageResource(source_path=full_path, site=self._site)

    def match(self, pattern: str) -> list[Any]:
        """Get all resources matching a glob pattern.

        Args:
            pattern: Glob pattern relative to assets/ directory

        Returns:
            List of ImageResource objects

        Example:
            {% for img in resources.match("gallery/*.jpg") %}
                {{ img.fit("400x300") }}
            {% end %}
        """
        from bengal.core.resources.image import ImageResource

        if not self._assets_dir.exists():
            return []

        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".avif",
            ".bmp",
            ".tiff",
        }
        results = []

        for match in self._assets_dir.glob(pattern):
            if match.is_file() and match.suffix.lower() in image_extensions:
                results.append(ImageResource(source_path=match, site=self._site))

        # Sort by path for deterministic ordering
        results.sort(key=lambda r: str(r.source_path))

        return results


def register(env: TemplateEnvironment, site: Site) -> None:
    """Register functions with template environment.

    Adds the `resources` proxy object to template globals.

    Args:
        env: Jinja2 Environment
        site: Site instance
    """
    resources_proxy = ResourcesProxy(site)

    env.globals.update(
        {
            "resources": resources_proxy,
        }
    )
