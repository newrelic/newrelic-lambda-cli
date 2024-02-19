# -*- coding: utf-8 -*-

from concurrent.futures import as_completed, ThreadPoolExecutor

import boto3
import click

from newrelic_lambda_cli import permissions, subscriptions
from newrelic_lambda_cli.cliutils import done, failure
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS
from newrelic_lambda_cli.functions import get_aliased_functions
from newrelic_lambda_cli.types import SubscriptionInstall, SubscriptionUninstall

DEFAULT_FILTER_PATTERN = '?REPORT ?NR_LAMBDA_MONITORING ?"Task timed out" ?RequestId'


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
    "--stackname",
    default="NewRelicLogIngestion",
    help="The AWS Cloudformation stack name which contains the newrelic-log-ingestion lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
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
    default=DEFAULT_FILTER_PATTERN,
    help="Custom log subscription filter pattern",
    metavar="<pattern>",
    show_default=False,
)
def install(**kwargs):
    """Install New Relic AWS Lambda Log Subscriptions"""
    input = SubscriptionInstall(session=None, **kwargs)

    if input.aws_permissions_check:
        permissions.ensure_subscription_install_permissions(input)

    functions = get_aliased_functions(input)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                subscriptions.create_log_subscription,
                input._replace(
                    session=boto3.Session(
                        profile_name=input.aws_profile, region_name=input.aws_region
                    )
                ),
                function,
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
    "--stackname",
    default="NewRelicLogIngestion",
    help="The AWS Cloudformation stack name which contains the newrelic-log-ingestion lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
)
@click.option(
    "excludes",
    "--exclude",
    "-e",
    help="Functions to exclude (if using 'all, 'installed', 'not-installed aliases)",
    metavar="<name>",
    multiple=True,
)
def uninstall(**kwargs):
    """Uninstall New Relic AWS Lambda Log Subscriptions"""
    input = SubscriptionUninstall(session=None, **kwargs)

    if input.aws_permissions_check:
        permissions.ensure_subscription_uninstall_permissions(input)

    functions = get_aliased_functions(input)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                subscriptions.remove_log_subscription,
                input._replace(
                    session=boto3.Session(
                        profile_name=input.aws_profile, region_name=input.aws_region
                    )
                ),
                function,
            )
            for function in functions
        ]
        uninstall_success = all(future.result() for future in as_completed(futures))

    if uninstall_success:
        done("Uninstall Complete")
    else:
        failure("Uninstall Incomplete. See messages above for details.", exit=True)
