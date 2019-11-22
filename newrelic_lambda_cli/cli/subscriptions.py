import boto3
import click

from .. import integrations, permissions
from .cliutils import done
from .decorators import add_options, AWS_OPTIONS


@click.group(name="subscriptions")
def subscriptions_group():
    """Manage New Relic AWS Lambda Log Subscriptions"""
    pass


def register(group):
    group.add_command(subscriptions_group)
    subscriptions_group.add_command(install)
    subscriptions_group.add_command(uninstall)


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
def install(ctx, aws_profile, aws_region, function):
    """Install New Relic AWS Lambda Log Subscription"""
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
    """Uninstall New Relic AWS Lambda Log Subscription"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_uninstall_permissions(session)

    integrations.remove_log_subscription(session, function)
    done("Uninstall Complete")
