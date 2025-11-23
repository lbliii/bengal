"""
Unit tests for CSS bundling functionality in Asset class.

Tests cover:
- @import resolution
- @layer block preservation
- Recursive imports
- Error handling
- Typography variable definitions
"""

import tempfile
from pathlib import Path

import pytest

from bengal.core.asset import Asset


@pytest.fixture
def temp_css_dir():
    """Create a temporary directory with CSS files for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    css_dir = temp_dir / "css"
    css_dir.mkdir(parents=True)
    
    # Create subdirectories
    tokens_dir = css_dir / "tokens"
    tokens_dir.mkdir()
    base_dir = css_dir / "base"
    base_dir.mkdir()
    
    yield css_dir
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


class TestCSSBundling:
    """Test CSS bundling functionality."""
    
    def test_bundles_simple_import(self, temp_css_dir):
        """Test that a simple @import is resolved correctly."""
        # Create imported file
        imported = temp_css_dir / "variables.css"
        imported.write_text(":root { --color-primary: blue; }")
        
        # Create entry point with @import
        entry = temp_css_dir / "style.css"
        entry.write_text("@import url('variables.css');")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        assert ":root { --color-primary: blue; }" in bundled
        assert "@import" not in bundled
    
    def test_bundles_import_with_quotes(self, temp_css_dir):
        """Test that @import with quotes works."""
        imported = temp_css_dir / "colors.css"
        imported.write_text("body { color: red; }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("@import 'colors.css';")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        assert "body { color: red; }" in bundled
    
    def test_preserves_layer_blocks(self, temp_css_dir):
        """Test that @layer blocks are preserved when bundling."""
        # Create typography tokens file
        tokens = temp_css_dir / "tokens" / "typography.css"
        tokens.write_text(":root { --font-size-base: 1rem; }")
        
        # Create entry point with @layer
        entry = temp_css_dir / "style.css"
        entry.write_text("@layer tokens {\n  @import url('tokens/typography.css');\n}")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # @layer block should be preserved
        assert "@layer tokens" in bundled
        assert "--font-size-base: 1rem" in bundled
        # Content should be inside the layer block
        assert bundled.index("@layer tokens") < bundled.index("--font-size-base")
    
    def test_preserves_multiple_layer_blocks(self, temp_css_dir):
        """Test that multiple @layer blocks are preserved."""
        tokens = temp_css_dir / "tokens" / "colors.css"
        tokens.write_text(":root { --color-primary: blue; }")
        
        base = temp_css_dir / "base" / "reset.css"
        base.write_text("*, *::before, *::after { box-sizing: border-box; }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("""@layer tokens {
  @import url('tokens/colors.css');
}
@layer base {
  @import url('base/reset.css');
}""")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Both layers should be preserved
        assert "@layer tokens" in bundled
        assert "@layer base" in bundled
        assert "--color-primary: blue" in bundled
        assert "box-sizing: border-box" in bundled
    
    def test_handles_nested_imports(self, temp_css_dir):
        """Test that nested @import statements are resolved recursively."""
        # Level 3: Deep nested
        deep = temp_css_dir / "deep.css"
        deep.write_text(":root { --deep: value; }")
        
        # Level 2: Imports deep
        mid = temp_css_dir / "mid.css"
        mid.write_text("@import url('deep.css');\n:root { --mid: value; }")
        
        # Level 1: Imports mid
        entry = temp_css_dir / "style.css"
        entry.write_text("@import url('mid.css');\n:root { --entry: value; }")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # All levels should be included
        assert "--deep: value" in bundled
        assert "--mid: value" in bundled
        assert "--entry: value" in bundled
    
    def test_handles_nested_imports_in_layers(self, temp_css_dir):
        """Test nested imports inside @layer blocks."""
        foundation = temp_css_dir / "tokens" / "foundation.css"
        foundation.write_text(":root { --size-base: 16px; }")
        
        typography = temp_css_dir / "tokens" / "typography.css"
        typography.write_text("@import url('foundation.css');\n:root { --font-size-base: var(--size-base); }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("@layer tokens {\n  @import url('tokens/typography.css');\n}")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Layer should be preserved
        assert "@layer tokens" in bundled
        # Both variables should be present
        assert "--size-base: 16px" in bundled
        assert "--font-size-base: var(--size-base)" in bundled
    
    def test_handles_missing_imports(self, temp_css_dir):
        """Test that missing @import files are left as-is."""
        entry = temp_css_dir / "style.css"
        entry.write_text("@import url('nonexistent.css');\nbody { color: black; }")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Missing import should be preserved
        assert "@import url('nonexistent.css');" in bundled
        # Other content should still be there
        assert "body { color: black; }" in bundled
    
    def test_handles_external_url_imports(self, temp_css_dir):
        """Test that external URL @imports are preserved."""
        entry = temp_css_dir / "style.css"
        entry.write_text("@import url('https://fonts.googleapis.com/css?family=Roboto');\nbody { font-family: sans-serif; }")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # External URL should be preserved
        assert "https://fonts.googleapis.com" in bundled
        assert "body { font-family: sans-serif; }" in bundled
    
    def test_handles_standalone_and_layered_imports(self, temp_css_dir):
        """Test mixing standalone @imports with @layer blocks."""
        standalone = temp_css_dir / "standalone.css"
        standalone.write_text(":root { --standalone: value; }")
        
        layered = temp_css_dir / "tokens" / "layered.css"
        layered.write_text(":root { --layered: value; }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("""@import url('standalone.css');
@layer tokens {
  @import url('tokens/layered.css');
}""")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Standalone import should be resolved
        assert "--standalone: value" in bundled
        # Layer block should be preserved
        assert "@layer tokens" in bundled
        assert "--layered: value" in bundled
    
    def test_preserves_layer_order(self, temp_css_dir):
        """Test that @layer declaration order is preserved."""
        tokens = temp_css_dir / "tokens" / "vars.css"
        tokens.write_text(":root { --var: value; }")
        
        base = temp_css_dir / "base" / "reset.css"
        base.write_text("*, *::before { margin: 0; }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("""@layer tokens {
  @import url('tokens/vars.css');
}
@layer base {
  @import url('base/reset.css');
}""")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Order should be preserved: tokens before base
        tokens_pos = bundled.find("@layer tokens")
        base_pos = bundled.find("@layer base")
        assert tokens_pos < base_pos
    
    def test_handles_multiple_imports_in_single_layer(self, temp_css_dir):
        """Test multiple @import statements in a single @layer block."""
        colors = temp_css_dir / "tokens" / "colors.css"
        colors.write_text(":root { --color-primary: blue; }")
        
        typography = temp_css_dir / "tokens" / "typography.css"
        typography.write_text(":root { --font-size-base: 1rem; }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("""@layer tokens {
  @import url('tokens/colors.css');
  @import url('tokens/typography.css');
}""")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Layer should be preserved
        assert "@layer tokens" in bundled
        # Both imports should be resolved
        assert "--color-primary: blue" in bundled
        assert "--font-size-base: 1rem" in bundled
    
    def test_typography_variables_preserved(self, temp_css_dir):
        """Test that typography CSS variables are preserved in bundled output."""
        # Create typography tokens matching the actual structure
        typography = temp_css_dir / "tokens" / "typography.css"
        typography.write_text(""":root {
  --font-size-base: clamp(0.9375rem, 0.9rem + 0.2vw, 1rem);
  --font-size-lg: clamp(1.125rem, 1.05rem + 0.3vw, 1.25rem);
  --font-size-xl: clamp(1.375rem, 1.3rem + 0.35vw, 1.5rem);
}""")
        
        semantic = temp_css_dir / "tokens" / "semantic.css"
        semantic.write_text(""":root {
  --text-body: var(--font-size-base);
  --text-h1: var(--font-size-xl);
}""")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("""@layer tokens {
  @import url('tokens/typography.css');
}
@layer tokens {
  @import url('tokens/semantic.css');
}""")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # All typography variables should be present
        assert "--font-size-base:" in bundled
        assert "--font-size-lg:" in bundled
        assert "--font-size-xl:" in bundled
        assert "--text-body:" in bundled
        assert "--text-h1:" in bundled
        # Layer blocks should be preserved
        assert "@layer tokens" in bundled
    
    def test_handles_import_with_layer_declaration(self, temp_css_dir):
        """Test that imported files with their own @layer declarations work."""
        # Imported file has its own @layer
        imported = temp_css_dir / "components.css"
        imported.write_text("@layer components { .button { color: blue; } }")
        
        entry = temp_css_dir / "style.css"
        entry.write_text("@layer tokens {\n  @import url('components.css');\n}")
        
        asset = Asset(source_path=entry)
        bundled = asset.bundle_css()
        
        # Both layers should be present
        assert "@layer tokens" in bundled
        assert "@layer components" in bundled
        assert ".button { color: blue; }" in bundled


class TestCSSEntryPointDetection:
    """Test CSS entry point detection."""
    
    def test_detects_style_css_as_entry_point(self, temp_css_dir):
        """Test that style.css is detected as an entry point."""
        entry = temp_css_dir / "style.css"
        entry.write_text("body { color: black; }")
        
        asset = Asset(source_path=entry)
        assert asset.is_css_entry_point() is True
        assert asset.is_css_module() is False
    
    def test_detects_other_css_as_module(self, temp_css_dir):
        """Test that non-style.css files are detected as modules."""
        module = temp_css_dir / "components" / "button.css"
        module.parent.mkdir()
        module.write_text(".button { color: blue; }")
        
        asset = Asset(source_path=module)
        assert asset.is_css_entry_point() is False
        assert asset.is_css_module() is True
    
    def test_detects_nested_style_css_as_entry_point(self, temp_css_dir):
        """Test that style.css at any level is an entry point."""
        nested = temp_css_dir / "themes" / "default" / "style.css"
        nested.parent.mkdir(parents=True)
        nested.write_text("body { color: black; }")
        
        asset = Asset(source_path=nested)
        assert asset.is_css_entry_point() is True

