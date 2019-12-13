import boto3
import click

from .. import permissions, subscriptions
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


@click.command(name="install")
@add_options(AWS_OPTIONS)
@click.option(
    "--function",
    "-f",
    help="AWS Lambda function name or ARN",
    metavar="<arn>",
    required=True,
)
def install(aws_profile, aws_region, aws_permissions_check, function):
    """Install New Relic AWS Lambda Log Subscription"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_install_permissions(session)

    subscriptions.create_log_subscription(session, function)
    done("Install Complete")


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
@click.option(
    "--function",
    "-f",
    help="Lambda function name or ARN",
    metavar="<arn>",
    required=True,
)
def uninstall(aws_profile, aws_region, aws_permissions_check, function):
    """Uninstall New Relic AWS Lambda Log Subscription"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_uninstall_permissions(session)

    subscriptions.remove_log_subscription(session, function)
    done("Uninstall Complete")
