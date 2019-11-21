import itertools
import shutil

import boto3
import click
from tabulate import tabulate

from .. import functions, permissions
from .decorators import add_options, AWS_OPTIONS


@click.group(name="functions")
def functions_group():
    """Manage New Relic AWS Lambda Functions"""
    pass


def register(group):
    group.add_command(functions_group)
    functions_group.add_command(list)


@click.command(name="list")
@add_options(AWS_OPTIONS)
@click.option(
    "--filter",
    "-f",
    help="Apply a filter to the list.",
    type=click.Choice(["all", "installed", "not-installed"]),
)
def list(aws_profile, aws_region, filter):
    """List AWS Lambda Functions"""
    _, rows = shutil.get_terminal_size((80, 50))
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_lambda_list_permissions(session)
    funcs = functions.list_functions(session, filter)

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
