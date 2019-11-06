import collections
import sys

import boto3
import botocore

from . import layers

NEW_RELIC_ARN_PREFIX_TEMPLATE = "arn:aws:lambda:%s:451483290750"
RUNTIME_CONFIG = {
    "nodejs10.x": {"Handler": "newrelic-lambda-wrapper.handler"},
    "python2.7": {"Handler": "newrelic_lambda_wrapper.handler"},
    "python3.6": {"Handler": "newrelic_lambda_wrapper.handler"},
    "python3.7": {"Handler": "newrelic_lambda_wrapper.handler"},
}


def catch_boto_errors(func):
    def _boto_error_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botocore.exceptions.NoRegionError:
            error("You must specify a region. Pass `--region` or run `aws configure`.")
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


def get_layers(region, runtime):
    return layers.index(get_region(region), runtime)


@catch_boto_errors
def get_lambda_client(region):
    boto_kwargs = {}
    if region:
        boto_kwargs["region_name"] = region
    AwsLambda = boto3.client("lambda", **boto_kwargs)
    return AwsLambda


@catch_boto_errors
def all_lambda_regions():
    return boto3.session.Session().get_available_regions("lambda")


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
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(1)