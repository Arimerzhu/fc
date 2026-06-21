"""Example fc plugin — hello command."""

import click


@click.command()
@click.argument("name", default="World")
def hello(name: str):
    """Say hello from a plugin.

    Args:
        name: Who to greet.
    """
    click.echo(f"Hello, {name}! This is a plugin command.")


# Export as fc_commands list
fc_commands = [hello]
