# -*- coding: utf-8 -*-

import json
import os
import time

import botocore
import click
import json

from newrelic_lambda_cli.cliutils import failure, success, warning
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.integrations import _exec_change_set
from newrelic_lambda_cli.types import (
    OtelIngestionInstall,
    OtelIngestionUpdate,
)
from newrelic_lambda_cli.utils import catch_boto_errors, NR_DOCS_ACT_LINKING_URL

OTEL_INGEST_STACK_NAME = "NewRelicOtelLogIngestion"
OTEL_INGEST_LAMBDA_NAME = "newrelic-aws-otel-log-ingestion"
OTEL_SAR_APP_ID = (
    "arn:aws:serverlessrepo:us-east-1:451483290750:applications/"
    + OTEL_INGEST_LAMBDA_NAME
)


def _check_for_ingest_stack(session, stack_name):
    return _get_cf_stack_status(session, stack_name)


def _get_cf_stack_status(session, stack_name, nr_account_id=None):
    """Returns the status of the CloudFormation stack if it exists"""
    try:
        res = session.client("cloudformation").describe_stacks(StackName=stack_name)
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] in (400, 404)
        ):
            return None
        raise click.UsageError(str(e))
    else:
        return res["Stacks"][0]["StackStatus"]


def get_unique_newrelic_otel_log_ingestion_name(session, stackname=None):
    if not stackname:
        stackname = OTEL_INGEST_STACK_NAME
    stack_id = _get_otel_cf_stack_id(session, stack_name=stackname)
    if stack_id:
        return "%s-%s" % (OTEL_INGEST_LAMBDA_NAME, stack_id.split("/")[2].split("-")[4])


def get_newrelic_otel_log_ingestion_function(session, stackname=None):
    unique_log_ingestion_name = get_unique_newrelic_otel_log_ingestion_name(
        session, stackname
    )
    if unique_log_ingestion_name:
        function = get_function(session, unique_log_ingestion_name)
        return function


def _get_otel_cf_stack_id(session, stack_name, nr_account_id=None):
    """Returns the StackId of the CloudFormation stack if it exists"""
    try:
        res = session.client("cloudformation").describe_stacks(StackName=stack_name)
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] in (400, 404)
        ):
            return None
        raise click.UsageError(str(e))
    else:
        return res["Stacks"][0]["StackId"]


def _get_otel_sar_template_url(session):
    sar_client = session.client("serverlessrepo")
    template_details = sar_client.create_cloud_formation_template(
        ApplicationId=OTEL_SAR_APP_ID
    )
    return template_details["TemplateUrl"]


def _create_otel_log_ingest_parameters(input, nr_license_key, mode="CREATE"):
    assert isinstance(input, (OtelIngestionInstall, OtelIngestionUpdate))

    update_mode = mode == "UPDATE"
    parameters = []

    if input.memory_size is not None:
        parameters.append(
            {"ParameterKey": "MemorySize", "ParameterValue": str(input.memory_size)}
        )
    elif update_mode:
        parameters.append({"ParameterKey": "MemorySize", "UsePreviousValue": True})

    if nr_license_key is not None:
        parameters.append(
            {"ParameterKey": "NRLicenseKey", "ParameterValue": nr_license_key}
        )
    elif update_mode:
        parameters.append({"ParameterKey": "NRLicenseKey", "UsePreviousValue": True})

    if input.timeout is not None:
        parameters.append(
            {"ParameterKey": "Timeout", "ParameterValue": str(input.timeout)}
        )
    elif update_mode:
        parameters.append({"ParameterKey": "Timeout", "UsePreviousValue": True})

    capabilities = ["CAPABILITY_IAM"]
    if input.role_name is not None:
        parameters.append(
            {"ParameterKey": "FunctionRole", "ParameterValue": input.role_name}
        )
        capabilities = []
    elif mode != "CREATE":
        parameters.append({"ParameterKey": "FunctionRole", "UsePreviousValue": True})
        capabilities = []

    return parameters, capabilities


def _create_otel_log_ingestion_function(
    input,
    nr_license_key,
    mode="CREATE",
):
    assert isinstance(input, (OtelIngestionInstall, OtelIngestionUpdate))

    parameters, capabilities = _create_otel_log_ingest_parameters(
        input, nr_license_key, mode
    )

    client = input.session.client("cloudformation")

    click.echo("Fetching new CloudFormation template url for OTEL log ingestion")
    template_url = _get_otel_sar_template_url(input.session)
    change_set_name = "%s-%s-%d" % (input.stackname, mode, int(time.time()))
    click.echo("Creating change set: %s" % change_set_name)
    try:
        change_set = client.create_change_set(
            StackName=input.stackname,
            TemplateURL=template_url,
            Parameters=parameters,
            Capabilities=capabilities,
            Tags=(
                [{"Key": key, "Value": value} for key, value in input.tags]
                if input.tags
                else []
            ),
            ChangeSetType=mode,
            ChangeSetName=change_set_name,
        )
    except Exception as e:
        print(f"Error: {e}")
    _exec_change_set(client, change_set, mode, input.stackname)


@catch_boto_errors
def update_otel_log_ingestion_function(input):
    assert isinstance(input, OtelIngestionUpdate)

    client = input.session.client("cloudformation")

    _create_otel_log_ingestion_function(
        input,
        nr_license_key=None,
        mode="UPDATE",
    )


@catch_boto_errors
def install_otel_log_ingestion(
    input,
    nr_license_key,
):
    """
    Installs the New Relic AWS Lambda log ingestion function and role.

    Returns True for success and False for failure.
    """
    assert isinstance(input, OtelIngestionInstall)
    function = get_function(input.session, OTEL_INGEST_LAMBDA_NAME)
    if function:
        warning(
            "It looks like an old log ingestion function is present in this region. "
            "Consider manually deleting this as it is no longer used and "
            "has been replaced by a log ingestion function specific to the stack."
        )
    stack_status = _check_for_ingest_stack(input.session, input.stackname)
    if stack_status is None:
        click.echo(
            "Setting up CloudFormation Stack %s in region: %s"
            % (input.stackname, input.session.region_name)
        )
        try:
            _create_otel_log_ingestion_function(
                input,
                nr_license_key,
            )
            return True
        except Exception as e:
            failure(
                "CloudFormation Stack %s exists (status: %s).\n"
                "Please manually delete the stack and re-run this command."
                % (input.stackname, stack_status)
            )
            return False
    else:
        function = get_newrelic_otel_log_ingestion_function(
            input.session, input.stackname
        )

        if function is None:
            failure(
                "CloudFormation Stack %s exists (status: %s), but "
                "%s Lambda function does not.\n"
                "Please manually delete the stack and re-run this command."
                % (input.stackname, stack_status, OTEL_INGEST_LAMBDA_NAME)
            )
            return False
        else:
            success(
                "The CloudFormation Stack %s and "
                "%s function already exists in region %s, "
                "skipping"
                % (input.stackname, OTEL_INGEST_LAMBDA_NAME, input.session.region_name)
            )
            return True


@catch_boto_errors
def update_otel_log_ingestion(input):
    """
    Updates the New Relic AWS Lambda log ingestion function and role.

    Returns True for success and False for failure.
    """
    assert isinstance(input, OtelIngestionUpdate)

    stack_status = _check_for_ingest_stack(input.session, input.stackname)
    if stack_status is None:
        failure(
            "No '%s' stack in region '%s'. "
            "This likely means the New Relic otel log ingestion function was "
            "installed manually. "
            "In order to install via the CLI, please delete this function and "
            "run 'newrelic-lambda otel-ingestion install'."
            % (OTEL_INGEST_STACK_NAME, input.session.region_name)
        )
        return False

    function = get_newrelic_otel_log_ingestion_function(input.session, input.stackname)
    if function is None:
        failure(
            "No %s function in region '%s'. "
            "Run 'newrelic-lambda otel-ingestion install' to install it."
            % (OTEL_INGEST_LAMBDA_NAME, input.session.region_name)
        )
        return False

    try:
        update_otel_log_ingestion_function(input)
    except Exception as e:
        failure("Failed to update newrelic-log-ingestion function: %s" % e)
        return False
    else:
        return True
