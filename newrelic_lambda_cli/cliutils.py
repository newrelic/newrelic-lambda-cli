# -*- coding: utf-8 -*-

import click
import emoji

from click.exceptions import Exit


def done(message):
    """Prints a done message to the terminal"""
    click.echo(emoji.emojize(":sparkles: %s :sparkles:" % message, use_aliases=True))


def failure(message, exit=False):
    """Prints a failure message to the terminal"""
    click.echo(
        emoji.emojize(":heavy_multiplication_x: %s" % message, use_aliases=True),
        color="red",
        err=True,
    )
    if exit:
        raise Exit(1)


def success(message):
    """Prints a success message to the terminal"""
    click.echo(
        emoji.emojize(":heavy_check_mark: %s" % message, use_aliases=True),
        color="green",
    )


def warning(message):
    """Prints a warningmessage to the terminal"""
    click.echo(
        emoji.emojize(":heavy_exclamation_mark: %s" % message, use_aliases=True),
        color="blue",
    )
