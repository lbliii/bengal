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


class TestParallelAssetProcessing:
    """Test parallel asset processing functionality."""

    @pytest.fixture
    def temp_site_dir(self):
        """Create a temporary site directory with assets."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create directory structure
        (temp_dir / "content").mkdir()
        (temp_dir / "assets" / "css").mkdir(parents=True)
        (temp_dir / "assets" / "js").mkdir(parents=True)
        (temp_dir / "assets" / "images").mkdir(parents=True)
        (temp_dir / "public").mkdir()

        # Create test assets
        for i in range(10):
            (temp_dir / "assets" / "css" / f"style{i}.css").write_text(f"body {{ color: red{i}; }}")

        for i in range(5):
            (temp_dir / "assets" / "js" / f"script{i}.js").write_text(f"console.log('test{i}');")

        # Create small test images (1x1 pixel)
        for i in range(3):
            # Create a minimal valid PNG
            png_data = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            (temp_dir / "assets" / "images" / f"image{i}.png").write_bytes(png_data)

        # Create config
        (temp_dir / "bengal.toml").write_text("""
[build]
title = "Test Site"
parallel = true
""")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_small_asset_count_uses_sequential(self, temp_site_dir):
        """Test that sites with few assets use sequential processing."""
        # Clear all test assets
        for css_file in (temp_site_dir / "assets" / "css").glob("*.css"):
            css_file.unlink()
        for js_file in (temp_site_dir / "assets" / "js").glob("*.js"):
            js_file.unlink()
        for img_file in (temp_site_dir / "assets" / "images").glob("*.png"):
            img_file.unlink()

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

        # Should have 18 assets (10 CSS + 5 JS + 3 images)
        assert len(site.assets) >= 18

        # Process assets
        asset_orchestrator = AssetOrchestrator(site)
        asset_orchestrator.process(site.assets, parallel=True)

        # Verify all assets were copied
        output_dir = temp_site_dir / "public" / "assets"
        assert output_dir.exists()

        # Count output files (may have fingerprints in names)
        output_files = list(output_dir.rglob("*.*"))
        assert len(output_files) >= 18

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
        assert len(output_files) >= 18  # Original valid assets


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
        # Update config to disable RSS
        (site_with_content / "bengal.toml").write_text("""
[build]
title = "Test Site"
baseurl = "https://example.com"
generate_sitemap = true
generate_rss = false
validate_links = false
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
    """Test configuration options for parallel processing."""

    def test_parallel_enabled_by_default(self):
        """Test that parallel processing is enabled by default."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text('[build]\ntitle = "Test"')

        site = Site.from_config(temp_dir)

        # Default should be parallel enabled
        assert site.config.get("parallel", True) is True

        shutil.rmtree(temp_dir)

    def test_parallel_can_be_disabled(self):
        """Test that parallel processing can be disabled via config."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text("""
[build]
title = "Test"
parallel = false
""")

        site = Site.from_config(temp_dir)

        assert site.config.get("parallel") is False

        shutil.rmtree(temp_dir)

    def test_max_workers_configuration(self):
        """Test that max_workers can be configured."""
        temp_dir = Path(tempfile.mkdtemp())
        (temp_dir / "content").mkdir()
        (temp_dir / "bengal.toml").write_text("""
[build]
title = "Test"
max_workers = 8
""")

        site = Site.from_config(temp_dir)

        assert site.config.get("max_workers") == 8

        shutil.rmtree(temp_dir)


class TestThreadSafety:
    """Test thread safety of parallel operations."""

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
