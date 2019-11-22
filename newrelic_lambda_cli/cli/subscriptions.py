import json

import boto3
import click

from .. import integrations, permissions
from .cliutils import done
from .decorators import add_options, AWS_OPTIONS


@click.group(name="subscriptions")
def subscriptions_group():
    """Manage New Relic AWS Lambda Layers"""
    pass


def register(group):
    group.add_command(subscriptions_group)
    subscriptions_group.add_command(install)
    subscriptions_group.add_command(uninstall)


@click.command(name="install")
@click.option(
    "--nr-account-id",
    "-a",
    envvar="NEW_RELIC_ACCOUNT_ID",
    help="New Relic Account ID",
    metavar="<account_id>",
    required=True,
    type=click.INT,
)
@add_options(AWS_OPTIONS)
@click.option(
    "--function",
    "-f",
    help="AWS Lambda function name or ARN",
    metavar="<arn>",
    required=True,
    type=click.STRING,
)
@click.pass_context
def install(ctx, nr_account_id, aws_profile, aws_region, function):
    """Install New Relic AWS Lambda Log Subsciption"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_install_permissions(session)

    integrations.create_log_subscription(session, function)
    done("Install Complete")


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
@click.option(
    "--function",
    "-f",
    required=True,
    metavar="<arn>",
    help="Lambda function name or ARN",
)
@click.pass_context
def uninstall(ctx, aws_profile, aws_region, function):
    """Uninstall New Relic AWS Lambda Layer"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_uninstall_permissions(session)

    integrations.remove_log_subscription(session, function)
    done("Uninstall Complete")
