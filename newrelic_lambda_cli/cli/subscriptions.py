import boto3
import click

from newrelic_lambda_cli import permissions, subscriptions
from newrelic_lambda_cli.cliutils import done, failure, success
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS


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
    "functions",
    "--function",
    "-f",
    help="AWS Lambda function name or ARN",
    metavar="<arn>",
    multiple=True,
    required=True,
)
def install(aws_profile, aws_region, aws_permissions_check, functions):
    """Install New Relic AWS Lambda Log Subscriptions"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_install_permissions(session)

    install_success = True

    for function in functions:
        result = subscriptions.create_log_subscription(session, function)
        install_success = result and install_success
        if result:
            success("Successfully installed log subscription on %s" % function)

    if install_success:
        done("Install Complete")
    else:
        failure("Install Incomplete. See messages above for details.", exit=True)


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
@click.option(
    "functions",
    "--function",
    "-f",
    help="Lambda function name or ARN",
    metavar="<arn>",
    multiple=True,
    required=True,
)
def uninstall(aws_profile, aws_region, aws_permissions_check, functions):
    """Uninstall New Relic AWS Lambda Log Subscriptions"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_uninstall_permissions(session)

    uninstall_success = True

    for function in functions:
        result = subscriptions.remove_log_subscription(session, function)
        uninstall_success = result and uninstall_success
        if result:
            success("Successfully uninstalled log subscription on %s" % function)

    if uninstall_success:
        done("Uninstall Complete")
    else:
        failure("Uninstall Incomplete. See messages above for details.", exit=True)
