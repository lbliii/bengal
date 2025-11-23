"""
Unit tests for asset processing functionality in Asset class.

Tests cover:
- CSS minification (with/without lightningcss)
- JavaScript minification
- CSS nesting transformation
- Asset fingerprinting
- Image optimization
- Copy to output
"""

import importlib.util
import tempfile
from pathlib import Path

import pytest

from bengal.core.asset import Asset


@pytest.fixture
def temp_asset_dir():
    """Create a temporary directory for asset tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


class TestCSSMinification:
    """Test CSS minification functionality."""

    def test_minifies_css_without_lightningcss(self, temp_asset_dir):
        """Test CSS minification fallback when lightningcss is unavailable."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("""
/* Comment */
body {
    color: blue;
    margin: 0;
}
""")

        asset = Asset(source_path=css_file)
        asset.minify()

        assert asset.minified is True
        assert hasattr(asset, "_minified_content")
        # Comments should be removed, whitespace reduced
        minified = asset._minified_content
        assert "Comment" not in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_minifies_bundled_css(self, temp_asset_dir):
        """Test that bundled CSS content is minified."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("""
/* Comment that will be stripped */
body { color: blue; }
""")

        asset = Asset(source_path=css_file)
        # Simulate bundled content
        asset._bundled_content = "/* Bundled */\nbody { color: blue; margin: 0; }"
        asset.minify()

        assert asset.minified is True
        # Should minify the bundled content, not the source
        minified = asset._minified_content
        assert "Bundled" not in minified

    def test_handles_css_nesting_transformation(self, temp_asset_dir):
        """Test that CSS nesting is transformed when lightningcss unavailable."""
        css_file = temp_asset_dir / "nested.css"
        css_file.write_text("""
.button {
    color: blue;
    &:hover {
        color: red;
    }
    &.active {
        font-weight: bold;
    }
}
""")

        asset = Asset(source_path=css_file)
        asset.minify()

        assert asset.minified is True
        minified = asset._minified_content
        # Nested selectors should be transformed
        assert ".button:hover" in minified or ".button:hover" in minified.replace(" ", "")
        assert ".button.active" in minified or ".button.active" in minified.replace(" ", "")

    def test_preserves_css_strings(self, temp_asset_dir):
        """Test that CSS strings are preserved during minification."""
        css_file = temp_asset_dir / "quotes.css"
        css_file.write_text('body { font-family: "Helvetica Neue", sans-serif; }')

        asset = Asset(source_path=css_file)
        asset.minify()

        minified = asset._minified_content
        # Quotes should be preserved
        assert "Helvetica Neue" in minified or '"Helvetica Neue"' in minified


class TestJavaScriptMinification:
    """Test JavaScript minification functionality."""

    def test_minifies_javascript_with_jsmin(self, temp_asset_dir):
        """Test JavaScript minification when jsmin is available."""
        js_file = temp_asset_dir / "script.js"
        js_file.write_text("""
function hello() {
    console.log('Hello, world!');
    return true;
}
""")

        asset = Asset(source_path=js_file)
        asset.minify()

        # If jsmin is available, should have minified content
        # If not available, minified flag should still be True but no _minified_content
        assert asset.minified is True

        jsmin_available = importlib.util.find_spec("jsmin") is not None
        if jsmin_available:
            # jsmin available - should have minified content
            assert hasattr(asset, "_minified_content")
            minified = asset._minified_content
            # Should be minified (whitespace removed)
            assert len(minified) <= len(js_file.read_text())
        else:
            # jsmin not available - it's okay if _minified_content is missing
            assert not hasattr(asset, "_minified_content")

    def test_handles_missing_jsmin_gracefully(self, temp_asset_dir, monkeypatch):
        """Test that missing jsmin doesn't crash."""
        js_file = temp_asset_dir / "script.js"
        js_file.write_text("console.log('test');")

        asset = Asset(source_path=js_file)

        # Mock ImportError for jsmin
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "jsmin":
                raise ImportError("No module named 'jsmin'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Should not raise exception
        asset.minify()
        # Asset should be marked as minified even if nothing happened
        assert asset.minified is True


class TestAssetFingerprinting:
    """Test asset fingerprinting/hashing."""

    def test_generates_consistent_hash(self, temp_asset_dir):
        """Test that same content generates same hash."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        asset1 = Asset(source_path=css_file)
        asset2 = Asset(source_path=css_file)

        hash1 = asset1.hash()
        hash2 = asset2.hash()

        assert hash1 == hash2
        assert len(hash1) == 8  # First 8 chars of SHA256
        assert asset1.fingerprint == hash1

    def test_different_content_generates_different_hash(self, temp_asset_dir):
        """Test that different content generates different hashes."""
        css1 = temp_asset_dir / "style1.css"
        css1.write_text("body { color: blue; }")

        css2 = temp_asset_dir / "style2.css"
        css2.write_text("body { color: red; }")

        asset1 = Asset(source_path=css1)
        asset2 = Asset(source_path=css2)

        hash1 = asset1.hash()
        hash2 = asset2.hash()

        assert hash1 != hash2

    def test_uses_minified_content_for_hash(self, temp_asset_dir):
        """Test that fingerprint uses minified content when available."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        asset = Asset(source_path=css_file)
        asset.minify()

        # Hash should be based on minified content
        fingerprint = asset.hash()

        # Verify it's different from source hash (comment removal changes content)
        asset2 = Asset(source_path=css_file)
        source_hash = asset2.hash()
        assert fingerprint != source_hash
        assert asset.fingerprint == fingerprint


class TestImageOptimization:
    """Test image optimization functionality."""

    def test_skips_svg_optimization(self, temp_asset_dir):
        """Test that SVG files are skipped (no raster optimization needed)."""
        svg_file = temp_asset_dir / "logo.svg"
        svg_file.write_text('<svg><circle r="10"/></svg>')

        asset = Asset(source_path=svg_file)
        asset.optimize()

        assert asset.optimized is True
        # Should not have _optimized_image attribute for SVG
        assert not hasattr(asset, "_optimized_image")

    def test_handles_missing_pillow_gracefully(self, temp_asset_dir, monkeypatch):
        """Test that missing PIL doesn't crash."""
        # Create a minimal PNG file
        png_file = temp_asset_dir / "image.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        asset = Asset(source_path=png_file)

        # Mock ImportError for PIL
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("No module named 'PIL'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Should not raise exception
        asset.optimize()
        assert asset.optimized is True


class TestCopyToOutput:
    """Test copying assets to output directory."""

    def test_copies_file_without_fingerprint(self, temp_asset_dir):
        """Test copying asset without fingerprinting."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        output_dir = temp_asset_dir / "output"
        output_dir.mkdir()

        asset = Asset(source_path=css_file)
        output_path = asset.copy_to_output(output_dir, use_fingerprint=False)

        assert output_path.exists()
        assert output_path.name == "style.css"
        assert output_path.read_text() == "body { color: blue; }"

    def test_copies_file_with_fingerprint(self, temp_asset_dir):
        """Test copying asset with fingerprinting."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        output_dir = temp_asset_dir / "output"
        output_dir.mkdir()

        asset = Asset(source_path=css_file)
        asset.hash()  # Generate fingerprint
        output_path = asset.copy_to_output(output_dir, use_fingerprint=True)

        assert output_path.exists()
        # Filename should include fingerprint
        assert asset.fingerprint in output_path.name
        assert output_path.name.startswith("style.")
        assert output_path.name.endswith(".css")

    def test_copies_minified_content(self, temp_asset_dir):
        """Test that minified content is written to output."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        output_dir = temp_asset_dir / "output"
        output_dir.mkdir()

        asset = Asset(source_path=css_file)
        asset.minify()
        output_path = asset.copy_to_output(output_dir, use_fingerprint=False)

        assert output_path.exists()
        # Should contain minified content
        output_content = output_path.read_text()
        assert output_content == asset._minified_content

    def test_preserves_directory_structure(self, temp_asset_dir):
        """Test that directory structure is preserved."""
        css_dir = temp_asset_dir / "css" / "components"
        css_dir.mkdir(parents=True)

        css_file = css_dir / "button.css"
        css_file.write_text(".button { color: blue; }")

        output_dir = temp_asset_dir / "output"
        output_dir.mkdir()

        asset = Asset(source_path=css_file, output_path=Path("css/components/button.css"))
        output_path = asset.copy_to_output(output_dir, use_fingerprint=False)

        assert output_path.exists()
        # Should preserve directory structure
        assert "css" in str(output_path)
        assert "components" in str(output_path)

    def test_removes_stale_fingerprints_on_copy(self, temp_asset_dir):
        """Copying a fingerprinted asset should remove older hashed siblings."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        output_dir = temp_asset_dir / "public" / "assets"
        asset = Asset(source_path=css_file, output_path=Path("css/style.css"))
        first_path = asset.copy_to_output(output_dir, use_fingerprint=True)
        assert first_path.exists()
        hashed_files = list((output_dir / "css").glob("style.*.css"))
        assert len(hashed_files) == 1

        # Change content so a new fingerprint is generated on the next build
        css_file.write_text("body { color: red; }")
        asset_next = Asset(source_path=css_file, output_path=Path("css/style.css"))
        second_path = asset_next.copy_to_output(output_dir, use_fingerprint=True)
        assert second_path.exists()

        hashed_files_after = sorted((output_dir / "css").glob("style.*.css"))
        assert len(hashed_files_after) == 1
        assert hashed_files_after[0] == second_path


class TestAssetTypeDetection:
    """Test asset type detection."""

    def test_detects_css_type(self, temp_asset_dir):
        """Test CSS file type detection."""
        css_file = temp_asset_dir / "style.css"
        css_file.write_text("body { color: blue; }")

        asset = Asset(source_path=css_file)
        assert asset.asset_type == "css"

    def test_detects_javascript_type(self, temp_asset_dir):
        """Test JavaScript file type detection."""
        js_file = temp_asset_dir / "script.js"
        js_file.write_text("console.log('test');")

        asset = Asset(source_path=js_file)
        assert asset.asset_type == "javascript"

    def test_detects_image_types(self, temp_asset_dir):
        """Test image file type detection."""
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
            img_file = temp_asset_dir / f"image{ext}"
            img_file.write_bytes(b"\x00" * 100)

            asset = Asset(source_path=img_file)
            assert asset.asset_type == "image", f"Failed for {ext}"

    def test_detects_font_types(self, temp_asset_dir):
        """Test font file type detection."""
        for ext in [".woff", ".woff2", ".ttf", ".eot"]:
            font_file = temp_asset_dir / f"font{ext}"
            font_file.write_bytes(b"\x00" * 100)

            asset = Asset(source_path=font_file)
            assert asset.asset_type == "font", f"Failed for {ext}"

    def test_detects_unknown_type(self, temp_asset_dir):
        """Test that unknown file types default to 'other'."""
        unknown_file = temp_asset_dir / "file.xyz"
        unknown_file.write_text("content")

        asset = Asset(source_path=unknown_file)
        assert asset.asset_type == "other"


class TestCSSNestingTransformation:
    """Test CSS nesting transformation (fallback when lightningcss unavailable)."""

    def test_transforms_basic_nesting(self, temp_asset_dir):
        """Test basic CSS nesting transformation."""
        from bengal.core.asset import _transform_css_nesting

        css = """
.button {
    color: blue;
    &:hover {
        color: red;
    }
}
"""

        transformed = _transform_css_nesting(css)

        # Should transform &:hover to .button:hover
        assert ".button:hover" in transformed
        assert "&:hover" not in transformed

    def test_transforms_class_nesting(self, temp_asset_dir):
        """Test class nesting transformation."""
        from bengal.core.asset import _transform_css_nesting

        css = """
.card {
    padding: 1rem;
    &.active {
        border: 2px solid blue;
    }
}
"""

        transformed = _transform_css_nesting(css)

        # Should transform &.active to .card.active
        assert ".card.active" in transformed
        assert "&.active" not in transformed

    def test_preserves_layer_blocks(self, temp_asset_dir):
        """Test that @layer blocks are preserved during nesting transformation."""
        from bengal.core.asset import _transform_css_nesting

        css = """
@layer components {
    .button {
        color: blue;
        &:hover {
            color: red;
        }
    }
}
"""

        transformed = _transform_css_nesting(css)

        # @layer should be preserved
        assert "@layer components" in transformed
        # Nesting should still be transformed
        assert ".button:hover" in transformed


class TestCSSMinifierUtility:
    """Test CSS minifier utility function."""

    def test_removes_comments(self, temp_asset_dir):
        """Test that CSS comments are removed."""
        from bengal.utils.css_minifier import minify_css

        css = "/* Comment */ body { color: blue; }"
        minified = minify_css(css)

        assert "Comment" not in minified
        assert "body" in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_reduces_whitespace(self, temp_asset_dir):
        """Test that unnecessary whitespace is removed."""
        from bengal.utils.css_minifier import minify_css

        css = """
body {
    color: blue;
    margin: 0;
}
"""
        minified = minify_css(css)

        # Should reduce whitespace but preserve essential structure
        assert "body{" in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_preserves_strings(self, temp_asset_dir):
        """Test that strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'body { font-family: "Helvetica Neue", sans-serif; }'
        minified = minify_css(css)

        # Strings should be preserved
        assert "Helvetica Neue" in minified

    def test_preserves_layer_blocks(self, temp_asset_dir):
        """Test that @layer blocks are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@layer tokens { :root { --color: blue; } }"
        minified = minify_css(css)

        assert "@layer tokens" in minified
        assert "--color:blue" in minified.replace(" ", "")

    def test_preserves_nesting(self, temp_asset_dir):
        """Test that CSS nesting syntax is preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ".parent { color: red; &:hover { color: blue; } }"
        minified = minify_css(css)

        # Nesting should be preserved (not transformed)
        assert "&:hover" in minified or ".parent:hover" in minified
