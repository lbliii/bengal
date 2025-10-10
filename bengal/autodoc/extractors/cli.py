"""
CLI documentation extractor for autodoc system.

Extracts documentation from command-line applications built with Click, argparse, or Typer.
"""

import inspect
from pathlib import Path
from typing import Any, List, Optional

import click

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.utils import sanitize_text


class CLIExtractor(Extractor):
    """
    Extract CLI documentation from Click/argparse/typer applications.
    
    This extractor introspects CLI frameworks to build comprehensive documentation
    for commands, options, arguments, and their relationships.
    
    Currently supported frameworks:
    - Click (full support)
    - argparse (planned)
    - Typer (planned)
    
    Example:
        >>> from bengal.cli import main
        >>> extractor = CLIExtractor(framework='click')
        >>> elements = extractor.extract(main)
        >>> # Returns list of DocElements for all commands
    """
    
    def __init__(self, framework: str = 'click', include_hidden: bool = False):
        """
        Initialize CLI extractor.
        
        Args:
            framework: CLI framework to extract from ('click', 'argparse', 'typer')
            include_hidden: Include hidden commands (default: False)
        """
        self.framework = framework
        self.include_hidden = include_hidden
        
        if framework not in ('click', 'argparse', 'typer'):
            raise ValueError(f"Unsupported framework: {framework}. Use 'click', 'argparse', or 'typer'")
    
    def extract(self, source: Any) -> List[DocElement]:
        """
        Extract documentation from CLI application.
        
        Args:
            source: CLI application object
                - For Click: click.Group or click.Command
                - For argparse: ArgumentParser instance
                - For Typer: Typer app instance
                
        Returns:
            List of DocElements representing the CLI structure
            
        Raises:
            ValueError: If source type doesn't match framework
        """
        if self.framework == 'click':
            return self._extract_from_click(source)
        elif self.framework == 'argparse':
            return self._extract_from_argparse(source)
        elif self.framework == 'typer':
            return self._extract_from_typer(source)
        else:
            raise ValueError(f"Unknown framework: {self.framework}")
    
    def _extract_from_click(self, cli: click.Group) -> List[DocElement]:
        """
        Extract documentation from Click command group.
        
        Args:
            cli: Click Group or Command instance
            
        Returns:
            List containing the main CLI element and all subcommands as separate pages
        """
        elements = []
        
        # Main CLI/command group
        main_doc = self._extract_click_group(cli)
        elements.append(main_doc)
        
        # Add each command as a separate top-level element for individual pages
        # Recursively flatten nested command groups
        def flatten_commands(children: List[DocElement]):
            for child in children:
                elements.append(child)
                # If this is a nested command group, also flatten its children
                if child.element_type == 'command-group' and child.children:
                    flatten_commands(child.children)
        
        flatten_commands(main_doc.children)
        
        return elements
    
    def _extract_click_group(self, group: click.Group, parent_name: str = None) -> DocElement:
        """
        Extract Click command group documentation.
        
        Args:
            group: Click Group instance
            parent_name: Parent command name for nested groups
            
        Returns:
            DocElement representing the command group
        """
        name = group.name or 'cli'
        qualified_name = f"{parent_name}.{name}" if parent_name else name
        
        # Get callback source file if available
        source_file = None
        line_number = None
        if group.callback:
            try:
                source_file = Path(inspect.getfile(group.callback))
                line_number = inspect.getsourcelines(group.callback)[1]
            except (TypeError, OSError):
                pass
        
        # Build children (subcommands)
        children = []
        if isinstance(group, click.Group):
            for cmd_name, cmd in sorted(group.commands.items()):
                # Skip hidden commands unless requested
                if hasattr(cmd, 'hidden') and cmd.hidden and not self.include_hidden:
                    continue
                
                if isinstance(cmd, click.Group):
                    # Nested command group
                    child_doc = self._extract_click_group(cmd, qualified_name)
                else:
                    # Regular command
                    child_doc = self._extract_click_command(cmd, qualified_name)
                
                children.append(child_doc)
        
        # Extract examples from docstring
        examples = []
        if group.callback:
            docstring = inspect.getdoc(group.callback)
            if docstring:
                examples = self._extract_examples_from_docstring(docstring)
        
        # Clean up description
        description = sanitize_text(group.help)
        
        return DocElement(
            name=name,
            qualified_name=qualified_name,
            description=description,
            element_type='command-group',
            source_file=source_file,
            line_number=line_number,
            metadata={
                'callback': group.callback.__name__ if group.callback else None,
                'command_count': len(children),
            },
            children=children,
            examples=examples,
            see_also=[],
            deprecated=None
        )
    
    def _extract_click_command(self, cmd: click.Command, parent_name: str = None) -> DocElement:
        """
        Extract Click command documentation.
        
        Args:
            cmd: Click Command instance
            parent_name: Parent group name
            
        Returns:
            DocElement representing the command
        """
        name = cmd.name
        qualified_name = f"{parent_name}.{name}" if parent_name else name
        
        # Get callback source
        source_file = None
        line_number = None
        if cmd.callback:
            try:
                source_file = Path(inspect.getfile(cmd.callback))
                line_number = inspect.getsourcelines(cmd.callback)[1]
            except (TypeError, OSError):
                pass
        
        # Extract options and arguments
        options = []
        arguments = []
        
        for param in cmd.params:
            param_doc = self._extract_click_parameter(param, qualified_name)
            
            if isinstance(param, click.Argument):
                arguments.append(param_doc)
            else:
                options.append(param_doc)
        
        # Combine arguments and options as children
        children = arguments + options
        
        # Extract examples from callback docstring and strip them from description
        examples = []
        description_text = cmd.help or ""
        if cmd.callback:
            docstring = inspect.getdoc(cmd.callback)
            if docstring:
                examples = self._extract_examples_from_docstring(docstring)
                # Use the docstring without examples as the description
                description_text = self._strip_examples_from_description(docstring)
        
        # Check for deprecation
        deprecated = None
        if hasattr(cmd, 'deprecated') and cmd.deprecated:
            deprecated = "This command is deprecated"
        
        # Clean up description
        description = sanitize_text(description_text)
        
        return DocElement(
            name=name,
            qualified_name=qualified_name,
            description=description,
            element_type='command',
            source_file=source_file,
            line_number=line_number,
            metadata={
                'callback': cmd.callback.__name__ if cmd.callback else None,
                'option_count': len(options),
                'argument_count': len(arguments),
            },
            children=children,
            examples=examples,
            see_also=[],
            deprecated=deprecated
        )
    
    def _extract_click_parameter(self, param: click.Parameter, parent_name: str) -> DocElement:
        """
        Extract Click parameter (option or argument) documentation.
        
        Args:
            param: Click Parameter instance
            parent_name: Parent command qualified name
            
        Returns:
            DocElement representing the parameter
        """
        # Determine element type
        if isinstance(param, click.Argument):
            element_type = 'argument'
        elif isinstance(param, click.Option):
            element_type = 'option'
        else:
            element_type = 'parameter'
        
        # Get parameter names/flags
        param_decls = getattr(param, 'opts', [param.name])
        
        # Get type information
        type_name = 'any'
        if hasattr(param.type, 'name'):
            type_name = param.type.name
        else:
            type_name = param.type.__class__.__name__.lower()
        
        # Build description (Arguments don't have help attribute)
        description = sanitize_text(getattr(param, 'help', None))
        
        # Build metadata
        metadata = {
            'param_type': param.__class__.__name__,
            'type': type_name,
            'required': param.required,
            'default': str(param.default) if param.default is not None else None,
            'multiple': getattr(param, 'multiple', False),
            'is_flag': getattr(param, 'is_flag', False),
            'count': getattr(param, 'count', False),
            'opts': param_decls,
        }
        
        # Add envvar if present
        if hasattr(param, 'envvar') and param.envvar:
            metadata['envvar'] = param.envvar
        
        return DocElement(
            name=param.name,
            qualified_name=f"{parent_name}.{param.name}",
            description=description,
            element_type=element_type,
            source_file=None,
            line_number=None,
            metadata=metadata,
            children=[],
            examples=[],
            see_also=[],
            deprecated=None
        )
    
    def _strip_examples_from_description(self, docstring: str) -> str:
        """
        Remove example blocks from docstring description.
        
        Args:
            docstring: Full docstring
            
        Returns:
            Description without Examples section
        """
        lines = docstring.split('\n')
        description_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Stop at Examples section
            if stripped.lower() in ('example:', 'examples:', 'usage:'):
                break
            
            description_lines.append(line)
        
        return '\n'.join(description_lines).strip()
    
    def _extract_examples_from_docstring(self, docstring: str) -> List[str]:
        """
        Extract example blocks from docstring.
        
        Args:
            docstring: Function or command docstring
            
        Returns:
            List of example code blocks
        """
        examples = []
        lines = docstring.split('\n')
        
        in_example = False
        current_example = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect example section start
            if stripped.lower() in ('example:', 'examples:', 'usage:'):
                in_example = True
                continue
            
            # Detect end of example section (next section header)
            if in_example and stripped and stripped.endswith(':') and not line.startswith(' '):
                if current_example:
                    examples.append('\n'.join(current_example))
                    current_example = []
                in_example = False
                continue
            
            # Collect example lines
            if in_example and line:
                current_example.append(line)
        
        # Add final example if any
        if current_example:
            examples.append('\n'.join(current_example))
        
        return examples
    
    def _extract_from_argparse(self, parser: Any) -> List[DocElement]:
        """
        Extract documentation from argparse ArgumentParser.
        
        Args:
            parser: ArgumentParser instance
            
        Returns:
            List of DocElements
            
        Note:
            This is a placeholder for future implementation
        """
        raise NotImplementedError("argparse support is planned but not yet implemented")
    
    def _extract_from_typer(self, app: Any) -> List[DocElement]:
        """
        Extract documentation from Typer app.
        
        Args:
            app: Typer app instance
            
        Returns:
            List of DocElements
            
        Note:
            This is a placeholder for future implementation
        """
        raise NotImplementedError("Typer support is planned but not yet implemented")
    
    def get_template_dir(self) -> str:
        """
        Get template directory name for CLI documentation.
        
        Returns:
            'cli'
        """
        return "cli"
    
    def get_output_path(self, element: DocElement) -> Path:
        """
        Determine output path for CLI element.
        
        Args:
            element: CLI DocElement
            
        Returns:
            Relative path for the generated markdown file
            
        Example:
            command-group (main) → _index.md (section index)
            command-group (nested) → commands/{name}.md
            command → commands/{name}.md
        """
        if element.element_type == 'command-group':
            # Main CLI group gets _index.md (section index)
            # Nested command groups (like 'new') get their own page in commands/
            if '.' not in element.qualified_name:
                return Path("_index.md")
            else:
                return Path(f"commands/{element.name}.md")
        elif element.element_type == 'command':
            # bengal.build → commands/build.md
            # Just use the command name, not the full qualified name
            return Path(f"commands/{element.name}.md")
        else:
            # Shouldn't happen, but fallback
            return Path(f"{element.name}.md")

