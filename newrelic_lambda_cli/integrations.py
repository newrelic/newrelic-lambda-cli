# -*- coding: utf-8 -*-

import os
import time

import botocore
import click
import json

from newrelic_lambda_cli.api import NewRelicGQL
from newrelic_lambda_cli.cliutils import failure, success
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.types import (
    IntegrationInstall,
    IntegrationUninstall,
    IntegrationUpdate,
)

INGEST_STACK_NAME = "NewRelicLogIngestion"
LICENSE_KEY_STACK_NAME = "NewRelicLicenseKeySecret"

__cached_license_key_policy_arn = None


def list_all_regions(session):
    """Returns all regions where Lambda is currently supported"""
    return session.get_available_regions("lambda")


def _get_role(session, role_name):
    """Returns details about an IAM role"""
    # We only want the role name if an ARN is passed
    if "/" in role_name:
        _, role_name = role_name.rsplit("/", 1)
    try:
        return session.client("iam").get_role(RoleName=role_name)
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        ):
            return None
        raise click.UsageError(str(e))


def _check_for_ingest_stack(session):
    return _get_cf_stack_status(session, INGEST_STACK_NAME)


def _get_cf_stack_status(session, stack_name):
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


# TODO: Merge this with create_integration_role?
def _create_role(input):
    assert isinstance(input, IntegrationInstall)
    client = input.session.client("cloudformation")
    role_policy_name = input.role_name or ""
    stack_name = "NewRelicLambdaIntegrationRole-%d" % input.nr_account_id
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates",
        "nr-lambda-integration-role.yaml",
    )
    with open(template_path) as template:
        client.create_stack(
            StackName=stack_name,
            TemplateBody=template.read(),
            Parameters=[
                {
                    "ParameterKey": "NewRelicAccountNumber",
                    "ParameterValue": str(input.nr_account_id),
                },
                {"ParameterKey": "PolicyName", "ParameterValue": role_policy_name},
            ],
            Capabilities=["CAPABILITY_NAMED_IAM"],
            Tags=[{"Key": key, "Value": value} for key, value in input.tags]
            if input.tags
            else [],
        )
        click.echo("Waiting for stack creation to complete...", nl=False)
        client.get_waiter("stack_create_complete").wait(StackName=stack_name)
        click.echo("Done")


def _get_sar_template_url(session):
    sar_client = session.client("serverlessrepo")
    sar_app_id = "arn:aws:serverlessrepo:us-east-1:463657938898:applications/NewRelic-log-ingestion"  # noqa
    template_details = sar_client.create_cloud_formation_template(
        ApplicationId=sar_app_id
    )
    return template_details["TemplateUrl"]


def _create_log_ingest_parameters(input, nr_license_key, mode="CREATE"):
    assert isinstance(input, (IntegrationInstall, IntegrationUpdate))
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

    if input.enable_logs is not None:
        parameters.append(
            {
                "ParameterKey": "NRLoggingEnabled",
                "ParameterValue": "True" if input.enable_logs else "False",
            }
        )
    elif update_mode:
        parameters.append(
            {"ParameterKey": "NRLoggingEnabled", "UsePreviousValue": True}
        )

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


def _import_log_ingestion_function(
    session, nr_license_key, enable_logs, memory_size, timeout, role_name, tags
):
    parameters, capabilities = _create_log_ingest_parameters(
        nr_license_key, enable_logs, memory_size, timeout, role_name, "IMPORT"
    )
    cf_client = session.client("cloudformation")

    click.echo("Fetching new CloudFormation template url")

    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "templates", "import-template.yaml"
    )
    with open(template_path) as template:
        change_set_name = "%s-IMPORT-%d" % (INGEST_STACK_NAME, int(time.time()))
        click.echo("Creating change set: %s" % change_set_name)

        change_set = cf_client.create_change_set(
            StackName=INGEST_STACK_NAME,
            TemplateBody=template.read(),
            Parameters=parameters,
            Capabilities=capabilities,
            Tags=[{"Key": key, "Value": value} for key, value in tags] if tags else [],
            ChangeSetType="IMPORT",
            ChangeSetName=change_set_name,
            ResourcesToImport=[
                {
                    "ResourceType": "AWS::Lambda::Function",
                    "LogicalResourceId": "NewRelicLogIngestionFunctionNoCap",
                    "ResourceIdentifier": {"FunctionName": "newrelic-log-ingestion"},
                }
            ],
        )

        _exec_change_set(cf_client, change_set, "IMPORT")


def _create_log_ingestion_function(
    input,
    nr_license_key,
    mode="CREATE",
):
    assert isinstance(input, (IntegrationInstall, IntegrationUpdate))

    parameters, capabilities = _create_log_ingest_parameters(
        input, nr_license_key, mode
    )

    client = input.session.client("cloudformation")

    click.echo("Fetching new CloudFormation template url")
    template_url = _get_sar_template_url(input.session)

    change_set_name = "%s-%s-%d" % (INGEST_STACK_NAME, mode, int(time.time()))
    click.echo("Creating change set: %s" % change_set_name)

    change_set = client.create_change_set(
        StackName=INGEST_STACK_NAME,
        TemplateURL=template_url,
        Parameters=parameters,
        Capabilities=capabilities,
        Tags=[{"Key": key, "Value": value} for key, value in input.tags]
        if input.tags
        else [],
        ChangeSetType=mode,
        ChangeSetName=change_set_name,
    )

    _exec_change_set(client, change_set, mode)


def _exec_change_set(client, change_set, mode, stack_name=INGEST_STACK_NAME):
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
        raise e
    client.execute_change_set(ChangeSetName=change_set["Id"])
    click.echo(
        "Waiting for change set to finish execution. This may take a minute... ",
        nl=False,
    )
    exec_waiter_type = "stack_%s_complete" % mode.lower()
    client.get_waiter(exec_waiter_type).wait(
        StackName=stack_name, WaiterConfig={"Delay": 15}
    )
    success("Done")


def update_log_ingestion_function(input):
    assert isinstance(input, IntegrationUpdate)

    # Detect an old-style nested install and unwrap it
    client = input.session.client("cloudformation")
    resources = client.describe_stack_resources(
        StackName=INGEST_STACK_NAME, LogicalResourceId="NewRelicLogIngestion"
    )
    stack_resources = resources["StackResources"]

    # The nested installs had a single Application resource
    if (
        len(stack_resources) > 0
        and stack_resources[0]["ResourceType"] == "AWS::CloudFormation::Stack"
    ):
        click.echo("Unwrapping nested stack")

        # Set the ingest function itself to disallow deletes
        nested_stack = stack_resources[0]
        template_response = client.get_template(
            StackName=nested_stack["PhysicalResourceId"], TemplateStage="Processed"
        )
        template_body = template_response["TemplateBody"]
        template_body["Resources"]["NewRelicLogIngestionFunction"][
            "DeletionPolicy"
        ] = "Retain"
        template_body["Resources"]["NewRelicLogIngestionFunctionRole"][
            "DeletionPolicy"
        ] = "Retain"

        # We can't change props during import, so let's set them to their current values
        lambda_client = input.session.client("lambda")
        old_props = lambda_client.get_function_configuration(
            FunctionName="newrelic-log-ingestion"
        )
        old_role_name = old_props["Role"].split("/")[-1]
        old_nr_license_key = old_props["Environment"]["Variables"]["LICENSE_KEY"]
        old_enable_logs = False
        if (
            "LOGGING_ENABLED" in old_props["Environment"]["Variables"]
            and old_props["Environment"]["Variables"]["LOGGING_ENABLED"].lower()
            == "true"
        ):
            old_enable_logs = True
        old_memory_size = old_props["MemorySize"]
        old_timeout = old_props["Timeout"]

        # Prepare to orphan the ingest function
        params = [
            {"ParameterKey": name, "UsePreviousValue": True}
            for name in template_body["Parameters"]
        ]
        client.update_stack(
            StackName=nested_stack["PhysicalResourceId"],
            TemplateBody=json.dumps(template_body),
            Parameters=params,
            Capabilities=["CAPABILITY_IAM"],
            Tags=[{"Key": key, "Value": value} for key, value in input.tags]
            if input.tags
            else [],
        )
        client.get_waiter("stack_update_complete").wait(
            StackName=nested_stack["PhysicalResourceId"]
        )

        click.echo("Removing outer stack")
        # Delete the parent stack, which will delete its child and orphan the
        # ingest function
        client.delete_stack(StackName=INGEST_STACK_NAME)
        client.get_waiter("stack_delete_complete").wait(StackName=INGEST_STACK_NAME)

        click.echo("Starting import")
        _import_log_ingestion_function(
            input.session,
            old_nr_license_key,
            old_enable_logs,
            old_memory_size,
            old_timeout,
            role_name=old_role_name,
            tags=input.tags,
        )
        # Now that we've unnested, do the actual update

    # Not a nested install; just update
    _create_log_ingestion_function(
        input,
        nr_license_key=None,
        mode="UPDATE",
    )


def remove_log_ingestion_function(input):
    assert isinstance(input, IntegrationUninstall)

    client = input.session.client("cloudformation")
    stack_status = _check_for_ingest_stack(input.session)
    if stack_status is None:
        click.echo(
            "No New Relic AWS Lambda log ingestion found in region %s, skipping"
            % input.session.region_name
        )
        return
    click.echo("Deleting New Relic log ingestion stack '%s'" % INGEST_STACK_NAME)
    client.delete_stack(StackName=INGEST_STACK_NAME)
    click.echo(
        "Waiting for stack deletion to complete, this may take a minute... ", nl=False
    )
    client.get_waiter("stack_delete_complete").wait(StackName=INGEST_STACK_NAME)
    success("Done")


def create_integration_role(input):
    """
    Creates a AWS CloudFormation stack that adds the New Relic AWSLambda Integration
    IAM role. This can be overridden with the `role_arn` parameter, which just checks
    that the role exists.
    """
    assert isinstance(input, IntegrationInstall)
    if input.integration_arn is not None:
        role = _get_role(input.session, input.integration_arn)
        if role:
            success(
                "Found existing AWS IAM role '%s', using it with the New Relic Lambda "
                "integration" % input.integration_arn
            )
            return role
        failure(
            "Could not find AWS IAM role '%s', please verify it exists and run this "
            "command again" % input.integration_arn
        )
        return

    role_name = "NewRelicLambdaIntegrationRole_%s" % input.nr_account_id
    stack_name = "NewRelicLambdaIntegrationRole-%s" % input.nr_account_id
    role = _get_role(input.session, role_name)
    if role:
        success("New Relic AWS Lambda integration role '%s' already exists" % role_name)
        return role
    stack_status = _get_cf_stack_status(input.session, stack_name)
    if stack_status is None:
        _create_role(input)
        role = _get_role(input.session, role_name)
        success(
            "Created role [%s] with policy [%s] in AWS account."
            % (role_name, input.role_policy)
        )
        return role
    failure(
        "Cannot create CloudFormation stack %s because it exists in state %s"
        % (stack_name, stack_status)
    )


def remove_integration_role(input):
    """
    Removes the AWS CloudFormation stack that includes the New Relic AWS Integration
    IAM role.
    """
    assert isinstance(input, IntegrationUninstall)
    client = input.session.client("cloudformation")
    stack_name = "NewRelicLambdaIntegrationRole-%s" % input.nr_account_id
    stack_status = _get_cf_stack_status(input.session, stack_name)
    if stack_status is None:
        click.echo("No New Relic AWS Lambda Integration found, skipping")
        return
    click.echo("Deleting New Relic AWS Lambda Integration stack '%s'" % stack_name)
    client.delete_stack(StackName=stack_name)
    click.echo(
        "Waiting for stack deletion to complete, this may take a minute... ", nl=False
    )
    client.get_waiter("stack_delete_complete").wait(StackName=stack_name)
    success("Done")


def validate_linked_account(gql, input):
    """
    Ensure that the aws account associated with the 'provider account',
    if it exists, is the same as the aws account of the default aws-cli
    profile configured in the local machine.
    """
    assert isinstance(gql, NewRelicGQL)
    assert isinstance(input, IntegrationInstall)

    account = gql.get_linked_account_by_name(input.linked_account_name)
    if account is not None:
        aws_account_id = get_aws_account_id(input.session)
        if aws_account_id != account["externalId"]:
            raise click.UsageError(
                "The selected linked AWS account [%s] does not match "
                "the AWS account of your AWS profile [%s]."
                % (account["externalId"], aws_account_id)
            )


def install_log_ingestion(
    input,
    nr_license_key,
):
    """
    Installs the New Relic AWS Lambda log ingestion function and role.

    Returns True for success and False for failure.
    """
    assert isinstance(input, IntegrationInstall)
    function = get_function(input.session, "newrelic-log-ingestion")
    if function is None:
        stack_status = _check_for_ingest_stack(input.session)
        if stack_status is None:
            click.echo(
                "Setting up 'newrelic-log-ingestion' function in region: %s"
                % input.session.region_name
            )
            try:
                _create_log_ingestion_function(
                    input,
                    nr_license_key,
                )
            except Exception as e:
                failure("Failed to create 'newrelic-log-ingestion' function: %s" % e)
                return False
        else:
            failure(
                "CloudFormation Stack NewRelicLogIngestion exists (status: %s), but "
                "newrelic-log-ingestion Lambda function does not.\n"
                "Please manually delete the stack and re-run this command."
                % stack_status
            )
            return False
    else:
        success(
            "The 'newrelic-log-ingestion' function already exists in region %s, "
            "skipping" % input.session.region_name
        )
    return True


def update_log_ingestion(input):
    """
    Updates the New Relic AWS Lambda log ingestion function and role.

    Returns True for success and False for failure.
    """
    assert isinstance(input, IntegrationUpdate)

    function = get_function(input.session, "newrelic-log-ingestion")
    if function is None:
        failure(
            "No 'newrelic-log-ingestion' function in region '%s'. "
            "Run 'newrelic-lambda integrations install' to install it."
            % input.session.region_name
        )
        return False
    stack_status = _check_for_ingest_stack(input.session)
    if stack_status is None:
        failure(
            "No 'NewRelicLogIngestion' stack in region '%s'. "
            "This likely means the New Relic log ingestion function was "
            "installed manually. "
            "In order to install via the CLI, please delete this function and "
            "run 'newrelic-lambda integrations install'." % input.session.region_name
        )
        return False
    try:
        update_log_ingestion_function(input)
    except Exception as e:
        failure("Failed to update 'newrelic-log-ingestion' function: %s" % e)
        return False
    else:
        return True


def get_log_ingestion_license_key(session):
    """
    Fetches the license key value from the log ingestion function
    """
    function = get_function(session, "newrelic-log-ingestion")
    if function:
        return function["Configuration"]["Environment"]["Variables"]["LICENSE_KEY"]
    return None


def auto_install_license_key(input):
    """
    If the LK secret is missing, create it, picking up the LK value from the ingest
    lambda's configuration.
    """
    assert isinstance(input, (IntegrationInstall, IntegrationUpdate))
    lk_stack_status = _get_cf_stack_status(input.session, LICENSE_KEY_STACK_NAME)
    if lk_stack_status is None:
        click.echo("Creating the managed secret for the New Relic License Key")
        lk = get_log_ingestion_license_key(input.session)
        if lk is None:
            failure(
                "Could not create license key secret; failed to fetch license key "
                "value from ingest lambda"
            )
            return False
        return install_license_key(input, nr_license_key=lk)
    return True


def install_license_key(input, nr_license_key, policy_name=None, mode="CREATE"):
    assert isinstance(input, (IntegrationInstall, IntegrationUpdate))
    lk_stack_status = _get_cf_stack_status(input.session, LICENSE_KEY_STACK_NAME)
    if lk_stack_status is None:
        click.echo(
            "Setting up %s stack in region: %s"
            % (LICENSE_KEY_STACK_NAME, input.session.region_name)
        )
        try:
            client = input.session.client("cloudformation")

            update_mode = mode == "UPDATE"
            parameters = []
            if policy_name is not None:
                parameters.append(
                    {"ParameterKey": "PolicyName", "ParameterValue": policy_name}
                )
            elif update_mode:
                parameters.append(
                    {"ParameterKey": "PolicyName", "UsePreviousValue": True}
                )

            parameters.append(
                {"ParameterKey": "LicenseKey", "ParameterValue": nr_license_key}
            )

            change_set_name = "%s-%s-%d" % (
                LICENSE_KEY_STACK_NAME,
                mode,
                int(time.time()),
            )
            click.echo("Creating change set: %s" % change_set_name)
            template_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "templates",
                "license-key-secret.yaml",
            )

            with open(template_path) as template:
                change_set = client.create_change_set(
                    StackName=LICENSE_KEY_STACK_NAME,
                    TemplateBody=template.read(),
                    Parameters=parameters,
                    Capabilities=["CAPABILITY_NAMED_IAM"],
                    Tags=[{"Key": key, "Value": value} for key, value in input.tags]
                    if input.tags
                    else [],
                    ChangeSetType=mode,
                    ChangeSetName=change_set_name,
                )

                _exec_change_set(
                    client, change_set, mode, stack_name=LICENSE_KEY_STACK_NAME
                )
        except Exception as e:
            failure("Failed to create %s stack: %s" % (LICENSE_KEY_STACK_NAME, e))
            return False
    return True


def remove_license_key(input):
    assert isinstance(input, (IntegrationUninstall, IntegrationUpdate))
    client = input.session.client("cloudformation")
    stack_status = _get_cf_stack_status(input.session, LICENSE_KEY_STACK_NAME)
    if stack_status is None:
        click.echo(
            "No New Relic license key secret found in region %s, skipping"
            % input.session.region_name
        )
        return
    click.echo("Deleting stack '%s'" % LICENSE_KEY_STACK_NAME)
    client.delete_stack(StackName=LICENSE_KEY_STACK_NAME)
    click.echo(
        "Waiting for stack deletion to complete, this may take a minute... ", nl=False
    )
    client.get_waiter("stack_delete_complete").wait(StackName=LICENSE_KEY_STACK_NAME)
    success("Done")


def _get_license_key_policy_arn(session):
    """Returns the policy ARN for the license key secret if it exists"""
    global __cached_license_key_policy_arn
    if __cached_license_key_policy_arn:
        return __cached_license_key_policy_arn
    client = session.client("cloudformation")
    try:
        stacks = client.describe_stacks(StackName=LICENSE_KEY_STACK_NAME).get(
            "Stacks", []
        )
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] in (400, 404)
        ):
            return None
        raise e
    else:
        if not stacks:
            return None
        stack = stacks[0]
        output_key = "ViewPolicyARN"
        for output in stack.get("Outputs", []):
            if output["OutputKey"] == output_key:
                __cached_license_key_policy_arn = output["OutputValue"]
                return __cached_license_key_policy_arn
        else:
            return None


def get_aws_account_id(session):
    return session.client("sts").get_caller_identity().get("Account")
