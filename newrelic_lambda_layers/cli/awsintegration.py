import boto3
import click

from .. import awsintegration, permissions, gql
from .decorators import add_options, AWS_OPTIONS, NR_OPTIONS


@click.group(name="integration")
def integration_group():
    """Manage New Relic AWS Lambda Integrations"""
    pass


def register(group):
    group.add_command(integration_group)
    integration_group.add_command(integration_install)
    integration_group.add_command(integration_uninstall)


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
@add_options(NR_OPTIONS)
def integration_install(
    aws_profile,
    aws_region,
    aws_role_policy,
    linked_account_name,
    nr_account_id,
    nr_api_key,
    nr_region,
):
    """Install New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_integration_install_permissions(session)

    click.echo("Validating New Relic credentials")
    gql_client = gql.validate_gql_credentials(nr_account_id, nr_api_key, nr_region)

    click.echo("Retrieving integration license key")
    nr_license_key = gql.retrieve_license_key(gql_client)

    click.echo("Checking for a pre-existing link between New Relic and AWS")
    awsintegration.validate_linked_account(session, gql_client, linked_account_name)

    click.echo("Creating the AWS role for the New Relic AWS Lambda Integration")
    role = awsintegration.create_integration_role(
        session, aws_role_policy, nr_account_id
    )

    click.echo("Linking New Relic account to AWS account")
    awsintegration.create_integration_account(
        gql_client, nr_account_id, linked_account_name, role
    )

    click.echo("Enabling Lambda integration on the link between New Relic and AWS")
    awsintegration.enable_lambda_integration(
        gql_client, nr_account_id, linked_account_name
    )

    click.echo("Creating newrelic-log-ingestion Lambda function in AWS account")
    awsintegration.install_log_ingestion(session, nr_license_key)


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
def integration_uninstall(aws_profile, aws_region):
    """Uninstall New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_integration_uninstall_permissions(session)

    click.confirm(
        "This will uninstall the New Relic AWS Lambda log ingestion. "
        "Are you sure you want to proceed?",
        abort=True,
        default=False,
    )
    awsintegration.remove_log_ingestion_function(session)
