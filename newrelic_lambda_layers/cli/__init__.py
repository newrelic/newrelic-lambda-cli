import click

from .. import utils

from . import awslambda


@click.group(name="cli")
def cli():
    pass


def register_groups(group):
    awslambda.register(group)


@utils.catch_boto_errors
def main():
    register_groups(cli)
    cli()
