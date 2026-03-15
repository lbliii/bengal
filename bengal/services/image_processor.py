"""Image processing service with caching.

Provides image processing using Pillow, with versioned cache and atomic writes.
All file I/O delegated to bengal.services.asset_io.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit

if TYPE_CHECKING:
    from bengal.core.resources.image import ProcessedImage
from bengal.core.resources.types import parse_spec
from bengal.services.asset_io import (
    load_pil_image,
    read_json_file,
    save_pil_image,
    write_json_file,
)

CACHE_SCHEMA_VERSION = 1
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
    """Image processing with caching. All I/O via asset_io."""

    CACHE_DIR = ".bengal/image-cache"

    def __init__(self, site: Any) -> None:
        self.site = site
        self.cache_dir = site.root_path / self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def process(
        self,
        source: Path,
        operation: str,
        spec: str,
    ) -> ProcessedImage | None:
        """Process image with caching."""
        try:
            if not source.exists():
                emit(self.site, "error", "image_not_found", source=str(source))
                return None

            params = parse_spec(spec)
            if params is None:
                emit(self.site, "error", "invalid_spec", spec=spec, source=str(source))
                return None

            cache_key = self._cache_key(source, operation, spec)
            cached = self._get_cached(cache_key, params)
            if cached:
                from bengal.core.resources.image import ImageResource, ProcessedImage

                return ProcessedImage(
                    source=ImageResource(source_path=source, site=self.site),
                    output_path=cached.output_path,
                    rel_permalink=cached.rel_permalink,
                    width=cached.width,
                    height=cached.height,
                    format=cached.format,
                    file_size=cached.file_size,
                )

            result = self._do_process(source, operation, params)
            if result is None:
                return None

            self._cache_result(cache_key, result)
            return result

        except FileNotFoundError:
            emit(self.site, "error", "image_not_found", source=str(source))
            return None
        except Exception as e:
            emit(
                self.site,
                "error",
                "image_process_error",
                source=str(source),
                operation=operation,
                spec=spec,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _cache_key(self, source: Path, operation: str, spec: str) -> str:
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
        output_format = params.format or "jpeg"
        output_ext = "jpg" if output_format == "jpeg" else output_format
        image_path = self.cache_dir / f"{cache_key}.{output_ext}"
        meta_path = self.cache_dir / f"{cache_key}.json"

        if not image_path.exists() or not meta_path.exists():
            return None

        meta = read_json_file(meta_path)
        if meta is None:
            return None

        try:
            return CachedResult(
                output_path=image_path,
                rel_permalink=meta["rel_permalink"],
                width=meta["width"],
                height=meta["height"],
                format=meta["format"],
                file_size=image_path.stat().st_size,
            )
        except KeyError:
            return None

    def _cache_result(self, cache_key: str, result: Any) -> None:
        meta_path = self.cache_dir / f"{cache_key}.json"
        meta = {
            "rel_permalink": result.rel_permalink,
            "width": result.width,
            "height": result.height,
            "format": result.format,
        }
        write_json_file(meta_path, meta, context=self.site)

    def _do_process(
        self,
        source: Path,
        operation: str,
        params: Any,
    ) -> ProcessedImage | None:
        try:
            import PIL  # noqa: F401
        except ImportError:
            emit(
                self.site,
                "error",
                "pillow_not_installed",
                hint="pip install bengal[images]",
            )
            return None

        img = load_pil_image(source, context=self.site)
        if img is None:
            return None

        # Memory optimization for large images
        if img.width * img.height > LARGE_IMAGE_THRESHOLD and params.width and params.height:
            img.draft(img.mode, (params.width * 2, params.height * 2))
            img.load()

        if params.format == "jpeg" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if operation == "fill":
            img = self._fill(img, params)
        elif operation == "fit":
            img = self._fit(img, params)
        elif operation == "resize":
            img = self._resize(img, params)
        elif operation == "filter":
            img = self._apply_filters(img, params)
        else:
            emit(self.site, "error", "unknown_operation", operation=operation)
            return None

        output_format = params.format or source.suffix[1:].lower()
        if output_format == "jpg":
            output_format = "jpeg"
        output_ext = "jpg" if output_format == "jpeg" else output_format
        cache_key = self._cache_key(source, operation, str(params))
        output_path = self.cache_dir / f"{cache_key}.{output_ext}"

        save_kwargs: dict[str, Any] = {}
        if output_format == "jpeg":
            save_kwargs["quality"] = params.quality
            save_kwargs["optimize"] = True
        elif output_format == "webp":
            save_kwargs["quality"] = params.quality
            save_kwargs["method"] = 4
        elif output_format == "png":
            save_kwargs["optimize"] = True

        if not save_pil_image(img, output_path, output_format, self.site, **save_kwargs):
            return None

        from bengal.core.resources.image import ImageResource, ProcessedImage

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

    def _fill(self, img: Any, params: Any) -> Any:
        from PIL import Image as PILImage
        from PIL import ImageOps

        target = (params.width, params.height)
        if target[0] is None or target[1] is None:
            return img
        if params.anchor == "smart":
            return self._smart_crop(img, target)
        centering = self._anchor_to_centering(params.anchor)
        return ImageOps.fit(img, target, method=PILImage.Resampling.LANCZOS, centering=centering)

    def _fit(self, img: Any, params: Any) -> Any:
        from PIL import Image as PILImage

        target_w = params.width or img.width
        target_h = params.height or img.height
        if img.width <= target_w and img.height <= target_h:
            return img
        img.thumbnail((target_w, target_h), PILImage.Resampling.LANCZOS)
        return img

    def _resize(self, img: Any, params: Any) -> Any:
        from PIL import Image as PILImage

        if params.width and not params.height:
            ratio = params.width / img.width
            new_height = int(img.height * ratio)
            return img.resize((params.width, new_height), PILImage.Resampling.LANCZOS)
        if params.height and not params.width:
            ratio = params.height / img.height
            new_width = int(img.width * ratio)
            return img.resize((new_width, params.height), PILImage.Resampling.LANCZOS)
        if params.width and params.height:
            return img.resize((params.width, params.height), PILImage.Resampling.LANCZOS)
        return img

    def _apply_filters(self, img: Any, params: Any) -> Any:
        from PIL import ImageFilter

        filter_spec = params.anchor.lower()
        if "grayscale" in filter_spec or "grey" in filter_spec:
            img = img.convert("L").convert("RGB")
        if "blur" in filter_spec:
            import re

            match = re.search(r"blur\s*(\d+)?", filter_spec)
            radius = int(match.group(1)) if match and match.group(1) else 2
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        return img

    def _smart_crop(
        self,
        img: Any,
        target: tuple[int, int],
    ) -> Any:
        from PIL import Image as PILImage

        try:
            import smartcrop  # type: ignore[import-not-found]

            sc = smartcrop.SmartCrop()
            result = sc.crop(img, target[0], target[1])
            box = (
                result["top_crop"]["x"],
                result["top_crop"]["y"],
                result["top_crop"]["x"] + result["top_crop"]["width"],
                result["top_crop"]["y"] + result["top_crop"]["height"],
            )
            return img.crop(box).resize(target, PILImage.Resampling.LANCZOS)
        except ImportError:
            from PIL import ImageOps

            return ImageOps.fit(img, target, method=PILImage.Resampling.LANCZOS)

    def _anchor_to_centering(self, anchor: str) -> tuple[float, float]:
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
    """Get image cache statistics."""
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
    """Clear the image cache."""
    import shutil

    cache_dir = site.root_path / ImageProcessor.CACHE_DIR
    if not cache_dir.exists():
        return 0
    count = sum(1 for p in cache_dir.iterdir() if p.is_file())
    shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return count
