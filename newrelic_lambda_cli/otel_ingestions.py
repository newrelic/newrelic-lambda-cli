# -*- coding: utf-8 -*-

import json
import os
import time

import botocore
import click
import json

from newrelic_lambda_cli.cliutils import failure, success, warning
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.types import (
    OtelIngestionInstall,
    OtelIngestionUninstall,
    OtelIngestionUpdate,
)
from newrelic_lambda_cli.utils import catch_boto_errors, NR_DOCS_ACT_LINKING_URL

INGEST_OTEL_STACK_NAME = "NewRelicOtelLogIngestion"


def _check_for_ingest_stack(session, stack_name):
    return _get_cf_stack_status(session, stack_name)


def _get_cf_stack_status(session, stack_name, nr_account_id=None):
    """Returns the status of the CloudFormation stack if it exists"""
    print(
        "_get_cf_stack_status: Returns the status of the CloudFormation stack if it exists"
    )
    try:
        res = session.client("cloudformation").describe_stacks(StackName=stack_name)
        print("res", res)
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
        stackname = INGEST_OTEL_STACK_NAME
    stack_id = _get_otel_cf_stack_id(session, stack_name=stackname)
    if stack_id:
        return "newrelic-aws-otel-log-ingestion-%s" % (
            stack_id.split("/")[2].split("-")[4]
        )


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
    sar_app_id = "arn:aws:serverlessrepo:us-west-2:466768951184:applications/newrelic-aws-otel-log-ingestion"  # noqa
    template_details = sar_client.create_cloud_formation_template(
        ApplicationId=sar_app_id
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


def _import_log_ingestion_function(input, nr_license_key):
    assert isinstance(input, OtelIngestionUpdate)

    parameters, capabilities = _create_otel_log_ingest_parameters(
        input, nr_license_key, "IMPORT"
    )
    client = input.session.client("cloudformation")

    click.echo("Fetching new CloudFormation template url")

    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates", "import-template.yaml"
    )

    with open(template_path) as template:
        unique_log_ingestion_name = get_unique_newrelic_otel_log_ingestion_name(
            input.session
        )
        if unique_log_ingestion_name:
            change_set_name = "%s-IMPORT-%d" % (
                INGEST_OTEL_STACK_NAME,
                int(time.time()),
            )
            click.echo("Creating change set: %s" % change_set_name)

            change_set = client.create_change_set(
                StackName=INGEST_OTEL_STACK_NAME,
                TemplateBody=template.read(),
                Parameters=parameters,
                Capabilities=capabilities,
                Tags=(
                    [{"Key": key, "Value": value} for key, value in input.tags]
                    if input.tags
                    else []
                ),
                ChangeSetType="IMPORT",
                ChangeSetName=change_set_name,
                ResourcesToImport=[
                    {
                        "ResourceType": "AWS::Lambda::Function",
                        "LogicalResourceId": "NewRelicLogIngestionFunctionNoCap",
                        "ResourceIdentifier": {
                            "FunctionName": unique_log_ingestion_name
                        },
                    }
                ],
            )

            _exec_change_set(client, change_set, "IMPORT")


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
    click.echo("Fetched template_url")
    print("template_url", template_url)
    change_set_name = "%s-%s-%d" % (input.stackname, mode, int(time.time()))
    click.echo("Creating change set: %s" % change_set_name)
    print(
        input.stackname, template_url, parameters, capabilities, change_set_name, mode
    )
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
    print("change set created....")
    _exec_change_set(client, change_set, mode, input.stackname)


def _exec_change_set(client, change_set, mode, stack_name):
    click.echo(
        "Waiting for change set creation to complete, this may take a minute... ",
        nl=False,
    )

    try:
        client.get_waiter("change_set_create_complete").wait(
            ChangeSetName=change_set["Id"], WaiterConfig={"Delay": 10}
        )
    except botocore.exceptions.WaiterError as e:
        response = e.last_response
        status = response["Status"]
        reason = response["StatusReason"]
        if (
            status == "FAILED"
            and "The submitted information didn't contain changes." in reason
            or "No updates are to be performed" in reason
        ):
            success("No Changes Detected")
            return
        else:
            failure(reason)
            return
    client.execute_change_set(ChangeSetName=change_set["Id"])
    click.echo(
        "Waiting for change set to finish execution. This may take a minute... ",
        nl=False,
    )

    exec_waiter_type = "stack_%s_complete" % mode.lower()

    try:
        client.get_waiter(exec_waiter_type).wait(
            StackName=stack_name, WaiterConfig={"Delay": 15}
        )
    except botocore.exceptions.WaiterError as e:
        failure(e.last_response["Status"]["StatusReason"])
    else:
        success("Done")


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
def remove_otel_log_ingestion_function(input):
    assert isinstance(input, OtelIngestionUninstall)

    client = input.session.client("cloudformation")
    stack_status = _check_for_ingest_stack(input.session, input.stackname)
    if stack_status is None:
        click.echo(
            "No New Relic AWS Lambda otel log ingestion found in region %s, skipping"
            % input.session.region_name
        )
        return
    click.echo("Deleting New Relic otel log ingestion stack '%s'" % input.stackname)
    client.delete_stack(StackName=input.stackname)
    click.echo(
        "Waiting for stack deletion to complete, this may take a minute... ", nl=False
    )
    client.get_waiter("stack_delete_complete").wait(StackName=input.stackname)
    success("Done")


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
    function = get_function(input.session, "newrelic-otel-log-ingestion")
    print("function", function)
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
                "CloudFormation Stack NewRelicOtelLogIngestion exists (status: %s).\n"
                "Please manually delete the stack and re-run this command."
                % stack_status
            )
            return False
    else:
        function = get_newrelic_otel_log_ingestion_function(input.session)

        if function is None:
            failure(
                "CloudFormation Stack NewRelicOtelLogIngestion exists (status: %s), but "
                "newrelic-otel-log-ingestion Lambda function does not.\n"
                "Please manually delete the stack and re-run this command."
                % stack_status
            )
            return False
        else:
            success(
                "The CloudFormation Stack NewRelicOtelLogIngestion and "
                "newrelic-log-ingestion function already exists in region %s, "
                "skipping" % input.session.region_name
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
            "No 'NewRelicOtelLogIngestion' stack in region '%s'. "
            "This likely means the New Relic log ingestion function was "
            "installed manually. "
            "In order to install via the CLI, please delete this function and "
            "run 'newrelic-lambda otel-ingestion install'." % input.session.region_name
        )
        return False

    function = get_newrelic_otel_log_ingestion_function(input.session, input.stackname)
    if function is None:
        failure(
            "No newrelic-otel-log-ingestion function in region '%s'. "
            "Run 'newrelic-lambda otel-ingestion install' to install it."
            % input.session.region_name
        )
        return False

    try:
        update_otel_log_ingestion_function(input)
    except Exception as e:
        failure("Failed to update newrelic-log-ingestion function: %s" % e)
        return False
    else:
        return True
