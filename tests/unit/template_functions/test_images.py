"""Tests for image processing template functions."""

import pytest
import tempfile
from pathlib import Path
from bengal.rendering.template_functions.images import (
    image_url,
    image_srcset,
    image_srcset_gen,
    image_alt,
    image_data_uri,
)


class TestImageUrl:
    """Tests for image_url function."""
    
    def test_basic_url(self):
        result = image_url('photo.jpg', '')
        assert result == '/assets/photo.jpg'
    
    def test_with_width(self):
        result = image_url('photo.jpg', '', width=800)
        assert result == '/assets/photo.jpg?w=800'
    
    def test_with_height(self):
        result = image_url('photo.jpg', '', height=600)
        assert result == '/assets/photo.jpg?h=600'
    
    def test_with_quality(self):
        result = image_url('photo.jpg', '', quality=85)
        assert result == '/assets/photo.jpg?q=85'
    
    def test_with_all_params(self):
        result = image_url('photo.jpg', '', width=800, height=600, quality=85)
        assert 'w=800' in result
        assert 'h=600' in result
        assert 'q=85' in result
    
    def test_with_base_url(self):
        result = image_url('photo.jpg', 'https://example.com')
        assert result == 'https://example.com/assets/photo.jpg'
    
    def test_empty_path(self):
        assert image_url('', '') == ''


class TestImageSrcset:
    """Tests for image_srcset filter."""
    
    def test_basic_srcset(self):
        result = image_srcset('photo.jpg', [400, 800])
        assert 'photo.jpg?w=400 400w' in result
        assert 'photo.jpg?w=800 800w' in result
    
    def test_empty_sizes(self):
        assert image_srcset('photo.jpg', []) == ''
    
    def test_empty_path(self):
        assert image_srcset('', [400, 800]) == ''


class TestImageSrcsetGen:
    """Tests for image_srcset_gen function."""
    
    def test_default_sizes(self):
        result = image_srcset_gen('photo.jpg')
        assert '400w' in result
        assert '800w' in result
        assert '1200w' in result
        assert '1600w' in result
    
    def test_custom_sizes(self):
        result = image_srcset_gen('photo.jpg', [320, 640])
        assert '320w' in result
        assert '640w' in result


class TestImageAlt:
    """Tests for image_alt filter."""
    
    def test_basic_filename(self):
        result = image_alt('mountain-sunset.jpg')
        assert result == 'Mountain Sunset'
    
    def test_with_underscores(self):
        result = image_alt('my_photo_2024.png')
        assert result == 'My Photo 2024'
    
    def test_mixed_separators(self):
        result = image_alt('cool-photo_here.jpg')
        assert result == 'Cool Photo Here'
    
    def test_empty_filename(self):
        assert image_alt('') == ''


class TestImageDataUri:
    """Tests for image_data_uri function."""
    
    def test_small_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / 'test.txt'
            file_path.write_text('test')
            
            result = image_data_uri('test.txt', Path(tmpdir))
            assert result.startswith('data:')
    
    def test_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = image_data_uri('missing.jpg', Path(tmpdir))
            assert result == ''
    
    def test_empty_path(self):
        result = image_data_uri('', Path('/tmp'))
        assert result == ''

