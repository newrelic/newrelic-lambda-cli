import click

from .. import utils
from ..awslambda import MultipleLayersException, UpdateLambdaException

from . import awslambda, stack


@click.group(name="cli")
def cli_group():
    pass


def click_groups(group):
    awslambda.register(group)
    stack.register(group)


@utils.catch_boto_errors
def main():
    try:
        click_groups(cli_group)
        cli_group()
    except MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except UpdateLambdaException as e:
        utils.error(e)
