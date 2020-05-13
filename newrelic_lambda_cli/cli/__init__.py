# -*- coding: utf-8 -*-

import click

from newrelic_lambda_cli import utils
from newrelic_lambda_cli.cli import functions, integrations, layers, subscriptions


@click.group()
@click.option("--verbose", "-v", help="Increase verbosity", is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose


def register_groups(group):
    functions.register(group)
    integrations.register(group)
    layers.register(group)
    subscriptions.register(group)


@utils.catch_boto_errors
def main():
    register_groups(cli)
    cli()
