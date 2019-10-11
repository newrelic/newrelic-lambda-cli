import click
import itertools
import json
import shutil

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
    help="Layer ARN for IOpipe library (default: auto-detect)",
)
@click.option(
    "--verbose",
    "-v",
    help="Print new function configuration upon completion.",
    is_flag=True,
)
@click.option(
    "--java-type",
    "-j",
    help="Specify Java handler type, required for Java functions.",
    type=click.Choice(["request", "stream"]),
)
@click.option(
    "--token",
    "-t",
    envvar="IOPIPE_TOKEN",
    required=True,
    metavar="<token>",
    help="IOpipe Token",
    callback=utils.check_token,
)
@click.option(
    "--upgrade",
    "-u",
    help="Permit upgrade of function layers to new version.",
    is_flag=True,
)
def lambda_install(region, function, layer_arn, verbose, token, java_type, upgrade):
    resp = awslambda.install(region, function, layer_arn, token, java_type, upgrade)
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
    help="Layer ARN for IOpipe library (default: auto-detect)",
)
@click.option(
    "--verbose",
    "-v",
    help="Print new function configuration upon completion.",
    is_flag=True,
)
def lambda_uninstall(region, function, layer_arn, verbose):
    resp = awslambda.uninstall(region, function, layer_arn)
    if not resp:
        click.echo("\nRemoval failed.")
        return
    if verbose:
        click.echo(json.dumps(resp, indent=2))
    click.echo("\nRemoval of IOpipe layers and configuration complete.")


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
    # this use of `filter` worries me as it's a keyword,
    # but it actually works? Clickly doesn't give
    # us enough control here to change the variable name? -Erica
    coltmpl = "{:<64}\t{:<12}\t{:>12}\n"
    conscols, consrows = shutil.get_terminal_size((80, 50))

    def _header():
        if not quiet:
            yield coltmpl.format("Function Name", "Runtime", "Installed")
            # ascii table limbo line ---
            yield ("{:-^%s}\n" % (str(conscols),)).format("")

    def _format(funcs):
        for f in funcs:
            yield coltmpl.format(
                f.get("FunctionName"),
                f.get("Runtime"),
                f.get("-x-iopipe-enabled", False),
            )

    buffer = []
    functions_iter = awslambda.list_functions(region, quiet, filter)
    for idx, line in enumerate(itertools.chain(_header(), _format(functions_iter))):
        buffer.append(line)

        # This is designed to ONLY page when there's
        # more rows than the height of the console.
        # If we've buffered as many lines as the height of the console,
        # then start a pager and empty the buffer.
        if idx > 0 and idx % consrows == 0:
            click.echo_via_pager(itertools.chain(iter(buffer), _format(functions_iter)))
            buffer = []
            return
    # Print all lines for non-paged results.
    for line in iter(buffer):
        click.echo(line, nl=False)
