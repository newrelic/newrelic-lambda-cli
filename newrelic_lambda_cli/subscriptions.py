import botocore
import click

from newrelic_lambda_cli.cliutils import failure
from newrelic_lambda_cli.functions import get_function

DEFAULT_FILTER_PATTERN = '?REPORT ?NR_LAMBDA_MONITORING ?"Task timed out" ?RequestId'


def get_log_group_name(function_name):
    """Builds a log group name path; handling ARNs if provided"""
    if ":" in function_name:
        parts = function_name.split(":")
        if len(parts) >= 7:
            return "/aws/lambda/%s" % parts[6]
    return "/aws/lambda/%s" % function_name


def get_subscription_filters(session, function_name):
    """Returns all the log subscription filters for the function"""
    log_group_name = get_log_group_name(function_name)
    try:
        res = session.client("logs").describe_subscription_filters(
            logGroupName=log_group_name
        )
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        ):
            return []
        failure(
            "Error retrieving log subscription filters for '%s': %s"
            % (function_name, e)
        )
    else:
        return res.get("subscriptionFilters", [])


def create_subscription_filter(
    session, function_name, destination_arn, filter_pattern=DEFAULT_FILTER_PATTERN
):
    try:
        session.client("logs").put_subscription_filter(
            logGroupName=get_log_group_name(function_name),
            filterName="NewRelicLogStreaming",
            filterPattern=filter_pattern,
            destinationArn=destination_arn,
        )
    except botocore.exceptions.ClientError as e:
        failure(
            "Error creating log subscription filter for '%s': %s" % (function_name, e)
        )
        return False
    else:
        return True


def remove_subscription_filter(session, function_name):
    try:
        session.client("logs").delete_subscription_filter(
            logGroupName=get_log_group_name(function_name),
            filterName="NewRelicLogStreaming",
        )
    except botocore.exceptions.ClientError as e:
        failure(
            "Error removing log subscription filter for '%s': %s" % (function_name, e)
        )
        return False
    else:
        return True


def create_log_subscription(
    session, function_name, filter_pattern=DEFAULT_FILTER_PATTERN
):
    destination = get_function(session, "newrelic-log-ingestion")
    if destination is None:
        failure(
            "Could not find 'newrelic-log-ingestion' function. Is the New Relic AWS "
            "integration installed?"
        )
        return False
    destination_arn = destination["Configuration"]["FunctionArn"]
    subscription_filters = get_subscription_filters(session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if filter["filterName"] == "NewRelicLogStreaming"
    ]
    if len(subscription_filters) > len(newrelic_filters):
        click.echo(
            "WARNING: Found a log subscription filter that was not installed by New "
            "Relic. This may prevent the New Relic log subscription filter from being "
            "installed. If you know you don't need this log subscription filter, you "
            "should first remove it and rerun this command. If your organization "
            "requires this log subscription filter, please contact New Relic at "
            "serverless@newrelic.com for assistance with getting the AWS log "
            "subscription filter limit increased.",
            color="blue",
        )
    if not newrelic_filters:
        click.echo("Adding New Relic log subscription to '%s'" % function_name)
        return create_subscription_filter(
            session, function_name, destination_arn, filter_pattern
        )
    else:
        click.echo(
            "Found log subscription for '%s', verifying configuration" % function_name
        )
        newrelic_filter = newrelic_filters[0]
        if newrelic_filter["filterPattern"] != filter_pattern:
            return remove_subscription_filter(
                session, function_name
            ) and create_subscription_filter(session, function_name, destination_arn)
        return True


def remove_log_subscription(session, function_name):
    subscription_filters = get_subscription_filters(session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if filter["filterName"] == "NewRelicLogStreaming"
    ]
    if not newrelic_filters:
        click.echo(
            "No New Relic subscription filters found for '%s', skipping" % function_name
        )
        return False
    click.echo("Removing New Relic log subscription from '%s'" % function_name)
    return remove_subscription_filter(session, function_name)
