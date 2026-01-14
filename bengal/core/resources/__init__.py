"""Resource processing for Bengal SSG.

This package provides image processing with caching:
- ImageResource: Image with processing methods (fill, fit, resize)
- ImageProcessor: Processing backend with caching
- ProcessedImage: Result of image processing

Public API:
resources.get(path) → ImageResource | None
resources.match(pattern) → list[ImageResource]

image.fill("800x600 webp q80") → ProcessedImage
image.fit("400x400") → ProcessedImage
image.resize("800x") → ProcessedImage

Dependencies:
Required: Pillow (pip install bengal[images])
Optional: smartcrop (pip install bengal[smartcrop])
Optional: pillow-avif-plugin (pip install bengal[avif])

Example:
    >>> from bengal.core.resources import ImageResource
    >>> img = ImageResource(source_path=Path("hero.jpg"), site=site)
    >>> processed = img.fill("800x600 webp q80")
    >>> print(processed.rel_permalink)
    '/assets/images/hero_800x600_q80.webp'

"""

from __future__ import annotations

from .image import ImageResource, ProcessedImage
from .types import ProcessParams, parse_spec

__all__ = ["ImageResource", "ProcessedImage", "ProcessParams", "parse_spec"]
