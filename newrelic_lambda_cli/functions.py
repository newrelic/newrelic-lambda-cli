import botocore
import click

from newrelic_lambda_cli import utils


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


def get_aliased_functions(session, functions, excludes):
    """
    Retrieves functions for 'all, 'installed' and 'not-installed' aliases and appends
    them to existing list of functions.
    """
    aliases = [
        function.lower()
        for function in functions
        if function.lower() in ("all", "installed", "not-installed")
    ]

    functions = [
        function
        for function in functions
        if function.lower()
        not in ("all", "installed", "not-installed", "newrelic-log-ingestion")
        and function not in excludes
    ]

    if not aliases:
        return functions

    for alias in set(aliases):
        for function in list_functions(session, alias):
            if (
                "FunctionName" in function
                and "newrelic-log-ingestion" not in function["FunctionName"]
                and function["FunctionName"] not in excludes
            ):
                functions.append(function["FunctionName"])

    return set(functions)
