import click

from bengal.cli.commands.assets import assets
from bengal.cli.commands.autodoc import autodoc, autodoc_cli
from bengal.cli.commands.graph import graph_cli
from bengal.cli.commands.perf import perf
from bengal.cli.commands.theme import theme


@click.group("utils")
def utils_cli():
    """
    🛠️  Developer utilities and analysis tools.

    Commands:
        autodoc    Generate API documentation from Python source code
        theme      Manage themes (list, install, create)
        assets     Manage site assets (minify, optimize)
        perf       Analyze build performance
        graph      Analyze site structure and connectivity
    """
    pass


utils_cli.add_command(perf)
utils_cli.add_command(autodoc)
utils_cli.add_command(autodoc_cli)
utils_cli.add_command(assets)
utils_cli.add_command(theme)
utils_cli.add_command(graph_cli)
