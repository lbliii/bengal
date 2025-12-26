"""Tests for image processing pipeline.

RFC: hugo-inspired-features

Tests Hugo-style image processing:
- ImageResource model and properties
- Processing operations (fill, fit, resize, filter)
- Spec string parsing
- Cache behavior
- Format conversion
"""

from pathlib import Path

import pytest
from PIL import Image

from bengal.core.resources.image import ImageResource, ProcessedImage, parse_spec
from bengal.core.resources.processor import (
    CACHE_SCHEMA_VERSION,
    ImageProcessor,
    clear_cache,
    get_cache_stats,
)


class TestSpecParsing:
    """Test Hugo-style spec string parsing."""

    def test_dimensions_only(self):
        """Parse dimensions without format/quality."""
        params = parse_spec("800x600")
        assert params.width == 800
        assert params.height == 600
        assert params.format is None
        assert params.quality == 85  # default

    def test_width_only(self):
        """Parse width with auto height."""
        params = parse_spec("800x")
        assert params.width == 800
        assert params.height is None

    def test_height_only(self):
        """Parse height with auto width."""
        params = parse_spec("x600")
        assert params.width is None
        assert params.height == 600

    def test_with_format(self):
        """Parse with format conversion."""
        params = parse_spec("800x600 webp")
        assert params.format == "webp"

    def test_jpg_normalized_to_jpeg(self):
        """jpg is normalized to jpeg."""
        params = parse_spec("100x100 jpg")
        assert params.format == "jpeg"

    def test_with_quality(self):
        """Parse with quality setting."""
        params = parse_spec("800x600 q80")
        assert params.quality == 80

    def test_full_spec(self):
        """Parse full spec with all options."""
        params = parse_spec("800x600 webp q75 center")
        assert params.width == 800
        assert params.height == 600
        assert params.format == "webp"
        assert params.quality == 75
        assert params.anchor == "center"

    def test_anchor_positions(self):
        """Parse various anchor positions."""
        positions = [
            "center",
            "top",
            "bottom",
            "left",
            "right",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "smart",
        ]
        for pos in positions:
            params = parse_spec(f"100x100 {pos}")
            assert params.anchor == pos

    def test_unknown_parts_tolerated(self):
        """Unknown spec parts are logged but tolerated."""
        params = parse_spec("800x600 unknownarg")
        assert params is not None
        assert params.width == 800


class TestImageResource:
    """Test ImageResource model."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image."""
        img = Image.new("RGB", (200, 100), color="blue")
        path = tmp_path / "assets" / "images" / "test.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "JPEG")
        return path

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site object."""

        class MockSite:
            def __init__(self):
                self.root_path = tmp_path

        return MockSite()

    def test_dimensions(self, test_image, mock_site):
        """ImageResource reports correct dimensions."""
        resource = ImageResource(source_path=test_image, site=mock_site)
        assert resource.width == 200
        assert resource.height == 100

    def test_exists(self, test_image, mock_site):
        """exists property is correct."""
        resource = ImageResource(source_path=test_image, site=mock_site)
        assert resource.exists is True

        missing = ImageResource(source_path=Path("/nonexistent.jpg"), site=mock_site)
        assert missing.exists is False

    def test_name_properties(self, test_image, mock_site):
        """Name properties are correct."""
        resource = ImageResource(source_path=test_image, site=mock_site)
        assert resource.name == "test.jpg"
        assert resource.stem == "test"
        assert resource.suffix == ".jpg"

    def test_bool(self, test_image, mock_site):
        """ImageResource is truthy when exists."""
        exists = ImageResource(source_path=test_image, site=mock_site)
        assert bool(exists) is True

        missing = ImageResource(source_path=Path("/missing.jpg"), site=mock_site)
        assert bool(missing) is False

    def test_str_returns_url(self, test_image, mock_site):
        """str() returns rel_permalink."""
        resource = ImageResource(source_path=test_image, site=mock_site)
        assert str(resource) == resource.rel_permalink


class TestImageProcessor:
    """Test image processing operations."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a 200x100 test image."""
        img = Image.new("RGB", (200, 100), color="red")
        path = tmp_path / "source.jpg"
        img.save(path, "JPEG")
        return path

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site object."""

        class MockSite:
            def __init__(self):
                self.root_path = tmp_path

        return MockSite()

    def test_resize_width_only(self, test_image, mock_site):
        """resize() with width only preserves aspect ratio."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "resize", "100x")

        assert result is not None
        assert result.width == 100
        assert result.height == 50  # 2:1 aspect preserved

    def test_resize_height_only(self, test_image, mock_site):
        """resize() with height only preserves aspect ratio."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "resize", "x50")

        assert result is not None
        assert result.width == 100  # 2:1 aspect preserved
        assert result.height == 50

    def test_fill_exact_dimensions(self, test_image, mock_site):
        """fill() crops to exact dimensions."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "fill", "50x50")

        assert result is not None
        assert result.width == 50
        assert result.height == 50

    def test_fit_preserves_aspect(self, test_image, mock_site):
        """fit() scales to fit within box."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "fit", "50x50")

        assert result is not None
        assert result.width == 50
        assert result.height == 25  # 2:1 aspect preserved

    def test_fit_no_upscale(self, test_image, mock_site):
        """fit() doesn't upscale images."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "fit", "400x400")

        assert result is not None
        # Original is 200x100, should not upscale
        assert result.width <= 200
        assert result.height <= 100

    def test_format_conversion_webp(self, test_image, mock_site):
        """Processing can convert to WebP."""
        processor = ImageProcessor(mock_site)
        result = processor.process(test_image, "resize", "100x webp")

        assert result is not None
        assert result.format == "webp"
        assert result.output_path.suffix == ".webp"

    def test_quality_setting(self, test_image, mock_site):
        """Quality setting affects output."""
        processor = ImageProcessor(mock_site)

        # High quality
        high = processor.process(test_image, "resize", "100x q95")
        # Low quality
        low = processor.process(test_image, "resize", "100x q10")

        assert high is not None
        assert low is not None
        # Low quality should be smaller
        assert low.file_size < high.file_size

    def test_missing_image_returns_none(self, mock_site):
        """Processing missing image returns None."""
        processor = ImageProcessor(mock_site)
        result = processor.process(Path("/nonexistent.jpg"), "resize", "100x")
        assert result is None


class TestImageCache:
    """Test image processing cache behavior."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image."""
        img = Image.new("RGB", (100, 100), color="green")
        path = tmp_path / "test.jpg"
        img.save(path, "JPEG")
        return path

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site object."""

        class MockSite:
            def __init__(self):
                self.root_path = tmp_path

        return MockSite()

    def test_cache_hit(self, test_image, mock_site):
        """Second processing of same image hits cache."""
        processor = ImageProcessor(mock_site)

        # First processing
        result1 = processor.process(test_image, "resize", "50x")
        # Second processing (should hit cache)
        result2 = processor.process(test_image, "resize", "50x")

        assert result1 is not None
        assert result2 is not None
        assert result1.output_path == result2.output_path

    def test_cache_stats(self, test_image, mock_site):
        """get_cache_stats returns correct info."""
        processor = ImageProcessor(mock_site)
        processor.process(test_image, "resize", "50x")

        stats = get_cache_stats(mock_site)
        assert stats["version"] == CACHE_SCHEMA_VERSION
        assert stats["count"] >= 2  # Image + metadata
        assert stats["size_bytes"] > 0

    def test_clear_cache(self, test_image, mock_site):
        """clear_cache removes cached images."""
        processor = ImageProcessor(mock_site)
        processor.process(test_image, "resize", "50x")

        # Clear cache
        count = clear_cache(mock_site)
        assert count > 0

        # Cache should be empty
        stats = get_cache_stats(mock_site)
        assert stats["count"] == 0


class TestProcessedImage:
    """Test ProcessedImage model."""

    def test_str_returns_url(self, tmp_path):
        """str() returns rel_permalink."""
        from bengal.core.resources.image import ImageResource

        processed = ProcessedImage(
            source=ImageResource(source_path=Path("/x.jpg"), site=None),
            output_path=tmp_path / "out.jpg",
            rel_permalink="/assets/cache/out.jpg",
            width=100,
            height=100,
            format="jpeg",
            file_size=1000,
        )

        assert str(processed) == "/assets/cache/out.jpg"
