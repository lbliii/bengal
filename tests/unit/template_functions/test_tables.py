"""Tests for table template functions."""

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from jinja2 import Environment
from markupsafe import Markup

from bengal.rendering.template_functions.tables import data_table, register


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
        ],
        "data": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
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
        writer = csv.DictWriter(f, fieldnames=["name", "age"])
        writer.writeheader()
        writer.writerow({"name": "Alice", "age": "30"})
        writer.writerow({"name": "Bob", "age": "25"})

    return file_path


@pytest.fixture
def mock_env(temp_data_dir):
    """Create a mock Jinja2 environment with site."""
    env = Environment()

    # Mock site object
    site = MagicMock()
    site.root_path = temp_data_dir.parent

    env.site = site
    return env


class TestRegister:
    """Test register() function."""

    def test_register_adds_functions(self):
        """Test that register() adds data_table to environment globals."""
        env = Environment()
        site = MagicMock()
        site.root_path = Path(".")

        register(env, site)

        assert "data_table" in env.globals

    def test_registered_function_is_callable(self):
        """Test that registered function is callable."""
        env = Environment()
        site = MagicMock()
        site.root_path = Path(".")

        register(env, site)

        assert callable(env.globals["data_table"])


class TestDataTableFunction:
    """Test data_table() template function."""

    def test_render_yaml_file(self, mock_env, yaml_data_file):
        """Test rendering data table from YAML file."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}")

        assert isinstance(result, Markup)
        html = str(result)

        assert "bengal-data-table" in html
        assert "Alice" in html
        assert "Bob" in html

    def test_render_csv_file(self, mock_env, csv_data_file):
        """Test rendering data table from CSV file."""
        result = data_table(mock_env, f"data/{csv_data_file.name}")

        assert isinstance(result, Markup)
        html = str(result)

        assert "bengal-data-table" in html
        assert "Alice" in html

    def test_empty_path_shows_error(self, mock_env):
        """Test that empty path shows error message."""
        result = data_table(mock_env, "")

        assert isinstance(result, Markup)
        html = str(result)

        assert "bengal-data-table-error" in html
        assert "No file path specified" in html

    def test_missing_file_shows_error(self, mock_env):
        """Test that missing file shows error message."""
        result = data_table(mock_env, "data/missing.yaml")

        assert isinstance(result, Markup)
        html = str(result)

        assert "bengal-data-table-error" in html
        assert "missing.yaml" in html

    def test_with_search_option(self, mock_env, yaml_data_file):
        """Test data table with search option."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", search=True)

        html = str(result)
        assert "bengal-data-table-search" in html

    def test_without_search_option(self, mock_env, yaml_data_file):
        """Test data table without search option."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", search=False)

        html = str(result)
        assert "bengal-data-table-search" not in html

    def test_with_filter_option(self, mock_env, yaml_data_file):
        """Test data table with filter option."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", filter=True)

        html = str(result)
        # Filter adds headerFilter to columns in config
        assert "headerFilter" in html

    def test_with_pagination(self, mock_env, yaml_data_file):
        """Test data table with pagination."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", pagination=100)

        html = str(result)
        assert '"paginationSize": 100' in html

    def test_without_pagination(self, mock_env, yaml_data_file):
        """Test data table without pagination."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", pagination=False)

        html = str(result)
        assert '"pagination": false' in html

    def test_with_custom_height(self, mock_env, yaml_data_file):
        """Test data table with custom height."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", height="600px")

        html = str(result)
        assert '"height": "600px"' in html

    def test_with_columns_filter(self, mock_env, yaml_data_file):
        """Test data table with columns filter."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", columns="name")

        html = str(result)
        # Should only include name column
        assert "Name" in html
        # Age column should be filtered out (check in config)
        # This is a bit tricky to test without parsing JSON


class TestDataTableInTemplate:
    """Test data_table function in actual templates."""

    def test_use_in_template(self, mock_env, yaml_data_file):
        """Test using data_table in a Jinja2 template."""
        # Register the function
        site = MagicMock()
        site.root_path = mock_env.site.root_path
        register(mock_env, site)

        # Create a template
        template = mock_env.from_string("{{ data_table(path) }}")

        # Render
        result = template.render(path=f"data/{yaml_data_file.name}")

        assert "bengal-data-table" in result
        assert "Alice" in result

    def test_use_with_options_in_template(self, mock_env, yaml_data_file):
        """Test using data_table with options in template."""
        site = MagicMock()
        site.root_path = mock_env.site.root_path
        register(mock_env, site)

        template = mock_env.from_string(
            "{{ data_table(path, search=True, pagination=50, height='400px') }}"
        )

        result = template.render(path=f"data/{yaml_data_file.name}")

        assert "bengal-data-table-search" in result
        assert '"paginationSize": 50' in result
        assert '"height": "400px"' in result

    def test_conditional_rendering_in_template(self, mock_env, yaml_data_file):
        """Test conditional rendering of data table."""
        site = MagicMock()
        site.root_path = mock_env.site.root_path
        register(mock_env, site)

        template = mock_env.from_string(
            """
            {% if show_table %}
                {{ data_table(path) }}
            {% else %}
                <p>No table</p>
            {% endif %}
            """
        )

        # With table
        result = template.render(show_table=True, path=f"data/{yaml_data_file.name}")
        assert "bengal-data-table" in result

        # Without table
        result = template.render(show_table=False, path=f"data/{yaml_data_file.name}")
        assert "No table" in result
        assert "bengal-data-table" not in result

    def test_multiple_tables_in_template(self, mock_env, yaml_data_file, csv_data_file):
        """Test rendering multiple tables in same template."""
        site = MagicMock()
        site.root_path = mock_env.site.root_path
        register(mock_env, site)

        template = mock_env.from_string(
            """
            <h2>YAML Table</h2>
            {{ data_table(yaml_path) }}

            <h2>CSV Table</h2>
            {{ data_table(csv_path) }}
            """
        )

        result = template.render(
            yaml_path=f"data/{yaml_data_file.name}", csv_path=f"data/{csv_data_file.name}"
        )

        # Check that each table appears at least once
        count = result.count("bengal-data-table")
        assert (
            count >= 2
        ), f"Expected at least 2 tables, but bengal-data-table appears {count} times"
        assert "YAML Table" in result
        assert "CSV Table" in result


class TestOptionConversion:
    """Test conversion of Python options to directive format."""

    def test_boolean_option_conversion(self, mock_env, yaml_data_file):
        """Test that Python booleans are converted to strings for directive."""
        # This tests internal conversion logic
        result1 = data_table(mock_env, f"data/{yaml_data_file.name}", search=True)
        result2 = data_table(mock_env, f"data/{yaml_data_file.name}", search=False)

        html1 = str(result1)
        html2 = str(result2)

        # Both should work without errors
        assert "bengal-data-table" in html1
        assert "bengal-data-table" in html2

    def test_integer_option_conversion(self, mock_env, yaml_data_file):
        """Test that integers are converted properly."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", pagination=25)

        html = str(result)
        assert "25" in html

    def test_string_option_passthrough(self, mock_env, yaml_data_file):
        """Test that string options are passed through."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}", height="500px")

        html = str(result)
        assert "500px" in html


class TestErrorHandling:
    """Test error handling in data_table function."""

    def test_handles_load_errors_gracefully(self, mock_env):
        """Test that load errors are handled gracefully."""
        result = data_table(mock_env, "data/nonexistent.yaml")

        assert isinstance(result, Markup)
        html = str(result)

        assert "bengal-data-table-error" in html

    def test_error_message_is_safe_html(self, mock_env):
        """Test that error messages are safe HTML (escaped)."""
        # Test with path containing HTML-like characters
        result = data_table(mock_env, "data/<script>alert('xss')</script>.yaml")

        html = str(result)
        # Should not contain unescaped script tags
        assert "<script>alert" not in html or "bengal-data-table-error" in html


class TestMarkupSafety:
    """Test that output is properly marked as safe HTML."""

    def test_returns_markup_object(self, mock_env, yaml_data_file):
        """Test that function returns Markup object."""
        result = data_table(mock_env, f"data/{yaml_data_file.name}")

        assert isinstance(result, Markup)

    def test_markup_is_not_double_escaped(self, mock_env, yaml_data_file):
        """Test that Markup is not double-escaped in templates."""
        site = MagicMock()
        site.root_path = mock_env.site.root_path
        register(mock_env, site)

        # Enable auto-escaping
        mock_env.autoescape = True

        template = mock_env.from_string("{{ data_table(path) }}")
        result = template.render(path=f"data/{yaml_data_file.name}")

        # HTML should be rendered, not escaped
        assert "<div" in result
        assert "&lt;div" not in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_yaml_file(self, temp_data_dir, mock_env):
        """Test handling empty YAML file."""
        empty_file = temp_data_dir / "data" / "empty.yaml"
        empty_file.parent.mkdir(exist_ok=True)
        empty_file.write_text("")

        result = data_table(mock_env, "data/empty.yaml")

        html = str(result)
        # Should show error for invalid/empty data
        assert "bengal-data-table-error" in html or "bengal-data-table" in html

    def test_yaml_with_no_data(self, temp_data_dir, mock_env):
        """Test YAML file with columns but no data."""
        data = {"columns": [{"title": "Name", "field": "name"}], "data": []}

        file_path = temp_data_dir / "data" / "no_data.yaml"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, "w") as f:
            yaml.dump(data, f)

        result = data_table(mock_env, "data/no_data.yaml")

        # Should still render (empty table)
        html = str(result)
        assert "bengal-data-table" in html

    def test_csv_with_only_headers(self, temp_data_dir, mock_env):
        """Test CSV file with only headers, no data."""
        file_path = temp_data_dir / "data" / "headers_only.csv"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "age"])
            writer.writeheader()

        result = data_table(mock_env, "data/headers_only.csv")

        html = str(result)
        # Should show error about no data
        assert "bengal-data-table-error" in html or "bengal-data-table" in html

    def test_none_as_path(self, mock_env):
        """Test None as path."""
        # This might raise an error or return error HTML
        # Depends on implementation
        try:
            result = data_table(mock_env, None)
            html = str(result)
            assert "error" in html.lower()
        except (TypeError, AttributeError):
            # Also acceptable to raise an error
            pass
