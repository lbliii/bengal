"""Resource processing for Bengal SSG.

RFC: hugo-inspired-features

This package provides Hugo-style resource processing:
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
    Optional: smartcrop-py (pip install bengal[smartcrop])
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

__all__ = ["ImageResource", "ProcessedImage"]
