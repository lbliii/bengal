import click

from bengal.cli.base import BengalGroup

from .build import build
from .clean import clean
from .serve import serve


@click.group("site", cls=BengalGroup)
def site_cli():
    """
    Site building and serving commands.
    """
    pass


site_cli.add_command(build)
site_cli.add_command(serve)
site_cli.add_command(clean)
