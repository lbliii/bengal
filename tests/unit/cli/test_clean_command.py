"""
Test clean command with new cache options.
"""

from click.testing import CliRunner

from bengal.cli.commands.clean import clean


class TestCleanCommand:
    """Test clean command behavior."""

    def test_clean_default_preserves_cache(self, tmp_path):
        """Test that default clean preserves cache."""
        # Setup site
        self._create_test_site(tmp_path)

        # Create cache
        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        # Create output
        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html>test</html>")

        # Run clean
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert cache_file.exists(), "Cache should be preserved"
        assert not (output_dir / "index.html").exists(), "Output should be removed"

    def test_clean_with_cache_flag_removes_cache(self, tmp_path):
        """Test that --cache flag removes cache."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # Run clean with --cache
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", "--cache", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert not cache_dir.exists(), "Cache should be removed"

    def test_clean_with_all_flag_removes_cache(self, tmp_path):
        """Test that --all flag removes cache."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text('{"test": "data"}')

        # Run clean with --all
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", "--all", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert not cache_dir.exists(), "Cache should be removed"

    def test_clean_messaging_indicates_cache_status(self, tmp_path):
        """Test that clean command shows correct messaging."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()

        # Test default mode
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])
        assert "cache" in result.output.lower()

        # Recreate cache for second test
        cache_dir.mkdir(exist_ok=True)

        # Test cache mode
        result = runner.invoke(clean, ["--force", "--cache", str(tmp_path)])
        assert "cache" in result.output.lower()

    def test_clean_without_force_shows_prompt(self, tmp_path):
        """Test that clean without --force shows confirmation prompt."""
        # Setup
        self._create_test_site(tmp_path)

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # Run clean without --force, simulate cancel
        runner = CliRunner()
        result = runner.invoke(clean, [str(tmp_path)], input="n\n")

        # Should ask for confirmation and cancel
        assert "Proceed" in result.output or "Delete" in result.output
        assert "Cancelled" in result.output or result.exit_code != 0

    def test_clean_handles_missing_output_dir_gracefully(self, tmp_path):
        """Test that clean handles missing output directory."""
        # Setup site without output dir
        self._create_test_site(tmp_path)

        # Run clean (output dir doesn't exist)
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])

        # Should complete without error
        assert result.exit_code == 0

    def test_clean_cache_removes_entire_directory(self, tmp_path):
        """Test that --cache removes entire .bengal directory."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        (cache_dir / "cache.json").write_text('{"test": "data"}')
        (cache_dir / "other-file.txt").write_text("other data")

        # Run clean with --cache
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", "--cache", str(tmp_path)])

        # Verify entire directory removed
        assert result.exit_code == 0
        assert not cache_dir.exists()

    def test_clean_preserves_cache_with_output_removed(self, tmp_path):
        """Test that cache is preserved when output is removed."""
        # Setup
        self._create_test_site(tmp_path)

        cache_dir = tmp_path / ".bengal"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_content = '{"file_hashes": {"test": "hash"}}'
        cache_file.write_text(cache_content)

        output_dir = tmp_path / "public"
        output_dir.mkdir()
        (output_dir / "page1.html").write_text("<html>1</html>")
        (output_dir / "page2.html").write_text("<html>2</html>")

        # Run clean (default mode)
        runner = CliRunner()
        result = runner.invoke(clean, ["--force", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        assert cache_file.exists(), "Cache should be preserved"
        assert cache_file.read_text() == cache_content, "Cache content unchanged"
        # Output should be empty or not exist
        if output_dir.exists():
            assert len(list(output_dir.glob("*.html"))) == 0, "HTML files should be removed"

    def _create_test_site(self, tmp_path):
        """Helper to create test site structure."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        config_file = tmp_path / "bengal.toml"
        config_file.write_text(
            """
[site]
title = "Test Site"

[build]
output_dir = "public"
"""
        )
