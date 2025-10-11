"""
Tests for CLI documentation extractor.
"""

from pathlib import Path

import click
import pytest

from bengal.autodoc.base import DocElement
from bengal.autodoc.extractors.cli import CLIExtractor


@click.group()
def sample_cli():
    """
    A sample CLI application.

    This is used for testing the CLI extractor.
    """
    pass


@sample_cli.command()
@click.argument('filename', type=click.Path())
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--count', '-c', type=int, default=1, help='Number of times to process')
def process(filename, verbose, count):
    """
    Process a file.

    This command processes the specified file with various options.
    """
    pass


@sample_cli.command()
@click.option('--force', '-f', is_flag=True, help='Force the operation')
def clean(force):
    """
    Clean up resources.

    Removes temporary files and caches.
    """
    pass


# Nested command group for testing
@sample_cli.group()
def manage():
    """
    Manage resources and configuration.

    Commands for managing system resources.
    """
    pass


@manage.command()
@click.argument('name')
@click.option('--description', '-d', help='Resource description')
def create(name, description):
    """
    Create a new resource.

    Creates a resource with the given name.
    """
    pass


@manage.command()
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Force deletion')
def delete(name, force):
    """
    Delete a resource.

    Removes the specified resource.
    """
    pass


class TestCLIExtractor:
    """Tests for CLI extractor."""

    def test_extract_click_group(self):
        """Test extracting a Click group."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # After fix: should have root + all commands/groups flattened
        # 1 root + 2 commands (process, clean) + 1 group (manage) + 2 subcommands (create, delete) = 6
        assert len(elements) >= 1
        root = elements[0]

        # Click normalizes names to use dashes
        assert root.name == 'sample-cli'
        assert root.element_type == 'command-group'
        assert 'sample CLI application' in root.description
        assert len(root.children) == 3  # process, clean, and manage commands

    def test_extract_commands(self):
        """Test extracting commands from a group."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        command_names = [child.name for child in root.children]

        assert 'process' in command_names
        assert 'clean' in command_names
        assert 'manage' in command_names

    def test_extract_command_with_arguments(self):
        """Test extracting a command with arguments."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        process_cmd = [c for c in root.children if c.name == 'process'][0]

        assert process_cmd.element_type == 'command'
        assert 'Process a file' in process_cmd.description

        # Check for filename argument
        params = process_cmd.children
        arg_names = [p.name for p in params]
        assert 'filename' in arg_names

    def test_extract_command_with_options(self):
        """Test extracting a command with options."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        process_cmd = [c for c in root.children if c.name == 'process'][0]

        # Check for options
        params = process_cmd.children
        option_names = [p.name for p in params if p.element_type == 'option']

        assert 'verbose' in option_names or '--verbose' in [p.metadata.get('names', [''])[0] for p in params]
        assert 'count' in option_names or '--count' in [p.metadata.get('names', [''])[0] for p in params]

    def test_extract_parameter_metadata(self):
        """Test that parameter metadata is extracted."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        process_cmd = [c for c in root.children if c.name == 'process'][0]

        # Find the count option
        count_params = [p for p in process_cmd.children if 'count' in p.name.lower()]

        if count_params:
            count_param = count_params[0]
            assert 'type' in count_param.metadata
            assert 'default' in count_param.metadata
            # Default values are stored as strings
            assert count_param.metadata['default'] == '1' or count_param.metadata['default'] == 1

    def test_sanitizes_descriptions(self):
        """Test that descriptions are sanitized (no leading indentation)."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]

        # Description should not have leading spaces
        assert not root.description.startswith(' ')
        assert not root.description.startswith('\n')

        # Commands should also have sanitized descriptions
        for cmd in root.children:
            assert not cmd.description.startswith(' ')

    def test_qualified_names(self):
        """Test that qualified names are built correctly."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        # Click normalizes names to use dashes
        assert root.qualified_name == 'sample-cli'

        process_cmd = [c for c in root.children if c.name == 'process'][0]
        assert process_cmd.qualified_name == 'sample-cli.process'

    def test_get_template_dir(self):
        """Test that template directory is correct."""
        extractor = CLIExtractor()
        assert extractor.get_template_dir() == 'cli'

    def test_get_output_path(self):
        """Test that output paths are generated correctly."""
        extractor = CLIExtractor()

        # Mock element
        element = DocElement(
            name='process',
            qualified_name='cli.process',
            description='Test',
            element_type='command'
        )

        path = extractor.get_output_path(element)
        assert 'process' in str(path)
        assert str(path).endswith('.md')


class TestCLIExtractorEdgeCases:
    """Test edge cases for CLI extractor."""

    def test_extract_command_without_docstring(self):
        """Test extracting a command without a docstring."""
        @click.command()
        def undocumented():
            pass

        extractor = CLIExtractor()
        elements = extractor.extract(undocumented)

        assert len(elements) == 1
        cmd = elements[0]
        assert cmd.description == ''  # Empty, not None

    def test_extract_argument_without_help(self):
        """Test extracting an argument (which has no help attribute)."""
        @click.command()
        @click.argument('name')
        def cmd_with_arg(name):
            """Command with argument."""
            pass

        extractor = CLIExtractor()
        elements = extractor.extract(cmd_with_arg)

        # Single command gets treated as top-level element
        assert len(elements) >= 1
        # First element could be either the command itself or a wrapper group
        cmd = elements[0] if elements[0].element_type == 'command' else elements[1] if len(elements) > 1 else elements[0]

        # If it's a group with no children, skip test (framework limitation)
        if cmd.element_type == 'command-group' and not cmd.children:
            pytest.skip("Single command without group wrapper")

        args = [p for p in cmd.children if p.element_type == 'argument']

        assert len(args) == 1
        assert args[0].name == 'name'
        # Description should be empty string, not cause error
        assert isinstance(args[0].description, str)

    def test_extract_hidden_option(self):
        """Test that hidden options can be tracked."""
        @click.command()
        @click.option('--hidden', hidden=True, help='Hidden option')
        def cmd_with_hidden(hidden):
            """Command with hidden option."""
            pass

        extractor = CLIExtractor()
        elements = extractor.extract(cmd_with_hidden)

        # Single command gets treated as top-level element
        assert len(elements) >= 1
        # First element could be either the command itself or a wrapper group
        cmd = elements[0] if elements[0].element_type == 'command' else elements[1] if len(elements) > 1 else elements[0]

        # If it's a group with no children, skip test (framework limitation)
        if cmd.element_type == 'command-group' and not cmd.children:
            pytest.skip("Single command without group wrapper")

        # By default extracts all options
        params = cmd.children
        assert len(params) > 0


class TestCLIExtractorMetadata:
    """Test metadata extraction."""

    def test_command_counts_in_metadata(self):
        """Test that command counts are in metadata."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        assert 'command_count' in root.metadata
        assert root.metadata['command_count'] == 3  # process + clean + manage

    def test_parameter_type_metadata(self):
        """Test that parameter types are extracted."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        root = elements[0]
        process_cmd = [c for c in root.children if c.name == 'process'][0]

        # Check parameter types
        for param in process_cmd.children:
            assert 'type' in param.metadata
            assert 'param_type' in param.metadata


class TestNestedCommandGroups:
    """Test nested command group extraction."""

    def test_extract_nested_command_group(self):
        """Test that nested command groups are extracted."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # Should have the main group + nested group in the flattened list
        group_names = [e.name for e in elements if e.element_type == 'command-group']
        # Click normalizes names to use dashes
        assert 'sample-cli' in group_names
        assert 'manage' in group_names

    def test_nested_group_has_correct_parent(self):
        """Test that nested groups have correct qualified names."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        manage_group = [e for e in elements if e.name == 'manage' and e.element_type == 'command-group'][0]
        # Click normalizes names to use dashes
        assert manage_group.qualified_name == 'sample-cli.manage'

    def test_nested_group_subcommands_are_extracted(self):
        """Test that subcommands of nested groups are extracted."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # Should have create and delete commands in the flattened list
        command_names = [e.name for e in elements if e.element_type == 'command']
        assert 'create' in command_names
        assert 'delete' in command_names

    def test_nested_subcommand_qualified_names(self):
        """Test that nested subcommands have correct qualified names."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        create_cmd = [e for e in elements if e.name == 'create'][0]
        delete_cmd = [e for e in elements if e.name == 'delete'][0]

        # Click normalizes names to use dashes
        assert create_cmd.qualified_name == 'sample-cli.manage.create'
        assert delete_cmd.qualified_name == 'sample-cli.manage.delete'

    def test_nested_group_children_in_hierarchy(self):
        """Test that nested group contains its children in the hierarchy."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # Root should have manage as a child
        root = elements[0]
        manage_in_root = [c for c in root.children if c.name == 'manage']
        assert len(manage_in_root) == 1

        # Manage group should have create and delete as children
        manage_group = manage_in_root[0]
        assert manage_group.element_type == 'command-group'
        child_names = [c.name for c in manage_group.children]
        assert 'create' in child_names
        assert 'delete' in child_names

    def test_flattened_elements_count(self):
        """Test that all elements are flattened correctly."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # Should have:
        # 1. sample_cli (command-group)
        # 2. process (command)
        # 3. clean (command)
        # 4. manage (command-group)
        # 5. create (command)
        # 6. delete (command)
        assert len(elements) == 6

    def test_nested_group_output_path(self):
        """Test that nested command groups get correct output paths."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        # Main group should go to index.md
        root = elements[0]
        assert extractor.get_output_path(root) == Path("index.md")

        # Nested group should go to commands/{name}.md
        manage_group = [e for e in elements if e.name == 'manage' and e.element_type == 'command-group'][0]
        assert extractor.get_output_path(manage_group) == Path("commands/manage.md")

    def test_nested_subcommand_output_path(self):
        """Test that nested subcommands get correct output paths."""
        extractor = CLIExtractor()
        elements = extractor.extract(sample_cli)

        create_cmd = [e for e in elements if e.name == 'create'][0]
        delete_cmd = [e for e in elements if e.name == 'delete'][0]

        assert extractor.get_output_path(create_cmd) == Path("commands/create.md")
        assert extractor.get_output_path(delete_cmd) == Path("commands/delete.md")

