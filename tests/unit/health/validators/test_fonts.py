"""
Tests for Font validator.
"""

import pytest
from unittest.mock import Mock

from bengal.health.validators.fonts import FontValidator
from bengal.health.report import CheckStatus


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Mock()
    site.output_dir = tmp_path
    site.config = {}
    return site


@pytest.fixture
def site_with_fonts(mock_site):
    """Create a site with font configuration."""
    mock_site.config = {
        'fonts': {
            'primary': 'Inter:400,600,700',
            'heading': 'Playfair Display:700'
        }
    }
    return mock_site


def test_font_validator_no_config(mock_site):
    """Test validator with no font configuration."""
    validator = FontValidator()
    results = validator.validate(mock_site)
    
    assert len(results) > 0
    assert any(r.status == CheckStatus.INFO for r in results)
    assert any("No fonts configured" in r.message for r in results)


def test_font_validator_missing_css(site_with_fonts):
    """Test validator warns when fonts.css not generated."""
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("not generated" in r.message.lower() for r in results)


def test_font_validator_valid_fonts(site_with_fonts, tmp_path):
    """Test validator passes for valid fonts."""
    # Create fonts directory and files
    fonts_dir = tmp_path / 'assets' / 'fonts'
    fonts_dir.mkdir(parents=True)
    
    (fonts_dir / 'inter-400.woff2').write_bytes(b'fake font data')
    (fonts_dir / 'inter-600.woff2').write_bytes(b'fake font data')
    (fonts_dir / 'inter-700.woff2').write_bytes(b'fake font data')
    (fonts_dir / 'playfair-display-700.woff2').write_bytes(b'fake font data')
    
    # Create fonts.css
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True, exist_ok=True)
    fonts_css_content = '''/* Generated fonts */
@font-face {
  font-family: 'Inter';
  font-weight: 400;
  src: url('/fonts/inter-400.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-weight: 600;
  src: url('/fonts/inter-600.woff2') format('woff2');
}'''
    fonts_css.write_text(fonts_css_content)
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    # Should have success results
    assert any(r.status == CheckStatus.SUCCESS for r in results)
    assert any("fonts.css generated" in r.message for r in results)
    assert any("font file(s) downloaded" in r.message for r in results)


def test_font_validator_no_font_files(site_with_fonts, tmp_path):
    """Test validator catches missing font files."""
    # Create fonts.css but no font files
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True)
    fonts_css.write_text('@font-face { font-family: "Test"; }')
    
    # Create empty fonts directory
    fonts_dir = tmp_path / 'assets' / 'fonts'
    fonts_dir.mkdir(parents=True)
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("No font files" in r.message for r in results)


def test_font_validator_missing_fonts_directory(site_with_fonts, tmp_path):
    """Test validator catches missing fonts directory."""
    # Create fonts.css but no fonts directory
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True)
    fonts_css.write_text('@font-face { font-family: "Test"; }')
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("directory does not exist" in r.message.lower() for r in results)


def test_font_validator_no_font_face_rules(site_with_fonts, tmp_path):
    """Test validator catches CSS without @font-face."""
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True)
    fonts_css.write_text('/* Empty CSS */')
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("no @font-face" in r.message.lower() for r in results)


def test_font_validator_broken_references(site_with_fonts, tmp_path):
    """Test validator catches broken font references."""
    # Create fonts directory with some fonts
    fonts_dir = tmp_path / 'assets' / 'fonts'
    fonts_dir.mkdir(parents=True)
    (fonts_dir / 'inter-400.woff2').write_bytes(b'fake font')
    
    # Create CSS that references missing font
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True, exist_ok=True)
    fonts_css_content = '''@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter-400.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  src: url('/fonts/missing-font.woff2') format('woff2');
}'''
    fonts_css.write_text(fonts_css_content)
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("missing files" in r.message.lower() for r in results)


def test_font_validator_oversized_fonts(site_with_fonts, tmp_path):
    """Test validator warns about oversized fonts."""
    fonts_dir = tmp_path / 'assets' / 'fonts'
    fonts_dir.mkdir(parents=True)
    
    # Create oversized font file (> 500 KB)
    large_font_data = b'x' * (600 * 1024)
    (fonts_dir / 'huge-font.woff2').write_bytes(large_font_data)
    
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True, exist_ok=True)
    fonts_css.write_text('@font-face { font-family: "Test"; src: url("/fonts/huge-font.woff2"); }')
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("very large" in r.message.lower() for r in results)


def test_font_validator_total_size_warning(site_with_fonts, tmp_path):
    """Test validator warns about total font size."""
    fonts_dir = tmp_path / 'assets' / 'fonts'
    fonts_dir.mkdir(parents=True)
    
    # Create multiple fonts totaling > 1 MB
    for i in range(5):
        font_data = b'x' * (300 * 1024)  # 300 KB each
        (fonts_dir / f'font-{i}.woff2').write_bytes(font_data)
    
    fonts_css = tmp_path / 'assets' / 'fonts.css'
    fonts_css.parent.mkdir(parents=True, exist_ok=True)
    fonts_css.write_text('@font-face { font-family: "Test"; }')
    
    validator = FontValidator()
    results = validator.validate(site_with_fonts)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    # Should warn about total size
    assert any("total" in r.message.lower() and "kb" in r.message.lower() for r in results)


def test_font_validator_name_and_description():
    """Test validator metadata."""
    validator = FontValidator()
    
    assert validator.name == "Fonts"
    assert "font" in validator.description.lower()
    assert validator.enabled_by_default is True

