#!/usr/bin/env python3
from . import awslambda
from . import cli_awslambda
from . import cli_stack
from . import utils

import boto3
import botocore
import click


@click.group(name="cli")
def cli_group():
    None


def click_groups(group):
    cli_awslambda.register(group)
    cli_stack.register(group)


@utils.catch_boto_errors
def main():
    try:
        click_groups(cli_group)
        cli_group()
    except awslambda.MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        utils.error(e)
