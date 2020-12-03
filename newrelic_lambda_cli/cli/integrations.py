# -*- coding: utf-8 -*-

import boto3
import click

from newrelic_lambda_cli import api, integrations, permissions
from newrelic_lambda_cli.types import (
    IntegrationInstall,
    IntegrationUninstall,
    IntegrationUpdate,
)
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
    required=False,
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
@click.option(
    "--role-name",
    default=None,
    help="The name of a pre-created execution role for the log ingest function",
    metavar="<role_name>",
    show_default=False,
)
@click.option(
    "--enable-license-key-secret/--disable-license-key-secret",
    default=True,
    show_default=True,
    help="Enable/disable the license key managed secret",
)
@click.option(
    "--integration-arn",
    default=None,
    help="The ARN of a pre-existing AWS IAM role for the New Relic Lambda integration",
    metavar="<role_arn>",
    show_default=False,
)
@click.option(
    "--tag",
    "tags",
    default=[],
    help="A tag to be added to the CloudFormation Stack (can be used multiple times)",
    metavar="<key> <value>",
    multiple=True,
    nargs=2,
)
@click.pass_context
def install(ctx, **kwargs):
    """Install New Relic AWS Lambda Integration"""
    input = IntegrationInstall(session=None, verbose=ctx.obj["VERBOSE"], **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if not input.linked_account_name:
        input = input._replace(
            linked_account_name=(
                "New Relic Lambda Integration - %s"
                % integrations.get_aws_account_id(input.session)
            )
        )

    if input.aws_permissions_check:
        permissions.ensure_integration_install_permissions(input)

    click.echo("Validating New Relic credentials")
    gql_client = api.validate_gql_credentials(input)

    click.echo("Retrieving integration license key")
    nr_license_key = api.retrieve_license_key(gql_client)

    click.echo("Checking for a pre-existing link between New Relic and AWS")
    integrations.validate_linked_account(gql_client, input)

    install_success = True

    click.echo("Creating the AWS role for the New Relic AWS Lambda Integration")
    role = integrations.create_integration_role(input)
    install_success = install_success and role

    if role:
        click.echo("Linking New Relic account to AWS account")
        res = api.create_integration_account(gql_client, input, role)
        install_success = res and install_success

        click.echo("Enabling Lambda integration on the link between New Relic and AWS")
        res = api.enable_lambda_integration(gql_client, input)
        install_success = res and install_success

    if input.enable_license_key_secret:
        click.echo("Creating the managed secret for the New Relic License Key")
        res = integrations.install_license_key(input, nr_license_key)
        install_success = install_success and res

    click.echo("Creating newrelic-log-ingestion Lambda function in AWS account")
    res = integrations.install_log_ingestion(input, nr_license_key)
    install_success = res and install_success

    if install_success:
        done("Install Complete")

        if input.verbose:
            click.echo(
                "\nNext steps: Add the New Relic layers to your Lambda functions with "
                "the below command.\n"
            )
            command = [
                "$",
                "newrelic-lambda",
                "layers",
                "install",
                "--function",
                "all",
                "--nr-account-id",
                input.nr_account_id,
            ]
            if input.aws_profile:
                command.append("--aws-profile %s" % input.aws_profile)
            if input.aws_region:
                command.append("--aws-region %s" % input.aws_region)
            click.echo(" ".join(command))
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
def uninstall(**kwargs):
    """Uninstall New Relic AWS Lambda Integration"""
    input = IntegrationUninstall(session=None, **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if input.aws_permissions_check:
        permissions.ensure_integration_uninstall_permissions(input)

    uninstall_integration = True

    if not input.force and input.nr_account_id:
        uninstall_integration = click.confirm(
            "This will uninstall the New Relic AWS Lambda integration role. "
            "Are you sure you want to proceed?"
        )

    if uninstall_integration and input.nr_account_id:
        integrations.remove_integration_role(input)

    if not input.force:
        click.confirm(
            "This will uninstall the New Relic AWS Lambda log ingestion function and "
            "role. Are you sure you want to proceed?",
            abort=True,
            default=False,
        )

    integrations.remove_log_ingestion_function(input)

    if not input.force:
        click.confirm(
            "This will uninstall the New Relic License Key managed secret, and IAM "
            "Policy. "
            "Are you sure you want to proceed?",
            abort=True,
            default=False,
        )
    integrations.remove_license_key(input)

    done("Uninstall Complete")


@click.command(name="update")
@add_options(AWS_OPTIONS)
@click.option(
    "--enable-logs/--disable-logs",
    default=None,
    help="Determines if logs are forwarded to New Relic Logging",
)
@click.option(
    "--memory-size",
    "-m",
    help="Memory size (in MiB) for the log ingestion function",
    metavar="<size>",
    type=click.INT,
)
@click.option(
    "--timeout",
    "-t",
    help="Timeout (in seconds) for the New Relic log ingestion function",
    metavar="<secs>",
    type=click.INT,
)
@click.option(
    "--role-name",
    default=None,
    help="The name of a new pre-created execution role for the log ingest function",
    metavar="<role_name>",
    show_default=False,
)
@click.option(
    "--enable-license-key-secret/--disable-license-key-secret",
    default=True,
    show_default=True,
    help="Enable/disable the license key managed secret",
)
@click.option(
    "--tag",
    "tags",
    default=[],
    help="A tag to be added to the CloudFormation Stack (can be used multiple times)",
    metavar="<key> <value>",
    multiple=True,
    nargs=2,
)
def update(**kwargs):
    """UpdateNew Relic AWS Lambda Integration"""
    input = IntegrationUpdate(session=None, **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if input.aws_permissions_check:
        permissions.ensure_integration_install_permissions(input)

    update_success = True

    click.echo("Updating newrelic-log-ingestion Lambda function in AWS account")
    res = integrations.update_log_ingestion(input)
    update_success = res and update_success

    if input.enable_license_key_secret:
        update_success = update_success and integrations.auto_install_license_key(input)
    else:
        integrations.remove_license_key(input)

    if update_success:
        done("Update Complete")
    else:
        failure("Update Incomplete. See messages above for details.", exit=True)
