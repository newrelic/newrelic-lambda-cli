import click

from .. import utils
from ..awslambda import MultipleLayersException, UpdateLambdaException

from . import awslambda, stack


@click.group(name="cli")
def cli():
    pass


def register_groups(group):
    awslambda.register(group)
    stack.register(group)


@utils.catch_boto_errors
def main():
    try:
        register_groups(cli)
        cli()
    except MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except UpdateLambdaException as e:
        utils.error(e)
