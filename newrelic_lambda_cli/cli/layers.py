# -*- coding: utf-8 -*-

from concurrent.futures import as_completed, ThreadPoolExecutor

import boto3
import click

from newrelic_lambda_cli import layers, permissions
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS
from newrelic_lambda_cli.cliutils import done, failure
from newrelic_lambda_cli.functions import get_aliased_functions
from newrelic_lambda_cli.types import LayerInstall, LayerUninstall


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
@click.option(
    "--nr-api-key",
    "-k",
    envvar="NEW_RELIC_API_KEY",
    help="New Relic User API Key",
    metavar="<key>",
    required=False,
)
@click.option(
    "--nr-region",
    default="us",
    envvar="NEW_RELIC_REGION",
    help="New Relic Account Region",
    metavar="<region>",
    show_default=True,
    type=click.Choice(["us", "eu", "staging"]),
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
@click.option(
    "--enable-extension/--disable-extension",
    "-x",
    default=True,
    show_default=True,
    help="Enable/disable the New Relic Lambda Extension",
)
@click.option(
    "--enable-extension-function-logs/--disable-extension-function-logs",
    default=False,
    show_default=True,
    help="Enable/disable sending Lambda function logs via the Extension",
)
@click.option(
    "--java_handler_method",
    "-j",
    default="handleRequest",
    help="Java runtimes only - Specify aws implementation method: RequestHandler or RequestStreamHandler",
    metavar="<java_handler>",
    show_default=True,
    type=click.Choice(["handleRequest", "handleStreamsRequest"]),
)
@click.option(
    "--nodejs_enable_esm",
    default=False,
    show_default=True,
    help="Nodejs runtimes only - Specify nodejs implementation method to /opt/nodejs/node_modules/newrelic-esm-lambda-wrapper/index.handler",
)
@click.pass_context
def install(ctx, **kwargs):
    """Install New Relic AWS Lambda Layers"""
    input = LayerInstall(session=None, verbose=ctx.obj["VERBOSE"], **kwargs)
    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )
    if input.aws_permissions_check:
        permissions.ensure_layer_install_permissions(input)

    functions = get_aliased_functions(input)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                layers.install,
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
        if ctx.obj["VERBOSE"]:
            click.echo(
                "\nNext step. Configure the CloudWatch subscription filter for your "
                "Lambda functions with the below command:\n"
            )
            command = [
                "$",
                "newrelic-lambda",
                "subscriptions",
                "install",
                "--function",
                "all",
            ]
            if input.aws_profile:
                command.append("--aws-profile %s" % input.aws_profile)
            if input.aws_region:
                command.append("--aws-region %s" % input.aws_region)
            click.echo(" ".join(command))
            click.echo(
                "\nIf you used `--enable-logs` for the `newrelic-lambda integrations "
                "install` command earlier, run this command instead:\n"
            )
            command.append('--filter-pattern ""')
            click.echo(" ".join(command))
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
def uninstall(ctx, **kwargs):
    """Uninstall New Relic AWS Lambda Layers"""
    input = LayerUninstall(session=None, verbose=ctx.obj["VERBOSE"], **kwargs)
    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )
    if input.aws_permissions_check:
        permissions.ensure_layer_uninstall_permissions(input)

    functions = get_aliased_functions(input)

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                layers.uninstall,
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
