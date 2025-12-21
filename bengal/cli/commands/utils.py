from __future__ import annotations

import click

from bengal.cli.base import BengalGroup
from bengal.cli.commands.assets import assets
from bengal.cli.commands.codemod import codemod_cli
from bengal.cli.commands.graph import graph_cli
from bengal.cli.commands.perf import perf
from bengal.cli.commands.theme import theme


@click.group("utils", cls=BengalGroup)
def utils_cli() -> None:
    """
    Utility commands for development and maintenance.
    """
    pass


utils_cli.add_command(perf)
utils_cli.add_command(assets)
utils_cli.add_command(theme)
utils_cli.add_command(graph_cli)
utils_cli.add_command(codemod_cli)
