"""
Tests for Asset validator.
"""

from unittest.mock import Mock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.assets import AssetValidator


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Mock()
    site.output_dir = tmp_path
    site.config = {}
    return site


def test_asset_validator_missing_assets_dir(mock_site):
    """Test validator warns when assets directory missing."""
    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert len(results) > 0
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("No assets directory" in r.message for r in results)


def test_asset_validator_valid_assets(mock_site, tmp_path):
    """Test validator passes for valid assets (silence is golden pattern)."""
    # Create assets directory with files
    assets_dir = tmp_path / "assets"
    css_dir = assets_dir / "css"
    css_dir.mkdir(parents=True)

    (css_dir / "style.css").write_text("body { color: black; }")

    js_dir = assets_dir / "js"
    js_dir.mkdir(parents=True)
    (js_dir / "main.js").write_text('console.log("test");')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Validators follow "silence is golden" - no warnings/errors means success
    # Valid assets should not produce any warnings or errors
    assert not any(r.status == CheckStatus.WARNING for r in results)
    assert not any(r.status == CheckStatus.ERROR for r in results)


def test_asset_validator_no_css(mock_site, tmp_path):
    """Test validator errors when no CSS files found."""
    # Create assets directory but no CSS
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("No CSS files" in r.message for r in results)


def test_asset_validator_large_css(mock_site, tmp_path):
    """Test validator warns about large CSS files."""
    assets_dir = tmp_path / "assets" / "css"
    assets_dir.mkdir(parents=True)

    # Create large CSS file (> 200 KB)
    large_css = "body { color: black; }" * (250 * 1024 // 25)
    (assets_dir / "huge.css").write_text(large_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("CSS file(s) are very large" in r.message for r in results)


def test_asset_validator_large_js(mock_site, tmp_path):
    """Test validator warns about large JS files."""
    assets_dir = tmp_path / "assets" / "js"
    assets_dir.mkdir(parents=True)

    # Create large JS file (> 500 KB)
    large_js = 'console.log("test");' * (600 * 1024 // 20)
    (assets_dir / "huge.js").write_text(large_js)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("JavaScript file(s) are very large" in r.message for r in results)


def test_asset_validator_large_images(mock_site, tmp_path):
    """Test validator warns about large images."""
    assets_dir = tmp_path / "assets" / "images"
    assets_dir.mkdir(parents=True)

    # Create large image file (> 1 MB)
    large_image = b"x" * (1200 * 1024)
    (assets_dir / "huge.jpg").write_bytes(large_image)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("image(s) are very large" in r.message.lower() for r in results)


def test_asset_validator_total_size(mock_site, tmp_path):
    """Test validator with small assets (silence is golden pattern)."""
    assets_dir = tmp_path / "assets"
    css_dir = assets_dir / "css"
    css_dir.mkdir(parents=True)

    # Create several small files
    (css_dir / "style.css").write_text("body {}")
    (assets_dir / "main.js").write_text("console.log();")

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Small assets should not trigger size warnings
    # Validators follow "silence is golden" - no warnings for reasonable sizes
    assert not any(
        r.status == CheckStatus.WARNING and "very large" in r.message.lower() for r in results
    )


def test_asset_validator_very_large_total(mock_site, tmp_path):
    """Test validator warns about very large total size."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    # Create files totaling > 10 MB
    for i in range(15):
        (assets_dir / f"file{i}.dat").write_bytes(b"x" * (1024 * 1024))

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("very large" in r.message.lower() for r in results)


def test_asset_validator_duplicate_detection(mock_site, tmp_path):
    """Test validator with multiple versioned assets (normal with cache busting)."""
    assets_dir = tmp_path / "assets" / "css"
    assets_dir.mkdir(parents=True)

    # Create files that look like duplicates (same base name)
    # Multiple versions are normal with cache busting, so no warning expected
    (assets_dir / "style.abc123.css").write_text("body {}")
    (assets_dir / "style.def456.css").write_text("body {}")

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Validators follow "silence is golden" - multiple versions are normal with cache busting
    # No warnings or errors expected for this pattern
    assert not any(r.status == CheckStatus.ERROR for r in results)
    # CSS warning should not be present since CSS files exist
    assert not any("No CSS files" in r.message for r in results)


def test_asset_validator_minification_hints(mock_site, tmp_path):
    """Test validator gives minification hints."""
    assets_dir = tmp_path / "assets" / "css"
    assets_dir.mkdir(parents=True)

    # Create large unminified CSS with proper formatting (lots of newlines)
    # This simulates real unminified CSS with spacing and structure
    unminified_css = "\n".join(
        [
            "body {",
            "    color: black;",
            "    font-size: 16px;",
            "    margin: 0;",
            "    padding: 0;",
            "}",
            "",
        ]
        * 1000
    )  # Repeat to make it > 50KB
    (assets_dir / "style.css").write_text(unminified_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should suggest minification
    assert any("may not be minified" in r.message.lower() for r in results)


def test_asset_validator_minified_assets_ok(mock_site, tmp_path):
    """Test validator recognizes minified assets."""
    assets_dir = tmp_path / "assets" / "css"
    assets_dir.mkdir(parents=True)

    # Create minified-looking CSS
    minified_css = "body{color:black}" * 100
    (assets_dir / "style.min.css").write_text(minified_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should not complain about minification
    assert not any(
        "not be minified" in r.message.lower() for r in results if r.status == CheckStatus.WARNING
    )


def test_asset_validator_with_js_files(mock_site, tmp_path):
    """Test validator with JS files (silence is golden pattern)."""
    assets_dir = tmp_path / "assets"
    css_dir = assets_dir / "css"
    js_dir = assets_dir / "js"
    css_dir.mkdir(parents=True)
    js_dir.mkdir(parents=True)

    (css_dir / "style.css").write_text("body {}")
    (js_dir / "main.js").write_text("console.log();")

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Validators follow "silence is golden" - valid assets produce no warnings/errors
    assert not any(r.status == CheckStatus.ERROR for r in results)
    assert not any(r.status == CheckStatus.WARNING for r in results)


def test_asset_validator_with_images(mock_site, tmp_path):
    """Test validator with image files (silence is golden pattern)."""
    assets_dir = tmp_path / "assets"
    img_dir = assets_dir / "images"
    css_dir = assets_dir / "css"
    img_dir.mkdir(parents=True)
    css_dir.mkdir(parents=True)

    (css_dir / "style.css").write_text("body {}")
    (img_dir / "logo.png").write_bytes(b"fake png")
    (img_dir / "hero.jpg").write_bytes(b"fake jpg")

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Validators follow "silence is golden" - valid assets produce no warnings/errors
    # Small images should not trigger size warnings
    assert not any(r.status == CheckStatus.ERROR for r in results)
    assert not any(
        r.status == CheckStatus.WARNING and "image(s) are very large" in r.message for r in results
    )


def test_asset_validator_name_and_description():
    """Test validator metadata."""
    validator = AssetValidator()

    assert validator.name == "Asset Processing"
    assert "asset" in validator.description.lower()
    assert validator.enabled_by_default is True


class TestCriticalAssetChecks:
    """
    Tests for critical asset checks that FAIL the build when essential assets are missing.

    Regression tests for: Theme assets skipped when Bengal installed in .venv

    These tests are theme-agnostic - they should work for any theme, not just the default.

    """

    def test_no_css_files_is_error(self, mock_site, tmp_path):
        """Test that having NO CSS files triggers an ERROR.

        Regression test: When theme assets weren't discovered (due to .venv bug),
        the site would build but be completely unstyled. This should now be an ERROR.
        """
        # Create assets directory but NO CSS files at all
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir(parents=True)

        # Only create non-CSS files
        (assets_dir / "favicon.ico").write_bytes(b"\x00" * 100)

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should be an ERROR - any themed site needs CSS
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) > 0, "No CSS files should trigger an ERROR"
        assert any("css" in r.message.lower() for r in error_results)

    def test_css_files_present_no_error(self, mock_site, tmp_path):
        """Test that having CSS files doesn't trigger the error."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)

        # Create CSS and JS files (any names work - theme-agnostic)
        (css_dir / "theme.abc123.css").write_text("body { color: black; }")
        (js_dir / "app.def456.js").write_text('console.log("test");')

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should NOT have the critical errors
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0, f"Valid assets should not trigger errors: {error_results}"

    def test_js_dir_empty_is_error(self, mock_site, tmp_path):
        """Test that having a js/ directory but no JS files triggers an ERROR.

        If js/ directory exists, the theme expects JavaScript. If it's empty,
        something went wrong with asset discovery/copying.
        """
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)  # Empty js/ directory

        (css_dir / "style.css").write_text("body { color: black; }")
        # js/ directory exists but is empty

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should be an ERROR - js/ exists but is empty
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) > 0, "Empty js/ directory should trigger an ERROR"
        assert any("javascript" in r.message.lower() for r in error_results)

    def test_no_js_dir_is_ok(self, mock_site, tmp_path):
        """Test that having no js/ directory is OK (CSS-only themes are valid)."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        css_dir.mkdir(parents=True)

        # CSS only, no js/ directory at all - this is fine for CSS-only themes
        (css_dir / "style.css").write_text("body { color: black; }")

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should NOT have errors - CSS-only themes are valid
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0, (
            f"CSS-only themes should not trigger errors: {error_results}"
        )

    def test_fingerprinted_assets_detected(self, mock_site, tmp_path):
        """Test that fingerprinted assets (e.g., theme.4bb1d291.css) are detected."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)

        # Create fingerprinted versions (common in production)
        (css_dir / "theme.4bb1d291.css").write_text("body { color: black; }")
        (js_dir / "app.c1d87ab4.js").write_text('console.log("test");')

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should NOT have the critical errors
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert len(error_results) == 0, f"Fingerprinted assets should be detected: {error_results}"


class TestEmptyAssetDetection:
    """
    Tests for empty (0-byte) asset file detection.

    Empty CSS/JS files are almost always a bug - they load but do nothing,
    causing silent failures that are hard to debug.

    """

    def test_empty_css_is_error(self, mock_site, tmp_path):
        """Test that empty CSS files trigger an ERROR."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        css_dir.mkdir(parents=True)

        # Create a 0-byte CSS file
        (css_dir / "style.css").write_text("")

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should be an ERROR - empty CSS is useless
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any(
            "empty" in r.message.lower() and "css" in r.message.lower() for r in error_results
        ), f"Empty CSS should trigger ERROR: {error_results}"

    def test_empty_js_is_error(self, mock_site, tmp_path):
        """Test that empty JS files trigger an ERROR."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)

        (css_dir / "style.css").write_text("body {}")  # Valid CSS
        (js_dir / "main.js").write_text("")  # Empty JS

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should be an ERROR - empty JS is useless
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any(
            "empty" in r.message.lower() and "javascript" in r.message.lower()
            for r in error_results
        ), f"Empty JS should trigger ERROR: {error_results}"

    def test_non_empty_assets_ok(self, mock_site, tmp_path):
        """Test that non-empty assets don't trigger the empty check."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        js_dir = assets_dir / "js"
        css_dir.mkdir(parents=True)
        js_dir.mkdir(parents=True)

        (css_dir / "style.css").write_text("body { color: black; }")
        (js_dir / "main.js").write_text("console.log('test');")

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should NOT have empty asset errors
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert not any("empty" in r.message.lower() for r in error_results), (
            f"Non-empty assets should not trigger empty errors: {error_results}"
        )

    def test_empty_other_files_warning_only(self, mock_site, tmp_path):
        """Test that empty non-CSS/JS files only warn if there are many."""
        assets_dir = tmp_path / "assets"
        css_dir = assets_dir / "css"
        css_dir.mkdir(parents=True)

        (css_dir / "style.css").write_text("body {}")  # Valid CSS

        # Create several empty files (not CSS/JS)
        for i in range(5):
            (assets_dir / f"empty{i}.txt").write_text("")

        validator = AssetValidator()
        results = validator.validate(mock_site)

        # Should be a WARNING (not error) for other empty files
        warning_results = [
            r for r in results if r.status == CheckStatus.WARNING and "empty" in r.message.lower()
        ]
        assert len(warning_results) > 0, "Many empty files should trigger a warning"
