"""Image processing backend with caching.

RFC: hugo-inspired-features

Provides the actual image processing using Pillow, with:
- Versioned cache to avoid reprocessing
- Atomic writes for parallel build safety
- Memory optimization for large images
- Multiple output formats (WebP, AVIF, JPEG, PNG)

Cache Structure:
    .bengal/image-cache/
    ├── v1_abc123_fill_def456.webp    # Processed images
    ├── v1_abc123_fill_def456.json    # Metadata (dimensions, etc.)
    └── ...

Cache Key Format:
    v{schema}_{source_hash}_{operation}_{spec_hash}.{ext}

Thread Safety:
    Uses atomic file writes (tempfile + rename) to prevent corruption
    during parallel builds where multiple workers might process the
    same image simultaneously.

Memory Management:
    For images >10MP, uses PIL.Image.draft() to reduce memory usage
    by loading at reduced resolution.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from PIL import Image


logger = get_logger(__name__)

# Cache schema version - bump when cache format changes
CACHE_SCHEMA_VERSION = 1

# Large image threshold for memory optimization (10 megapixels)
LARGE_IMAGE_THRESHOLD = 10_000_000


@dataclass
class CachedResult:
    """Cached processing result metadata."""

    output_path: Path
    rel_permalink: str
    width: int
    height: int
    format: str
    file_size: int


class ImageProcessor:
    """Image processing with caching.

    Uses Pillow for processing, with optional libvips for performance.
    Caches processed images in .bengal/image-cache/.

    Thread Safety:
        Uses atomic file writes to prevent corruption during parallel builds.
        Cache reads are lock-free; writes use tempfile + rename pattern.

    Memory Management:
        For images >10MP, uses chunked processing via PIL.Image.draft()
        to reduce peak memory usage.

    Attributes:
        site: Site instance for configuration
        cache_dir: Path to image cache directory
    """

    CACHE_DIR = ".bengal/image-cache"

    def __init__(self, site: Any):
        """Initialize processor with site configuration.

        Args:
            site: Site instance (for root_path and output configuration)
        """
        self.site = site
        self.cache_dir = site.root_path / self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def process(
        self,
        source: Path,
        operation: str,
        spec: str,
    ) -> Any | None:
        """Process image with caching.

        Checks cache first, processes only if cache miss.

        Args:
            source: Path to source image
            operation: Processing operation (fill, fit, resize, filter)
            spec: Operation parameters

        Returns:
            ProcessedImage on success, None on error

        Cache key includes:
        - Schema version (for cache invalidation on format changes)
        - Source path + mtime
        - Operation + spec
        """
        from bengal.core.resources.image import ProcessedImage, parse_spec

        try:
            # Check if source exists
            if not source.exists():
                logger.error("image_not_found", source=str(source))
                return None

            # Parse spec
            params = parse_spec(spec)
            if params is None:
                logger.error("invalid_spec", spec=spec, source=str(source))
                return None

            # Generate cache key
            cache_key = self._cache_key(source, operation, spec)

            # Check cache
            cached = self._get_cached(cache_key, params)
            if cached:
                # Return cached result as ProcessedImage
                from bengal.core.resources.image import ImageResource

                return ProcessedImage(
                    source=ImageResource(source_path=source, site=self.site),
                    output_path=cached.output_path,
                    rel_permalink=cached.rel_permalink,
                    width=cached.width,
                    height=cached.height,
                    format=cached.format,
                    file_size=cached.file_size,
                )

            # Process image
            result = self._do_process(source, operation, params)
            if result is None:
                return None

            # Cache result
            self._cache_result(cache_key, result)

            return result

        except FileNotFoundError:
            logger.error("image_not_found", source=str(source))
            return None
        except Exception as e:
            logger.error(
                "image_process_error",
                source=str(source),
                operation=operation,
                spec=spec,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _cache_key(self, source: Path, operation: str, spec: str) -> str:
        """Generate cache key with schema version.

        Format: v{schema}_{source_hash}_{op}_{spec_hash}
        """
        source_stat = source.stat()
        source_id = f"{source}:{source_stat.st_mtime_ns}"

        components = [
            f"v{CACHE_SCHEMA_VERSION}",
            hashlib.md5(source_id.encode()).hexdigest()[:12],
            operation,
            hashlib.md5(spec.encode()).hexdigest()[:8],
        ]
        return "_".join(components)

    def _get_cached(self, cache_key: str, params: Any) -> CachedResult | None:
        """Check if cached result exists.

        Args:
            cache_key: Cache key string
            params: ProcessParams for format determination

        Returns:
            CachedResult if cache hit, None if miss
        """
        # Determine output format
        output_format = params.format or "jpeg"
        output_ext = "jpg" if output_format == "jpeg" else output_format

        # Check for cached image file
        image_path = self.cache_dir / f"{cache_key}.{output_ext}"
        meta_path = self.cache_dir / f"{cache_key}.json"

        if not image_path.exists() or not meta_path.exists():
            return None

        try:
            with open(meta_path) as f:
                meta = json.load(f)

            return CachedResult(
                output_path=image_path,
                rel_permalink=meta["rel_permalink"],
                width=meta["width"],
                height=meta["height"],
                format=meta["format"],
                file_size=image_path.stat().st_size,
            )
        except (json.JSONDecodeError, KeyError, OSError):
            # Invalid cache entry, will reprocess
            return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache processing result atomically.

        Uses tempfile + rename pattern for atomic writes.
        """
        meta_path = self.cache_dir / f"{cache_key}.json"

        # Write metadata atomically
        fd, temp_path = tempfile.mkstemp(
            dir=self.cache_dir,
            prefix=f".{cache_key}_",
            suffix=".tmp",
        )
        try:
            meta = {
                "rel_permalink": result.rel_permalink,
                "width": result.width,
                "height": result.height,
                "format": result.format,
            }
            with os.fdopen(fd, "w") as f:
                json.dump(meta, f)
            os.replace(temp_path, meta_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def _do_process(
        self,
        source: Path,
        operation: str,
        params: Any,
    ) -> Any | None:
        """Actually process the image using Pillow.

        Args:
            source: Path to source image
            operation: Processing operation
            params: ProcessParams

        Returns:
            ProcessedImage on success, None on error
        """
        try:
            from PIL import Image

            from bengal.core.resources.image import ImageResource, ProcessedImage
        except ImportError:
            logger.error(
                "pillow_not_installed",
                message="Pillow required for image processing. Install: pip install bengal[images]",
            )
            return None

        # Open image
        img = Image.open(source)

        # Memory optimization for large images
        if img.width * img.height > LARGE_IMAGE_THRESHOLD:
            if params.width and params.height:
                # Use draft mode to load at reduced resolution
                img.draft(img.mode, (params.width * 2, params.height * 2))
                img.load()

        # Convert RGBA to RGB for JPEG output
        if params.format == "jpeg" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Apply operation
        if operation == "fill":
            img = self._fill(img, params)
        elif operation == "fit":
            img = self._fit(img, params)
        elif operation == "resize":
            img = self._resize(img, params)
        elif operation == "filter":
            img = self._apply_filters(img, params)
        else:
            logger.error("unknown_operation", operation=operation)
            return None

        # Determine output format and path
        output_format = params.format or source.suffix[1:].lower()
        if output_format == "jpg":
            output_format = "jpeg"

        output_ext = "jpg" if output_format == "jpeg" else output_format
        cache_key = self._cache_key(source, operation, str(params))
        output_path = self.cache_dir / f"{cache_key}.{output_ext}"

        # Save image atomically
        fd, temp_path = tempfile.mkstemp(
            dir=self.cache_dir,
            prefix=f".{cache_key}_",
            suffix=f".{output_ext}",
        )
        try:
            os.close(fd)

            # Determine save options
            save_kwargs: dict[str, Any] = {}
            if output_format == "jpeg":
                save_kwargs["quality"] = params.quality
                save_kwargs["optimize"] = True
            elif output_format == "webp":
                save_kwargs["quality"] = params.quality
                save_kwargs["method"] = 4  # Balance speed/quality
            elif output_format == "png":
                save_kwargs["optimize"] = True

            img.save(temp_path, format=output_format.upper(), **save_kwargs)
            os.replace(temp_path, output_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

        # Build relative permalink
        rel_permalink = f"/assets/cache/{output_path.name}"

        return ProcessedImage(
            source=ImageResource(source_path=source, site=self.site),
            output_path=output_path,
            rel_permalink=rel_permalink,
            width=img.width,
            height=img.height,
            format=output_format,
            file_size=output_path.stat().st_size,
        )

    def _fill(self, img: Image.Image, params: Any) -> Image.Image:
        """Resize and crop to exact dimensions.

        Args:
            img: PIL Image
            params: ProcessParams with width, height, anchor

        Returns:
            Processed PIL Image
        """
        from PIL import ImageOps

        target = (params.width, params.height)

        if target[0] is None or target[1] is None:
            logger.error("fill_requires_dimensions", params=str(params))
            return img

        if params.anchor == "smart":
            return self._smart_crop(img, target)
        else:
            centering = self._anchor_to_centering(params.anchor)
            return ImageOps.fit(img, target, method=3, centering=centering)  # LANCZOS = 3

    def _fit(self, img: Image.Image, params: Any) -> Image.Image:
        """Resize to fit within dimensions.

        Args:
            img: PIL Image
            params: ProcessParams with width, height

        Returns:
            Processed PIL Image (not upscaled)
        """
        target_w = params.width or img.width
        target_h = params.height or img.height

        # Don't upscale
        if img.width <= target_w and img.height <= target_h:
            return img

        img.thumbnail((target_w, target_h), 3)  # LANCZOS = 3
        return img

    def _resize(self, img: Image.Image, params: Any) -> Image.Image:
        """Resize with aspect ratio preservation.

        Args:
            img: PIL Image
            params: ProcessParams with width and/or height

        Returns:
            Processed PIL Image
        """
        if params.width and not params.height:
            # Width specified, calculate height
            ratio = params.width / img.width
            new_height = int(img.height * ratio)
            return img.resize((params.width, new_height), 3)  # LANCZOS = 3
        elif params.height and not params.width:
            # Height specified, calculate width
            ratio = params.height / img.height
            new_width = int(img.width * ratio)
            return img.resize((new_width, params.height), 3)
        elif params.width and params.height:
            # Both specified - resize to exact dimensions
            return img.resize((params.width, params.height), 3)
        else:
            # No dimensions specified
            return img

    def _apply_filters(self, img: Image.Image, params: Any) -> Image.Image:
        """Apply image filters.

        Currently supports: grayscale, blur

        Args:
            img: PIL Image
            params: ProcessParams (anchor field contains filter spec)

        Returns:
            Processed PIL Image
        """
        from PIL import ImageFilter

        # Parse filter string from anchor (reusing field for simplicity)
        filter_spec = params.anchor.lower()

        if "grayscale" in filter_spec or "grey" in filter_spec:
            img = img.convert("L").convert("RGB")

        if "blur" in filter_spec:
            # Extract blur radius if specified
            import re

            match = re.search(r"blur\s*(\d+)?", filter_spec)
            radius = int(match.group(1)) if match and match.group(1) else 2
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))

        return img

    def _smart_crop(
        self,
        img: Image.Image,
        target: tuple[int, int],
    ) -> Image.Image:
        """Smart cropping with face/feature detection.

        Falls back to center crop if smartcrop-py is not installed.

        Args:
            img: PIL Image
            target: (width, height) tuple

        Returns:
            Cropped PIL Image
        """
        try:
            import smartcrop

            sc = smartcrop.SmartCrop()
            result = sc.crop(img, target[0], target[1])
            box = (
                result["top_crop"]["x"],
                result["top_crop"]["y"],
                result["top_crop"]["x"] + result["top_crop"]["width"],
                result["top_crop"]["y"] + result["top_crop"]["height"],
            )
            return img.crop(box).resize(target, 3)  # LANCZOS = 3
        except ImportError:
            logger.info(
                "smartcrop_not_available",
                message="Install with: pip install bengal[smartcrop]",
                fallback="center crop",
            )
            from PIL import ImageOps

            return ImageOps.fit(img, target, method=3)

    def _anchor_to_centering(self, anchor: str) -> tuple[float, float]:
        """Convert anchor name to PIL centering tuple.

        Args:
            anchor: Anchor name (center, top, bottom, etc.)

        Returns:
            (x, y) centering tuple for ImageOps.fit
        """
        anchors = {
            "center": (0.5, 0.5),
            "top": (0.5, 0.0),
            "bottom": (0.5, 1.0),
            "left": (0.0, 0.5),
            "right": (1.0, 0.5),
            "topleft": (0.0, 0.0),
            "topright": (1.0, 0.0),
            "bottomleft": (0.0, 1.0),
            "bottomright": (1.0, 1.0),
        }
        return anchors.get(anchor, (0.5, 0.5))


def get_cache_stats(site: Any) -> dict[str, Any]:
    """Get image cache statistics.

    Args:
        site: Site instance

    Returns:
        Dict with cache stats (count, size, etc.)
    """
    cache_dir = site.root_path / ImageProcessor.CACHE_DIR

    if not cache_dir.exists():
        return {
            "version": CACHE_SCHEMA_VERSION,
            "count": 0,
            "size_bytes": 0,
            "size_mb": 0.0,
        }

    count = 0
    total_size = 0

    for path in cache_dir.iterdir():
        if path.is_file() and not path.name.startswith("."):
            count += 1
            total_size += path.stat().st_size

    return {
        "version": CACHE_SCHEMA_VERSION,
        "count": count,
        "size_bytes": total_size,
        "size_mb": round(total_size / (1024 * 1024), 2),
    }


def clear_cache(site: Any) -> int:
    """Clear the image cache.

    Args:
        site: Site instance

    Returns:
        Number of files deleted
    """
    import shutil

    cache_dir = site.root_path / ImageProcessor.CACHE_DIR

    if not cache_dir.exists():
        return 0

    count = sum(1 for p in cache_dir.iterdir() if p.is_file())
    shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    return count
