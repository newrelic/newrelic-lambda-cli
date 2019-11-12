import os

import botocore
import click


def list_all_regions(session):
    """Returns all regions where Lambda is currently supported"""
    return session.get_available_regions("lambda")


def get_role(session, role_name):
    """Returns details about an IAM role"""
    try:
        return session.client("iam").get_role(RoleName=role_name)
    except botocore.errorfactory.NoSuchEntityException:
        return None


def get_function(session, function_name):
    """Returns details about an AWS lambda function"""
    try:
        return session.client("lambda").get_function(FunctionName=function_name)
    except botocore.errorfactory.ResourceNotFoundException:
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


def get_streaming_filters(session, function_name):
    """Returns all the log subscription filters for the function"""
    log_group_name = "/aws/lambda/%s" % function_name
    try:
        res = session.client("logs").describe_subscription_filters(
            logGroupName=log_group_name
        )
    except botocore.errorfactory.ResourceNotFoundException:
        return []
    else:
        return res.get("SubscriptionFilters", [])


def create_role(session, role_policy, nr_account_id):
    client = session.client("cloudformation")
    role_policy_name = "" if role_policy is None else role_policy
    stack_name = "NewRelicLambdaIntegrationRole-%d" % nr_account_id
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates",
        "nr-integration-role.yaml",
    )
    with open(template_path) as template:
        client.create_stack(
            StackName=stack_name,
            TemplateBody=template.read(),
            Parameters=[
                {
                    "ParameterKey": "NewRelicAccountNumber",
                    "ParameterValue": nr_account_id,
                },
                {"ParameterKey": "PolicyName", "ParameterValue": role_policy_name},
            ],
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )
        client.get_waiter("stack_create_complete").wait(StackName=stack_name)


def create_function(session, nr_license_key):
    client = session.client("cloudformation")
    stack_name = ("NewRelicLogIngestion",)
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
                {"ParameterKey": "NewRelicLicenseKey", "ParamterValue": nr_license_key}
            ],
            Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        )
        client.get_waiter("stack_create_complete").wait(StackName=stack_name)


def add_function_streaming_filter(session, function_name, destination_arn):
    return session.client("logs").put_subscription_filter(
        logGroupName="/aws/lambda/%s" % function_name,
        filterName="NewRelicLogStreaming",
        filterPattern="NR_LAMBDA_MONITORING",
        destinationArn=destination_arn,
    )


def remove_function_streaming_filter(session, function_name):
    return session.client("logs").delete_subscription_filter(
        logGroupName="/aws/lambda/%s" % function_name, filterName="NewRelicLogStreaming"
    )


def create_log_subscription(session, function_name):
    destination = get_function(session, "newrelic-log-ingestion")
    destination_arn = destination["Configuration"]["FunctionArn"]
    streaming_filters = get_streaming_filters(session, function_name)
    if not streaming_filters:
        add_function_streaming_filter(session, function_name, destination_arn)
    else:
        filter = streaming_filters[0]
        if (
            filter["filterName"] == "NewRelicLogStreaming"
            and filter["filterPattern"] == ""
        ):
            remove_function_streaming_filter(session, function_name)
            add_function_streaming_filter(session, function_name, destination_arn)


def create_integration_role(session, role_policy, nr_account_id):
    role_name = "NewRelicLambdaIntegrationRole_%s" % nr_account_id
    stack_name = "NewRelicLambdaIntegrationRole-%s" % nr_account_id
    role = get_role(session, role_name)
    if role is None:
        stack_status = get_cf_stack_status(session, stack_name)
        if stack_status is None:
            create_role(session, role_policy, nr_account_id)
            role = get_role(session, role_name)
            click.echo(
                "Created role [%s] with policy [%s] in AWS account."
                % (role_name, role_policy)
            )
        else:
            raise click.UsageError(
                "Cannot create CloudFormation stack %s because it exists in state %s"
                % (stack_name, stack_status)
            )
    return role


def create_integration_account(gql, nr_account_id, linked_account_name, role):
    role_arn = role["Role"]["Arn"]
    account = gql.get_linked_account_by_name(linked_account_name)
    if account is None:
        account = gql.create_linked_account(role_arn, linked_account_name)
        click.echo(
            "Cloud integrations account [%s] was created in New Relic account [%s]"
            "with role [%s]." % (linked_account_name, nr_account_id, role_arn)
        )
    else:
        click.echo(
            "Cloud integrations account [%s] already exists "
            "in New Relic account [%d]." % (account["name"], nr_account_id)
        )
    return account


def enable_lambda_integration(gql, nr_account_id, linked_account_name):
    account = gql.get_linked_account_by_name(linked_account_name)
    if account is None:
        raise click.UsageError(
            "Could not find Cloud integrations account "
            "[%s] in New Relic account [%d]." % (linked_account_name, nr_account_id)
        )
    is_lambda_enabled = gql.is_integration_enabled(account["id"], "lambda")
    if is_lambda_enabled:
        click.echo(
            "The AWS Lambda integration is already enabled in "
            "Cloud integrations account [%s] of New Relic account [%d]."
            % (linked_account_name, nr_account_id)
        )
    else:
        integration = gql.enable_integration(account["id"], "aws", "lambda")
        click.echo(
            "Integration [id=%s, name=%s] has been enabled in Cloud "
            "integrations account [%s] of New Relic account [%d]."
            % (
                integration["id"],
                integration["name"],
                linked_account_name,
                nr_account_id,
            )
        )


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


def setup_log_ingestion(session, nr_license_key):
    function = get_function(session, "newrelic-log-ingestion")
    if function is None:
        stack_status = check_for_ingest_stack(session)
        if stack_status is None:
            click.echo(
                "Setting up 'newrelic-log-ingestion' function in region: %s"
                % session.region_name
            )
            try:
                create_function(session, nr_license_key)
            except Exception as e:
                raise click.UsageError(
                    "Failed to create 'newrelic-log-ingestion' function: %s" % e
                )
        else:
            raise click.UsageError(
                "CloudFormation Stack NewRelicLogIngestion exists (status: %s), but "
                "newrelic-log-ingestion Lambda function does not.\n"
                "Please manually delete the stack and re-run this command."
                % stack_status
            )
    else:
        click.echo(
            "The 'newrelic-log-ingestion' function already exists in region %s"
            % session.region_name
        )
