# -*- coding: utf-8 -*-

from enum import Enum
import sys

import boto3
import botocore
import click

NR_DOCS_ACT_LINKING_URL = "https://docs.newrelic.com/docs/serverless-function-monitoring/aws-lambda-monitoring/enable-lambda-monitoring/account-linking/#manually-configuring-the-license-key-secret"
NEW_RELIC_ARN_PREFIX_TEMPLATE = "arn:aws:lambda:%s:451483290750"
RUNTIME_CONFIG = {
    "dotnetcore3.1": {"LambdaExtension": True},
    "java11": {
        "Handler": "com.newrelic.java.HandlerWrapper::",
        "LambdaExtension": True,
    },
    "java8.al2": {
        "Handler": "com.newrelic.java.HandlerWrapper::",
        "LambdaExtension": True,
    },
    "nodejs10.x": {
        "Handler": "newrelic-lambda-wrapper.handler",
        "LambdaExtension": True,
    },
    "nodejs12.x": {
        "Handler": "newrelic-lambda-wrapper.handler",
        "LambdaExtension": True,
    },
    "nodejs14.x": {
        "Handler": "newrelic-lambda-wrapper.handler",
        "LambdaExtension": True,
    },
    "provided": {"LambdaExtension": True},
    "provided.al2": {"LambdaExtension": True},
    "python2.7": {
        "Handler": "newrelic_lambda_wrapper.handler",
        "LambdaExtension": False,
    },
    "python3.6": {
        "Handler": "newrelic_lambda_wrapper.handler",
        "LambdaExtension": False,
    },
    "python3.7": {
        "Handler": "newrelic_lambda_wrapper.handler",
        "LambdaExtension": True,
    },
    "python3.8": {
        "Handler": "newrelic_lambda_wrapper.handler",
        "LambdaExtension": True,
    },
    "python3.9": {
        "Handler": "newrelic_lambda_wrapper.handler",
        "LambdaExtension": True,
    },
}


class DefaultStackNames(Enum):
    """Possible Default Stack Names depending on how log-ingestion function may exist in ecosystem

    Args:
        Enum ([type]): names of CloudFormation Stacks, based around
        how the log-ingestion function might exist in one's AWS ecosystem
    """

    SERVERLESS_INSTALLED_FUNC_STACK = "serverlessrepo-NewRelic-log-ingestion"
    CLI_TOOL_BASED_INSTALLED_FUNC_STACK = "NewRelic-log-ingestion"


def catch_boto_errors(func):
    def _boto_error_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botocore.exceptions.NoRegionError:
            error(
                "You must specify a region. Pass `--aws-region` or run `aws configure`."
            )
        except botocore.exceptions.NoCredentialsError:
            error("No AWS credentials configured. Did you run `aws configure`?")
        except botocore.exceptions.BotoCoreError as e:
            error("Unexpected AWS error: %s" % e)

    return _boto_error_wrapper


def get_arn_prefix(region):
    return NEW_RELIC_ARN_PREFIX_TEMPLATE % (get_region(region),)


@catch_boto_errors
def get_region(region):
    boto_kwargs = {}
    if region:
        boto_kwargs["region_name"] = region
    session = boto3.session.Session(**boto_kwargs)
    return session.region_name


@catch_boto_errors
def get_lambda_client(session):
    return session.client("lambda")


@catch_boto_errors
def all_lambda_regions():
    return boto3.Session().get_available_regions("lambda")


def is_valid_handler(runtime, handler):
    runtime_handler = RUNTIME_CONFIG.get(runtime, {}).get("Handler", None)
    if isinstance(runtime_handler, dict):
        for _, valid_handler in runtime_handler.items():
            if handler == valid_handler:
                return True
        return False
    elif handler == runtime_handler:
        return True
    return False


def error(*args, **kwargs):
    raise click.UsageError(*args, **kwargs)


def validate_aws_profile(ctx, param, value):
    """A click callback to validate that an AWS profile exists"""
    try:
        boto3.Session(profile_name=value)
    except botocore.exceptions.ProfileNotFound as e:
        raise click.BadParameter(e.fmt, ctx=ctx, param=param, param_hint="AWS Profile")
    else:
        return value


def unique(seq):
    """Returns unique values in a sequence while preserving order"""
    seen = set()
    # Why assign seen.add to seen_add instead of just calling seen.add?
    # Python is a dynamic language, and resolving seen.add each iteration is more costly
    # than resolving a local variable.
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def parse_arn(arn):
    # http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
    elements = arn.split(":")
    result = {
        "arn": elements[0],
        "partition": elements[1],
        "service": elements[2],
        "region": elements[3],
        "account": elements[4],
    }
    if len(elements) == 7:
        result["resourcetype"], result["resource"] = elements[5:]
    elif "/" not in elements[5]:
        result["resource"] = elements[5]
        result["resourcetype"] = None
    else:
        result["resourcetype"], result["resource"] = elements[5].split("/")
    return result


def supports_lambda_extension(runtime):
    return RUNTIME_CONFIG.get(runtime, {}).get("LambdaExtension", False)
