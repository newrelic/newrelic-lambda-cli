# -*- coding: utf-8 -*-

import boto3
import click

from newrelic_lambda_cli import api, apm, otel_ingestions, permissions, integrations
from newrelic_lambda_cli.types import (
    AlertsMigrate,
)
from newrelic_lambda_cli.cli.decorators import add_options, AWS_OPTIONS, NR_OPTIONS
from newrelic_lambda_cli.cliutils import done, failure


@click.group(name="apm")
def apm_mode_group():
    """Manage New Relic APM Mode of AWS Lambda instrumentation"""
    pass


def register(group):
    group.add_command(apm_mode_group)
    apm_mode_group.add_command(alerts_migrate)


@click.command(name="alerts-migrate")
@click.option(
    "--nr-account-id",
    "-a",
    envvar="NEW_RELIC_ACCOUNT_ID",
    help="New Relic Account ID",
    metavar="<account_id>",
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
    type=click.Choice(["us", "eu", "staging"]),
)
@add_options(AWS_OPTIONS)
@click.option(
    "function",
    "--function",
    "-f",
    help="AWS Lambda function name or ARN",
    metavar="<arn>",
    multiple=False,
    required=True,
)
@click.option(
    "excludes",
    "--exclude",
    "-e",
    help="Functions to exclude (if using 'all, 'installed', 'not-installed aliases)",
    metavar="<name>",
    multiple=True,
)
@click.pass_context
def alerts_migrate(ctx, **kwargs):
    """Migrate New Relic AWS Lambda Alerts to APM mode"""
    input = AlertsMigrate(session=None, verbose=ctx.obj["VERBOSE"], **kwargs)
    input = input._replace(
        session=boto3.Session(
            profile_name=input.aws_profile, region_name=input.aws_region
        )
    )

    # Validate required parameters
    if not input.nr_api_key:
        failure(
            "New Relic API key is required. Provide it via --nr-api-key or NEW_RELIC_API_KEY environment variable.",
            exit=True,
        )

    print("Started migration of alerts")
    if ctx.obj["VERBOSE"]:
        print("Will migrate alerts for {}".format(input.function))
        print(f"Using account ID: {input.nr_account_id}")
        print(f"Using region: {input.nr_region}")

    # setup client
    client = apm.NRGQL_APM(
        account_id=input.nr_account_id,
        api_key=input.nr_api_key,
        region=input.nr_region,
    )

    print(f"Getting entity GUID for function: {input.function}")
    result = client.get_entity_guids_from_entity_name(input.function)
    lambda_entity_guid = ""
    apm_entity_guid = ""
    for entity_type, entity_guid in result.items():
        if entity_type == "AWSLAMBDAFUNCTION":
            lambda_entity_guid = entity_guid
        if entity_type == "APPLICATION":
            apm_entity_guid = entity_guid
    lambda_entity_data = client.get_entity_alert_details(lambda_entity_guid)
    apm_entity_data = client.get_entity_alert_details(apm_entity_guid)
    lambda_entity_selected_alerts = apm.select_lambda_entity_impacted_alerts(
        lambda_entity_data, apm_entity_data
    )
    if lambda_entity_selected_alerts:
        client.create_alert_for_new_entity(
            lambda_entity_selected_alerts, lambda_entity_guid, apm_entity_guid
        )
    else:
        print(
            "No alerts need to be migrated - all eligible alerts have already been migrated."
        )
