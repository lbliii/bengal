"""
Test that all directives are properly registered with Mistune.

This test ensures we don't forget to register directives in the
create_documentation_directives() function.
"""

from __future__ import annotations

import inspect

import pytest

from bengal.directives.admonitions import AdmonitionDirective
from bengal.directives.build import BuildDirective
from bengal.directives.button import ButtonDirective
from bengal.directives.cards import (
    CardDirective,
    CardsDirective,
)
from bengal.directives.checklist import ChecklistDirective
from bengal.directives.code_tabs import CodeTabsDirective
from bengal.directives.data_table import DataTableDirective
from bengal.directives.dropdown import DropdownDirective
from bengal.directives.list_table import ListTableDirective
from bengal.directives.rubric import RubricDirective
from bengal.directives.tabs import TabItemDirective, TabSetDirective
from bengal.parsing import PatitasParser


class TestDirectiveRegistration:
    """Test that all directives are properly registered."""

    def test_all_directive_classes_importable(self):
        """Test that all directive classes can be imported from the directives package."""
        # This test ensures __init__.py imports are correct
        assert AdmonitionDirective is not None
        assert BuildDirective is not None
        assert ButtonDirective is not None
        assert CardDirective is not None
        assert CardsDirective is not None
        assert ChecklistDirective is not None
        assert CodeTabsDirective is not None
        assert DataTableDirective is not None
        assert DropdownDirective is not None
        assert ListTableDirective is not None
        assert RubricDirective is not None
        assert TabItemDirective is not None
        assert TabSetDirective is not None

    def test_data_table_directive_registered(self):
        """Test that data-table directive is registered and works."""
        parser = PatitasParser()

        # Test that the directive syntax is recognized (not treated as code)
        # Bengal uses colon-fenced syntax (:::{directive}) to avoid conflicts with code blocks
        content = """
:::{data-table} data/test.yaml
:search: true
:::
"""
        result = parser.parse(content, {})

        # Should contain data table error (file doesn't exist)
        # but should NOT contain raw directive syntax
        assert ":::{data-table}" not in result
        assert "bengal-data-table" in result or "Data Table Error" in result

    def test_all_core_directives_registered(self):
        """Test that all core directives are properly registered with Mistune."""
        parser = PatitasParser()

        # Test cases for each directive type
        # Bengal uses colon-fenced syntax (:::{directive}) to avoid conflicts with code blocks
        test_cases = [
            # (directive_name, markdown_content, expected_in_output)
            ("note", ":::{note}\nTest note\n:::", "admonition"),
            ("tip", ":::{tip}\nTest tip\n:::", "admonition"),
            ("warning", ":::{warning}\nTest warning\n:::", "admonition"),
            ("tabs", ":::{tabs}\n:::{tab-item} One\nContent\n:::\n:::", "tabs"),
            ("dropdown", ":::{dropdown} Title\nContent\n:::", "dropdown"),
            ("rubric", ":::{rubric} Heading\n:::", "rubric"),
            ("button", ":::{button} https://example.com\nClick me\n:::", "button button-primary"),
            ("card", ":::{card} Title\nContent\n:::", "card-title"),
            ("checklist", ":::{checklist}\n- Item one\n- Item two\n:::", "checklist"),
            ("list-table", ":::{list-table}\n* - Row 1\n  - Col 1\n:::", "list-table"),
            ("build", ":::{build}\n:::", "bengal-build-badge"),
        ]

        for directive_name, markdown, expected in test_cases:
            result = parser.parse(markdown, {})

            # Should NOT contain raw directive syntax
            assert f":::{{{directive_name}" not in result, (
                f"Directive '{directive_name}' not properly registered - raw syntax found in output"
            )

            # Should contain expected output marker
            assert expected in result, (
                f"Directive '{directive_name}' did not produce expected output. "
                f"Expected '{expected}' in output"
            )

    def test_myst_colon_syntax_registered(self):
        """Test that MyST colon syntax works for directives."""
        parser = PatitasParser()

        # Test colon-fenced directive
        content = """
:::{note}
This is a MyST-style note.
:::
"""
        result = parser.parse(content, {})

        assert ":::{note}" not in result
        assert "admonition" in result
        assert "This is a MyST-style note" in result

    def test_data_table_with_myst_syntax(self):
        """Test that data-table works with MyST colon syntax."""
        parser = PatitasParser()

        content = """
:::{data-table} data/test.yaml
:search: true
:::
"""
        result = parser.parse(content, {})

        # Should be processed as directive (not code block)
        assert ":::{data-table}" not in result
        assert "bengal-data-table" in result or "Data Table Error" in result


class TestDirectiveModuleConsistency:
    """Test that directive imports match what's actually registered."""

    def test_create_documentation_directives_includes_all_imports(self):
        """
        Verify that create_documentation_directives() includes all directive
        classes that are imported in bengal.directives.factory.

        Note: Directive classes have moved to bengal.directives.
        """
        # Import the module to inspect its source
        from bengal.directives import create_documentation_directives

        # Initialize the plugin (ensures registration code runs)
        create_documentation_directives()

        # We can't easily inspect the closure, but we can test that
        # all directive classes are actually being used
        directive_classes = [
            AdmonitionDirective,
            BuildDirective,
            ButtonDirective,
            CardDirective,
            CardsDirective,
            ChecklistDirective,
            CodeTabsDirective,
            DataTableDirective,
            DropdownDirective,
            ListTableDirective,
            RubricDirective,
            TabItemDirective,
            TabSetDirective,
        ]

        # Read the source code of factory.py to verify directives are in the list
        import bengal.directives.factory as factory_module

        source = inspect.getsource(factory_module)

        # Check each directive class is instantiated in directives_list
        for directive_cls in directive_classes:
            class_name = directive_cls.__name__
            # Should appear as ClassName() in the directives_list
            assert f"{class_name}()" in source, (
                f"{class_name} is imported but not added to directives_list in "
                f"create_documentation_directives()"
            )


class TestRealWorldDirectiveUsage:
    """Test directives with real-world examples."""

    @pytest.fixture
    def parser(self):
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_data_table_directive_with_options(self, parser):
        """Test data-table directive with various options."""
        # Bengal uses colon-fenced syntax (:::{directive}) to avoid conflicts with code blocks
        content = """
:::{data-table} data/nonexistent.csv
:search: false
:filter: true
:pagination: 100
:height: 500px
:::
"""
        result = parser.parse(content, {})

        # Should be processed as directive (even if file doesn't exist)
        assert ":::{data-table}" not in result
        # Will show error since file doesn't exist
        assert "Data Table Error" in result or "bengal-data-table" in result

    def test_mixed_directives_in_document(self, parser):
        """Test multiple different directives in one document."""
        # Bengal uses colon-fenced syntax (:::{directive}) to avoid conflicts with code blocks
        content = """
# Document with Multiple Directives

:::{note}
This is a note.
:::

:::{data-table} data/test.yaml
:search: true
:::

:::{button} https://example.com
Click Here
:::

:::{dropdown} More Info
Hidden content
:::
"""
        result = parser.parse(content, {})

        # None of the raw directive syntax should remain
        assert ":::{note}" not in result
        assert ":::{data-table}" not in result
        assert ":::{button}" not in result
        assert ":::{dropdown}" not in result

        # All should be processed
        assert "admonition" in result
        assert "bengal-data-table" in result or "Data Table Error" in result
        assert "button button-primary" in result
        assert "dropdown" in result
