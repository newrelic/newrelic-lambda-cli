import json
import shutil

import click
from tabulate import tabulate

from .. import awslambda, utils


@click.group(name="lambda")
def lambda_group():
    pass


def register(group):
    group.add_command(lambda_group)
    lambda_group.add_command(lambda_list_functions)
    lambda_group.add_command(lambda_install)
    lambda_group.add_command(lambda_uninstall)


@click.command(name="install")
@click.option(
    "--region", "-r", help="AWS region", type=click.Choice(utils.all_lambda_regions())
)
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
    metavar="<arn>",
    help="ARN for New Relic layer (default: auto-detect)",
)
@click.option(
    "--verbose",
    "-v",
    help="Print new function configuration upon completion.",
    is_flag=True,
)
@click.option(
    "--account-id",
    "-a",
    envvar="NEW_RELIC_ACCOUNT_ID",
    required=True,
    metavar="<account_id>",
    help="New Relic Account ID",
)
@click.option(
    "--upgrade",
    "-u",
    help="Permit upgrade of function layers to new version.",
    is_flag=True,
)
def lambda_install(region, function, layer_arn, verbose, account_id, upgrade):
    try:
        resp = awslambda.install(region, function, layer_arn, account_id, upgrade)
    except awslambda.MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        utils.error(e)
    if not resp:
        click.echo("\nInstallation failed.")
        return
    if verbose:
        click.echo(json.dumps(resp, indent=2))
    click.echo("\nInstall complete.")


@click.command(name="uninstall")
@click.option(
    "--region", "-r", help="AWS region", type=click.Choice(utils.all_lambda_regions())
)
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
    metavar="<arn>",
    help="ARN for New Relic layer (default: auto-detect)",
)
@click.option(
    "--verbose",
    "-v",
    help="Print new function configuration upon completion.",
    is_flag=True,
)
def lambda_uninstall(region, function, layer_arn, verbose):
    try:
        resp = awslambda.uninstall(region, function, layer_arn)
    except awslambda.MultipleLayersException:
        utils.error("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        utils.error(e)
    if not resp:
        click.echo("\nRemoval failed.")
        return
    if verbose:
        click.echo(json.dumps(resp, indent=2))
    click.echo("\nRemoval of New Relic layers and configuration complete.")


@click.command(name="list")
@click.option(
    "--region", "-r", help="AWS region", type=click.Choice(utils.all_lambda_regions())
)
@click.option("--quiet", "-q", help="Skip headers", is_flag=True)
@click.option(
    "--filter",
    "-f",
    help="Apply a filter to the list.",
    type=click.Choice(["all", "installed", "not-installed"]),
)
def lambda_list_functions(region, quiet, filter):
    """List Lambda Functions"""
    _, rows = shutil.get_terminal_size((80, 50))
    funcs = awslambda.list_functions(region, quiet, filter)

    table = []
    for func in funcs:
        table.append(
            [
                func.get("FunctionName"),
                func.get("Runtime"),
                "Yes" if func.get("-x-new-relic-enabled", False) else "No",
            ]
        )

    rendered_table = tabulate(
        table, headers=["Function Name", "Runtime", "Installed"]
    ).rstrip()

    if len(table) > rows:
        click.echo_via_pager(rendered_table)
    else:
        click.echo(rendered_table)
