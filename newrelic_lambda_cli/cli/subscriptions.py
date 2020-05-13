# -*- coding: utf-8 -*-

from concurrent.futures import as_completed, ThreadPoolExecutor

import boto3
import click

from newrelic_lambda_cli import permissions, subscriptions
from newrelic_lambda_cli.cliutils import done, failure, success
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

    install_success = True
    futures = []

    with ThreadPoolExecutor() as executor:
        for function in functions:
            futures.append(
                executor.submit(
                    subscriptions.create_log_subscription,
                    session,
                    function,
                    filter_pattern,
                )
            )
        for future in as_completed(futures):
            result = future.result()
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

    uninstall_success = True
    futures = []

    with ThreadPoolExecutor() as executor:
        for function in functions:
            futures.append(
                executor.submit(
                    subscriptions.remove_log_subscription, session, function
                )
            )
        for future in as_completed(futures):
            result = future.result()
            uninstall_success = result and uninstall_success
            if result:
                success("Successfully uninstalled log subscription on %s" % function)

    if uninstall_success:
        done("Uninstall Complete")
    else:
        failure("Uninstall Incomplete. See messages above for details.", exit=True)
