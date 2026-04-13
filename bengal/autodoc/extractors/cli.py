"""
CLI documentation extractor for autodoc system.

Extracts documentation from command-line applications built with
Click, argparse, Typer, or milo.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, override

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.models import CLICommandMetadata, CLIGroupMetadata, CLIOptionMetadata
from bengal.autodoc.utils import sanitize_text
from bengal.utils.observability.logger import get_logger

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
    import click

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
    Extract CLI documentation from Click/argparse/typer/milo applications.

    This extractor introspects CLI frameworks to build comprehensive documentation
    for commands, options, arguments, and their relationships.

    Supported frameworks:
    - Click (full support)
    - milo (full support)
    - argparse (planned)
    - Typer (planned)

    Example:
            >>> from bengal.cli import cli
            >>> extractor = CLIExtractor(framework='milo')
            >>> elements = extractor.extract(cli)
            >>> # Returns list of DocElements for all commands

    """

    def __init__(self, framework: str = "click", include_hidden: bool = False):
        """
        Initialize CLI extractor.

        Args:
            framework: CLI framework to extract from ('click', 'argparse', 'typer', 'milo')
            include_hidden: Include hidden commands (default: False)
        """
        self.framework = framework
        self.include_hidden = include_hidden

        if framework not in ("click", "argparse", "typer", "milo"):
            from bengal.errors import BengalConfigError, ErrorCode

            raise BengalConfigError(
                f"Unsupported framework: {framework}. Use 'click', 'argparse', 'typer', or 'milo'",
                suggestion="Set framework to 'click', 'argparse', 'typer', or 'milo'",
                code=ErrorCode.C003,
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
                - For milo: milo.commands.CLI instance

        Returns:
            List of DocElements representing the CLI structure

        Raises:
            ValueError: If source type doesn't match framework
        """
        if self.framework == "click":
            return self._extract_from_click(source)
        if self.framework == "argparse":
            return self._extract_from_argparse(source)
        if self.framework == "typer":
            return self._extract_from_typer(source)
        if self.framework == "milo":
            return self._extract_from_milo(source)
        from bengal.errors import BengalConfigError, ErrorCode

        raise BengalConfigError(
            f"Unknown framework: {self.framework}",
            suggestion="Set framework to 'click', 'argparse', 'typer', or 'milo'",
            code=ErrorCode.C003,
        )

    def _extract_from_click(self, cli: Any) -> list[DocElement]:
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

    def _extract_click_group(self, group: Any, parent_name: str | None = None) -> DocElement:
        """
        Extract Click command group documentation.

        Contract: Must use list_commands(ctx) and get_command(ctx, name),
        not group.commands.items(). Lazy-loaded groups (e.g. Bengal CLI)
        have empty group.commands and only expose subcommands via those APIs.

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
            except TypeError, OSError:
                pass

        # Build children (subcommands)
        # Use list_commands + get_command to support lazy-loaded groups (e.g. Bengal CLI).
        # group.commands is empty for lazy groups that defer loading until invocation.
        import click

        children = []
        seen_command_ids: set[int] = set()
        if isinstance(group, click.Group):
            # Context required: list_commands/get_command need it for lazy-loaded groups.
            ctx = click.Context(group)
            for cmd_name in sorted(group.list_commands(ctx)):
                cmd = group.get_command(ctx, cmd_name)
                if cmd is None:
                    continue
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
        callback_name = getattr(group.callback, "__name__", None) if group.callback else None
        typed_meta = CLIGroupMetadata(
            callback=callback_name,
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
                "callback": callback_name,
                "command_count": len(children),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=examples,
            see_also=[],
            deprecated=None,
        )

    def _extract_click_command(self, cmd: Any, parent_name: str | None = None) -> DocElement:
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
            except TypeError, OSError:
                pass

        # Extract options and arguments
        import click

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
        cmd_callback_name = getattr(cmd.callback, "__name__", None) if cmd.callback else None
        typed_meta = CLICommandMetadata(
            callback=cmd_callback_name,
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
                "callback": cmd_callback_name,
                "option_count": len(options),
                "argument_count": len(arguments),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=examples,
            see_also=[],
            deprecated=deprecated,
        )

    def _extract_click_parameter(self, param: Any, parent_name: str) -> DocElement:
        """
        Extract Click parameter (option or argument) documentation.

        Args:
            param: Click Parameter instance
            parent_name: Parent command qualified name

        Returns:
            DocElement representing the parameter
        """
        # Determine element type
        import click

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

        # Add envvar if present (can be str or Sequence[str])
        envvar: str | None = None
        if hasattr(param, "envvar") and param.envvar:
            metadata["envvar"] = param.envvar
            # Convert Sequence[str] to comma-separated string for typed metadata
            raw_envvar = param.envvar
            if isinstance(raw_envvar, str):
                envvar = raw_envvar
            elif hasattr(raw_envvar, "__iter__"):
                envvar = ",".join(raw_envvar)

        # Build typed metadata
        typed_meta = CLIOptionMetadata(
            name=param.name or "",
            param_type="argument" if element_type == "argument" else "option",
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

    # ------------------------------------------------------------------
    # Milo extraction
    # ------------------------------------------------------------------

    def _extract_from_milo(self, cli: Any) -> list[DocElement]:
        """
        Extract documentation from a milo CLI instance.

        Args:
            cli: milo.commands.CLI instance

        Returns:
            Flat list of DocElements (root group + all commands/groups)
        """
        elements: list[DocElement] = []

        root = self._extract_milo_group_root(cli)
        elements.append(root)

        # Flatten children into top-level list for individual pages
        def flatten(children: list[DocElement]) -> None:
            for child in children:
                elements.append(child)
                if child.element_type == "command-group" and child.children:
                    flatten(child.children)

        flatten(root.children)
        return elements

    def _extract_milo_group_root(self, cli: Any) -> DocElement:
        """
        Extract root CLI object as a command-group DocElement.

        Args:
            cli: milo.commands.CLI instance

        Returns:
            Root DocElement with children for all commands and groups
        """
        name = cli.name or "cli"

        children: list[DocElement] = []

        # Extract top-level commands
        for cmd_name in sorted(cli._commands):
            cmd_def = cli._commands[cmd_name]
            if getattr(cmd_def, "hidden", False) and not self.include_hidden:
                continue
            children.append(self._extract_milo_command(cmd_def, name))

        # Extract groups (recursive)
        for group_name in sorted(cli._groups):
            group = cli._groups[group_name]
            if getattr(group, "hidden", False) and not self.include_hidden:
                continue
            children.append(self._extract_milo_group(group, name))

        typed_meta = CLIGroupMetadata(
            callback=None,
            command_count=len(children),
        )

        return DocElement(
            name=name,
            qualified_name=name,
            description=sanitize_text(cli.description),
            element_type="command-group",
            source_file=None,
            line_number=None,
            metadata={
                "callback": None,
                "command_count": len(children),
                "version": getattr(cli, "version", ""),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=[],
            see_also=[],
            deprecated=None,
        )

    def _extract_milo_group(self, group: Any, parent_name: str) -> DocElement:
        """
        Extract a milo Group as a command-group DocElement (recursive).

        Args:
            group: milo.groups.Group instance
            parent_name: Parent qualified name

        Returns:
            DocElement for the group with its children
        """
        name = group.name
        qualified_name = f"{parent_name}.{name}"

        children: list[DocElement] = []

        for cmd_name in sorted(group._commands):
            cmd_def = group._commands[cmd_name]
            if getattr(cmd_def, "hidden", False) and not self.include_hidden:
                continue
            children.append(self._extract_milo_command(cmd_def, qualified_name))

        for sub_name in sorted(group._groups):
            sub = group._groups[sub_name]
            if getattr(sub, "hidden", False) and not self.include_hidden:
                continue
            children.append(self._extract_milo_group(sub, qualified_name))

        typed_meta = CLIGroupMetadata(
            callback=None,
            command_count=len(children),
        )

        return DocElement(
            name=name,
            qualified_name=qualified_name,
            description=sanitize_text(group.description),
            element_type="command-group",
            source_file=None,
            line_number=None,
            metadata={
                "callback": None,
                "command_count": len(children),
            },
            typed_metadata=typed_meta,
            children=children,
            examples=[],
            see_also=[],
            deprecated=None,
        )

    def _extract_milo_command(self, cmd_def: Any, parent_name: str) -> DocElement:
        """
        Extract a milo CommandDef or LazyCommandDef as a command DocElement.

        For LazyCommandDef, tries pre-computed _schema first to avoid
        importing the handler module. Falls back to resolve(), and if
        that fails, creates the element with description only.

        Args:
            cmd_def: CommandDef or LazyCommandDef instance
            parent_name: Parent qualified name

        Returns:
            DocElement for the command
        """
        name = cmd_def.name
        qualified_name = f"{parent_name}.{name}"
        description = sanitize_text(cmd_def.description)

        # Get schema — may require resolving lazy commands
        schema: dict[str, Any] = {}
        source_file = None
        line_number = None

        # Check for LazyCommandDef by attribute (avoid importing milo types)
        is_lazy = hasattr(cmd_def, "import_path")

        if is_lazy:
            # Try pre-computed schema first (no import needed)
            if cmd_def._schema is not None:
                schema = cmd_def._schema
            else:
                try:
                    resolved = cmd_def.resolve()
                    schema = resolved.schema
                    source_file, line_number = self._get_handler_source(resolved.handler)
                except Exception as e:
                    logger.debug(
                        "cli_extractor_lazy_resolve_failed",
                        command=name,
                        import_path=cmd_def.import_path,
                        error=str(e),
                    )
        else:
            # Regular CommandDef — schema and handler always available
            schema = cmd_def.schema
            source_file, line_number = self._get_handler_source(cmd_def.handler)

        # Extract parameters from JSON Schema properties
        options: list[DocElement] = []
        properties = schema.get("properties", {})
        required_params = set(schema.get("required", []))

        for prop_name, prop_schema in properties.items():
            options.append(
                self._extract_milo_parameter(
                    prop_name, prop_schema, prop_name in required_params, qualified_name
                )
            )

        # Extract examples from command def
        examples: list[str] = []
        for ex in getattr(cmd_def, "examples", ()):
            if isinstance(ex, dict):
                # milo examples are dicts with 'command' and optional 'description'
                cmd_str = ex.get("command", "")
                desc = ex.get("description", "")
                if desc and cmd_str:
                    examples.append(f"# {desc}\n{cmd_str}")
                elif cmd_str:
                    examples.append(cmd_str)
            elif isinstance(ex, str):
                examples.append(ex)

        typed_meta = CLICommandMetadata(
            callback=None,
            option_count=len(options),
            argument_count=0,  # milo uses keyword args only
            is_group=False,
            is_hidden=getattr(cmd_def, "hidden", False),
        )

        return DocElement(
            name=name,
            qualified_name=qualified_name,
            description=description,
            element_type="command",
            source_file=source_file,
            line_number=line_number,
            metadata={
                "callback": None,
                "option_count": len(options),
                "argument_count": 0,
            },
            typed_metadata=typed_meta,
            children=options,
            examples=examples,
            see_also=[],
            deprecated=None,
        )

    def _extract_milo_parameter(
        self,
        name: str,
        prop_schema: dict[str, Any],
        required: bool,
        parent_name: str,
    ) -> DocElement:
        """
        Extract a parameter from a JSON Schema property.

        Args:
            name: Parameter name
            prop_schema: JSON Schema property definition
            required: Whether the parameter is required
            parent_name: Parent command qualified name

        Returns:
            DocElement for the option
        """
        type_name = prop_schema.get("type", "string").upper()
        description = sanitize_text(prop_schema.get("description"))
        default = prop_schema.get("default")
        default_str = str(default) if default is not None else None

        # Detect boolean flags
        is_flag = type_name == "BOOLEAN"

        typed_meta = CLIOptionMetadata(
            name=name,
            param_type="option",
            type_name=type_name,
            required=required,
            default=default_str,
            multiple=False,
            is_flag=is_flag,
            count=False,
            opts=(f"--{name.replace('_', '-')}",),
            envvar=None,
            help_text=description or "",
        )

        return DocElement(
            name=name,
            qualified_name=f"{parent_name}.{name}",
            description=description,
            element_type="option",
            source_file=None,
            line_number=None,
            metadata={
                "param_type": "option",
                "type": type_name,
                "required": required,
                "default": default_str,
                "multiple": False,
                "is_flag": is_flag,
                "count": False,
                "opts": [f"--{name.replace('_', '-')}"],
            },
            typed_metadata=typed_meta,
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )

    def _extract_milo_global_option(self, opt: Any, parent_name: str) -> DocElement:
        """
        Extract a milo GlobalOption as an option DocElement.

        Args:
            opt: milo GlobalOption instance
            parent_name: Root CLI qualified name

        Returns:
            DocElement for the global option
        """
        type_name = getattr(opt.option_type, "__name__", "str").upper()
        default_str = str(opt.default) if opt.default is not None else None
        opts: list[str] = [f"--{opt.name.replace('_', '-')}"]
        if opt.short:
            opts.append(opt.short)

        typed_meta = CLIOptionMetadata(
            name=opt.name,
            param_type="GlobalOption",
            type_name=type_name,
            required=False,
            default=default_str,
            multiple=False,
            is_flag=opt.is_flag,
            count=False,
            opts=tuple(opts),
            envvar=None,
            help_text=opt.description or "",
        )

        return DocElement(
            name=opt.name,
            qualified_name=f"{parent_name}.{opt.name}",
            description=sanitize_text(opt.description),
            element_type="option",
            source_file=None,
            line_number=None,
            metadata={
                "param_type": "GlobalOption",
                "type": type_name,
                "required": False,
                "default": default_str,
                "is_flag": opt.is_flag,
                "opts": opts,
            },
            typed_metadata=typed_meta,
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )

    @staticmethod
    def _get_handler_source(handler: Any) -> tuple[Path | None, int | None]:
        """
        Extract source file and line number from a handler function.

        Args:
            handler: Callable to inspect

        Returns:
            (source_file, line_number) tuple; either may be None
        """
        try:
            source_file = Path(inspect.getfile(handler))
            line_number = inspect.getsourcelines(handler)[1]
            return source_file, line_number
        except TypeError, OSError:
            return None, None

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
        import typer  # type: ignore[import-not-found]

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

        # Method 3: Direct attribute access (older Typer versions)
        if click_app is None and hasattr(app, "_click_group"):
            click_app = app._click_group

        # If we successfully got a Click app, extract from it
        if click_app is not None:
            return self._extract_from_click(click_app)

        # Fallback: raise error if we couldn't extract
        from bengal.errors import BengalDiscoveryError, ErrorCode

        raise BengalDiscoveryError(
            "Unable to extract Click app from Typer instance. "
            "Make sure you're passing a Typer() app object.",
            suggestion="Pass a Typer() app instance, not a command function",
            code=ErrorCode.O004,
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
            import typer  # type: ignore[import-not-found]

            if hasattr(typer.main, "get_group"):
                return typer.main.get_group(typer_app)
            if hasattr(typer.main, "get_command"):
                return typer.main.get_command(typer_app)
        except Exception as e:
            logger.debug(
                "cli_extractor_typer_to_click_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_none",
            )

        return None

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
        if element.element_type == "command":
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
        # Shouldn't happen, but fallback
        return Path(f"{element.name}.md")
