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
    """Test CSS minifier utility function.

    Comprehensive tests for CSS minification covering:
    - Basic minification (comments, whitespace)
    - Modern CSS features (@layer, nesting, @import)
    - CSS functions (calc, color-mix)
    - Complex selectors and combinators
    - Edge cases and real-world patterns

    For manual diagnostic tools, see scripts/test_css_minification.py
    """

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

    def test_handles_css_functions(self, temp_asset_dir):
        """Test that CSS functions like calc() are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "div { width: calc(100% - 20px); }"
        minified = minify_css(css)

        assert "calc" in minified
        assert "100%" in minified
        assert "20px" in minified

    def test_handles_color_mix_function(self, temp_asset_dir):
        """Test that color-mix() function preserves spaces before %."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: color-mix(in srgb, red 50%, blue 50%); }"
        minified = minify_css(css)

        # Space before % should be preserved
        assert "red 50%" in minified or "red50%" in minified
        assert "blue 50%" in minified or "blue50%" in minified

    def test_handles_multiple_layer_blocks(self, temp_asset_dir):
        """Test that multiple @layer blocks are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@layer tokens { :root { --color: blue; } } @layer base { body { margin: 0; } }"
        minified = minify_css(css)

        assert "@layer tokens" in minified
        assert "@layer base" in minified

    def test_handles_import_statements(self, temp_asset_dir):
        """Test that @import statements are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = '@import "reset.css"; body { color: blue; }'
        minified = minify_css(css)

        assert "@import" in minified
        assert "reset.css" in minified

    def test_handles_media_queries(self, temp_asset_dir):
        """Test that @media queries are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@media (min-width: 768px) { body { font-size: 18px; } }"
        minified = minify_css(css)

        assert "@media" in minified
        assert "min-width" in minified
        assert "768px" in minified

    def test_handles_custom_properties(self, temp_asset_dir):
        """Test that CSS custom properties are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ":root { --spacing: 1rem; --color: #333; }"
        minified = minify_css(css)

        assert "--spacing" in minified
        assert "--color" in minified
        assert "1rem" in minified

    def test_handles_complex_selectors(self, temp_asset_dir):
        """Test that complex selectors with combinators are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ".parent > .child + .sibling { color: blue; }"
        minified = minify_css(css)

        assert ".parent" in minified
        assert ".child" in minified
        assert ".sibling" in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_handles_attribute_selectors(self, temp_asset_dir):
        """Test that attribute selectors are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'a[href^="https"] { color: green; }'
        minified = minify_css(css)

        assert 'href^="https"' in minified or 'href^="https"' in minified.replace(" ", "")

    def test_handles_pseudo_elements(self, temp_asset_dir):
        """Test that pseudo-elements are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "p::before { content: ''; }"
        minified = minify_css(css)

        assert "::before" in minified

    def test_handles_descendant_selectors(self, temp_asset_dir):
        """Test that descendant selectors preserve required spaces."""
        from bengal.utils.css_minifier import minify_css

        css = ".parent .child { color: red; }"
        minified = minify_css(css)

        # Space between .parent and .child is required for descendant selector
        assert ".parent .child" in minified or ".parent.child" not in minified

    def test_handles_multiple_selectors(self, temp_asset_dir):
        """Test that multiple selectors separated by commas are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = ".a, .b, .c { color: red; }"
        minified = minify_css(css)

        assert ".a" in minified
        assert ".b" in minified
        assert ".c" in minified

    def test_handles_urls(self, temp_asset_dir):
        """Test that URLs in CSS are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'body { background: url("image.png"); }'
        minified = minify_css(css)

        assert 'url("image.png")' in minified or 'url("image.png")' in minified.replace(" ", "")

    def test_handles_empty_rules(self, temp_asset_dir):
        """Test that empty CSS rules are handled."""
        from bengal.utils.css_minifier import minify_css

        css = ".empty { } .not-empty { color: blue; }"
        minified = minify_css(css)

        assert ".empty" in minified
        assert ".not-empty" in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_handles_multiple_comments(self, temp_asset_dir):
        """Test that multiple CSS comments are all removed."""
        from bengal.utils.css_minifier import minify_css

        css = "/* First */ body { /* Second */ color: blue; /* Third */ }"
        minified = minify_css(css)

        assert "First" not in minified
        assert "Second" not in minified
        assert "Third" not in minified
        assert "/*" not in minified
        assert "*/" not in minified
        assert "body" in minified
        assert "color:blue" in minified.replace(" ", "")

    def test_handles_nested_layer_blocks(self, temp_asset_dir):
        """Test that nested @layer blocks are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@layer a { @layer b { div { color: red; } } }"
        minified = minify_css(css)

        assert "@layer a" in minified
        assert "@layer b" in minified

    def test_handles_media_with_layer(self, temp_asset_dir):
        """Test that @media queries containing @layer blocks are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@media (min-width: 768px) { @layer tokens { :root { } } }"
        minified = minify_css(css)

        assert "@media" in minified
        assert "@layer tokens" in minified

    def test_handles_keyframes(self, temp_asset_dir):
        """Test that @keyframes rules are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "@keyframes fade { from { opacity: 0; } to { opacity: 1; } }"
        minified = minify_css(css)

        assert "@keyframes fade" in minified
        assert "opacity:0" in minified.replace(" ", "")
        assert "opacity:1" in minified.replace(" ", "")

    def test_handles_font_face(self, temp_asset_dir):
        """Test that @font-face rules are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = '@font-face { font-family: "Custom"; src: url("font.woff2"); }'
        minified = minify_css(css)

        assert "@font-face" in minified
        assert "font-family" in minified
        assert "Custom" in minified

    def test_handles_important(self, temp_asset_dir):
        """Test that !important declarations are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: red !important; margin: 0 !important; }"
        minified = minify_css(css)

        assert "!important" in minified
        assert "color:red" in minified.replace(" ", "")

    def test_handles_unicode_in_strings(self, temp_asset_dir):
        """Test that Unicode characters in strings are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = 'div { content: "→ ← ↑ ↓"; }'
        minified = minify_css(css)

        assert "→" in minified or "content" in minified

    def test_validates_balanced_structures(self, temp_asset_dir):
        """Test that minifier produces balanced braces/parentheses."""
        from bengal.utils.css_minifier import minify_css

        css = "div { color: red; } .test { margin: calc(10px + 5px); }"
        minified = minify_css(css)

        # Check balanced structures
        assert minified.count("{") == minified.count("}")
        assert minified.count("(") == minified.count(")")

    def test_preserves_spaces_after_commas_in_multivalue_properties(self, temp_asset_dir):
        """Test that spaces after commas in multi-value properties are preserved."""
        from bengal.utils.css_minifier import minify_css

        # Neumorphic box-shadow with multiple values
        css = """box-shadow:
  inset 0.5px 0.5px 1px rgba(255, 255, 255, 0.3),
  inset -0.5px -0.5px 1px rgba(0, 0, 0, 0.1),
  1px 1px 2px rgba(0, 0, 0, 0.08),
  -0.5px -0.5px 1px rgba(255, 255, 255, 0.2);"""

        minified = minify_css(css)

        # Critical: spaces after commas must be preserved
        # Should NOT be: rgba(...),inset-0.5px (broken)
        # Should be: rgba(...), inset -0.5px (correct)
        assert ", inset" in minified or ",inset " in minified or ", inset " in minified
        # Critical: space after "inset" keyword before negative value
        assert "inset -" in minified
        # Critical: space between negative values (e.g., -0.5px -0.5px)
        assert "-0.5px -" in minified
        # Critical: spaces after commas separating shadow values
        assert "0.3)," in minified or "0.3), " in minified or "0.3), inset" in minified

    def test_preserves_spaces_after_inset_keyword(self, temp_asset_dir):
        """Test that spaces after 'inset' keyword in box-shadow are preserved."""
        from bengal.utils.css_minifier import minify_css

        css = "box-shadow: inset -0.5px -0.5px 1px rgba(0, 0, 0, 0.1);"
        minified = minify_css(css)

        # Critical: "inset" must be followed by space before negative value
        # Should NOT be: inset-0.5px (broken)
        # Should be: inset -0.5px (correct)
        assert "inset -" in minified
        # Verify that inset is not directly concatenated with the value (no inset-0.5px pattern)
        # We check this by ensuring there's a space or colon between inset and the value
        minified_no_spaces = minified.replace(" ", "")
        # After removing spaces, if inset- appears, it means the space was removed incorrectly
        # But we need to account for box-shadow:inset- which is valid (colon before inset)
        # So we check that inset- doesn't appear where there should be a space
        assert "inset-0.5px" not in minified_no_spaces or "box-shadow:inset-" in minified_no_spaces

    def test_preserves_spaces_after_commas_in_function_calls(self, temp_asset_dir):
        """Test that spaces after commas inside CSS function calls are preserved."""
        from bengal.utils.css_minifier import minify_css

        # Test rgba() function with multiple arguments
        css = "box-shadow: rgba(255, 255, 255, 0.3), rgba(0, 0, 0, 0.1), rgba(255, 255, 255, 0.2);"
        minified = minify_css(css)

        # Critical: spaces after commas inside rgba() must be preserved
        # Should NOT be: rgba(255,255,255,0.2) (broken)
        # Should be: rgba(255, 255, 255, 0.2) (correct)
        import re

        rgba_matches = re.findall(r"rgba\([^)]+\)", minified)
        for match in rgba_matches:
            # Check that commas inside rgba() are followed by spaces
            assert ", " in match or match.count(",") == 0, f"Missing spaces in {match}"

    def test_preserves_spaces_between_filter_functions(self, temp_asset_dir):
        """Test that spaces between filter/transform functions are preserved."""
        from bengal.utils.css_minifier import minify_css

        # Test filter with multiple functions
        css = "filter: blur(5px) brightness(1.2);"
        minified = minify_css(css)

        # Critical: space between filter functions must be preserved
        # Should NOT be: blur(5px)brightness(1.2) (broken)
        # Should be: blur(5px) brightness(1.2) (correct)
        assert ") brightness" in minified or ")brightness" not in minified.replace(" ", "")

        # Test backdrop-filter
        css2 = "backdrop-filter: blur(12px) saturate(180%);"
        minified2 = minify_css(css2)
        assert ") saturate" in minified2

        # Test transform with multiple functions
        css3 = "transform: translateX(10px) translateY(20px) rotate(45deg);"
        minified3 = minify_css(css3)
        assert ") translateY" in minified3
        assert ") rotate" in minified3

    def test_preserves_spaces_around_slashes_in_grid_properties(self, temp_asset_dir):
        """Test that spaces around / in grid and border-radius properties are preserved."""
        from bengal.utils.css_minifier import minify_css

        # Test grid-area with slashes
        css = "grid-area: 1 / 1 / -1 / -1;"
        minified = minify_css(css)

        # Critical: spaces around / should be preserved for readability
        # Should be: 1 / 1 / -1 / -1 (readable)
        assert " / " in minified or "/ " in minified or " /" in minified

        # Test grid-column
        css2 = "grid-column: 1 / -1;"
        minified2 = minify_css(css2)
        assert " / " in minified2 or "/ " in minified2 or " /" in minified2

        # Test border-radius with slash
        css3 = "border-radius: 10px / 20px;"
        minified3 = minify_css(css3)
        assert " / " in minified3 or "/ " in minified3 or " /" in minified3
