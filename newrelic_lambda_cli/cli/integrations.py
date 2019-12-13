import boto3
import click

from .. import gql, integrations, permissions
from .decorators import add_options, AWS_OPTIONS, NR_OPTIONS
from .cliutils import done


@click.group(name="integrations")
def integrations_group():
    """Manage New Relic AWS Lambda Integrations"""
    pass


def register(group):
    group.add_command(integrations_group)
    integrations_group.add_command(install)
    integrations_group.add_command(uninstall)


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
def install(
    aws_profile,
    aws_region,
    aws_permissions_check,
    aws_role_policy,
    linked_account_name,
    nr_account_id,
    nr_api_key,
    nr_region,
):
    """Install New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_integration_install_permissions(session)

    click.echo("Validating New Relic credentials")
    gql_client = gql.validate_gql_credentials(nr_account_id, nr_api_key, nr_region)

    click.echo("Retrieving integration license key")
    nr_license_key = gql.retrieve_license_key(gql_client)

    click.echo("Checking for a pre-existing link between New Relic and AWS")
    integrations.validate_linked_account(session, gql_client, linked_account_name)

    click.echo("Creating the AWS role for the New Relic AWS Lambda Integration")
    role = integrations.create_integration_role(session, aws_role_policy, nr_account_id)

    if role:
        click.echo("Linking New Relic account to AWS account")
        gql.create_integration_account(
            gql_client, nr_account_id, linked_account_name, role
        )

        click.echo("Enabling Lambda integration on the link between New Relic and AWS")
        gql.enable_lambda_integration(gql_client, nr_account_id, linked_account_name)

    click.echo("Creating newrelic-log-ingestion Lambda function in AWS account")
    integrations.install_log_ingestion(session, nr_license_key)

    done("Install Complete")


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
def uninstall(aws_profile, aws_region, aws_permissions_check):
    """Uninstall New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_integration_uninstall_permissions(session)

    click.confirm(
        "This will uninstall the New Relic AWS Lambda log ingestion. "
        "Are you sure you want to proceed?",
        abort=True,
        default=False,
    )
    integrations.remove_log_ingestion_function(session)

    done("Uninstall Complete")
