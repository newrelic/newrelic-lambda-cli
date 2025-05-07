# -*- coding: utf-8 -*-

import boto3
import click

from newrelic_lambda_cli import api, otel_ingestions, permissions, integrations
from newrelic_lambda_cli.types import (
    OtelIngestionInstall,
    OtelIngestionUninstall,
    OtelIngestionUpdate,
)
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS, NR_OPTIONS
from newrelic_lambda_cli.cliutils import done, failure


@click.group(name="otel-ingestions")
def ingestion_group():
    """Manage New Relic AWS Lambda Otel Log Ingestion lambda"""
    pass


def register(group):
    group.add_command(ingestion_group)
    ingestion_group.add_command(install)
    ingestion_group.add_command(uninstall)
    ingestion_group.add_command(update)


@click.command(name="install")
@add_options(AWS_OPTIONS)
@click.option(
    "--aws-role-policy",
    help="Alternative AWS role policy to use for integration",
    metavar="<arn>",
)
@click.option(
    "--stackname",
    default=otel_ingestions.OTEL_INGEST_STACK_NAME,
    help=f"The AWS Cloudformation stack name which contains the {otel_ingestions.OTEL_INGEST_LAMBDA_NAME} lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
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
@click.option(
    "--role-name",
    default=None,
    help="The name of a pre-created execution role for the log ingest function",
    metavar="<role_name>",
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
    """Install New Relic AWS OTEL Ingestion Lambda"""
    input = OtelIngestionInstall(session=None, verbose=ctx.obj["VERBOSE"], **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if input.aws_permissions_check:
        permissions.ensure_integration_install_permissions(input)

    click.echo("Validating New Relic credentials")
    gql_client = api.validate_gql_credentials(input)

    click.echo("Retrieving integration license key")
    nr_license_key = api.retrieve_license_key(gql_client)

    install_success = True

    click.echo(
        f"Creating {otel_ingestions.OTEL_INGEST_LAMBDA_NAME} Lambda function in AWS account"
    )
    res = otel_ingestions.install_otel_log_ingestion(input, nr_license_key)
    install_success = res and install_success


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
@click.option(
    "--stackname",
    default=otel_ingestions.OTEL_INGEST_STACK_NAME,
    help=f"The AWS Cloudformation stack name which contains the {otel_ingestions.OTEL_INGEST_LAMBDA_NAME} lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
)
@click.option("--force", "-f", help="Force uninstall non-interactively", is_flag=True)
def uninstall(**kwargs):
    """Uninstall New Relic AWS OTEL Ingestion Lambda"""
    input = OtelIngestionUninstall(session=None, **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if input.aws_permissions_check:
        permissions.ensure_integration_uninstall_permissions(input)

    integrations.remove_log_ingestion_function(input, otel=True)

    done("Uninstall Complete")


@click.command(name="update")
@add_options(AWS_OPTIONS)
@click.option(
    "--stackname",
    default=otel_ingestions.OTEL_INGEST_STACK_NAME,
    help=f"The AWS Cloudformation stack name which contains the {otel_ingestions.OTEL_INGEST_LAMBDA_NAME} lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
)
@click.option(
    "--memory-size",
    "-m",
    help="Memory size (in MiB) for the log ingestion function",
    metavar="<size>",
    type=click.INT,
)
@add_options(NR_OPTIONS)
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
    "--stackname",
    default="NewRelicOtelLogIngestion",
    help="The AWS Cloudformation stack name which contains the newrelic-log-ingestion lambda function",
    metavar="<arn>",
    show_default=False,
    required=False,
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
    """UpdateNew New Relic AWS OTEL Ingestion Lambda"""
    input = OtelIngestionUpdate(session=None, **kwargs)

    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    if input.aws_permissions_check:
        permissions.ensure_integration_install_permissions(input)

    update_success = True

    click.echo(
        f"Updating {otel_ingestions.OTEL_INGEST_LAMBDA_NAME} Lambda function in AWS account"
    )
    res = otel_ingestions.update_otel_log_ingestion(input)
    update_success = res and update_success

    if update_success:
        done("Update Complete")
    else:
        failure("Update Incomplete. See messages above for details.", exit=True)
