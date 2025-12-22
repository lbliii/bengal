"""
Helper for loading CLI applications from module paths.

Provides a utility to dynamically import and load Click applications
from a string path specification. Used primarily by plugin systems
and extension mechanisms.

Functions:
    load_cli_app: Load a Click app from "module.path:attribute_name" format
"""

from __future__ import annotations

import importlib
from typing import Any

import click

from bengal.cli.helpers.cli_output import get_cli_output
from bengal.output import CLIOutput


def load_cli_app(
    app_path: str,
    cli: CLIOutput | None = None,
) -> Any:
    """
    Load a CLI application from a module path.

    Args:
        app_path: Module path in format "module.path:attribute_name"
                  (e.g., "bengal.cli:main")
        cli: Optional CLIOutput instance (creates new if not provided)

    Returns:
        The CLI application object (typically a Click group or command)

    Raises:
        click.Abort: If loading fails

    Example:
        @click.command()
        def my_command():
            app = load_cli_app("bengal.cli:main")
            # ... use app ...
    """
    if cli is None:
        cli = get_cli_output()

    try:
        module_path, attr_name = app_path.split(":")
        module = importlib.import_module(module_path)
        cli_app = getattr(module, attr_name)
        return cli_app
    except ValueError as e:
        cli.error(f"❌ Invalid app path format: {app_path}")
        cli.blank()
        cli.info("Expected format: 'module.path:attribute_name'")
        cli.info("  • Example: 'bengal.cli:main'")
        cli.blank()
        raise click.Abort() from e
    except ImportError as e:
        cli.error(f"❌ Failed to import module: {module_path}")
        cli.blank()
        cli.info("Make sure the module path is correct:")
        cli.info(f"  • Module: {module_path}")
        cli.info(f"  • Attribute: {attr_name if ':' in app_path else '(missing)'}")
        cli.blank()
        raise click.Abort() from e
    except AttributeError as e:
        cli.error(f"❌ Failed to load app: {e}")
        cli.blank()
        cli.info("Make sure the module path is correct:")
        cli.info(f"  • Module: {module_path}")
        cli.info(f"  • Attribute: {attr_name if ':' in app_path else '(missing)'}")
        cli.blank()
        raise click.Abort() from e
    except Exception as e:
        cli.error(f"❌ Failed to load app: {e}")
        cli.blank()
        cli.info("Make sure the module path is correct:")
        cli.info(f"  • Module: {app_path.split(':')[0] if ':' in app_path else app_path}")
        cli.info(f"  • Attribute: {app_path.split(':')[1] if ':' in app_path else '(missing)'}")
        cli.blank()
        raise click.Abort() from e
