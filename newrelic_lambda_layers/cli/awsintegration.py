import boto3
import click
import requests

from .. import awsintegration, permissions
from ..gql import NewRelicGQL
from .decorators import add_options, AWS_OPTIONS


@click.group(name="integration")
def integration_group():
    """Manage New Relic AWS Integrations"""
    pass


def register(group):
    group.add_command(integration_group)
    integration_group.add_command(integration_install)


@click.command(name="install")
@add_options(AWS_OPTIONS)
@click.option(
    "--aws-role-policy",
    help="Alternative AWS role policy to use for integration",
    metavar="<arn>",
)
@click.option(
    "--linked-account-name",
    "-n",
    help="New Relic Linked Account Label",
    metavar="<name>",
    required=True,
)
@click.option(
    "--nr-account-id",
    "-a",
    envvar="NEW_RELIC_ACCOUNT_ID",
    help="New Relic Account ID",
    metavar="<id>",
    required=True,
    type=click.INT,
)
@click.option(
    "--nr-api-key",
    "-k",
    envvar="NEW_RELIC_API_KEY",
    help="New Relic User API Key",
    metavar="<key>",
    required=True,
)
@click.option(
    "--nr-region",
    default="us",
    envvar="NEW_RELIC_REGION",
    help="New Relic Account Region",
    metavar="<region>",
    show_default=True,
    type=click.Choice(["us", "eu"]),
)
def integration_install(
    aws_profile,
    aws_region,
    aws_role_policy,
    linked_account_name,
    nr_account_id,
    nr_api_key,
    nr_region,
):
    """Install New Relic AWS Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_setup_permissions(session)

    click.echo("Validating New Relic credentials")

    try:
        gql = NewRelicGQL(nr_account_id, nr_api_key, nr_region)
    except requests.exceptions.HTTPError:
        raise click.BadParameterError(
            "Could not authenticate with New Relic. Check that your New Relic API Key "
            "is valid and try again.",
            param="nr_api_key",
        )

    click.echo("Retrieving integration license key")

    try:
        nr_license_key = gql.get_license_key()
    except Exception:
        raise click.BadParameterError(
            "Could not retrieve license key from New Relic. Check that your New Relic "
            "Account ID is valid and try again.",
            param="nr_account_id",
        )

    click.echo("Checking for a pre-existing link between New Relic and AWS")
    awsintegration.validate_linked_account(session, gql, linked_account_name)

    click.echo("Creating the AWS role for the New Relic integration")
    role = awsintegration.create_integration_role(
        session, aws_role_policy, nr_account_id
    )

    click.echo("Linking New Relic account to AWS account")
    awsintegration.create_integration_account(
        gql, nr_account_id, linked_account_name, role
    )

    click.echo("Enabling Lambda integration on the link between New Relic and AWS")
    awsintegration.enable_lambda_integration(gql, nr_account_id, linked_account_name)

    click.echo("Creating newrelic-log-ingestion Lambda function in AWS account")
    awsintegration.setup_log_ingestion(session, nr_license_key)
