import click

from .. import utils

AWS_OPTIONS = [
    click.option(
        "--aws-profile",
        "-p",
        callback=utils.validate_aws_profile,
        default="default",
        envvar="AWS_PROFILE",
        help="AWS profile",
        metavar="<profile>",
        show_default=True,
    ),
    click.option(
        "--aws-region",
        "-r",
        envvar="AWS_DEFAULT_REGION",
        help="AWS region",
        metavar="<region>",
        type=click.Choice(utils.all_lambda_regions()),
    ),
    click.option(
        "--aws-permissions-check/--no-aws-permissions-check",
        help="Perform AWS permissions checks",
        default=True,
        show_default=True,
    ),
]

NR_OPTIONS = [
    click.option(
        "--nr-account-id",
        "-a",
        envvar="NEW_RELIC_ACCOUNT_ID",
        help="New Relic Account ID",
        metavar="<id>",
        required=True,
        type=click.INT,
    ),
    click.option(
        "--nr-api-key",
        "-k",
        envvar="NEW_RELIC_API_KEY",
        help="New Relic User API Key",
        metavar="<key>",
        required=True,
    ),
    click.option(
        "--nr-region",
        default="us",
        envvar="NEW_RELIC_REGION",
        help="New Relic Account Region",
        metavar="<region>",
        show_default=True,
        type=click.Choice(["us", "eu"]),
    ),
]


def add_options(options):
    """
    A decorator to add a set of options to a click command. This allows options that
    are used in multiple places to be defined in one place.

    :param options: A list of click options to add to the command
    """

    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options
