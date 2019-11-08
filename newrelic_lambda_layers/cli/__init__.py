import boto3
import click

from .. import utils

from . import awsintegration, awslambda


@click.group()
@click.option("--verbose", "-v", help="Increase verbosity", is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose


def register_groups(group):
    awsintegration.register(group)
    awslambda.register(group)


@utils.catch_boto_errors
def main():
    register_groups(cli)
    cli()
