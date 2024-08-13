# -*- coding: utf-8 -*-

import botocore
import click

from newrelic_lambda_cli.cliutils import failure, success, warning
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.integrations import get_unique_newrelic_log_ingestion_name
from newrelic_lambda_cli.integrations import get_newrelic_log_ingestion_function
from newrelic_lambda_cli.otel_ingestions import get_newrelic_otel_log_ingestion_function
from newrelic_lambda_cli.types import (
    LayerInstall,
    SubscriptionInstall,
    SubscriptionUninstall,
)
from newrelic_lambda_cli.utils import catch_boto_errors


def _get_log_group_name(function_name):
    """Builds a log group name path; handling ARNs if provided"""
    if ":" in function_name:
        parts = function_name.split(":")
        if len(parts) >= 7:
            return "/aws/lambda/%s" % parts[6]
    return "/aws/lambda/%s" % function_name


def _get_subscription_filters(session, function_name):
    """Returns all the log subscription filters for the function"""
    log_group_name = _get_log_group_name(function_name)
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


def _create_subscription_filter(
    session,
    function_name,
    destination_arn,
    filter_pattern,
    filter_name="NewRelicLogStreaming",
):
    try:
        session.client("logs").put_subscription_filter(
            logGroupName=_get_log_group_name(function_name),
            filterName=filter_name,
            filterPattern=filter_pattern,
            destinationArn=destination_arn,
        )
    except botocore.exceptions.ClientError as e:
        failure(
            "Error creating log subscription filter for '%s': %s" % (function_name, e)
        )
        return False
    else:
        success("Successfully installed log subscription on %s" % function_name)
        return True


def _remove_subscription_filter(session, function_name, filter_name):
    try:
        session.client("logs").delete_subscription_filter(
            logGroupName=_get_log_group_name(function_name), filterName=filter_name
        )
    except botocore.exceptions.ClientError as e:
        failure(
            "Error removing log subscription filter for '%s': %s" % (function_name, e)
        )
        return False
    else:
        success("Successfully uninstalled log subscription on %s" % function_name)
        return True


@catch_boto_errors
def create_log_subscription(input, function_name):
    assert isinstance(input, SubscriptionInstall)
    function = get_function(input.session, "newrelic-log-ingestion")
    if function:
        warning(
            "It looks like an old log ingestion function is present in this region. "
            "Consider manually deleting this as it is no longer used and "
            "has been replaced by a log ingestion function specific to the stack."
        )
    destination = get_newrelic_log_ingestion_function(input.session, input.stackname)
    if destination is None:
        failure(
            "Could not find newrelic-log-ingestion function. Is the New Relic AWS "
            "integration installed?"
        )
        return False
    destination_arn = destination["Configuration"]["FunctionArn"]
    subscription_filters = _get_subscription_filters(input.session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if "NewRelicLogStreaming" in filter["filterName"]
    ]
    if len(subscription_filters) > len(newrelic_filters):
        warning(
            "WARNING: Found a log subscription filter that was not installed by New "
            "Relic. This may prevent the New Relic log subscription filter from being "
            "installed. If you know you don't need this log subscription filter, you "
            "should first remove it and rerun this command. If your organization "
            "requires this log subscription filter, please contact New Relic at "
            "serverless@newrelic.com for assistance with getting the AWS log "
            "subscription filter limit increased."
        )
    if not newrelic_filters:
        click.echo("Adding New Relic log subscription to '%s'" % function_name)
        return _create_subscription_filter(
            input.session, function_name, destination_arn, input.filter_pattern
        )
    else:
        click.echo(
            "Found log subscription for '%s', verifying configuration" % function_name
        )
        newrelic_filter = newrelic_filters[0]
        if newrelic_filter["filterPattern"] != input.filter_pattern:
            return _remove_subscription_filter(
                input.session, function_name, newrelic_filter["filterName"]
            ) and _create_subscription_filter(
                input.session, function_name, destination_arn, input.filter_pattern
            )
        return True


@catch_boto_errors
def create_otel_log_subscription(input, function_name):
    assert isinstance(input, SubscriptionInstall)

    destination = get_newrelic_otel_log_ingestion_function(
        input.session, input.stackname
    )
    if destination is None:
        failure(
            "Could not find newrelic-otel-log-ingestion function. Is the New Relic AWS "
            "integration installed?"
        )
        return False
    destination_arn = destination["Configuration"]["FunctionArn"]

    subscription_filters = _get_subscription_filters(input.session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if "NewRelicOtelLogStreaming" in filter["filterName"]
    ]
    if len(subscription_filters) > len(newrelic_filters):
        warning(
            "WARNING: Found otel log subscription filter that was not installed by New "
            "Relic. This may prevent the New Relic log subscription filter from being "
            "installed. If you know you don't need this log subscription filter, you "
            "should first remove it and rerun this command. If your organization "
            "requires this log subscription filter, please contact New Relic at "
            "serverless@newrelic.com for assistance with getting the AWS log "
            "subscription filter limit increased."
        )
        return False
    if not newrelic_filters:
        click.echo("Adding New Relic otel log subscription to '%s'" % function_name)
        return _create_subscription_filter(
            input.session,
            function_name,
            destination_arn,
            input.filter_pattern,
            "NewRelicOtelLogStreaming",
        )
    else:
        click.echo(
            "Found log subscription for '%s', verifying configuration" % function_name
        )
        newrelic_filter = newrelic_filters[0]
        if newrelic_filter["filterPattern"] != input.filter_pattern:
            return _remove_subscription_filter(
                input.session, function_name, newrelic_filter["filterName"]
            ) and _create_subscription_filter(
                input.session,
                function_name,
                destination_arn,
                input.filter_pattern,
                "NewRelicOtelLogStreaming",
            )
        return True


@catch_boto_errors
def remove_log_subscription(input, function_name):
    assert isinstance(input, (LayerInstall, SubscriptionUninstall))
    subscription_filters = _get_subscription_filters(input.session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if "NewRelicLogStreaming" in filter["filterName"]
    ]
    if not newrelic_filters:
        click.echo(
            "No New Relic subscription filters found for '%s', skipping" % function_name
        )
        return True
    newrelic_filter = newrelic_filters[0]
    click.echo("Removing New Relic log subscription from '%s'" % function_name)
    return _remove_subscription_filter(
        input.session, function_name, newrelic_filter["filterName"]
    )


@catch_boto_errors
def remove_otel_log_subscription(input, function_name):
    assert isinstance(input, (SubscriptionUninstall))
    subscription_filters = _get_subscription_filters(input.session, function_name)
    if subscription_filters is None:
        return False
    newrelic_filters = [
        filter
        for filter in subscription_filters
        if "NewRelicOtelLogStreaming" in filter["filterName"]
    ]
    if not newrelic_filters:
        click.echo(
            "No New Relic otel subscription filters found for '%s', skipping"
            % function_name
        )
        return True
    newrelic_filter = newrelic_filters[0]
    click.echo("Removing New Relic otel log subscription from '%s'" % function_name)
    return _remove_subscription_filter(
        input.session, function_name, newrelic_filter["filterName"]
    )
