"""
Image processing functions for templates.

Provides 6 functions for working with images in templates.
Note: Some functions are stubs for future PIL/Pillow integration.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register image processing functions with Jinja2 environment."""

    # Create closures that have access to site
    def image_url_with_site(path: str, **params: Any) -> str:
        return image_url(path, site.config.get("baseurl", ""), **params)

    def image_dimensions_with_site(path: str) -> tuple[int, int] | None:
        return image_dimensions(path, site.root_path)

    def image_data_uri_with_site(path: str) -> str:
        return image_data_uri(path, site.root_path)

    env.filters.update(
        {
            "image_srcset": image_srcset,
            "image_alt": image_alt,
        }
    )

    env.globals.update(
        {
            "image_url": image_url_with_site,
            "image_dimensions": image_dimensions_with_site,
            "image_srcset_gen": image_srcset_gen,
            "image_data_uri": image_data_uri_with_site,
        }
    )


def image_url(
    path: str,
    base_url: str,
    width: int | None = None,
    height: int | None = None,
    quality: int | None = None,
) -> str:
    """
    Generate image URL with optional parameters.

    Args:
        path: Image path
        base_url: Base URL for site
        width: Target width (optional)
        height: Target height (optional)
        quality: JPEG quality (optional)

    Returns:
        Image URL with query parameters

    Example:
        {{ image_url('photos/hero.jpg', width=800) }}
        # /assets/photos/hero.jpg?w=800
    """
    if not path:
        return ""

    # Normalize path
    if not path.startswith("/"):
        path = f"/assets/{path}"

    # Build query string
    params = []
    if width:
        params.append(f"w={width}")
    if height:
        params.append(f"h={height}")
    if quality:
        params.append(f"q={quality}")

    url = path
    if params:
        url += "?" + "&".join(params)

    if base_url:
        url = base_url.rstrip("/") + url

    return url


def image_dimensions(path: str, root_path: Path) -> tuple[int, int] | None:
    """
    Get image dimensions (width, height).

    Requires Pillow (PIL) library. Returns None if not available or file not found.

    Args:
        path: Image path
        root_path: Site root path

    Returns:
        Tuple of (width, height) or None

    Example:
        {% set width, height = image_dimensions('photo.jpg') %}
        <img width="{{ width }}" height="{{ height }}" src="..." alt="...">
    """
    if not path:
        logger.debug("image_dimensions_empty_path", caller="template")
        return None

    # Try multiple paths
    tried_paths = []
    file_path = Path(root_path) / path
    tried_paths.append(str(file_path))

    if not file_path.exists():
        # Try in assets directory
        file_path = Path(root_path) / "assets" / path
        tried_paths.append(str(file_path))
        if not file_path.exists():
            logger.warning("image_not_found", path=path, tried_paths=tried_paths, caller="template")
            return None

    try:
        from PIL import Image

        with Image.open(file_path) as img:
            dimensions = img.size
            logger.debug(
                "image_dimensions_extracted",
                path=path,
                width=dimensions[0],
                height=dimensions[1],
                format=img.format,
            )
            return dimensions
    except ImportError:
        logger.warning(
            "pillow_not_available",
            path=path,
            message="Pillow library not installed, cannot get image dimensions",
            suggestion="Install with: pip install Pillow",
            caller="template",
        )
        return None
    except Exception as e:
        logger.error(
            "image_read_error",
            path=path,
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__,
            caller="template",
        )
        return None


def image_srcset(image_path: str, sizes: list[int]) -> str:
    """
    Generate srcset attribute for responsive images.

    Args:
        image_path: Base image path
        sizes: List of widths (e.g., [400, 800, 1200])

    Returns:
        srcset attribute value

    Example:
        <img srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}" />
        # hero.jpg?w=400 400w, hero.jpg?w=800 800w, hero.jpg?w=1200 1200w
    """
    if not image_path or not sizes:
        return ""

    srcset_parts = []
    for size in sizes:
        url = f"{image_path}?w={size}" if "?" not in image_path else f"{image_path}&w={size}"
        srcset_parts.append(f"{url} {size}w")

    return ", ".join(srcset_parts)


def image_srcset_gen(image_path: str, sizes: list[int] | None = None) -> str:
    """
    Generate srcset attribute with default sizes.

    Args:
        image_path: Base image path
        sizes: List of widths (default: [400, 800, 1200, 1600])

    Returns:
        srcset attribute value

    Example:
        <img srcset="{{ image_srcset_gen('hero.jpg') }}" />
    """
    if sizes is None:
        sizes = [400, 800, 1200, 1600]

    return image_srcset(image_path, sizes)


def image_alt(filename: str) -> str:
    """
    Generate alt text from filename.

    Converts filename to human-readable alt text by:
    - Removing extension
    - Replacing hyphens/underscores with spaces
    - Capitalizing words

    Args:
        filename: Image filename

    Returns:
        Alt text suggestion

    Example:
        {{ 'mountain-sunset.jpg' | image_alt }}
        # "Mountain Sunset"
    """
    if not filename:
        return ""

    # Remove extension
    name = Path(filename).stem

    # Replace separators with spaces
    name = name.replace("-", " ").replace("_", " ")

    # Capitalize words
    return name.title()


def image_data_uri(path: str, root_path: Path) -> str:
    """
    Convert image to data URI for inline embedding.

    Args:
        path: Image path
        root_path: Site root path

    Returns:
        Data URI string

    Example:
        <img src="{{ image_data_uri('icons/logo.svg') }}" alt="Logo">
    """
    if not path:
        logger.debug("image_data_uri_empty_path", caller="template")
        return ""

    # Try multiple paths
    tried_paths = []
    file_path = Path(root_path) / path
    tried_paths.append(str(file_path))

    if not file_path.exists():
        file_path = Path(root_path) / "assets" / path
        tried_paths.append(str(file_path))
        if not file_path.exists():
            logger.warning("image_not_found", path=path, tried_paths=tried_paths, caller="template")
            return ""

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # Determine MIME type
        suffix = file_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        # For SVG, we can use text encoding
        if suffix == ".svg":
            try:
                svg_text = data.decode("utf-8")
                # URL encode for data URI
                from urllib.parse import quote

                data_uri = f"data:{mime_type};utf8,{quote(svg_text)}"
                logger.debug(
                    "image_data_uri_created",
                    path=path,
                    format="svg",
                    encoding="utf8",
                    size_bytes=len(data),
                )
                return data_uri
            except UnicodeDecodeError:
                pass

        # Base64 encode for other images
        encoded = base64.b64encode(data).decode("ascii")
        data_uri = f"data:{mime_type};base64,{encoded}"
        logger.debug(
            "image_data_uri_created",
            path=path,
            mime_type=mime_type,
            encoding="base64",
            size_bytes=len(data),
            encoded_length=len(encoded),
        )
        return data_uri

    except OSError as e:
        logger.error(
            "image_read_error",
            path=path,
            file_path=str(file_path),
            error=str(e),
            error_type="IOError",
            caller="template",
        )
        return ""
    except Exception as e:
        logger.error(
            "image_encoding_error",
            path=path,
            file_path=str(file_path),
            error=str(e),
            error_type=type(e).__name__,
            caller="template",
        )
        return ""
