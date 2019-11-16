import json

import boto3
import click

from .. import awsintegration, layers, permissions
from .cliutils import done
from .decorators import add_options, AWS_OPTIONS


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
    "--function",
    "-f",
    help="AWS Lambda function name or ARN",
    metavar="<arn>",
    required=True,
    type=click.STRING,
)
@click.option(
    "--layer-arn",
    "-l",
    help="ARN for New Relic layer (default: auto-detect)",
    metavar="<arn>",
    type=click.STRING,
)
@click.option(
    "--upgrade",
    "-u",
    help="Permit upgrade of function layers to new version.",
    is_flag=True,
)
@click.pass_context
def install(ctx, account_id, aws_profile, aws_region, function, layer_arn, upgrade):
    """Install New Relic AWS Lambda Layer"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_install_permissions(session)

    res = layers.install(session, function, layer_arn, account_id, upgrade)
    if not res:
        click.echo("\nInstallation failed.")
        return

    if ctx.obj["VERBOSE"]:
        click.echo(json.dumps(res, indent=2))

    awsintegration.create_log_subscription(session, function)

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
@click.option(
    "--layer-arn",
    "-l",
    help="ARN for New Relic layer (default: auto-detect)",
    metavar="<arn>",
)
@click.pass_context
def uninstall(ctx, aws_profile, aws_region, function, layer_arn):
    """Uninstall New Relic AWS Lambda Layer"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_uninstall_permissions(session)

    res = layers.uninstall(session, function, layer_arn)
    if not res:
        click.echo("\nUninstall failed.")
        return

    if ctx.obj["VERBOSE"]:
        click.echo(json.dumps(res, indent=2))

    awsintegration.remove_log_subscription(session, function)

    done("Uninstall Complete")
