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
    """Test validator passes for valid assets."""
    # Create assets directory with files
    assets_dir = tmp_path / 'assets'
    css_dir = assets_dir / 'css'
    css_dir.mkdir(parents=True)

    (css_dir / 'style.css').write_text('body { color: black; }')

    js_dir = assets_dir / 'js'
    js_dir.mkdir(parents=True)
    (js_dir / 'main.js').write_text('console.log("test");')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should have success results
    assert any(r.status == CheckStatus.SUCCESS for r in results)
    assert any("Assets directory exists" in r.message for r in results)
    assert any("CSS file(s)" in r.message for r in results)


def test_asset_validator_no_css(mock_site, tmp_path):
    """Test validator warns when no CSS files found."""
    # Create assets directory but no CSS
    assets_dir = tmp_path / 'assets'
    assets_dir.mkdir()

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("No CSS files" in r.message for r in results)


def test_asset_validator_large_css(mock_site, tmp_path):
    """Test validator warns about large CSS files."""
    assets_dir = tmp_path / 'assets' / 'css'
    assets_dir.mkdir(parents=True)

    # Create large CSS file (> 200 KB)
    large_css = 'body { color: black; }' * (250 * 1024 // 25)
    (assets_dir / 'huge.css').write_text(large_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("CSS file(s) are very large" in r.message for r in results)


def test_asset_validator_large_js(mock_site, tmp_path):
    """Test validator warns about large JS files."""
    assets_dir = tmp_path / 'assets' / 'js'
    assets_dir.mkdir(parents=True)

    # Create large JS file (> 500 KB)
    large_js = 'console.log("test");' * (600 * 1024 // 20)
    (assets_dir / 'huge.js').write_text(large_js)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("JavaScript file(s) are very large" in r.message for r in results)


def test_asset_validator_large_images(mock_site, tmp_path):
    """Test validator warns about large images."""
    assets_dir = tmp_path / 'assets' / 'images'
    assets_dir.mkdir(parents=True)

    # Create large image file (> 1 MB)
    large_image = b'x' * (1200 * 1024)
    (assets_dir / 'huge.jpg').write_bytes(large_image)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("image(s) are very large" in r.message.lower() for r in results)


def test_asset_validator_total_size(mock_site, tmp_path):
    """Test validator reports total asset size."""
    assets_dir = tmp_path / 'assets'
    assets_dir.mkdir()

    # Create several small files
    (assets_dir / 'style.css').write_text('body {}')
    (assets_dir / 'main.js').write_text('console.log();')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should report size
    assert any("size" in r.message.lower() and "mb" in r.message.lower() for r in results)


def test_asset_validator_very_large_total(mock_site, tmp_path):
    """Test validator warns about very large total size."""
    assets_dir = tmp_path / 'assets'
    assets_dir.mkdir()

    # Create files totaling > 10 MB
    for i in range(15):
        (assets_dir / f'file{i}.dat').write_bytes(b'x' * (1024 * 1024))

    validator = AssetValidator()
    results = validator.validate(mock_site)

    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("very large" in r.message.lower() for r in results)


def test_asset_validator_duplicate_detection(mock_site, tmp_path):
    """Test validator detects duplicate assets."""
    assets_dir = tmp_path / 'assets' / 'css'
    assets_dir.mkdir(parents=True)

    # Create files that look like duplicates (same base name)
    (assets_dir / 'style.abc123.css').write_text('body {}')
    (assets_dir / 'style.def456.css').write_text('body {}')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should note multiple versions
    assert any(r.status == CheckStatus.INFO for r in results)
    assert any("multiple versions" in r.message.lower() for r in results)


def test_asset_validator_minification_hints(mock_site, tmp_path):
    """Test validator gives minification hints."""
    assets_dir = tmp_path / 'assets' / 'css'
    assets_dir.mkdir(parents=True)

    # Create large unminified CSS
    unminified_css = '\n'.join(['body { color: black; }'] * 1000)
    (assets_dir / 'style.css').write_text(unminified_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should suggest minification
    assert any("may not be minified" in r.message.lower() for r in results)


def test_asset_validator_minified_assets_ok(mock_site, tmp_path):
    """Test validator recognizes minified assets."""
    assets_dir = tmp_path / 'assets' / 'css'
    assets_dir.mkdir(parents=True)

    # Create minified-looking CSS
    minified_css = 'body{color:black}' * 100
    (assets_dir / 'style.min.css').write_text(minified_css)

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should not complain about minification
    assert not any("not be minified" in r.message.lower() for r in results if r.status == CheckStatus.WARNING)


def test_asset_validator_with_js_files(mock_site, tmp_path):
    """Test validator reports JS files as info."""
    assets_dir = tmp_path / 'assets'
    css_dir = assets_dir / 'css'
    js_dir = assets_dir / 'js'
    css_dir.mkdir(parents=True)
    js_dir.mkdir(parents=True)

    (css_dir / 'style.css').write_text('body {}')
    (js_dir / 'main.js').write_text('console.log();')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should report JS files
    assert any(r.status == CheckStatus.INFO and "JavaScript file(s)" in r.message for r in results)


def test_asset_validator_with_images(mock_site, tmp_path):
    """Test validator reports image files as info."""
    assets_dir = tmp_path / 'assets'
    img_dir = assets_dir / 'images'
    css_dir = assets_dir / 'css'
    img_dir.mkdir(parents=True)
    css_dir.mkdir(parents=True)

    (css_dir / 'style.css').write_text('body {}')
    (img_dir / 'logo.png').write_bytes(b'fake png')
    (img_dir / 'hero.jpg').write_bytes(b'fake jpg')

    validator = AssetValidator()
    results = validator.validate(mock_site)

    # Should report images
    assert any(r.status == CheckStatus.INFO and "image file(s)" in r.message.lower() for r in results)


def test_asset_validator_name_and_description():
    """Test validator metadata."""
    validator = AssetValidator()

    assert validator.name == "Asset Processing"
    assert "asset" in validator.description.lower()
    assert validator.enabled_by_default is True

