import boto3
import click

from newrelic_lambda_cli import api, integrations, permissions
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS, NR_OPTIONS
from newrelic_lambda_cli.cliutils import done, failure


@click.group(name="integrations")
def integrations_group():
    """Manage New Relic AWS Lambda Integrations"""
    pass


def register(group):
    group.add_command(integrations_group)
    integrations_group.add_command(install)
    integrations_group.add_command(uninstall)
    integrations_group.add_command(update)


@click.command(name="install")
@add_options(AWS_OPTIONS)
@click.option(
    "--aws-role-policy",
    help="Alternative AWS role policy to use for integration",
    metavar="<arn>",
)
@click.option(
    "--enable-logs",
    "-e",
    help="Determines if logs are forwarded to New Relic Logging",
    is_flag=True,
)
@click.option(
    "--memory-size",
    "-m",
    default=128,
    help="Memory size (in MiB) for the log ingestion function",
    metavar="<size>",
    show_default=True,
    type=click.INT,
)
@click.option(
    "--linked-account-name",
    "-n",
    help="New Relic Linked Account Label",
    metavar="<name>",
    required=True,
)
@add_options(NR_OPTIONS)
@click.option(
    "--timeout",
    "-t",
    default=30,
    help="Timeout (in seconds) for the New Relic log ingestion function",
    metavar="<secs>",
    show_default=True,
    type=click.INT,
)
def install(
    aws_profile,
    aws_region,
    aws_permissions_check,
    aws_role_policy,
    enable_logs,
    memory_size,
    linked_account_name,
    nr_account_id,
    nr_api_key,
    nr_region,
    timeout,
):
    """Install New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_integration_install_permissions(session)

    click.echo("Validating New Relic credentials")
    gql_client = api.validate_gql_credentials(nr_account_id, nr_api_key, nr_region)

    click.echo("Retrieving integration license key")
    nr_license_key = api.retrieve_license_key(gql_client)

    click.echo("Checking for a pre-existing link between New Relic and AWS")
    integrations.validate_linked_account(session, gql_client, linked_account_name)

    click.echo("Creating the AWS role for the New Relic AWS Lambda Integration")
    role = integrations.create_integration_role(session, aws_role_policy, nr_account_id)

    install_success = True

    if role:
        click.echo("Linking New Relic account to AWS account")
        res = api.create_integration_account(
            gql_client, nr_account_id, linked_account_name, role
        )
        install_success = res and install_success

        click.echo("Enabling Lambda integration on the link between New Relic and AWS")
        res = api.enable_lambda_integration(
            gql_client, nr_account_id, linked_account_name
        )
        install_success = res and install_success

    click.echo("Creating newrelic-log-ingestion Lambda function in AWS account")
    res = integrations.install_log_ingestion(
        session, nr_license_key, enable_logs, memory_size, timeout
    )
    install_success = res and install_success

    if install_success:
        done("Install Complete")
    else:
        failure("Install Incomplete. See messages above for details.", exit=True)


@click.command(name="uninstall")
@add_options(AWS_OPTIONS)
@click.option(
    "--nr-account-id",
    "-a",
    envvar="NEW_RELIC_ACCOUNT_ID",
    help="New Relic Account ID",
    metavar="<id>",
    required=False,
    type=click.INT,
)
@click.option("--force", "-f", help="Force uninstall non-interactively", is_flag=True)
def uninstall(aws_profile, aws_region, aws_permissions_check, nr_account_id, force):
    """Uninstall New Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_integration_uninstall_permissions(session)

    uninstall_integration = True

    if not force and nr_account_id:
        uninstall_integration = click.confirm(
            "This will uninstall the New Relic AWS Lambda integration role. "
            "Are you sure you want to proceed?"
        )

    if uninstall_integration and nr_account_id:
        integrations.remove_integration_role(session, nr_account_id)

    if not force:
        click.confirm(
            "This will uninstall the New Relic AWS Lambda log ingestion function and "
            "role. Are you sure you want to proceed?",
            abort=True,
            default=False,
        )

    integrations.remove_log_ingestion_function(session)

    done("Uninstall Complete")


@click.command(name="update")
@add_options(AWS_OPTIONS)
@click.option(
    "--enable-logs/--disable-logs",
    default=False,
    help="Determines if logs are forwarded to New Relic Logging",
    show_default=True,
)
@click.option(
    "--memory-size",
    "-m",
    default=128,
    help="Memory size (in MiB) for the log ingestion function",
    metavar="<size>",
    show_default=True,
    type=click.INT,
)
@add_options(NR_OPTIONS)
@click.option(
    "--timeout",
    "-t",
    default=30,
    help="Timeout (in seconds) for the New Relic log ingestion function",
    metavar="<secs>",
    show_default=True,
    type=click.INT,
)
def update(
    aws_profile,
    aws_region,
    aws_permissions_check,
    enable_logs,
    memory_size,
    nr_account_id,
    nr_api_key,
    nr_region,
    timeout,
):
    """UpdateNew Relic AWS Lambda Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)

    if aws_permissions_check:
        permissions.ensure_integration_install_permissions(session)

    click.echo("Validating New Relic credentials")
    gql_client = api.validate_gql_credentials(nr_account_id, nr_api_key, nr_region)

    click.echo("Retrieving integration license key")
    nr_license_key = api.retrieve_license_key(gql_client)

    update_success = True

    click.echo("Updating newrelic-log-ingestion Lambda function in AWS account")
    res = integrations.update_log_ingestion(
        session, nr_license_key, enable_logs, memory_size, timeout
    )
    update_success = res and update_success

    if update_success:
        done("Update Complete")
    else:
        failure("Update Incomplete. See messages above for details.", exit=True)
