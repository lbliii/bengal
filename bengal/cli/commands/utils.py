import click

from bengal.cli.commands.assets import assets
from bengal.cli.commands.autodoc import autodoc, autodoc_cli
from bengal.cli.commands.perf import perf
from bengal.cli.commands.theme import theme


@click.group("utils")
def utils_cli():
    """
    Utility and analysis commands.
    """
    pass

from bengal.cli.commands.graph import graph_cli


utils_cli.add_command(perf)
utils_cli.add_command(autodoc)
utils_cli.add_command(autodoc_cli)
utils_cli.add_command(assets)
utils_cli.add_command(theme)
utils_cli.add_command(graph_cli)