"""
Tests for file I/O utilities.
"""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from bengal.utils.file_io import (
    read_text_file,
    load_json,
    load_yaml,
    load_toml,
    load_data_file,
    write_text_file,
    write_json,
)


class TestReadTextFile:
    """Tests for read_text_file function."""
    
    def test_read_utf8_file(self, tmp_path):
        """Test reading UTF-8 encoded file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World! 你好世界"
        file_path.write_text(content, encoding='utf-8')
        
        result = read_text_file(file_path)
        assert result == content
    
    def test_read_with_fallback_encoding(self, tmp_path):
        """Test fallback to latin-1 encoding."""
        file_path = tmp_path / "latin1.txt"
        # Write with latin-1 encoding
        with open(file_path, 'w', encoding='latin-1') as f:
            f.write("café")
        
        # Should fallback to latin-1 when UTF-8 fails
        result = read_text_file(file_path, fallback_encoding='latin-1')
        assert result is not None
        assert "caf" in result
    
    def test_file_not_found_raise(self, tmp_path):
        """Test FileNotFoundError when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            read_text_file(tmp_path / "nonexistent.txt", on_error='raise')
    
    def test_file_not_found_return_empty(self, tmp_path):
        """Test returning empty string when file not found."""
        result = read_text_file(tmp_path / "nonexistent.txt", on_error='return_empty')
        assert result == ''
    
    def test_file_not_found_return_none(self, tmp_path):
        """Test returning None when file not found."""
        result = read_text_file(tmp_path / "nonexistent.txt", on_error='return_none')
        assert result is None
    
    def test_path_is_directory_raise(self, tmp_path):
        """Test ValueError when path is a directory."""
        with pytest.raises(ValueError, match="not a file"):
            read_text_file(tmp_path, on_error='raise')
    
    def test_path_is_directory_return_empty(self, tmp_path):
        """Test returning empty string when path is directory."""
        result = read_text_file(tmp_path, on_error='return_empty')
        assert result == ''
    
    def test_empty_file(self, tmp_path):
        """Test reading empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text('')
        
        result = read_text_file(file_path)
        assert result == ''
    
    def test_multiline_content(self, tmp_path):
        """Test reading multiline content."""
        file_path = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"
        file_path.write_text(content)
        
        result = read_text_file(file_path)
        assert result == content
        assert result.count('\n') == 2


class TestLoadJson:
    """Tests for load_json function."""
    
    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON file."""
        file_path = tmp_path / "data.json"
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        file_path.write_text(json.dumps(data))
        
        result = load_json(file_path)
        assert result == data
    
    def test_load_empty_object(self, tmp_path):
        """Test loading empty JSON object."""
        file_path = tmp_path / "empty.json"
        file_path.write_text('{}')
        
        result = load_json(file_path)
        assert result == {}
    
    def test_load_array(self, tmp_path):
        """Test loading JSON array."""
        file_path = tmp_path / "array.json"
        data = [1, 2, 3, "four"]
        file_path.write_text(json.dumps(data))
        
        result = load_json(file_path)
        assert result == data
    
    def test_invalid_json_raise(self, tmp_path):
        """Test JSONDecodeError on invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text('{"invalid": }')
        
        with pytest.raises(json.JSONDecodeError):
            load_json(file_path, on_error='raise')
    
    def test_invalid_json_return_empty(self, tmp_path):
        """Test returning empty dict on invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text('{"invalid": }')
        
        result = load_json(file_path, on_error='return_empty')
        assert result == {}
    
    def test_invalid_json_return_none(self, tmp_path):
        """Test returning None on invalid JSON."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text('{"invalid": }')
        
        result = load_json(file_path, on_error='return_none')
        assert result is None
    
    def test_file_not_found_return_empty(self, tmp_path):
        """Test returning empty dict when file not found."""
        result = load_json(tmp_path / "missing.json", on_error='return_empty')
        assert result == {}


class TestLoadYaml:
    """Tests for load_yaml function."""
    
    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML file."""
        file_path = tmp_path / "data.yaml"
        content = """
        key: value
        number: 42
        nested:
          a: 1
        """
        file_path.write_text(content)
        
        result = load_yaml(file_path)
        assert result['key'] == 'value'
        assert result['number'] == 42
        assert result['nested']['a'] == 1
    
    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file."""
        file_path = tmp_path / "empty.yaml"
        file_path.write_text('')
        
        result = load_yaml(file_path)
        assert result == {}
    
    def test_load_list_yaml(self, tmp_path):
        """Test loading YAML list."""
        file_path = tmp_path / "list.yaml"
        content = """
        - item1
        - item2
        - item3
        """
        file_path.write_text(content)
        
        result = load_yaml(file_path)
        assert result == ['item1', 'item2', 'item3']
    
    def test_invalid_yaml_raise(self, tmp_path):
        """Test YAMLError on invalid YAML."""
        pytest.importorskip('yaml')  # Skip if yaml not installed
        
        file_path = tmp_path / "invalid.yaml"
        file_path.write_text('key: [invalid')
        
        with pytest.raises(Exception):  # yaml.YAMLError
            load_yaml(file_path, on_error='raise')
    
    def test_invalid_yaml_return_empty(self, tmp_path):
        """Test returning empty dict on invalid YAML."""
        pytest.importorskip('yaml')
        
        file_path = tmp_path / "invalid.yaml"
        file_path.write_text('key: [invalid')
        
        result = load_yaml(file_path, on_error='return_empty')
        assert result == {}
    
    def test_yaml_not_installed_return_empty(self, tmp_path, monkeypatch):
        """Test graceful handling when PyYAML not installed."""
        file_path = tmp_path / "data.yaml"
        file_path.write_text('key: value')
        
        # Mock yaml import to fail by raising ImportError
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError("No module named 'yaml'")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr(builtins, '__import__', mock_import)
        
        result = load_yaml(file_path, on_error='return_empty')
        assert result == {}


class TestLoadToml:
    """Tests for load_toml function."""
    
    def test_load_valid_toml(self, tmp_path):
        """Test loading valid TOML file."""
        file_path = tmp_path / "data.toml"
        content = """
        key = "value"
        number = 42
        
        [nested]
        a = 1
        """
        file_path.write_text(content)
        
        result = load_toml(file_path)
        assert result['key'] == 'value'
        assert result['number'] == 42
        assert result['nested']['a'] == 1
    
    def test_load_empty_toml(self, tmp_path):
        """Test loading empty TOML file."""
        file_path = tmp_path / "empty.toml"
        file_path.write_text('')
        
        result = load_toml(file_path)
        assert result == {}
    
    def test_invalid_toml_raise(self, tmp_path):
        """Test error on invalid TOML."""
        file_path = tmp_path / "invalid.toml"
        file_path.write_text('[invalid')
        
        with pytest.raises(Exception):  # toml.TomlDecodeError
            load_toml(file_path, on_error='raise')
    
    def test_invalid_toml_return_empty(self, tmp_path):
        """Test returning empty dict on invalid TOML."""
        file_path = tmp_path / "invalid.toml"
        file_path.write_text('[invalid')
        
        result = load_toml(file_path, on_error='return_empty')
        assert result == {}


class TestLoadDataFile:
    """Tests for load_data_file function."""
    
    def test_load_json_by_extension(self, tmp_path):
        """Test auto-detection of JSON file."""
        file_path = tmp_path / "data.json"
        data = {"format": "json"}
        file_path.write_text(json.dumps(data))
        
        result = load_data_file(file_path)
        assert result == data
    
    def test_load_yaml_by_extension(self, tmp_path):
        """Test auto-detection of YAML file."""
        file_path = tmp_path / "data.yaml"
        content = "format: yaml"
        file_path.write_text(content)
        
        result = load_data_file(file_path)
        assert result['format'] == 'yaml'
    
    def test_load_yml_extension(self, tmp_path):
        """Test .yml extension recognition."""
        file_path = tmp_path / "data.yml"
        content = "format: yml"
        file_path.write_text(content)
        
        result = load_data_file(file_path)
        assert result['format'] == 'yml'
    
    def test_load_toml_by_extension(self, tmp_path):
        """Test auto-detection of TOML file."""
        file_path = tmp_path / "data.toml"
        content = 'format = "toml"'
        file_path.write_text(content)
        
        result = load_data_file(file_path)
        assert result['format'] == 'toml'
    
    def test_unsupported_extension_raise(self, tmp_path):
        """Test ValueError for unsupported format."""
        file_path = tmp_path / "data.xml"
        file_path.write_text('<data/>')
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_data_file(file_path, on_error='raise')
    
    def test_unsupported_extension_return_empty(self, tmp_path):
        """Test returning empty dict for unsupported format."""
        file_path = tmp_path / "data.xml"
        file_path.write_text('<data/>')
        
        result = load_data_file(file_path, on_error='return_empty')
        assert result == {}


class TestWriteTextFile:
    """Tests for write_text_file function."""
    
    def test_write_simple_text(self, tmp_path):
        """Test writing simple text file."""
        file_path = tmp_path / "output.txt"
        content = "Hello, World!"
        
        write_text_file(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_write_with_parent_creation(self, tmp_path):
        """Test creating parent directories."""
        file_path = tmp_path / "subdir" / "nested" / "file.txt"
        content = "Nested file"
        
        write_text_file(file_path, content, create_parents=True)
        
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_write_multiline(self, tmp_path):
        """Test writing multiline content."""
        file_path = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"
        
        write_text_file(file_path, content)
        
        result = file_path.read_text()
        assert result == content
    
    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting existing file."""
        file_path = tmp_path / "existing.txt"
        file_path.write_text("Old content")
        
        new_content = "New content"
        write_text_file(file_path, new_content)
        
        assert file_path.read_text() == new_content
    
    def test_write_empty_string(self, tmp_path):
        """Test writing empty string."""
        file_path = tmp_path / "empty.txt"
        
        write_text_file(file_path, '')
        
        assert file_path.exists()
        assert file_path.read_text() == ''


class TestWriteJson:
    """Tests for write_json function."""
    
    def test_write_simple_dict(self, tmp_path):
        """Test writing simple dictionary as JSON."""
        file_path = tmp_path / "data.json"
        data = {"key": "value", "number": 42}
        
        write_json(file_path, data)
        
        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded == data
    
    def test_write_with_indent(self, tmp_path):
        """Test writing JSON with indentation."""
        file_path = tmp_path / "formatted.json"
        data = {"key": "value"}
        
        write_json(file_path, data, indent=2)
        
        content = file_path.read_text()
        assert content.count('\n') > 0  # Has newlines from formatting
        assert '  "key"' in content  # Has indentation
    
    def test_write_compact_json(self, tmp_path):
        """Test writing compact JSON."""
        file_path = tmp_path / "compact.json"
        data = {"key": "value"}
        
        write_json(file_path, data, indent=None)
        
        content = file_path.read_text()
        assert '\n' not in content or content.count('\n') <= 1  # No extra newlines
    
    def test_write_nested_structure(self, tmp_path):
        """Test writing nested JSON structure."""
        file_path = tmp_path / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }
        
        write_json(file_path, data)
        
        loaded = json.loads(file_path.read_text())
        assert loaded == data
    
    def test_write_list(self, tmp_path):
        """Test writing list as JSON."""
        file_path = tmp_path / "list.json"
        data = [1, 2, 3, "four"]
        
        write_json(file_path, data)
        
        loaded = json.loads(file_path.read_text())
        assert loaded == data
    
    def test_write_with_unicode(self, tmp_path):
        """Test writing JSON with Unicode characters."""
        file_path = tmp_path / "unicode.json"
        data = {"greeting": "Hello 世界", "emoji": "😀"}
        
        write_json(file_path, data)
        
        loaded = json.loads(file_path.read_text())
        assert loaded == data
    
    def test_write_with_parent_creation(self, tmp_path):
        """Test creating parent directories when writing JSON."""
        file_path = tmp_path / "nested" / "data.json"
        data = {"test": "value"}
        
        write_json(file_path, data, create_parents=True)
        
        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded == data
    
    def test_non_serializable_raises(self, tmp_path):
        """Test TypeError for non-serializable data."""
        file_path = tmp_path / "bad.json"
        
        class NonSerializable:
            pass
        
        with pytest.raises(TypeError):
            write_json(file_path, {"obj": NonSerializable()})

