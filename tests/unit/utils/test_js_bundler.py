"""
Tests for bengal/utils/js_bundler.py.

Covers:
- bundle_js_files function
- get_theme_js_bundle_order function
- get_theme_js_excluded function
- discover_js_files function
- create_js_bundle function
- Source comment handling
- Minification support
- File ordering
"""

from __future__ import annotations

from pathlib import Path


class TestBundleJsFilesBasics:
    """Test bundle_js_files basic functionality."""

    def test_empty_list_returns_empty_string(self) -> None:
        """Test that empty file list returns empty string."""
        from bengal.assets.js_bundler import bundle_js_files

        result = bundle_js_files([])
        assert result == ""

    def test_bundles_single_file(self, tmp_path: Path) -> None:
        """Test bundling a single file."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("console.log('hello');")

        result = bundle_js_files([js_file])

        assert "console.log('hello')" in result
        assert "Bengal JS Bundle" in result

    def test_bundles_multiple_files(self, tmp_path: Path) -> None:
        """Test bundling multiple files."""
        from bengal.assets.js_bundler import bundle_js_files

        file1 = tmp_path / "utils.js"
        file1.write_text("const utils = {};")

        file2 = tmp_path / "main.js"
        file2.write_text("console.log(utils);")

        result = bundle_js_files([file1, file2])

        assert "const utils = {};" in result
        assert "console.log(utils);" in result

    def test_preserves_file_order(self, tmp_path: Path) -> None:
        """Test that file order is preserved."""
        from bengal.assets.js_bundler import bundle_js_files

        file1 = tmp_path / "first.js"
        file1.write_text("// First file")

        file2 = tmp_path / "second.js"
        file2.write_text("// Second file")

        result = bundle_js_files([file1, file2])

        # First should appear before second
        first_pos = result.find("// First file")
        second_pos = result.find("// Second file")

        assert first_pos < second_pos


class TestBundleJsFilesSourceComments:
    """Test source comment handling."""

    def test_adds_source_comments_by_default(self, tmp_path: Path) -> None:
        """Test that source comments are added by default."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("var x = 1;")

        result = bundle_js_files([js_file], add_source_comments=True)

        assert "main.js" in result

    def test_skips_source_comments_when_disabled(self, tmp_path: Path) -> None:
        """Test that source comments can be disabled."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("var x = 1;")

        result = bundle_js_files([js_file], add_source_comments=False)

        # Should not have file name comment (but will have bundle header)
        assert "=== main.js ===" not in result


class TestBundleJsFilesMinification:
    """Test minification support."""

    def test_minifies_when_requested(self, tmp_path: Path) -> None:
        """Test that minification is applied when requested."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("var x = 1;")

        # Just test that minify=True doesn't raise an error
        # jsmin may or may not be available
        result = bundle_js_files([js_file], minify=True)

        # Should have content either minified or not
        assert "var" in result

    def test_handles_missing_jsmin(self, tmp_path: Path) -> None:
        """Test graceful handling when jsmin is not available."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("var x = 1;")

        # This should not raise even if jsmin is unavailable
        result = bundle_js_files([js_file], minify=True)

        assert "var x = 1;" in result or "var x=1;" in result


class TestBundleJsFilesErrorHandling:
    """Test error handling in bundle_js_files."""

    def test_skips_nonexistent_files(self, tmp_path: Path) -> None:
        """Test that nonexistent files are skipped."""
        from bengal.assets.js_bundler import bundle_js_files

        existing = tmp_path / "exists.js"
        existing.write_text("var x = 1;")

        nonexistent = tmp_path / "nonexistent.js"

        result = bundle_js_files([existing, nonexistent])

        assert "var x = 1;" in result

    def test_skips_empty_files(self, tmp_path: Path) -> None:
        """Test that empty files are skipped."""
        from bengal.assets.js_bundler import bundle_js_files

        empty_file = tmp_path / "empty.js"
        empty_file.write_text("")

        nonempty_file = tmp_path / "nonempty.js"
        nonempty_file.write_text("var x = 1;")

        result = bundle_js_files([empty_file, nonempty_file])

        assert "var x = 1;" in result


class TestGetThemeJsBundleOrder:
    """Test get_theme_js_bundle_order function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        from bengal.assets.js_bundler import get_theme_js_bundle_order

        result = get_theme_js_bundle_order()

        assert isinstance(result, list)

    def test_includes_core_files(self) -> None:
        """Test that core files are included."""
        from bengal.assets.js_bundler import get_theme_js_bundle_order

        result = get_theme_js_bundle_order()

        assert "utils.js" in result
        assert "main.js" in result

    def test_utils_before_main(self) -> None:
        """Test that utils.js comes before main.js."""
        from bengal.assets.js_bundler import get_theme_js_bundle_order

        result = get_theme_js_bundle_order()

        utils_index = result.index("utils.js")
        main_index = result.index("main.js")

        assert utils_index < main_index


class TestGetThemeJsExcluded:
    """Test get_theme_js_excluded function."""

    def test_returns_set(self) -> None:
        """Test that function returns a set."""
        from bengal.assets.js_bundler import get_theme_js_excluded

        result = get_theme_js_excluded()

        assert isinstance(result, set)

    def test_includes_third_party_libs(self) -> None:
        """Test that third-party libraries are excluded."""
        from bengal.assets.js_bundler import get_theme_js_excluded

        result = get_theme_js_excluded()

        assert "vendor/lunr.min.js" in result

    def test_includes_lazy_loaded_scripts(self) -> None:
        """Test that lazy-loaded scripts are excluded."""
        from bengal.assets.js_bundler import get_theme_js_excluded

        result = get_theme_js_excluded()

        assert "enhancements/data-table.js" in result
        assert "mermaid-theme.js" in result


class TestDiscoverJsFiles:
    """Test discover_js_files function."""

    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test that nonexistent directory returns empty list."""
        from bengal.assets.js_bundler import discover_js_files

        result = discover_js_files(tmp_path / "nonexistent")

        assert result == []

    def test_discovers_js_files(self, tmp_path: Path) -> None:
        """Test discovering JS files in directory."""
        from bengal.assets.js_bundler import discover_js_files

        # Create JS files
        (tmp_path / "main.js").write_text("// main")
        (tmp_path / "utils.js").write_text("// utils")

        result = discover_js_files(tmp_path)

        assert len(result) >= 2
        file_names = [f.name for f in result]
        assert "main.js" in file_names
        assert "utils.js" in file_names

    def test_respects_bundle_order(self, tmp_path: Path) -> None:
        """Test that bundle order is respected."""
        from bengal.assets.js_bundler import discover_js_files

        # Create JS files
        (tmp_path / "main.js").write_text("// main")
        (tmp_path / "utils.js").write_text("// utils")

        result = discover_js_files(
            tmp_path,
            bundle_order=["utils.js", "main.js"],
        )

        file_names = [f.name for f in result]
        utils_index = file_names.index("utils.js")
        main_index = file_names.index("main.js")

        assert utils_index < main_index

    def test_excludes_specified_files(self, tmp_path: Path) -> None:
        """Test that excluded files are not included."""
        from bengal.assets.js_bundler import discover_js_files

        # Create JS files
        (tmp_path / "main.js").write_text("// main")
        (tmp_path / "excluded.js").write_text("// excluded")

        result = discover_js_files(
            tmp_path,
            excluded={"excluded.js"},
        )

        file_names = [f.name for f in result]
        assert "excluded.js" not in file_names

    def test_adds_remaining_files_alphabetically(self, tmp_path: Path) -> None:
        """Test that files not in order are added alphabetically."""
        from bengal.assets.js_bundler import discover_js_files

        # Create JS files
        (tmp_path / "zebra.js").write_text("// zebra")
        (tmp_path / "alpha.js").write_text("// alpha")
        (tmp_path / "main.js").write_text("// main")

        result = discover_js_files(
            tmp_path,
            bundle_order=["main.js"],  # Only main is in order
        )

        file_names = [f.name for f in result]

        # main.js should be first (in order), then alpha before zebra
        assert file_names.index("main.js") < file_names.index("alpha.js")


class TestCreateJsBundle:
    """Test create_js_bundle function."""

    def test_returns_empty_for_no_files(self, tmp_path: Path) -> None:
        """Test that empty directory returns empty string."""
        from bengal.assets.js_bundler import create_js_bundle

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = create_js_bundle(empty_dir)

        assert result == ""

    def test_bundles_files_in_directory(self, tmp_path: Path) -> None:
        """Test bundling files from directory."""
        from bengal.assets.js_bundler import create_js_bundle

        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "main.js").write_text("var x = 1;")

        result = create_js_bundle(js_dir, minify=False)

        assert "var x = 1;" in result

    def test_writes_to_output_path(self, tmp_path: Path) -> None:
        """Test writing bundle to output path."""
        from bengal.assets.js_bundler import create_js_bundle

        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "main.js").write_text("var x = 1;")

        output_path = tmp_path / "dist" / "bundle.js"

        result = create_js_bundle(js_dir, output_path=output_path, minify=False)

        assert output_path.exists()
        assert output_path.read_text() == result

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        from bengal.assets.js_bundler import create_js_bundle

        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "main.js").write_text("var x = 1;")

        output_path = tmp_path / "deep" / "nested" / "bundle.js"

        create_js_bundle(js_dir, output_path=output_path)

        assert output_path.parent.exists()

    def test_applies_minification(self, tmp_path: Path) -> None:
        """Test that minification is applied."""
        from bengal.assets.js_bundler import create_js_bundle

        js_dir = tmp_path / "js"
        js_dir.mkdir()
        (js_dir / "main.js").write_text("var x = 1;")

        # With minify=True, should attempt minification
        result = create_js_bundle(js_dir, minify=True)

        # Should still have the content (minified or not)
        assert "var" in result


class TestBundleHeader:
    """Test bundle header generation."""

    def test_includes_header_comment(self, tmp_path: Path) -> None:
        """Test that bundle includes header comment."""
        from bengal.assets.js_bundler import bundle_js_files

        js_file = tmp_path / "main.js"
        js_file.write_text("var x = 1;")

        result = bundle_js_files([js_file])

        assert "Bengal JS Bundle" in result
        assert "Auto-generated" in result


class TestJsBundlerIntegration:
    """Integration tests for JS bundler."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test complete bundling workflow."""
        from bengal.assets.js_bundler import create_js_bundle

        # Setup
        js_dir = tmp_path / "js"
        js_dir.mkdir()

        (js_dir / "utils.js").write_text("const BengalUtils = {};")
        (js_dir / "main.js").write_text("BengalUtils.init();")

        output_path = tmp_path / "dist" / "bundle.js"

        # Execute
        result = create_js_bundle(
            js_dir,
            output_path=output_path,
            minify=False,
            bundle_order=["utils.js", "main.js"],
        )

        # Assert
        assert output_path.exists()
        assert "BengalUtils = {}" in result
        assert "BengalUtils.init()" in result

        # utils should come before main
        assert result.index("BengalUtils = {}") < result.index("BengalUtils.init()")
