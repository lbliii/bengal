"""Image resource model and processing.

Provides image processing with caching:
- ImageResource: Image with processing methods
- ProcessedImage: Result of processing operation
- ProcessParams: Parsed processing parameters

Processing Methods:
    fill(spec): Resize and crop to exact dimensions
    fit(spec): Resize to fit within dimensions
    resize(spec): Resize by width or height
filter(*filters): Apply image filters

Spec String Format:
"WIDTHxHEIGHT [format] [quality] [anchor]"

Examples:
    "800x600"           - dimensions only
    "800x600 webp"      - with format conversion
    "800x600 webp q80"  - with quality
    "800x600 center"    - with anchor point
    "800x"              - width only (height auto)
    "x600"              - height only (width auto)

Anchor Points:
center, top, bottom, left, right
topleft, topright, bottomleft, bottomright
smart (face detection, requires smartcrop)

Dependencies:
- Pillow: Required for image processing
- smartcrop: Optional for smart cropping
- pillow-avif-plugin: Optional for AVIF output

"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Import shared types from types.py to avoid circular imports with processor
if TYPE_CHECKING:
    pass


@dataclass
class ProcessedImage:
    """Result of image processing operation.

    Contains the processed image path and metadata.

    """

    source: ImageResource
    output_path: Path
    rel_permalink: str
    width: int
    height: int
    format: str
    file_size: int

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink

    def __repr__(self) -> str:
        return f"ProcessedImage({self.rel_permalink!r}, {self.width}x{self.height})"


@dataclass
class ImageResource:
    """Image resource with processing and caching.

    Provides methods for resizing, cropping, and format conversion
    with automatic caching of processed results.

    Attributes:
        source_path: Path to source image file
        site: Site instance for output configuration

    Example:
            >>> img = ImageResource(source_path=Path("hero.jpg"), site=site)
            >>> processed = img.fill("800x600 webp q80")
            >>> print(processed.rel_permalink)
            '/assets/images/hero_800x600_q80.webp'

    """

    source_path: Path
    site: Any  # Site | None - using Any to avoid circular import

    # Cached dimensions
    _width: int | None = field(default=None, repr=False, init=False)
    _height: int | None = field(default=None, repr=False, init=False)
    _format: str | None = field(default=None, repr=False, init=False)

    @property
    def exists(self) -> bool:
        """Check if source image exists.

        Cost: O(DISK) — path.exists().
        """
        return self.source_path.exists()

    @cached_property
    def _dimensions(self) -> tuple[int, int] | None:
        """Load image dimensions (lazy) via services layer.

        Cost: O(DISK) first access, O(1) cached thereafter.
        """
        from bengal.services.asset_io import get_image_dimensions

        return get_image_dimensions(self.source_path, context=self.site)

    @property
    def width(self) -> int:
        """Get image width (loads image if needed).

        Cost: O(1) cached — from _dimensions.
        """
        dims = self._dimensions
        return dims[0] if dims else 0

    @property
    def height(self) -> int:
        """Get image height (loads image if needed).

        Cost: O(1) cached — from _dimensions.
        """
        dims = self._dimensions
        return dims[1] if dims else 0

    @property
    def name(self) -> str:
        """Filename with extension.

        Cost: O(1) — Path.name.
        """
        return self.source_path.name

    @property
    def stem(self) -> str:
        """Filename without extension.

        Cost: O(1) — Path.stem.
        """
        return self.source_path.stem

    @property
    def suffix(self) -> str:
        """File extension including dot.

        Cost: O(1) — Path.suffix.
        """
        return self.source_path.suffix

    @property
    def rel_permalink(self) -> str:
        """URL to original image (relative to site root).

        Cost: O(1) — path computation.
        """
        if self.site is None:
            return f"/{self.source_path.name}"

        try:
            rel_path = self.source_path.relative_to(self.site.root_path / "assets")
            return f"/assets/{rel_path}"
        except ValueError:
            # Not under assets, use filename
            return f"/assets/{self.source_path.name}"

    def fill(self, spec: str) -> ProcessedImage | None:
        """Resize and crop to exact dimensions.

        Crops the image to fill the exact specified dimensions,
        maintaining aspect ratio by cropping excess.

        Args:
            spec: "WIDTHxHEIGHT [format] [quality] [anchor]"
                  e.g., "800x600", "800x600 webp q80", "800x600 smart"

        Returns:
            ProcessedImage with output path and metadata, or None on error

        Example:
            >>> img.fill("800x600 webp q80 center")
        """
        return self._process("fill", spec)

    def fit(self, spec: str) -> ProcessedImage | None:
        """Resize to fit within dimensions, preserving aspect ratio.

        Scales image down to fit within the box, without cropping.
        Will not upscale images.

        Args:
            spec: "WIDTHxHEIGHT [format] [quality]"

        Returns:
            ProcessedImage or None on error

        Example:
            >>> img.fit("400x400 webp")
        """
        return self._process("fit", spec)

    def resize(self, spec: str) -> ProcessedImage | None:
        """Resize to width or height, preserving aspect ratio.

        Specify width only (800x) or height only (x600) to
        auto-calculate the other dimension.

        Args:
            spec: "WIDTHx" or "xHEIGHT" or "WIDTHxHEIGHT"

        Returns:
            ProcessedImage or None on error

        Example:
            >>> img.resize("800x")  # 800px wide, height auto
            >>> img.resize("x600")  # 600px tall, width auto
        """
        return self._process("resize", spec)

    def filter(self, *filters: str) -> ProcessedImage | None:
        """Apply image filters.

        Args:
            filters: Filter names with optional args
                     "grayscale", "blur 5", "brightness 1.2"

        Returns:
            ProcessedImage or None on error

        Example:
            >>> img.filter("grayscale", "blur 2")
        """
        return self._process("filter", " ".join(filters))

    def _process(self, operation: str, spec: str) -> ProcessedImage | None:
        """Execute image processing with caching.

        Delegates to ImageProcessor (services layer) for actual processing.
        Results are cached to avoid reprocessing.

        Args:
            operation: Processing operation (fill, fit, resize, filter)
            spec: Operation-specific parameters

        Returns:
            ProcessedImage on success, None on error
        """
        if self.site is None:
            return None

        try:
            from bengal.services.image_processor import ImageProcessor

            processor = ImageProcessor(self.site)
            return processor.process(self.source_path, operation, spec)
        except ImportError:
            return None
        except Exception:
            return None

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink

    def __bool__(self) -> bool:
        """True if image exists."""
        return self.exists
