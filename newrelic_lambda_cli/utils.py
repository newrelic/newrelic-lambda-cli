# -*- coding: utf-8 -*-

import boto3
import botocore
import click
from click.exceptions import Exit

NEW_RELIC_ARN_PREFIX_TEMPLATE = "arn:aws:lambda:%s:451483290750"
RUNTIME_CONFIG = {
    "dotnetcore3.1": {},
    "java11": {},
    "java8.al2": {},
    "nodejs10.x": {"Handler": "newrelic-lambda-wrapper.handler"},
    "nodejs12.x": {"Handler": "newrelic-lambda-wrapper.handler"},
    "provided": {},
    "provided.al2": {},
    "python2.7": {"Handler": "newrelic_lambda_wrapper.handler"},
    "python3.6": {"Handler": "newrelic_lambda_wrapper.handler"},
    "python3.7": {"Handler": "newrelic_lambda_wrapper.handler"},
    "python3.8": {"Handler": "newrelic_lambda_wrapper.handler"},
}


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
    click.echo(*args, err=True, **kwargs)
    raise Exit(1)


def validate_aws_profile(ctx, param, value):
    """A click callback to validate that an AWS profile exists"""
    try:
        boto3.Session(profile_name=value)
    except botocore.exceptions.ProfileNotFound as e:
        raise click.BadParameter(e.fmt)
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
