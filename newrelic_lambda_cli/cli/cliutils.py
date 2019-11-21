import click


def done(message):
    """Prints a done message to the terminal"""
    click.echo("✨ ", color="yellow", nl=False)
    click.echo(message, nl=False)
    click.echo(" ✨", color="yellow")


def failure(message):
    """Prints a failure message to the terminal"""
    click.echo("✖️ ", color="red", err=True, nl=False)
    click.echo(message, err=True)


def success(message):
    """Prints a success message to the terminal"""
    click.echo("✔️ ", color="green", nl=False)
    click.echo(message)
