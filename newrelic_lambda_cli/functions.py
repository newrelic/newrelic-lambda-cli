# -*- coding: utf-8 -*-

import botocore
import click

from newrelic_lambda_cli.types import (
    LayerInstall,
    LayerUninstall,
    SubscriptionInstall,
    SubscriptionUninstall,
)
from newrelic_lambda_cli import utils


@utils.catch_boto_errors
def list_functions(session, filter=None):
    client = session.client("lambda")

    all = filter == "all" or not filter

    pager = client.get_paginator("list_functions")
    for res in pager.paginate():
        funcs = res.get("Functions", [])
        for func in funcs:
            func.setdefault("x-new-relic-enabled", False)
            for layer in func.get("Layers", []):
                if layer.get("Arn", "").startswith(
                    utils.get_arn_prefix(session.region_name)
                ):
                    func["x-new-relic-enabled"] = True
            if all:
                yield func
            elif filter == "installed" and func["x-new-relic-enabled"]:
                yield func
            elif filter == "not-installed" and not func["x-new-relic-enabled"]:
                yield func


def get_function(session, function_name):
    """Returns details about an AWS lambda function"""
    try:
        if len(function_name) > 170 or len(function_name) == 0:
            raise click.UsageError(
                str(
                    "Lambda Function name does not meet constraints ref: https://docs.aws.amazon.com/lambda/latest/dg/API_GetFunction.html#API_GetFunction_RequestSyntax"
                )
            )
        return session.client("lambda").get_function(FunctionName=function_name)
    except botocore.exceptions.ClientError as e:
        if (
            e.response
            and "ResponseMetadata" in e.response
            and "HTTPStatusCode" in e.response["ResponseMetadata"]
            and e.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        ):
            return None
        raise click.UsageError(str(e))


def get_aliased_functions(input):
    """
    Retrieves functions for 'all, 'installed' and 'not-installed' aliases and appends
    them to existing list of functions.
    """
    assert isinstance(
        input,
        (LayerInstall, LayerUninstall, SubscriptionInstall, SubscriptionUninstall),
    )

    aliases = [
        function.lower()
        for function in input.functions
        if function.lower() in ("all", "installed", "not-installed")
    ]

    functions = [
        function
        for function in input.functions
        if function.lower()
        not in ("all", "installed", "not-installed", "newrelic-log-ingestion")
        and function not in input.excludes
    ]

    if not aliases:
        return utils.unique(functions)

    for alias in set(aliases):
        for function in list_functions(input.session, alias):
            if (
                "FunctionName" in function
                and "newrelic-log-ingestion" not in function["FunctionName"]
                and function["FunctionName"] not in input.excludes
            ):
                functions.append(function["FunctionName"])

    return utils.unique(functions)
