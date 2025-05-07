# -*- coding: utf-8 -*-

import click

from click.exceptions import Exit


def done(message):
    """Prints a done message to the terminal"""
    click.echo(f"✔️ {message} ✔️")


def failure(message, exit=False):
    """Prints a failure message to the terminal"""
    click.secho(
        f"✘ {message}",
        fg="red",
        err=True,
    )
    if exit:
        raise Exit(1)


def success(message):
    """Prints a success message to the terminal"""
    click.secho(
        f"✔️ {message}",
        fg="green",
    )


def warning(message):
    """Prints a warning message to the terminal"""
    click.secho(
        f"⚠️ {message}",
        fg="blue",
    )
