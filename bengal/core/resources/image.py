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

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class ProcessParams:
    """Parsed image processing parameters.
    
    Parsed from Hugo-style spec strings like "800x600 webp q80 center".
        
    """

    width: int | None = None
    height: int | None = None
    format: str | None = None
    quality: int = 85
    anchor: str = "center"

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.quality < 1 or self.quality > 100:
            logger.warning(
                "invalid_quality",
                quality=self.quality,
                message="Quality must be 1-100, using 85",
            )
            self.quality = 85


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


def parse_spec(spec: str) -> ProcessParams | None:
    """Parse Hugo-style spec string.
    
    Args:
        spec: Spec string like "800x600 webp q80 center"
    
    Returns:
        ProcessParams if valid, None if invalid
    
    Examples:
            >>> parse_spec("800x600")
        ProcessParams(width=800, height=600)
            >>> parse_spec("800x webp q80")
        ProcessParams(width=800, height=None, format='webp', quality=80)
        
    """
    parts = spec.split()
    params = ProcessParams()

    valid_formats = {"webp", "avif", "jpeg", "jpg", "png", "gif"}
    valid_anchors = {
        "center",
        "smart",
        "top",
        "bottom",
        "left",
        "right",
        "topleft",
        "topright",
        "bottomleft",
        "bottomright",
    }

    for part in parts:
        part_lower = part.lower()

        # Try to parse as dimension (WIDTHxHEIGHT or WIDTHx or xHEIGHT)
        if "x" in part_lower:
            try:
                w_str, h_str = part_lower.split("x", 1)
                params.width = int(w_str) if w_str else None
                params.height = int(h_str) if h_str else None
                continue
            except ValueError:
                logger.error("invalid_dimension_spec", spec=part)
                return None

        # Try to parse as format
        if part_lower in valid_formats:
            params.format = "jpeg" if part_lower == "jpg" else part_lower
            continue

        # Try to parse as quality (q80, q75, etc.)
        if part_lower.startswith("q") and part_lower[1:].isdigit():
            params.quality = int(part_lower[1:])
            continue

        # Try to parse as anchor
        if part_lower in valid_anchors:
            params.anchor = part_lower
            continue

        # Unknown part - log warning but continue
        logger.warning("unknown_spec_part", part=part, full_spec=spec)

    return params


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
        """Check if source image exists."""
        return self.source_path.exists()

    @cached_property
    def _dimensions(self) -> tuple[int, int] | None:
        """Load image dimensions (lazy)."""
        try:
            from PIL import Image

            with Image.open(self.source_path) as img:
                return img.size
        except ImportError:
            logger.warning(
                "pillow_not_available",
                message="Pillow required for image dimensions. Install: pip install bengal[images]",
            )
            return None
        except Exception as e:
            logger.error("image_load_error", path=str(self.source_path), error=str(e))
            return None

    @property
    def width(self) -> int:
        """Get image width (loads image if needed)."""
        dims = self._dimensions
        return dims[0] if dims else 0

    @property
    def height(self) -> int:
        """Get image height (loads image if needed)."""
        dims = self._dimensions
        return dims[1] if dims else 0

    @property
    def name(self) -> str:
        """Filename with extension."""
        return self.source_path.name

    @property
    def stem(self) -> str:
        """Filename without extension."""
        return self.source_path.stem

    @property
    def suffix(self) -> str:
        """File extension including dot."""
        return self.source_path.suffix

    @property
    def rel_permalink(self) -> str:
        """URL to original image (relative to site root)."""
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

        Delegates to ImageProcessor for actual processing.
        Results are cached to avoid reprocessing.

        Args:
            operation: Processing operation (fill, fit, resize, filter)
            spec: Operation-specific parameters

        Returns:
            ProcessedImage on success, None on error
        """
        try:
            from bengal.core.resources.processor import ImageProcessor

            if self.site is None:
                logger.warning(
                    "image_process_no_site",
                    path=str(self.source_path),
                    message="Cannot process image without site context",
                )
                return None

            processor = ImageProcessor(self.site)
            return processor.process(self.source_path, operation, spec)

        except ImportError as e:
            logger.warning(
                "image_processing_unavailable",
                path=str(self.source_path),
                error=str(e),
                message="Install Pillow: pip install bengal[images]",
            )
            return None
        except Exception as e:
            logger.error(
                "image_process_error",
                path=str(self.source_path),
                operation=operation,
                spec=spec,
                error=str(e),
            )
            return None

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink

    def __bool__(self) -> bool:
        """True if image exists."""
        return self.exists
