"""
Unit tests for asset discovery.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.discovery.asset_discovery import AssetDiscovery


@pytest.fixture
def temp_assets_dir():
    """Create a temporary assets directory with test files."""
    temp_dir = Path(tempfile.mkdtemp())
    assets_dir = temp_dir / "assets"
    assets_dir.mkdir()

    # Create test assets
    (assets_dir / "style.css").write_text("body { color: blue; }")
    (assets_dir / "script.js").write_text("console.log('test');")
    (assets_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Minimal PNG
    (assets_dir / "logo.svg").write_text("<svg></svg>")
    (assets_dir / "font.woff2").write_bytes(b"WOFF2" + b"\x00" * 50)

    # Create subdirectory with assets
    (assets_dir / "css").mkdir()
    (assets_dir / "css" / "base.css").write_text("html { font-size: 16px; }")

    (assets_dir / "js").mkdir()
    (assets_dir / "js" / "app.js").write_text("alert('hi');")

    yield assets_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestAssetDiscovery:
    """Test asset discovery functionality."""

    def test_discovers_all_valid_assets(self, temp_assets_dir):
        """Test that all valid asset files are discovered."""
        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should find 7 assets (excluding any hidden or temp files)
        assert len(assets) == 7

        # Verify asset types
        asset_names = {asset.source_path.name for asset in assets}
        assert "style.css" in asset_names
        assert "script.js" in asset_names
        assert "image.png" in asset_names
        assert "logo.svg" in asset_names
        assert "font.woff2" in asset_names
        assert "base.css" in asset_names
        assert "app.js" in asset_names

    def test_skips_hidden_files(self, temp_assets_dir):
        """Test that hidden files are skipped."""
        # Create hidden files
        (temp_assets_dir / ".hidden.css").write_text("body { color: red; }")
        (temp_assets_dir / ".DS_Store").write_bytes(b"\x00" * 100)

        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should still find only 7 assets (hidden files skipped)
        assert len(assets) == 7
        asset_names = {asset.source_path.name for asset in assets}
        assert ".hidden.css" not in asset_names
        assert ".DS_Store" not in asset_names

    def test_skips_markdown_files(self, temp_assets_dir):
        """Test that markdown files are skipped."""
        # Create markdown files
        (temp_assets_dir / "README.md").write_text("# Assets")
        (temp_assets_dir / "CHANGELOG.md").write_text("## Changes")

        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should still find only 7 assets (markdown files skipped)
        assert len(assets) == 7
        asset_names = {asset.source_path.name for asset in assets}
        assert "README.md" not in asset_names
        assert "CHANGELOG.md" not in asset_names

    def test_skips_temp_files(self, temp_assets_dir):
        """Test that temporary files (.tmp) are skipped during discovery."""
        # Create temp files that might be left by atomic writes or image optimization
        (temp_assets_dir / "style.css.tmp").write_text("body { color: red; }")
        (temp_assets_dir / ".image.png.12345.67890.abc123.tmp").write_bytes(
            b"\x89PNG" + b"\x00" * 100
        )
        (temp_assets_dir / "script.js.tmp").write_text("console.log('temp');")

        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should still find only 7 assets (temp files skipped)
        assert len(assets) == 7
        asset_names = {asset.source_path.name for asset in assets}
        assert "style.css.tmp" not in asset_names
        assert ".image.png.12345.67890.abc123.tmp" not in asset_names
        assert "script.js.tmp" not in asset_names

    def test_discovers_nested_assets(self, temp_assets_dir):
        """Test that assets in nested directories are discovered."""
        # Create deeply nested assets
        (temp_assets_dir / "level1").mkdir()
        (temp_assets_dir / "level1" / "level2").mkdir()
        (temp_assets_dir / "level1" / "level2" / "nested.css").write_text("div { margin: 0; }")

        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should find 8 assets now (7 original + 1 nested)
        assert len(assets) == 8
        nested_asset = next(a for a in assets if a.source_path.name == "nested.css")
        assert nested_asset is not None

    def test_creates_missing_assets_directory(self):
        """Test that discovery creates assets directory if it doesn't exist."""
        temp_dir = Path(tempfile.mkdtemp())
        assets_dir = temp_dir / "assets"

        # Directory doesn't exist yet
        assert not assets_dir.exists()

        discovery = AssetDiscovery(assets_dir)
        assets = discovery.discover()

        # Directory should be created
        assert assets_dir.exists()
        assert len(assets) == 0  # Empty directory

        shutil.rmtree(temp_dir)

    def test_asset_output_paths_are_relative(self, temp_assets_dir):
        """Test that asset output paths are relative to assets directory."""
        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        for asset in assets:
            # Output path should be relative
            assert not asset.output_path.is_absolute()
            # Should not start with assets directory name
            assert str(asset.output_path) == str(asset.source_path.relative_to(temp_assets_dir))

    def test_handles_multiple_extensions(self, temp_assets_dir):
        """Test that files with multiple extensions are handled correctly."""
        # Create files with multiple extensions
        (temp_assets_dir / "bundle.min.js").write_text("console.log('min');")
        (temp_assets_dir / "style.min.css").write_text("body{margin:0}")

        discovery = AssetDiscovery(temp_assets_dir)
        assets = discovery.discover()

        # Should discover these files
        asset_names = {asset.source_path.name for asset in assets}
        assert "bundle.min.js" in asset_names
        assert "style.min.css" in asset_names

    def test_empty_directory(self):
        """Test discovery in an empty directory."""
        temp_dir = Path(tempfile.mkdtemp())
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()

        discovery = AssetDiscovery(assets_dir)
        assets = discovery.discover()

        assert len(assets) == 0

        shutil.rmtree(temp_dir)


@pytest.mark.parallel_unsafe
class TestAssetDiscoveryWithRaceConditions:
    """Test asset discovery behavior during parallel operations.

    Marked parallel_unsafe: Uses ThreadPoolExecutor internally, which conflicts
    with pytest-xdist's parallel test execution (nested parallelism causes worker crashes).
    """

    def test_ignores_temp_files_during_parallel_processing(self):
        """Test that temp files created during parallel processing are ignored."""
        import concurrent.futures
        import time

        temp_dir = Path(tempfile.mkdtemp())
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()

        # Create some real assets
        for i in range(3):
            (assets_dir / f"image{i}.png").write_bytes(b"\x89PNG" + b"\x00" * 100)

        def create_temp_files():
            """Simulate parallel processing creating temp files."""
            for i in range(3):
                temp_file = assets_dir / f".image{i}.png.12345.67890.abc{i}.tmp"
                temp_file.write_bytes(b"\x89PNG" + b"\x00" * 50)
                time.sleep(0.01)  # Small delay

        def discover_assets():
            """Run asset discovery."""
            discovery = AssetDiscovery(assets_dir)
            return discovery.discover()

        # Run discovery and temp file creation concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(create_temp_files)
            time.sleep(0.005)  # Let temp files start being created
            future2 = executor.submit(discover_assets)

            future1.result()
            assets = future2.result()

        # Should only find the 3 real PNG files, not the temp files
        assert len(assets) == 3
        asset_names = {asset.source_path.name for asset in assets}
        assert all(name.startswith("image") and name.endswith(".png") for name in asset_names)
        assert not any(".tmp" in name for name in asset_names)

        shutil.rmtree(temp_dir)
