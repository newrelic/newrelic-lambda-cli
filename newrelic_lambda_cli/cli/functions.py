import itertools
import shutil

import boto3
import click
from tabulate import tabulate

from newrelic_lambda_cli import functions, permissions
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS


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
@click.option(
    "--output",
    "-o",
    default="table",
    help="Formet output",
    show_default=True,
    type=click.Choice(["table", "text"]),
)
def list(aws_profile, aws_region, aws_permissions_check, filter, output):
    """List AWS Lambda Functions"""
    _, rows = shutil.get_terminal_size((80, 50))
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_lambda_list_permissions(session)

    funcs = functions.list_functions(session, filter)

    def format_table(funcs, header=False):
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

    def format_text(funcs, header=False):
        text = []
        if header:
            text.append("\t".join(["Function Name", "Runtime", "Installed"]))
        for func in funcs:
            text.append(
                "\t".join(
                    [
                        func.get("FunctionName"),
                        func.get("Runtime"),
                        "Yes" if func.get("x-new-relic-enabled", False) else "No",
                    ]
                )
            )
        return "\n".join(text)

    _format = format_table

    if output == "text":
        _format = format_text

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
