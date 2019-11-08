import json
import itertools
import shutil

import boto3
import click
from tabulate import tabulate

from .. import awslambda, utils
from .decorators import add_options, AWS_OPTIONS


@click.group(name="lambda")
def lambda_group():
    """Manage New Relic AWS Lambda Layers"""
    pass


def register(group):
    group.add_command(lambda_group)
    lambda_group.add_command(lambda_list_functions)
    lambda_group.add_command(lambda_install)
    lambda_group.add_command(lambda_uninstall)


@click.command(name="install")
@click.option(
    "--account-id",
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
def lambda_install(
    ctx, account_id, aws_profile, aws_region, function, layer_arn, upgrade
):
    """Install New Relic AWS Lambda Layer"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    try:
        resp = awslambda.install(session, function, layer_arn, account_id, upgrade)
    except awslambda.MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        utils.error(e)

    if not resp:
        click.echo("\nInstallation failed.")
        return

    if ctx.obj["VERBOSE"]:
        click.echo(json.dumps(resp, indent=2))

    click.echo("\nInstall complete.")


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
def lambda_uninstall(ctx, aws_profile, aws_region, function, layer_arn):
    """Uninstall New Relic AWS Lambda Layer"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    try:
        resp = awslambda.uninstall(session, function, layer_arn)
    except awslambda.MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        utils.error(e)

    if not resp:
        click.echo("\nRemoval failed.")
        return

    if ctx.obj["VERBOSE"]:
        click.echo(json.dumps(resp, indent=2))

    click.echo("\nRemoval of New Relic layers and configuration complete.")


@click.command(name="list")
@add_options(AWS_OPTIONS)
@click.option(
    "--filter",
    "-f",
    help="Apply a filter to the list.",
    type=click.Choice(["all", "installed", "not-installed"]),
)
def lambda_list_functions(aws_profile, aws_region, filter):
    """List AWS Lambda Functions"""
    _, rows = shutil.get_terminal_size((80, 50))
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    funcs = awslambda.list_functions(session, filter)

    def _format(funcs, header=False):
        table = []
        for func in funcs:
            table.append(
                [
                    func.get("FunctionName"),
                    func.get("Runtime"),
                    "Yes" if func.get("x-new-relic-enabled", False) else "No",
                ]
            )
        return tabulate(
            table, headers=["Function Name", "Runtime", "Installed"] if header else []
        ).rstrip()

    buffer = []
    for i, func in enumerate(funcs):
        buffer.append(func)
        if i > 0 and i % rows == 0:
            click.echo_via_pager(
                itertools.chain(iter(_format(buffer, header=True)), _format(funcs))
            )
            buffer = []
            return
    click.echo(_format(buffer, header=True))
