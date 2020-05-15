# -*- coding: utf-8 -*-

from concurrent.futures import as_completed, ThreadPoolExecutor

import boto3
import click

from newrelic_lambda_cli import permissions, subscriptions
from newrelic_lambda_cli.cliutils import done, failure
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS
from newrelic_lambda_cli.functions import get_aliased_functions


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
@click.option(
    "excludes",
    "--exclude",
    "-e",
    help="Functions to exclude (if using 'all, 'installed', 'not-installed aliases)",
    metavar="<name>",
    multiple=True,
)
@click.option(
    "filter_pattern",
    "--filter-pattern",
    default=subscriptions.DEFAULT_FILTER_PATTERN,
    help="Custom log subscription filter pattern",
    metavar="<pattern>",
)
def install(
    aws_profile, aws_region, aws_permissions_check, functions, excludes, filter_pattern
):
    """Install New Relic AWS Lambda Log Subscriptions"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_install_permissions(session)

    functions = get_aliased_functions(session, functions, excludes)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                subscriptions.create_log_subscription, session, function, filter_pattern
            )
            for function in functions
        ]
        install_success = all(future.result() for future in as_completed(futures))

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
@click.option(
    "excludes",
    "--exclude",
    "-e",
    help="Functions to exclude (if using 'all, 'installed', 'not-installed aliases)",
    metavar="<name>",
    multiple=True,
)
def uninstall(aws_profile, aws_region, aws_permissions_check, functions, excludes):
    """Uninstall New Relic AWS Lambda Log Subscriptions"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_subscription_uninstall_permissions(session)

    functions = get_aliased_functions(session, functions, excludes)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(subscriptions.remove_log_subscription, session, function)
            for function in functions
        ]
        uninstall_success = all(future.result() for future in as_completed(futures))

    if uninstall_success:
        done("Uninstall Complete")
    else:
        failure("Uninstall Incomplete. See messages above for details.", exit=True)
