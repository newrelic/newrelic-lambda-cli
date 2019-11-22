import os

import botocore
import click

from .cli.cliutils import failure, success


def list_all_regions(session):
    """Returns all regions where Lambda is currently supported"""
    return session.get_available_regions("lambda")


def get_role(session, role_name):
    """Returns details about an IAM role"""
    try:
        return session.client("iam").get_role(RoleName=role_name)
    except botocore.exceptions.ClientError:
        return None


def get_function(session, function_name):
    """Returns details about an AWS lambda function"""
    try:
        return session.client("lambda").get_function(FunctionName=function_name)
    except botocore.exceptions.ClientError:
        return None


def check_for_ingest_stack(session):
    return get_cf_stack_status(session, "NewRelicLogIngestion")


def get_cf_stack_status(session, stack_name):
    """Returns the status of the CloudFormation stack if it exists"""
    try:
        res = session.client("cloudformation").describe_stacks(StackName=stack_name)
    except botocore.exceptions.ClientError:
        return None
    else:
        return res["Stacks"][0]["StackStatus"]


def get_subscription_filters(session, function_name):
    """Returns all the log subscription filters for the function"""
    log_group_name = "/aws/lambda/%s" % function_name
    try:
        res = session.client("logs").describe_subscription_filters(
            logGroupName=log_group_name
        )
    except botocore.exceptions.ClientError:
        return []
    else:
        return res.get("subscriptionFilters", [])


# TODO: Merge this with create_integration_role?
def create_role(session, role_policy, nr_account_id):
    client = session.client("cloudformation")
    role_policy_name = "" if role_policy is None else role_policy
    stack_name = "NewRelicLambdaIntegrationRole-%d" % nr_account_id
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
                    "ParameterValue": str(nr_account_id),
                },
                {"ParameterKey": "PolicyName", "ParameterValue": role_policy_name},
            ],
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )
        click.echo("Waiting for stack creation to complete...", nl=False)
        client.get_waiter("stack_create_complete").wait(StackName=stack_name)
        click.echo("Done")


def create_log_ingestion_function(session, nr_license_key):
    client = session.client("cloudformation")
    stack_name = "NewRelicLogIngestion"
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates",
        "newrelic-log-ingestion.yaml",
    )
    with open(template_path) as template:
        client.create_stack(
            StackName=stack_name,
            TemplateBody=template.read(),
            Parameters=[
                {"ParameterKey": "NewRelicLicenseKey", "ParameterValue": nr_license_key}
            ],
            Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        )
        click.echo(
            "Waiting for stack creation to complete, this may take a minute... ",
            nl=False,
        )
        client.get_waiter("stack_create_complete").wait(StackName=stack_name)
        success("Done")


def remove_log_ingestion_function(session):
    client = session.client("cloudformation")
    stack_name = "NewRelicLogIngestion"
    stack_status = check_for_ingest_stack(session)
    if stack_status is None:
        click.echo(
            "No New Relic AWS Lambda log ingestion found in region %s, skipping"
            % session.region_name
        )
        return
    click.echo("Deleting New Relic log ingestion stack '%s'" % stack_name)
    client.delete_stack(StackName=stack_name)
    click.echo(
        "Waiting for stack deletion to complete, this may take a minute... ", nl=False
    )
    client.get_waiter("stack_delete_complete").wait(StackName=stack_name)
    success("Done")


def create_subscription_filter(session, function_name, destination_arn):
    return session.client("logs").put_subscription_filter(
        logGroupName="/aws/lambda/%s" % function_name,
        filterName="NewRelicLogStreaming",
        filterPattern="NR_LAMBDA_MONITORING",
        destinationArn=destination_arn,
    )


def remove_subscription_filter(session, function_name):
    return session.client("logs").delete_subscription_filter(
        logGroupName="/aws/lambda/%s" % function_name, filterName="NewRelicLogStreaming"
    )


def create_log_subscription(session, function_name):
    destination = get_function(session, "newrelic-log-ingestion")
    if destination is None:
        failure(
            "Could not find 'newrelic-log-ingestion' function. Is the New Relic AWS "
            "integration installed?"
        )
        return
    destination_arn = destination["Configuration"]["FunctionArn"]
    subscription_filters = [
        filter
        for filter in get_subscription_filters(session, function_name)
        if filter["filterName"] == "NewRelicLogStreaming"
    ]
    if not subscription_filters:
        click.echo("Adding New Relic log subscription to '%s'" % function_name)
        create_subscription_filter(session, function_name, destination_arn)
    else:
        click.echo(
            "Found log subscription for '%s', verifying configuration" % function_name
        )
        subscription_filter = subscription_filters[0]
        if subscription_filter["filterPattern"] == "":
            remove_subscription_filter(session, function_name)
            create_subscription_filter(session, function_name, destination_arn)


def remove_log_subscription(session, function_name):
    subscription_filters = [
        filter
        for filter in get_subscription_filters(session, function_name)
        if filter["filterName"] == "NewRelicLogStreaming"
    ]
    if not subscription_filters:
        click.echo(
            "No New Relic subscription filters found for '%s', skipping" % function_name
        )
    else:
        click.echo("Removing New Relic log subscription from '%s'" % function_name)
        remove_subscription_filter(session, function_name)


def create_integration_role(session, role_policy, nr_account_id):
    """
    Creates a AWS CloudFormation stack that adds the New Relic AWSLambda Integration
    IAM role.
   """
    role_name = "NewRelicLambdaIntegrationRole_%s" % nr_account_id
    stack_name = "NewRelicLambdaIntegrationRole-%s" % nr_account_id
    role = get_role(session, role_name)
    if role:
        success("New Relic AWS Lambda integration role '%s' already exists" % role_name)
        return role
    stack_status = get_cf_stack_status(session, stack_name)
    if stack_status is None:
        create_role(session, role_policy, nr_account_id)
        role = get_role(session, role_name)
        success(
            "Created role [%s] with policy [%s] in AWS account."
            % (role_name, role_policy)
        )
        return role
    failure(
        "Cannot create CloudFormation stack %s because it exists in state %s"
        % (stack_name, stack_status)
    )


def remove_integration_role(session, nr_account_id):
    """
    Removes the AWS CloudFormation stack that includes the New Relic AWS Integration
    IAM role.
    """
    client = session.client("cloudformation")
    stack_name = "NewRelicLambdaIntegrationRole-%s" % nr_account_id
    stack_status = get_cf_stack_status(session, stack_name)
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


def validate_linked_account(session, gql, linked_account_name):
    """
    Ensure that the aws account associated with the 'provider account',
    if it exists, is the same as the aws account of the default aws-cli
    profile configured in the local machine.
    """
    account = gql.get_linked_account_by_name(linked_account_name)
    if account is not None:
        res = session.client("sts").get_caller_identity()
        if res["Account"] != account["externalId"]:
            raise click.UsageError(
                "The selected linked AWS account [%s] does not match "
                "the AWS account of your AWS profile [%s]."
                % (account["externalId"], res["Account"])
            )


def install_log_ingestion(session, nr_license_key):
    """
    Installs the New Relic AWS Lambda log ingestion function and role.
    """
    function = get_function(session, "newrelic-log-ingestion")
    if function is None:
        stack_status = check_for_ingest_stack(session)
        if stack_status is None:
            click.echo(
                "Setting up 'newrelic-log-ingestion' function in region: %s"
                % session.region_name
            )
            try:
                create_log_ingestion_function(session, nr_license_key)
            except Exception as e:
                failure("Failed to create 'newrelic-log-ingestion' function: %s" % e)
        else:
            failure(
                "CloudFormation Stack NewRelicLogIngestion exists (status: %s), but "
                "newrelic-log-ingestion Lambda function does not.\n"
                "Please manually delete the stack and re-run this command."
                % stack_status
            )
    else:
        success(
            "The 'newrelic-log-ingestion' function already exists in region %s, "
            "skipping" % session.region_name
        )
