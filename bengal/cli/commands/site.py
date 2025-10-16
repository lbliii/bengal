import click

from bengal.cli.commands.build import build
from bengal.cli.commands.clean import clean
from bengal.cli.commands.serve import serve


@click.group("site")
def site_cli():
    """
    🌐 Manage your Bengal site.

    Commands:
        build      Build the static site
        serve      Start development server with live reload
        clean      Clean build artifacts and cache
    """
    pass


site_cli.add_command(build)
site_cli.add_command(serve)
site_cli.add_command(clean)
