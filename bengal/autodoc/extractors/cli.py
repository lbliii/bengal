"""
CLI documentation extractor for autodoc system.

Extracts documentation from command-line applications built with Click, argparse, or Typer.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, override

import click

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.models import CLICommandMetadata, CLIGroupMetadata, CLIOptionMetadata
from bengal.autodoc.utils import sanitize_text
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def _is_sentinel_value(value: Any) -> bool:
    """
    Check if a value is a Click sentinel (like UNSET).

    Click uses sentinel objects to distinguish between "not provided" and None.
    These should not appear in user-facing documentation.

    Args:
        value: Value to check

    Returns:
        True if value is a sentinel that should be filtered
    """
    if value is None:
        return False

    # Convert to string and check for sentinel markers
    value_str = str(value)

    # Common sentinel patterns in Click
    if any(marker in value_str for marker in ["Sentinel", "UNSET", "_missing"]):
        return True

    # Check if it's Click's actual _missing sentinel
    return (
        hasattr(click, "core") and hasattr(click.core, "_missing") and value is click.core._missing
    )


def _format_default_value(value: Any) -> str | None:
    """
    Format a default value for display, filtering sentinel values.

    Args:
        value: The default value to format

    Returns:
        Formatted string or None if value should not be displayed
    """
    if value is None:
        return None

    if _is_sentinel_value(value):
        return None

    return str(value)


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

    def __init__(self, framework: str = "click", include_hidden: bool = False):
        """
        Initialize CLI extractor.

        Args:
            framework: CLI framework to extract from ('click', 'argparse', 'typer')
            include_hidden: Include hidden commands (default: False)
        """
        self.framework = framework
        self.include_hidden = include_hidden

        if framework not in ("click", "argparse", "typer"):
            from bengal.errors import BengalConfigError

            raise BengalConfigError(
                f"Unsupported framework: {framework}. Use 'click', 'argparse', or 'typer'",
                suggestion="Set framework to 'click', 'argparse', or 'typer'",
            )

    @override
    def extract(self, source: Any) -> list[DocElement]:
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
        if self.framework == "click":
            return self._extract_from_click(source)
        elif self.framework == "argparse":
            return self._extract_from_argparse(source)
        elif self.framework == "typer":
            return self._extract_from_typer(source)
        else:
            from bengal.errors import BengalConfigError

            raise BengalConfigError(
                f"Unknown framework: {self.framework}",
                suggestion="Set framework to 'click', 'argparse', or 'typer'",
            )

    def _extract_from_click(self, cli: click.Group) -> list[DocElement]:
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
        def flatten_commands(children: list[DocElement]) -> None:
            for child in children:
                # Always add nested command groups (they get _index.md)
                # Always add regular commands (they get individual pages)
                # But don't double-add: only add each element once
                if child.element_type == "command-group":
                    # Add the group itself (generates _index.md)
                    elements.append(child)
                    # Then flatten its children (but don't add them directly to avoid duplicates)
                    if child.children:
                        flatten_commands(child.children)
                elif child.element_type == "command":
                    # Regular commands get individual pages
                    elements.append(child)

        flatten_commands(main_doc.children)

        return elements

    def _extract_click_group(
        self, group: click.Group, parent_name: str | None = None
    ) -> DocElement:
        """
        Extract Click command group documentation.

        Args:
            group: Click Group instance
            parent_name: Parent command name for nested groups

        Returns:
            DocElement representing the command group
        """
        name = group.name or "cli"
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
        seen_command_ids: set[int] = set()
        if isinstance(group, click.Group):
            for _cmd_name, cmd in sorted(group.commands.items()):
                # Skip hidden commands unless requested
                if hasattr(cmd, "hidden") and cmd.hidden and not self.include_hidden:
                    continue

                cmd_identity = id(cmd)
                if cmd_identity in seen_command_ids:
                    continue
                seen_command_ids.add(cmd_identity)

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

        # Build typed metadata
        typed_meta = CLIGroupMetadata(
            callback=group.callback.__name__ if group.callback else None,
            command_count=len(children),
        )

        return DocElement(
            name=name,
            qualified_name=qualified_name,
            description=description,
            element_type="command-group",
            source_file=source_file,
            line_number=line_number,
            metadata={
                "callback": group.callback.__name__ if group.callback else None,
                "command_count": len(children),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=examples,
            see_also=[],
            deprecated=None,
        )

    def _extract_click_command(
        self, cmd: click.Command, parent_name: str | None = None
    ) -> DocElement:
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
            param_doc = self._extract_click_parameter(param, qualified_name or "")

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
        if hasattr(cmd, "deprecated") and cmd.deprecated:
            deprecated = "This command is deprecated"

        # Clean up description
        description = sanitize_text(description_text)

        # Check if hidden
        is_hidden = hasattr(cmd, "hidden") and cmd.hidden

        # Build typed metadata
        typed_meta = CLICommandMetadata(
            callback=cmd.callback.__name__ if cmd.callback else None,
            option_count=len(options),
            argument_count=len(arguments),
            is_group=False,
            is_hidden=is_hidden,
        )

        return DocElement(
            name=name or "",
            qualified_name=qualified_name or "",
            description=description,
            element_type="command",
            source_file=source_file,
            line_number=line_number,
            metadata={
                "callback": cmd.callback.__name__ if cmd.callback else None,
                "option_count": len(options),
                "argument_count": len(arguments),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=examples,
            see_also=[],
            deprecated=deprecated,
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
            element_type = "argument"
        elif isinstance(param, click.Option):
            element_type = "option"
        else:
            element_type = "parameter"

        # Get parameter names/flags
        param_decls = getattr(param, "opts", [param.name])

        # Get type information
        type_name = "any"
        if hasattr(param.type, "name"):
            type_name = param.type.name
        else:
            type_name = param.type.__class__.__name__.lower()

        # Build description (Arguments don't have help attribute)
        description = sanitize_text(getattr(param, "help", None))

        # Build metadata
        metadata = {
            "param_type": param.__class__.__name__,
            "type": type_name,
            "required": param.required,
            "default": _format_default_value(param.default),
            "multiple": getattr(param, "multiple", False),
            "is_flag": getattr(param, "is_flag", False),
            "count": getattr(param, "count", False),
            "opts": param_decls,
        }

        # Add envvar if present
        envvar = None
        if hasattr(param, "envvar") and param.envvar:
            metadata["envvar"] = param.envvar
            envvar = param.envvar

        # Build typed metadata
        typed_meta = CLIOptionMetadata(
            name=param.name or "",
            param_type="argument" if isinstance(param, click.Argument) else "option",
            type_name=type_name.upper() if type_name else "STRING",
            required=param.required,
            default=_format_default_value(param.default),
            multiple=getattr(param, "multiple", False),
            is_flag=getattr(param, "is_flag", False),
            count=getattr(param, "count", False),
            opts=tuple(param_decls),
            envvar=envvar,
            help_text=getattr(param, "help", "") or "",
        )

        return DocElement(
            name=param.name or "",
            qualified_name=f"{parent_name}.{param.name or ''}",
            description=description,
            element_type=element_type,
            source_file=None,
            line_number=None,
            metadata=metadata,
            typed_metadata=typed_meta,
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )

    def _strip_examples_from_description(self, docstring: str) -> str:
        """
        Remove example blocks from docstring description.

        Args:
            docstring: Full docstring

        Returns:
            Description without Examples section
        """
        lines = docstring.split("\n")
        description_lines = []

        for line in lines:
            stripped = line.strip()

            # Stop at Examples section
            if stripped.lower() in ("example:", "examples:", "usage:"):
                break

            description_lines.append(line)

        return "\n".join(description_lines).strip()

    def _extract_examples_from_docstring(self, docstring: str) -> list[str]:
        """
        Extract example blocks from docstring.

        Args:
            docstring: Function or command docstring

        Returns:
            List of example code blocks
        """
        examples = []
        lines = docstring.split("\n")

        in_example = False
        current_example: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Detect example section start
            if stripped.lower() in ("example:", "examples:", "usage:"):
                in_example = True
                continue

            # Detect end of example section (next section header)
            if in_example and stripped and stripped.endswith(":") and not line.startswith(" "):
                if current_example:
                    examples.append("\n".join(current_example))
                    current_example = []
                in_example = False
                continue

            # Collect example lines
            if in_example and line:
                current_example.append(line)

        # Add final example if any
        if current_example:
            examples.append("\n".join(current_example))

        return examples

    def _extract_from_argparse(self, parser: Any) -> list[DocElement]:
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

    def _extract_from_typer(self, app: Any) -> list[DocElement]:
        """
        Extract documentation from Typer app.

        Typer is built on top of Click, so we can leverage the existing Click
        extraction logic. Typer apps expose their underlying Click structure
        through various methods.

        Args:
            app: Typer app instance

        Returns:
            List of DocElements

        Raises:
            ValueError: If unable to extract Click app from Typer
        """
        import typer

        # Typer apps have multiple ways to expose their Click structure
        click_app = None

        # Method 1: Try the registered_commands attribute (Typer 0.9+)
        if hasattr(app, "registered_commands") and hasattr(app, "registered_groups"):
            # Build a Click group from Typer's commands
            # Typer stores commands but needs to be converted to Click format
            # The easiest way is to get the Click app via typer.main
            try:
                # Get the Click group by invoking Typer's internal conversion
                import click

                # Create a Click group that wraps the Typer app
                @click.group()
                def typer_wrapper() -> None:
                    pass

                # Typer apps store their info, we can extract via the callback
                if hasattr(app, "info"):
                    typer_wrapper.help = app.info.help if app.info.help else ""

                # Add all registered commands
                for command in app.registered_commands:
                    if hasattr(command, "callback"):
                        # Convert Typer command to Click command
                        click_cmd = typer.main.get_command(command)
                        if click_cmd:
                            typer_wrapper.add_command(click_cmd, name=command.name)

                # Add all registered groups
                for group in app.registered_groups:
                    if hasattr(group, "typer_instance"):
                        # Recursively convert nested Typer groups
                        nested_click = self._typer_to_click_group(group.typer_instance)
                        if nested_click:
                            typer_wrapper.add_command(nested_click, name=group.name)

                click_app = typer_wrapper

            except Exception as e:
                logger.debug(
                    "cli_extractor_typer_wrapper_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_method_2",
                )
                pass

        # Method 2: Try using Typer's own conversion (most reliable)
        if click_app is None:
            try:
                # Typer can convert itself to Click via typer.main.get_group/get_command
                if hasattr(typer.main, "get_group"):
                    click_app = typer.main.get_group(app)
                elif hasattr(typer.main, "get_command"):
                    click_app = typer.main.get_command(app)
            except Exception as e:
                logger.debug(
                    "cli_extractor_typer_main_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_method_3",
                )
                pass

        # Method 3: Direct attribute access (older Typer versions)
        if click_app is None and hasattr(app, "_click_group"):
            click_app = app._click_group

        # If we successfully got a Click app, extract from it
        if click_app is not None:
            return self._extract_from_click(click_app)

        # Fallback: raise error if we couldn't extract
        from bengal.errors import BengalDiscoveryError

        raise BengalDiscoveryError(
            "Unable to extract Click app from Typer instance. "
            "Make sure you're passing a Typer() app object.",
            suggestion="Pass a Typer() app instance, not a command function",
        )

    def _typer_to_click_group(self, typer_app: Any) -> Any:
        """
        Helper to convert a Typer app to a Click group recursively.

        Args:
            typer_app: Typer app instance

        Returns:
            Click group or None
        """
        try:
            import typer

            if hasattr(typer.main, "get_group"):
                return typer.main.get_group(typer_app)
            elif hasattr(typer.main, "get_command"):
                return typer.main.get_command(typer_app)
        except Exception as e:
            logger.debug(
                "cli_extractor_typer_to_click_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_none",
            )
            pass

        return None

    def get_template_dir(self) -> str:
        """
        Get the template directory name for this extractor.

        Returns:
            Template directory name (e.g., 'cli', 'python', 'openapi')
        """
        return "cli"

    @override
    def get_output_path(self, element: DocElement) -> Path:
        """
        Determine output path for CLI element.

        Args:
            element: CLI DocElement

        Returns:
            Relative path for the generated markdown file

        Example:
            command-group (main) → _index.md (section index)
            command-group (nested) → {name}/_index.md
            command → {name}.md
        """
        if element.element_type == "command-group":
            # Main CLI group gets _index.md (section index)
            # Nested command groups should be namespaced by their qualified path
            # Example: bengal.theme → theme/_index.md
            if "." not in element.qualified_name:
                return Path("_index.md")
            # For nested groups, place an index under <qualified path>/
            parts = element.qualified_name.split(".")[1:]  # drop root cli name
            return Path("/".join(parts)) / "_index.md"
        elif element.element_type == "command":
            # Use the full qualified name (minus root) to preserve hierarchy
            # Examples:
            #   bengal.build            → build.md
            #   bengal.theme.new        → theme/new.md
            #   bengal.theme.swizzle    → theme/swizzle.md
            qualified = element.qualified_name
            parts = qualified.split(".")
            # drop root cli name if present
            if len(parts) > 1:
                parts = parts[1:]
            return Path("/".join(parts)).with_suffix(".md")
        else:
            # Shouldn't happen, but fallback
            return Path(f"{element.name}.md")
