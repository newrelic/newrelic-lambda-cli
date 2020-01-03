import botocore
import click

from newrelic_lambda_cli import utils


def list_functions(session, filter_choice):
    client = session.client("lambda")

    # set all if the filter_choice is "all" or there is no filter_choice active.
    all = filter_choice == "all" or not filter_choice

    pager = client.get_paginator("list_functions")
    for func_resp in pager.paginate():
        funcs = func_resp.get("Functions", [])

        for f in funcs:
            f.setdefault("x-new-relic-enabled", False)
            for layer in f.get("Layers", []):
                if layer.get("Arn", "").startswith(
                    utils.get_arn_prefix(session.region_name)
                ):
                    f["x-new-relic-enabled"] = True
            if all:
                yield f
            elif filter_choice == "installed" and f["x-new-relic-enabled"]:
                yield f
            elif filter_choice == "not_installed" and not f["x-new-relic-enabled"]:
                yield f


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
