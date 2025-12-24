"""
Tests for JSON compatibility utilities.
"""

import json

import pytest


class TestJsonCompatDumps:
    """Tests for dumps function."""

    def test_dumps_basic(self):
        """Test basic JSON serialization."""
        from bengal.utils.json_compat import dumps

        data = {"key": "value", "number": 42}
        result = dumps(data)

        assert result == '{"key": "value", "number": 42}'

    def test_dumps_with_indent(self):
        """Test JSON serialization with indentation."""
        from bengal.utils.json_compat import dumps

        data = {"key": "value"}
        result = dumps(data, indent=2)

        assert result == '{\n  "key": "value"\n}'

    def test_dumps_unicode(self):
        """Test JSON serialization with Unicode."""
        from bengal.utils.json_compat import dumps

        data = {"greeting": "Hello 世界", "emoji": "🐯"}
        result = dumps(data)

        # Should not escape Unicode
        assert "世界" in result
        assert "🐯" in result

    def test_dumps_nested(self):
        """Test JSON serialization with nested structures."""
        from bengal.utils.json_compat import dumps

        data = {"level1": {"level2": {"level3": "value"}}}
        result = dumps(data)

        parsed = json.loads(result)
        assert parsed == data


class TestJsonCompatLoads:
    """Tests for loads function."""

    def test_loads_basic(self):
        """Test basic JSON deserialization."""
        from bengal.utils.json_compat import loads

        data = '{"key": "value"}'
        result = loads(data)

        assert result == {"key": "value"}

    def test_loads_bytes(self):
        """Test JSON deserialization from bytes."""
        from bengal.utils.json_compat import loads

        data = b'{"key": "value"}'
        result = loads(data)

        assert result == {"key": "value"}

    def test_loads_invalid_json(self):
        """Test error on invalid JSON."""
        from bengal.utils.json_compat import JSONDecodeError, loads

        with pytest.raises(JSONDecodeError):
            loads('{"invalid": }')


class TestJsonCompatDump:
    """Tests for dump function (file write)."""

    def test_dump_basic(self, tmp_path):
        """Test JSON file write."""
        from bengal.utils.json_compat import dump

        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        dump(data, file_path)

        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded == data

    def test_dump_creates_parent_dirs(self, tmp_path):
        """Test that dump creates parent directories."""
        from bengal.utils.json_compat import dump

        file_path = tmp_path / "nested" / "dir" / "test.json"
        data = {"test": "value"}

        dump(data, file_path)

        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded == data

    def test_dump_with_indent(self, tmp_path):
        """Test JSON file write with indentation."""
        from bengal.utils.json_compat import dump

        file_path = tmp_path / "formatted.json"
        data = {"key": "value"}

        dump(data, file_path, indent=2)

        content = file_path.read_text()
        assert "\n" in content
        assert '  "key"' in content

    def test_dump_compact(self, tmp_path):
        """Test compact JSON file write."""
        from bengal.utils.json_compat import dump

        file_path = tmp_path / "compact.json"
        data = {"key": "value"}

        dump(data, file_path, indent=None)

        content = file_path.read_text()
        assert content == '{"key": "value"}'


class TestJsonCompatLoad:
    """Tests for load function (file read)."""

    def test_load_basic(self, tmp_path):
        """Test JSON file read."""
        from bengal.utils.json_compat import load

        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        file_path.write_text(json.dumps(data))

        result = load(file_path)

        assert result == data

    def test_load_file_not_found(self, tmp_path):
        """Test error on missing file."""
        from bengal.utils.json_compat import load

        with pytest.raises(FileNotFoundError):
            load(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path):
        """Test error on invalid JSON file."""
        from bengal.utils.json_compat import JSONDecodeError, load

        file_path = tmp_path / "invalid.json"
        file_path.write_text('{"invalid": }')

        with pytest.raises(JSONDecodeError):
            load(file_path)


class TestJsonCompatRoundtrip:
    """Test dump/load roundtrip."""

    def test_roundtrip_complex_data(self, tmp_path):
        """Test roundtrip with complex data."""
        from bengal.utils.json_compat import dump, load

        file_path = tmp_path / "complex.json"
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, "four"],
            "nested": {"a": {"b": {"c": "deep"}}},
            "unicode": "Hello 世界 🐯",
        }

        dump(data, file_path)
        result = load(file_path)

        assert result == data


