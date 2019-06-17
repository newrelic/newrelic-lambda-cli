from . import layers

import boto3
import botocore
import click
import collections
import jwt
import os
import sys

IOPIPE_ARN_PREFIX_TEMPLATE = "arn:aws:lambda:%s:5558675309"
RUNTIME_CONFIG = {
    "java8": {
        "Handler": {
            "request": "com.iopipe.generic.GenericAWSRequestHandler",
            "stream": "com.iopipe.generic.GenericAWSRequestStreamHandler",
        }
    },
    "python2.7": {"Handler": "iopipe.handler.wrapper"},
    "python3.7": {"Handler": "iopipe.handler.wrapper"},
}

if os.getenv("IOPIPE_FF_NODEJS"):
    RUNTIME_CONFIG["nodejs6.10"] = {"Handler": "@iopipe/iopipe.handler"}
    RUNTIME_CONFIG["nodejs8.10"] = {"Handler": "@iopipe/iopipe.handler"}

def format_generic_arn(arn):
    return collections.namedtuple(
        "GenericArn",
        [
            "arn",
            "partition",
            "service",
            "region",
            "account_id",
            "resource_type",
            "resource",
            "qualifier"
        ],
        defaults=[
            "arn",
            "aws",
            None,
            get_region(None),
            None,
            None,
            None,
            None
        ]
    )(arn.split(":"))

def format_lambda_arn(arn):
    return collections.namedtuple(
        "LambdaArn",
        [
            "arn",
            "partition",
            "service",
            "region",
            "account_id",
            "resource_type",
            "function_name",
            "version"
        ],
        defaults=[
           "arn",
           "aws",
           "lambda",
            get_region(None),
            None,
            "function",
            None,
            "$LATEST"
        ]
    )(arn.split(":"))

def runtime_config_iter():
    for runtime, obj in RUNTIME_CONFIG.items():
        if isinstance(obj.get("Handler"), dict):
            for java_type in obj.get("Handler").keys():
                yield {"runtime": runtime, "java_type": java_type}
        else:
            yield {"runtime": runtime, "java_type": None}


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
    return IOPIPE_ARN_PREFIX_TEMPLATE % (get_region(region),)


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


def check_token(ctx, param, value):
    if not hasattr(jwt, "PyJWT"):
        raise Exception(
            "Incompatible `jwt` library detected. Must have `pyjwt` installed."
        )
    try:
        jwt.decode(value, verify=False)
        return value
    except:
        raise click.BadParameter("token invalid.")


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


def local_apply_updates(config, updates):
    result = config.copy()
    result["Configuration"]["Handler"] = (
        updates.get("Handler") or result["Configuration"]["Handler"]
    )

    new_envvars = updates.get("Environment", {}).get("Variables")
    if new_envvars:
        result["Configuration"]["Environment"]["Variables"].update(new_envvars)

    layer_map = map(lambda layer: {"Arn": layer}, updates.get("Layers", []))
    result["Layers"] = layer_map
    return result


def error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.exit(1)
