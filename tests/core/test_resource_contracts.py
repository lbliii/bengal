"""
Resource processing contract tests.

These tests verify resource handling contracts, particularly around:
- Image processing with correct PIL types
- Graceful handling of missing dependencies
- Cache key generation stability
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _pillow_available() -> bool:
    """Check if Pillow is installed."""
    try:
        from PIL import Image

        return True
    except ImportError:
        return False


class TestProcessParamsValidation:
    """Verify ProcessParams validation."""

    def test_quality_clamped_to_valid_range(self) -> None:
        """Quality values outside 1-100 are reset to 85."""
        from bengal.core.resources.types import ProcessParams

        # Too low
        params = ProcessParams(quality=0)
        assert params.quality == 85

        # Too high
        params = ProcessParams(quality=101)
        assert params.quality == 85

        # Valid
        params = ProcessParams(quality=50)
        assert params.quality == 50

    def test_default_anchor_is_center(self) -> None:
        """Default anchor position is center."""
        from bengal.core.resources.types import ProcessParams

        params = ProcessParams()
        assert params.anchor == "center"


class TestSpecParsing:
    """Verify spec string parsing."""

    def test_dimension_parsing(self) -> None:
        """Dimensions are parsed correctly."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("800x600")
        assert params is not None
        assert params.width == 800
        assert params.height == 600

    def test_width_only(self) -> None:
        """Width-only spec parsed correctly."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("800x")
        assert params is not None
        assert params.width == 800
        assert params.height is None

    def test_height_only(self) -> None:
        """Height-only spec parsed correctly."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("x600")
        assert params is not None
        assert params.width is None
        assert params.height == 600

    def test_format_parsing(self) -> None:
        """Format is parsed from spec."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("800x600 webp")
        assert params is not None
        assert params.format == "webp"

    def test_jpg_normalized_to_jpeg(self) -> None:
        """jpg format is normalized to jpeg."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("800x600 jpg")
        assert params is not None
        assert params.format == "jpeg"

    def test_quality_parsing(self) -> None:
        """Quality is parsed from qNN pattern."""
        from bengal.core.resources.types import parse_spec

        params = parse_spec("800x600 q75")
        assert params is not None
        assert params.quality == 75

    def test_anchor_parsing(self) -> None:
        """Anchor position is parsed."""
        from bengal.core.resources.types import parse_spec

        for anchor in ["center", "top", "bottom", "left", "right", "smart"]:
            params = parse_spec(f"800x600 {anchor}")
            assert params is not None
            assert params.anchor == anchor


class TestImageResourceGracefulDegradation:
    """Verify ImageResource handles missing dependencies gracefully."""

    def test_dimensions_return_zero_without_pillow(self) -> None:
        """Width/height return 0 when Pillow unavailable."""
        from bengal.core.resources.image import ImageResource

        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            # Force reimport to pick up mocked modules
            resource = ImageResource(
                source_path=Path("/fake/image.jpg"),
                site=None,
            )

            # Clear cached property if exists
            if hasattr(resource, "_dimensions"):
                del resource.__dict__["_dimensions"]

            # Should return 0, not crash
            assert resource.width == 0
            assert resource.height == 0

    def test_process_returns_none_without_site(self) -> None:
        """Image processing returns None without site context."""
        from bengal.core.resources.image import ImageResource

        resource = ImageResource(
            source_path=Path("/fake/image.jpg"),
            site=None,
        )

        result = resource.fill("800x600")
        assert result is None


class TestImageProcessorMethods:
    """Verify ImageProcessor method contracts."""

    @pytest.mark.skipif(not _pillow_available(), reason="Pillow not installed")
    def test_fill_requires_both_dimensions(self, tmp_path: Path) -> None:
        """_fill returns input image if dimensions missing."""
        from PIL import Image

        from bengal.core.resources.processor import ImageProcessor
        from bengal.core.resources.types import ProcessParams

        # Create test image
        img = Image.new("RGB", (100, 100), color="red")

        # Create processor with mock site
        site = MagicMock()
        site.root_path = tmp_path
        processor = ImageProcessor(site)

        # Missing height
        params = ProcessParams(width=50, height=None)
        result = processor._fill(img, params)

        # Should return original (unchanged)
        assert result.size == (100, 100)

    @pytest.mark.skipif(not _pillow_available(), reason="Pillow not installed")
    def test_fit_does_not_upscale(self, tmp_path: Path) -> None:
        """_fit doesn't upscale images."""
        from PIL import Image

        from bengal.core.resources.processor import ImageProcessor
        from bengal.core.resources.types import ProcessParams

        # Create small test image
        img = Image.new("RGB", (50, 50), color="blue")

        site = MagicMock()
        site.root_path = tmp_path
        processor = ImageProcessor(site)

        # Request larger size
        params = ProcessParams(width=100, height=100)
        result = processor._fit(img, params)

        # Should NOT upscale
        assert result.size == (50, 50)

    @pytest.mark.skipif(not _pillow_available(), reason="Pillow not installed")
    def test_resize_preserves_aspect_ratio_width_only(self, tmp_path: Path) -> None:
        """_resize preserves aspect ratio with width-only spec."""
        from PIL import Image

        from bengal.core.resources.processor import ImageProcessor
        from bengal.core.resources.types import ProcessParams

        # Create 100x50 image (2:1 aspect ratio)
        img = Image.new("RGB", (100, 50), color="green")

        site = MagicMock()
        site.root_path = tmp_path
        processor = ImageProcessor(site)

        # Resize to width=50, height should be 25
        params = ProcessParams(width=50, height=None)
        result = processor._resize(img, params)

        assert result.size == (50, 25)


class TestCacheKeyStability:
    """Verify cache keys are stable and deterministic."""

    def test_same_inputs_produce_same_key(self, tmp_path: Path) -> None:
        """Identical inputs produce identical cache keys."""
        from bengal.core.resources.processor import ImageProcessor

        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        site = MagicMock()
        site.root_path = tmp_path
        processor = ImageProcessor(site)

        key1 = processor._cache_key(test_file, "fill", "800x600")
        key2 = processor._cache_key(test_file, "fill", "800x600")

        assert key1 == key2

    def test_different_operations_produce_different_keys(self, tmp_path: Path) -> None:
        """Different operations produce different cache keys."""
        from bengal.core.resources.processor import ImageProcessor

        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        site = MagicMock()
        site.root_path = tmp_path
        processor = ImageProcessor(site)

        key_fill = processor._cache_key(test_file, "fill", "800x600")
        key_fit = processor._cache_key(test_file, "fit", "800x600")

        assert key_fill != key_fit
