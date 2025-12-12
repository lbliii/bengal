"""
Unit tests for BengalPaths class.

Tests the single source of truth for all .bengal directory paths.
"""

from pathlib import Path

from bengal.cache.paths import STATE_DIR_NAME, BengalPaths


class TestBengalPaths:
    """Test suite for BengalPaths."""

    def test_state_dir_name_constant(self):
        """Test STATE_DIR_NAME is '.bengal'."""
        assert STATE_DIR_NAME == ".bengal"

    def test_state_dir_under_root(self, tmp_path: Path):
        """Test .bengal is directly under root."""
        paths = BengalPaths(tmp_path)

        assert paths.state_dir == tmp_path / ".bengal"
        assert paths.state_dir.parent == tmp_path

    def test_all_paths_under_state_dir(self, tmp_path: Path):
        """Test all path properties are under .bengal."""
        paths = BengalPaths(tmp_path)
        state_dir = paths.state_dir

        # All file paths should be under .bengal
        file_paths = [
            paths.build_cache,
            paths.page_cache,
            paths.asset_cache,
            paths.taxonomy_cache,
            paths.build_log,
            paths.serve_log,
            paths.build_history,
            paths.server_pid,
            paths.asset_manifest,
            paths.swizzle_registry,
        ]

        for file_path in file_paths:
            assert str(file_path).startswith(str(state_dir)), f"{file_path} not under {state_dir}"

        # All directory paths should be under .bengal
        dir_paths = [
            paths.indexes_dir,
            paths.templates_dir,
            paths.content_dir,
            paths.generated_dir,
            paths.logs_dir,
            paths.metrics_dir,
            paths.profiles_dir,
            paths.themes_dir,
            paths.js_bundle_dir,
            paths.pipeline_out_dir,
        ]

        for dir_path in dir_paths:
            assert str(dir_path).startswith(str(state_dir)), f"{dir_path} not under {state_dir}"

    def test_paths_are_path_objects(self, tmp_path: Path):
        """Test all path properties return Path objects."""
        paths = BengalPaths(tmp_path)

        all_paths = [
            paths.root,
            paths.state_dir,
            paths.build_cache,
            paths.page_cache,
            paths.asset_cache,
            paths.taxonomy_cache,
            paths.indexes_dir,
            paths.templates_dir,
            paths.content_dir,
            paths.generated_dir,
            paths.logs_dir,
            paths.build_log,
            paths.serve_log,
            paths.metrics_dir,
            paths.profiles_dir,
            paths.build_history,
            paths.server_pid,
            paths.asset_manifest,
            paths.themes_dir,
            paths.swizzle_registry,
            paths.js_bundle_dir,
            paths.pipeline_out_dir,
        ]

        for path in all_paths:
            assert isinstance(path, Path), f"{path} is not a Path object"

    def test_ensure_dirs_creates_directories(self, tmp_path: Path):
        """Test ensure_dirs creates all necessary directories."""
        paths = BengalPaths(tmp_path)

        # Directories should not exist yet
        assert not paths.state_dir.exists()
        assert not paths.indexes_dir.exists()
        assert not paths.templates_dir.exists()

        # Create directories
        paths.ensure_dirs()

        # All directories should now exist
        expected_dirs = [
            paths.state_dir,
            paths.indexes_dir,
            paths.templates_dir,
            paths.content_dir,
            paths.generated_dir,
            paths.logs_dir,
            paths.metrics_dir,
            paths.profiles_dir,
            paths.themes_dir,
            paths.js_bundle_dir,
            paths.pipeline_out_dir,
        ]

        for directory in expected_dirs:
            assert directory.exists(), f"Directory not created: {directory}"
            assert directory.is_dir(), f"Not a directory: {directory}"

    def test_ensure_dirs_idempotent(self, tmp_path: Path):
        """Test ensure_dirs can be called multiple times safely."""
        paths = BengalPaths(tmp_path)

        # Call ensure_dirs multiple times
        paths.ensure_dirs()
        paths.ensure_dirs()
        paths.ensure_dirs()

        # Should still work, no errors
        assert paths.state_dir.exists()

    def test_build_cache_path(self, tmp_path: Path):
        """Test build_cache returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "cache.json"
        assert paths.build_cache == expected

    def test_page_cache_path(self, tmp_path: Path):
        """Test page_cache returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "page_metadata.json"
        assert paths.page_cache == expected

    def test_asset_cache_path(self, tmp_path: Path):
        """Test asset_cache returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "asset_deps.json"
        assert paths.asset_cache == expected

    def test_taxonomy_cache_path(self, tmp_path: Path):
        """Test taxonomy_cache returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "taxonomy_index.json"
        assert paths.taxonomy_cache == expected

    def test_indexes_dir_path(self, tmp_path: Path):
        """Test indexes_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "indexes"
        assert paths.indexes_dir == expected

    def test_templates_dir_path(self, tmp_path: Path):
        """Test templates_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "templates"
        assert paths.templates_dir == expected

    def test_content_dir_path(self, tmp_path: Path):
        """Test content_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "content_cache"
        assert paths.content_dir == expected

    def test_generated_dir_path(self, tmp_path: Path):
        """Test generated_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "generated"
        assert paths.generated_dir == expected

    def test_logs_dir_path(self, tmp_path: Path):
        """Test logs_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "logs"
        assert paths.logs_dir == expected

    def test_build_log_path(self, tmp_path: Path):
        """Test build_log returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "logs" / "build.log"
        assert paths.build_log == expected

    def test_serve_log_path(self, tmp_path: Path):
        """Test serve_log returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "logs" / "serve.log"
        assert paths.serve_log == expected

    def test_metrics_dir_path(self, tmp_path: Path):
        """Test metrics_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "metrics"
        assert paths.metrics_dir == expected

    def test_profiles_dir_path(self, tmp_path: Path):
        """Test profiles_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "profiles"
        assert paths.profiles_dir == expected

    def test_build_history_path(self, tmp_path: Path):
        """Test build_history returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "build_history.json"
        assert paths.build_history == expected

    def test_server_pid_path(self, tmp_path: Path):
        """Test server_pid returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "server.pid"
        assert paths.server_pid == expected

    def test_asset_manifest_path(self, tmp_path: Path):
        """Test asset_manifest returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "asset-manifest.json"
        assert paths.asset_manifest == expected

    def test_themes_dir_path(self, tmp_path: Path):
        """Test themes_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "themes"
        assert paths.themes_dir == expected

    def test_swizzle_registry_path(self, tmp_path: Path):
        """Test swizzle_registry returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "themes" / "sources.json"
        assert paths.swizzle_registry == expected

    def test_js_bundle_dir_path(self, tmp_path: Path):
        """Test js_bundle_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "js_bundle"
        assert paths.js_bundle_dir == expected

    def test_pipeline_out_dir_path(self, tmp_path: Path):
        """Test pipeline_out_dir returns correct path."""
        paths = BengalPaths(tmp_path)

        expected = tmp_path / ".bengal" / "pipeline_out"
        assert paths.pipeline_out_dir == expected

    def test_repr(self, tmp_path: Path):
        """Test __repr__ returns useful string."""
        paths = BengalPaths(tmp_path)

        repr_str = repr(paths)

        assert "BengalPaths" in repr_str
        assert str(tmp_path) in repr_str

    def test_legacy_path_compatibility(self, tmp_path: Path):
        """Test paths match current hardcoded strings for backwards compatibility."""
        paths = BengalPaths(tmp_path)

        # These should match current hardcoded paths in the codebase
        assert paths.build_cache.name == "cache.json"
        assert paths.page_cache.name == "page_metadata.json"
        assert paths.asset_cache.name == "asset_deps.json"
        assert paths.taxonomy_cache.name == "taxonomy_index.json"
        assert paths.build_history.name == "build_history.json"
        assert paths.server_pid.name == "server.pid"
        assert paths.swizzle_registry.name == "sources.json"
        assert paths.asset_manifest.name == "asset-manifest.json"

    def test_different_roots_have_different_paths(self):
        """Test that different roots produce different paths."""
        paths1 = BengalPaths(Path("/site1"))
        paths2 = BengalPaths(Path("/site2"))

        assert paths1.build_cache != paths2.build_cache
        assert paths1.state_dir != paths2.state_dir
        assert str(paths1.build_cache).startswith("/site1")
        assert str(paths2.build_cache).startswith("/site2")
