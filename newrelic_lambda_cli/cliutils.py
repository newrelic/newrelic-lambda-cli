# -*- coding: utf-8 -*-

import click
import emoji

from click.exceptions import Exit


def done(message):
    """Prints a done message to the terminal"""
    click.echo(emoji.emojize(":sparkles: ", use_aliases=True), color="yellow", nl=False)
    click.echo(message, nl=False)
    click.echo(emoji.emojize(" :sparkles:", use_aliases=True), color="yellow")


def failure(message, exit=False):
    """Prints a failure message to the terminal"""
    click.echo(
        emoji.emojize(":heavy_multiplication_x: ", use_aliases=True),
        color="red",
        err=True,
        nl=False,
    )
    click.echo(message, err=True)
    if exit:
        raise Exit(1)


def success(message):
    """Prints a success message to the terminal"""
    click.echo(
        emoji.emojize(":heavy_check_mark: ", use_aliases=True), color="green", nl=False
    )
    click.echo(message)
