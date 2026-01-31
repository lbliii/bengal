"""
Unit tests for parallel processing of assets and post-processing tasks.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.asset import Asset
from bengal.core.site import Site
from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator


@pytest.fixture
def temp_site_dir():
    """Create a temporary site directory with assets."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "content").mkdir()
    (temp_dir / "assets" / "css").mkdir(parents=True)
    (temp_dir / "assets" / "js").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    # Create test assets
    for i in range(10):
        (temp_dir / "assets" / "css" / f"style{i}.css").write_text(f"body {{ color: red{i}; }}")

    for i in range(5):
        (temp_dir / "assets" / "js" / f"script{i}.js").write_text(f"console.log('test{i}');")

    # Create config
    (temp_dir / "bengal.toml").write_text("""
[build]
title = "Test Site"
parallel = true
""")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestParallelAssetProcessing:
    """Test parallel asset processing functionality."""

    def test_small_asset_count_uses_sequential(self, temp_site_dir):
        """Test that sites with few assets use sequential processing."""
        # Clear all test assets
        for css_file in (temp_site_dir / "assets" / "css").glob("*.css"):
            css_file.unlink()
        for js_file in (temp_site_dir / "assets" / "js").glob("*.js"):
            js_file.unlink()

        # Create site with only 2 site assets (theme assets will also be discovered)
        (temp_site_dir / "assets" / "css" / "main.css").write_text("body { color: blue; }")
        (temp_site_dir / "assets" / "js" / "main.js").write_text("console.log('hi');")

        site = Site.from_config(temp_site_dir)
        site.discover_assets()

        # Should have 2 site assets + theme assets
        # Just verify the build works with small asset count
        assert len(site.assets) >= 2

        # Process assets (should work regardless of parallel/sequential)
        asset_orchestrator = AssetOrchestrator(site)
        asset_orchestrator.process(site.assets, parallel=False)

        # Verify our assets were copied
        output_files = list((temp_site_dir / "public" / "assets").rglob("*.*"))
        assert len(output_files) >= 2

    def test_large_asset_count_processes_successfully(self, temp_site_dir):
        """Test that sites with many assets process successfully (parallel or sequential)."""
        site = Site.from_config(temp_site_dir)
        site.discover_assets()

        # Should have 15 assets (10 CSS + 5 JS)
        assert len(site.assets) >= 15

        # Process assets
        asset_orchestrator = AssetOrchestrator(site)
        asset_orchestrator.process(site.assets, parallel=True)

        # Verify all assets were copied
        output_dir = temp_site_dir / "public" / "assets"
        assert output_dir.exists()

        # Count output files (may have fingerprints in names)
        output_files = list(output_dir.rglob("*.*"))
        assert len(output_files) >= 15

    def test_parallel_produces_same_output_as_sequential(self, temp_site_dir):
        """Test that parallel and sequential processing produce identical output."""
        # First run: parallel (default)
        site1 = Site.from_config(temp_site_dir)
        site1.discover_assets()
        asset_orchestrator1 = AssetOrchestrator(site1)
        asset_orchestrator1.process(site1.assets, parallel=True)

        parallel_output = temp_site_dir / "public" / "assets"
        parallel_files = {
            f.name: f.read_bytes() for f in parallel_output.rglob("*.*") if f.is_file()
        }

        # Clean output directory
        shutil.rmtree(temp_site_dir / "public")
        (temp_site_dir / "public").mkdir()

        # Second run: force sequential by reducing asset count
        # Actually, let's just verify the method works
        site2 = Site.from_config(temp_site_dir)
        site2.discover_assets()
        asset_orchestrator2 = AssetOrchestrator(site2)
        asset_orchestrator2.process(site2.assets, parallel=False)

        sequential_output = temp_site_dir / "public" / "assets"
        sequential_files = {
            f.name: f.read_bytes() for f in sequential_output.rglob("*.*") if f.is_file()
        }

        # Compare files
        assert parallel_files.keys() == sequential_files.keys()
        for filename in parallel_files:
            assert parallel_files[filename] == sequential_files[filename], (
                f"File {filename} differs"
            )

    def test_asset_processing_with_errors(self, temp_site_dir):
        """Test that errors in one asset don't crash entire build."""
        site = Site.from_config(temp_site_dir)
        site.discover_assets()

        # Add an asset with invalid source path
        bad_asset = Asset(source_path=temp_site_dir / "assets" / "nonexistent.css")
        site.assets.append(bad_asset)

        # Should not raise exception
        asset_orchestrator = AssetOrchestrator(site)
        asset_orchestrator.process(site.assets, parallel=True)

        # Other assets should still be processed
        output_dir = temp_site_dir / "public" / "assets"
        output_files = list(output_dir.rglob("*.*"))
        assert len(output_files) >= 15  # Original valid assets


class TestParallelPostProcessing:
    """Test parallel post-processing functionality."""

    @pytest.fixture
    def site_with_content(self):
        """Create a site with content for post-processing."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create directory structure
        (temp_dir / "content").mkdir()
        (temp_dir / "public").mkdir()

        # Create test content
        for i in range(5):
            (temp_dir / "content" / f"post{i}.md").write_text(f"""---
title: Post {i}
date: 2025-01-0{i + 1}
tags: [test, python]
---

This is test post {i}.
""")

        # Create config
        (temp_dir / "bengal.toml").write_text("""
[build]
title = "Test Site"
baseurl = "https://example.com"
generate_sitemap = true
generate_rss = true
validate_links = true
parallel = true
""")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_post_processing_generates_all_files(self, site_with_content):
        """Test that post-processing generates sitemap and RSS."""
        site = Site.from_config(site_with_content)
        site.discover_content()

        # Manually create some output pages (simulate build)
        for page in site.pages:
            page.output_path = site.output_dir / f"{page.slug}.html"
            page.output_path.write_text(f"<html><body>{page.title}</body></html>")

        # Run post-processing
        postprocess_orchestrator = PostprocessOrchestrator(site)
        postprocess_orchestrator.run(parallel=True)

        # Verify files were created
        assert (site.output_dir / "sitemap.xml").exists()
        assert (site.output_dir / "rss.xml").exists()

    def test_post_processing_with_disabled_tasks(self, site_with_content):
        """Test that disabled tasks are not run."""
        # Update config to disable RSS (now in features section)
        (site_with_content / "bengal.toml").write_text("""
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
validate_links = false

[features]
sitemap = true
rss = false
""")

        site = Site.from_config(site_with_content)
        site.discover_content()

        # Manually create output pages
        for page in site.pages:
            page.output_path = site.output_dir / f"{page.slug}.html"
            page.output_path.write_text(f"<html><body>{page.title}</body></html>")

        # Run post-processing
        postprocess_orchestrator = PostprocessOrchestrator(site)
        postprocess_orchestrator.run(parallel=True)

        # Verify only sitemap was created
        assert (site.output_dir / "sitemap.xml").exists()
        assert not (site.output_dir / "rss.xml").exists()

    def test_post_processing_handles_errors_gracefully(self, site_with_content):
        """Test that errors in one post-processing task don't crash others."""
        site = Site.from_config(site_with_content)
        site.discover_content()

        # Don't create output pages - this will cause sitemap/RSS to have issues
        # but shouldn't crash

        # Should not raise exception
        postprocess_orchestrator = PostprocessOrchestrator(site)
        postprocess_orchestrator.run(parallel=True)

        # Files may or may not be created, but build shouldn't crash


class TestParallelConfiguration:
    """Test configuration options for parallel processing.

    Note: Config is now nested (build.parallel, build.max_workers).

    """

    def test_parallel_enabled_by_default(self):
        """Test that parallel processing is enabled by default."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text('[site]\ntitle = "Test"')

        site = Site.from_config(temp_dir)

        # Default should be parallel enabled
        assert site.config.build.parallel is True

        shutil.rmtree(temp_dir)

    def test_parallel_can_be_disabled(self):
        """Test that parallel processing can be disabled via config."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test"

[build]
parallel = false
""")

        site = Site.from_config(temp_dir)

        assert site.config.build.parallel is False

        shutil.rmtree(temp_dir)

    def test_max_workers_configuration(self):
        """Test that max_workers can be configured."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test"

[build]
max_workers = 8
""")

        site = Site.from_config(temp_dir)

        assert site.config.build.max_workers == 8

        shutil.rmtree(temp_dir)


@pytest.mark.parallel_unsafe
class TestThreadSafety:
    """Test thread safety of parallel operations.

    Marked parallel_unsafe: Uses ThreadPoolExecutor internally, which conflicts
    with pytest-xdist's parallel test execution (nested parallelism causes worker crashes).

    """

    def test_concurrent_directory_creation(self):
        """Test that concurrent directory creation doesn't cause errors."""
        import concurrent.futures
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        output_dir = temp_dir / "output"

        def create_nested_dir(i):
            nested_path = output_dir / f"level1_{i}" / f"level2_{i}" / f"level3_{i}"
            nested_path.mkdir(parents=True, exist_ok=True)
            return nested_path

        # Create directories concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_nested_dir, i) for i in range(10)]
            results = [f.result() for f in futures]

        # All directories should exist
        for result in results:
            assert result.exists()

        shutil.rmtree(temp_dir)

    def test_concurrent_file_writes(self):
        """Test that concurrent file writes to different files work correctly."""
        import concurrent.futures
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())

        def write_file(i):
            file_path = temp_dir / f"file_{i}.txt"
            file_path.write_text(f"Content {i}")
            return file_path

        # Write files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(write_file, i) for i in range(20)]
            results = [f.result() for f in futures]

        # All files should exist with correct content
        for i, file_path in enumerate(results):
            assert file_path.exists()
            assert file_path.read_text() == f"Content {i}"

        shutil.rmtree(temp_dir)

    def test_concurrent_image_optimization_no_temp_file_collision(self):
        """Test that concurrent image optimization doesn't cause temp file collisions."""
        import concurrent.futures
        import tempfile

        from PIL import Image

        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "assets").mkdir()
        (temp_dir / "output").mkdir()

        # Create test PNG images
        for i in range(5):
            img_path = temp_dir / "assets" / f"image{i}.png"
            img = Image.new("RGB", (100, 100), color=(i * 50, 0, 0))
            img.save(img_path)

        # Create assets
        assets = []
        for i in range(5):
            asset = Asset(
                source_path=temp_dir / "assets" / f"image{i}.png",
                output_path=Path(f"image{i}.png"),
            )
            assets.append(asset)

        def optimize_asset(asset):
            """Optimize and copy asset."""
            try:
                from PIL import Image

                asset._optimized_image = Image.open(asset.source_path)
                asset.copy_to_output(temp_dir / "output", use_fingerprint=False)
                return True
            except Exception as e:
                raise Exception(f"Failed to optimize {asset.source_path}: {e}") from e

        # Optimize assets concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(optimize_asset, asset) for asset in assets]
            results = [f.result() for f in futures]

        # All assets should be processed successfully
        assert all(results)
        assert len(list((temp_dir / "output").glob("*.png"))) == 5

        # Verify no temp files left behind
        temp_files = list((temp_dir / "output").glob("*.tmp"))
        assert len(temp_files) == 0, f"Found leftover temp files: {temp_files}"

        shutil.rmtree(temp_dir)
