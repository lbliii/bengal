"""Tests for data table directive."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from bengal.rendering.plugins.directives.data_table import (
    DataTableDirective,
    render_data_table,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directory for test data files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def yaml_data_file(temp_data_dir):
    """Create a sample YAML data file."""
    data = {
        "columns": [
            {"title": "Name", "field": "name"},
            {"title": "Age", "field": "age"},
            {"title": "City", "field": "city"},
        ],
        "data": [
            {"name": "Alice", "age": 30, "city": "Seattle"},
            {"name": "Bob", "age": 25, "city": "Portland"},
            {"name": "Charlie", "age": 35, "city": "Denver"},
        ],
    }

    file_path = temp_data_dir / "people.yaml"
    with open(file_path, "w") as f:
        yaml.dump(data, f)

    return file_path


@pytest.fixture
def csv_data_file(temp_data_dir):
    """Create a sample CSV data file."""
    file_path = temp_data_dir / "people.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
        writer.writeheader()
        writer.writerow({"name": "Alice", "age": "30", "city": "Seattle"})
        writer.writerow({"name": "Bob", "age": "25", "city": "Portland"})
        writer.writerow({"name": "Charlie", "age": "35", "city": "Denver"})

    return file_path


@pytest.fixture
def mock_state(temp_data_dir):
    """Create a mock state object with root_path."""

    class State:
        pass

    state = State()
    state.root_path = temp_data_dir.parent
    return state


class TestDataTableDirective:
    """Test DataTableDirective class."""

    def test_initialization(self):
        """Test creating directive instance."""
        directive = DataTableDirective()
        assert directive is not None

    def test_parse_yaml_file(self, yaml_data_file, mock_state):
        """Test parsing YAML data file."""
        directive = DataTableDirective()

        # Mock the match object
        match = MagicMock()
        match.group.return_value = f"data/{yaml_data_file.name}"

        # Mock the block parser
        block = MagicMock()

        result = directive.parse(block, match, mock_state)

        assert result["type"] == "data_table"
        assert "error" not in result["attrs"]
        assert len(result["attrs"]["columns"]) == 3
        assert len(result["attrs"]["data"]) == 3
        assert result["attrs"]["columns"][0]["title"] == "Name"
        assert result["attrs"]["data"][0]["name"] == "Alice"

    def test_parse_csv_file(self, csv_data_file, mock_state):
        """Test parsing CSV data file."""
        directive = DataTableDirective()

        match = MagicMock()
        match.group.return_value = f"data/{csv_data_file.name}"

        block = MagicMock()

        result = directive.parse(block, match, mock_state)

        assert result["type"] == "data_table"
        assert "error" not in result["attrs"]
        assert len(result["attrs"]["columns"]) == 3
        assert len(result["attrs"]["data"]) == 3
        assert result["attrs"]["columns"][0]["title"] == "name"

    def test_parse_missing_file(self, mock_state):
        """Test parsing when file doesn't exist."""
        directive = DataTableDirective()

        match = MagicMock()
        match.group.return_value = "data/missing.yaml"

        block = MagicMock()

        result = directive.parse(block, match, mock_state)

        assert result["type"] == "data_table"
        assert "error" in result["attrs"]
        assert "not found" in result["attrs"]["error"].lower()

    def test_parse_no_path(self, mock_state):
        """Test parsing when no file path is provided."""
        directive = DataTableDirective()

        match = MagicMock()
        match.group.return_value = ""

        block = MagicMock()

        result = directive.parse(block, match, mock_state)

        assert result["type"] == "data_table"
        assert "error" in result["attrs"]


class TestLoadData:
    """Test _load_data() method."""

    def test_load_yaml_with_columns(self, yaml_data_file, mock_state):
        """Test loading YAML file with explicit columns."""
        directive = DataTableDirective()
        relative_path = f"data/{yaml_data_file.name}"

        result = directive._load_data(relative_path, mock_state)

        assert "error" not in result
        assert "columns" in result
        assert "data" in result
        assert len(result["columns"]) == 3
        assert len(result["data"]) == 3

    def test_load_yaml_without_columns(self, temp_data_dir, mock_state):
        """Test loading YAML file without explicit columns (auto-generate)."""
        # Create YAML without columns field
        data = {"data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}

        file_path = temp_data_dir / "auto_columns.yaml"
        with open(file_path, "w") as f:
            yaml.dump(data, f)

        directive = DataTableDirective()
        result = directive._load_data("data/auto_columns.yaml", mock_state)

        assert "error" not in result
        assert len(result["columns"]) == 2
        # Auto-generated columns from keys
        column_fields = [col["field"] for col in result["columns"]]
        assert "name" in column_fields
        assert "age" in column_fields

    def test_load_csv(self, csv_data_file, mock_state):
        """Test loading CSV file."""
        directive = DataTableDirective()
        result = directive._load_data(f"data/{csv_data_file.name}", mock_state)

        assert "error" not in result
        assert len(result["columns"]) == 3
        assert len(result["data"]) == 3
        assert result["data"][0]["name"] == "Alice"

    def test_load_missing_file(self, mock_state):
        """Test loading non-existent file."""
        directive = DataTableDirective()
        result = directive._load_data("data/missing.yaml", mock_state)

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_load_unsupported_format(self, temp_data_dir, mock_state):
        """Test loading unsupported file format."""
        file_path = temp_data_dir / "file.txt"
        file_path.write_text("some data")

        directive = DataTableDirective()
        # Pass path relative to root_path (which is temp_data_dir.parent)
        result = directive._load_data("data/file.txt", mock_state)

        assert "error" in result
        assert "unsupported" in result["error"].lower()

    def test_load_file_too_large(self, tmp_path, mock_state):
        """Test loading file that exceeds size limit."""
        # Create a file larger than 5MB
        large_file = tmp_path / "large.yaml"
        large_file.write_text("a" * 1_100_000)  # >1MB

        directive = DataTableDirective()

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 1_100_000  # 6MB

            result = directive._load_data(str(large_file), mock_state)

            assert "error" in result
            assert "too large" in result["error"].lower()

    def test_load_invalid_yaml(self, temp_data_dir, mock_state):
        """Test loading invalid YAML."""
        invalid_file = temp_data_dir / "data" / "invalid.yaml"
        invalid_file.parent.mkdir(exist_ok=True)
        invalid_file.write_text("invalid: yaml: content: :")

        directive = DataTableDirective()
        result = directive._load_data("data/invalid.yaml", mock_state)

        assert "error" in result


class TestOptionParsing:
    """Test parsing directive options."""

    def test_parse_bool_true(self):
        """Test parsing boolean true values."""
        directive = DataTableDirective()

        assert directive._parse_bool("true") is True
        assert directive._parse_bool("True") is True
        assert directive._parse_bool("1") is True
        assert directive._parse_bool("yes") is True
        assert directive._parse_bool("on") is True
        assert directive._parse_bool(True) is True

    def test_parse_bool_false(self):
        """Test parsing boolean false values."""
        directive = DataTableDirective()

        assert directive._parse_bool("false") is False
        assert directive._parse_bool("False") is False
        assert directive._parse_bool("0") is False
        assert directive._parse_bool("no") is False
        assert directive._parse_bool("off") is False
        assert directive._parse_bool(False) is False

    def test_parse_pagination_numbers(self):
        """Test parsing pagination number values."""
        directive = DataTableDirective()

        assert directive._parse_pagination("50") == 50
        assert directive._parse_pagination("100") == 100
        assert directive._parse_pagination(25) == 25

    def test_parse_pagination_false(self):
        """Test parsing pagination false values."""
        directive = DataTableDirective()

        assert directive._parse_pagination("false") is False
        assert directive._parse_pagination("0") is False
        assert directive._parse_pagination("no") is False
        assert directive._parse_pagination("off") is False
        assert directive._parse_pagination(False) is False

    def test_parse_pagination_invalid(self):
        """Test parsing invalid pagination values defaults to 50."""
        directive = DataTableDirective()

        assert directive._parse_pagination("invalid") == 50
        assert directive._parse_pagination("abc") == 50

    def test_parse_pagination_negative(self):
        """Test parsing negative pagination returns 0."""
        directive = DataTableDirective()

        assert directive._parse_pagination("-10") == 0
        assert directive._parse_pagination("-1") == 0

    def test_parse_columns_list(self):
        """Test parsing columns list."""
        directive = DataTableDirective()

        result = directive._parse_columns("col1,col2,col3")
        assert result == ["col1", "col2", "col3"]

    def test_parse_columns_with_spaces(self):
        """Test parsing columns list with spaces."""
        directive = DataTableDirective()

        result = directive._parse_columns("col1, col2 , col3")
        assert result == ["col1", "col2", "col3"]

    def test_parse_columns_empty(self):
        """Test parsing empty columns string returns None."""
        directive = DataTableDirective()

        assert directive._parse_columns("") is None
        assert directive._parse_columns("   ") is None


class TestTableID:
    """Test table ID generation."""

    def test_generate_table_id(self):
        """Test generating unique table ID from path."""
        directive = DataTableDirective()

        id1 = directive._generate_table_id("data/file1.yaml")
        id2 = directive._generate_table_id("data/file2.yaml")
        id3 = directive._generate_table_id("data/file1.yaml")

        # IDs should start with prefix
        assert id1.startswith("data-table-")
        assert id2.startswith("data-table-")

        # Same path should generate same ID
        assert id1 == id3

        # Different paths should generate different IDs
        assert id1 != id2

    def test_table_id_length(self):
        """Test that table ID has consistent length."""
        directive = DataTableDirective()

        id1 = directive._generate_table_id("short.yaml")
        id2 = directive._generate_table_id("very/long/path/to/data/file.yaml")

        # Both should have same format: "data-table-" + 8 hex chars
        assert len(id1) == len("data-table-") + 8
        assert len(id2) == len("data-table-") + 8


class TestRenderDataTable:
    """Test render_data_table() function."""

    def test_render_basic_table(self):
        """Test rendering basic data table."""
        attrs = {
            "table_id": "data-table-abc123",
            "path": "data/test.yaml",
            "columns": [{"title": "Name", "field": "name"}, {"title": "Age", "field": "age"}],
            "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "search": True,
            "filter": True,
            "sort": True,
            "pagination": 50,
            "height": "auto",
            "visible_columns": None,
        }

        html = render_data_table(None, "", **attrs)

        assert "data-table-abc123" in html
        assert "bengal-data-table" in html
        assert "application/json" in html

    def test_render_with_error(self):
        """Test rendering error message."""
        attrs = {"error": "File not found", "path": "data/missing.yaml"}

        html = render_data_table(None, "", **attrs)

        assert "bengal-data-table-error" in html
        assert "File not found" in html
        assert "data/missing.yaml" in html

    def test_render_with_search(self):
        """Test rendering with search box."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [],
            "data": [],
            "search": True,
            "filter": False,
            "pagination": False,
            "height": "auto",
        }

        html = render_data_table(None, "", **attrs)

        assert "bengal-data-table-search" in html
        assert 'placeholder="Search table..."' in html

    def test_render_without_search(self):
        """Test rendering without search box."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [],
            "data": [],
            "search": False,
            "filter": False,
            "pagination": False,
            "height": "auto",
        }

        html = render_data_table(None, "", **attrs)

        assert "bengal-data-table-search" not in html

    def test_render_with_pagination(self):
        """Test rendering with pagination."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [],
            "data": [],
            "search": False,
            "filter": False,
            "pagination": 25,
            "height": "auto",
        }

        html = render_data_table(None, "", **attrs)

        # Check JSON config contains pagination settings
        assert "pagination" in html
        assert '"paginationSize": 25' in html

    def test_render_without_pagination(self):
        """Test rendering without pagination."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [],
            "data": [],
            "search": False,
            "filter": False,
            "pagination": False,
            "height": "auto",
        }

        html = render_data_table(None, "", **attrs)

        assert '"pagination": false' in html

    def test_render_with_custom_height(self):
        """Test rendering with custom height."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [],
            "data": [],
            "search": False,
            "filter": False,
            "pagination": False,
            "height": "400px",
        }

        html = render_data_table(None, "", **attrs)

        assert '"height": "400px"' in html

    def test_render_with_visible_columns(self):
        """Test rendering with column visibility filter."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [
                {"title": "Name", "field": "name"},
                {"title": "Age", "field": "age"},
                {"title": "City", "field": "city"},
            ],
            "data": [],
            "search": False,
            "filter": False,
            "pagination": False,
            "height": "auto",
            "visible_columns": ["name", "city"],
        }

        html = render_data_table(None, "", **attrs)

        # Should only include visible columns in config
        # The JSON is in the next part between script tags
        json_start = html.find(">{") + 1
        json_end = html.find("}</script>") + 1
        config_json = json.loads(html[json_start:json_end])

        assert len(config_json["columns"]) == 2
        fields = [col["field"] for col in config_json["columns"]]
        assert "name" in fields
        assert "city" in fields
        assert "age" not in fields

    def test_render_json_config(self):
        """Test that JSON config is properly formatted."""
        attrs = {
            "table_id": "data-table-test",
            "columns": [{"title": "Name", "field": "name"}],
            "data": [{"name": "Alice"}],
            "search": False,
            "filter": False,
            "pagination": 50,
            "height": "auto",
        }

        html = render_data_table(None, "", **attrs)

        # Extract JSON config from HTML
        json_start = html.find(">{") + 1
        json_end = html.find("}</script>") + 1
        config_json_str = html[json_start:json_end]

        # Should be valid JSON
        config = json.loads(config_json_str)
        assert "columns" in config
        assert "data" in config
        assert config["data"][0]["name"] == "Alice"


class TestDirectiveIntegration:
    """Test full directive integration."""

    def test_parse_with_options(self, yaml_data_file, mock_state):
        """Test parsing with all options."""
        directive = DataTableDirective()

        match = MagicMock()
        match.group.return_value = f"data/{yaml_data_file.name}"

        # Mock parse_title and parse_options
        directive.parse_title = lambda m: f"data/{yaml_data_file.name}"
        directive.parse_options = lambda m: [
            ("search", "false"),
            ("filter", "true"),
            ("pagination", "100"),
            ("height", "500px"),
        ]

        block = MagicMock()
        result = directive.parse(block, match, mock_state)

        assert result["attrs"]["search"] is False
        assert result["attrs"]["filter"] is True
        assert result["attrs"]["pagination"] == 100
        assert result["attrs"]["height"] == "500px"

    def test_complete_workflow(self, yaml_data_file, mock_state):
        """Test complete parse-to-render workflow."""
        directive = DataTableDirective()

        # Parse
        match = MagicMock()
        match.group.return_value = f"data/{yaml_data_file.name}"
        directive.parse_title = lambda m: f"data/{yaml_data_file.name}"
        directive.parse_options = lambda m: []

        block = MagicMock()
        result = directive.parse(block, match, mock_state)

        # Render
        html = render_data_table(None, "", **result["attrs"])

        # Verify output
        assert "bengal-data-table" in html
        assert "Alice" in html
        assert "Bob" in html
        assert "Charlie" in html
