# -*- coding: utf-8 -*-

from concurrent.futures import as_completed, ThreadPoolExecutor
import json

import boto3
import click

from newrelic_lambda_cli import layers, permissions
from newrelic_lambda_cli.cliutils import done, failure, success
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS
from newrelic_lambda_cli.functions import get_aliased_functions


@click.group(name="layers")
def layers_group():
    """Manage New Relic AWS Lambda Layers"""
    pass


def register(group):
    group.add_command(layers_group)
    layers_group.add_command(install)
    layers_group.add_command(uninstall)


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
    "--layer-arn",
    "-l",
    help="ARN for New Relic layer (default: auto-detect)",
    metavar="<arn>",
)
@click.option(
    "--upgrade",
    "-u",
    help="Permit upgrade of function layers to new version.",
    is_flag=True,
)
@click.pass_context
def install(
    ctx,
    nr_account_id,
    aws_profile,
    aws_region,
    aws_permissions_check,
    functions,
    excludes,
    layer_arn,
    upgrade,
):
    """Install New Relic AWS Lambda Layers"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_lambda_install_permissions(session)

    functions = get_aliased_functions(session, functions, excludes)

    install_success = True
    futures = []

    with ThreadPoolExecutor() as executor:
        for function in functions:
            futures.append(
                executor.submit(
                    layers.install, session, function, layer_arn, nr_account_id, upgrade
                )
            )
        for future in as_completed(futures):
            res = future.result()
            install_success = res and install_success
            if res:
                success("Successfully installed layer on %s" % function)
                if ctx.obj["VERBOSE"]:
                    click.echo(json.dumps(res, indent=2))

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
@click.pass_context
def uninstall(ctx, aws_profile, aws_region, aws_permissions_check, functions, excludes):
    """Uninstall New Relic AWS Lambda Layers"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_lambda_uninstall_permissions(session)

    functions = get_aliased_functions(session, functions, excludes)

    uninstall_success = True
    futures = []

    with ThreadPoolExecutor() as executor:
        for function in functions:
            futures.append(executor.submit(layers.uninstall, session, function))
        for future in as_completed(futures):
            res = future.result()
            uninstall_success = res and uninstall_success
            if res:
                success("Successfully uninstalled layer on %s" % function)
                if ctx.obj["VERBOSE"]:
                    click.echo(json.dumps(res, indent=2))

    if uninstall_success:
        done("Uninstall Complete")
    else:
        failure("Uninstall Incomplete. See messages above for details.", exit=True)
