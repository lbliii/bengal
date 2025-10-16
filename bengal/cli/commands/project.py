import click
from bengal.cli.commands.init import init


@click.group("project")
def project_cli():
    """
    Commands for managing Bengal projects.
    """
    pass

project_cli.add_command(init)