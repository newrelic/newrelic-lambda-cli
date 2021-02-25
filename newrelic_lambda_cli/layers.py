# -*- coding: utf-8 -*-

import botocore
import click
import json
import requests

from newrelic_lambda_cli import api, subscriptions, utils
from newrelic_lambda_cli.cliutils import failure, success, warning
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.integrations import _get_license_key_policy_arn
from newrelic_lambda_cli.types import LayerInstall, LayerUninstall

NEW_RELIC_ENV_VARS = (
    "NEW_RELIC_ACCOUNT_ID",
    "NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS",
    "NEW_RELIC_LAMBDA_EXTENSION_ENABLED",
    "NEW_RELIC_LAMBDA_HANDLER",
    "NEW_RELIC_LICENSE_KEY",
    "NEW_RELIC_LOG_ENDPOINT",
    "NEW_RELIC_TELEMETRY_ENDPOINT",
)


def index(region, runtime):
    req = requests.get(
        "https://%s.layers.newrelic-external.com/get-layers?CompatibleRuntime=%s"
        % (region, runtime)
    )
    layers_response = req.json()
    return layers_response.get("Layers", [])


def _add_new_relic(input, config, nr_license_key):
    assert isinstance(input, LayerInstall)

    aws_region = input.session.region_name

    runtime = config["Configuration"]["Runtime"]
    if runtime not in utils.RUNTIME_CONFIG:
        failure(
            "Unsupported Lambda runtime for '%s': %s"
            % (config["Configuration"]["FunctionArn"], runtime)
        )
        return True

    handler = config["Configuration"]["Handler"]
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get("Handler")

    existing_newrelic_layer = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers", [])
        if layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    if not input.upgrade and existing_newrelic_layer:
        success(
            "Already installed on function '%s'. Pass --upgrade (or -u) to allow "
            "upgrade or reinstall to latest layer version."
            % config["Configuration"]["FunctionArn"]
        )
        return True

    existing_layers = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers", [])
        if not layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    new_relic_layers = []

    if input.layer_arn:
        new_relic_layers = [input.layer_arn]
    else:
        # discover compatible layers...
        available_layers = index(aws_region, runtime)

        if not available_layers:
            failure(
                "No Lambda layers published for '%s' runtime: %s"
                % (config["Configuration"]["FunctionArn"], runtime)
            )
            return False

        # TODO: MAke this a layer selection screen
        if len(available_layers) > 1:
            message = ["Discovered layers for runtime (%s)" % runtime]
            for layer in available_layers:
                message.append(
                    "%s\t%s"
                    % (
                        layer["LatestMatchingVersion"]["LayerVersionArn"],
                        layer.get("Description", ""),
                    )
                )
            message.append(
                "\nMultiple layers found. Pass --layer-arn to specify layer ARN"
            )
            raise click.UsageError("\n".join(message))

        new_relic_layers = [
            available_layers[0]["LatestMatchingVersion"]["LayerVersionArn"]
        ]

    update_kwargs = {
        "FunctionName": config["Configuration"]["FunctionArn"],
        "Environment": {
            "Variables": config["Configuration"]
            .get("Environment", {})
            .get("Variables", {})
        },
        "Layers": new_relic_layers + existing_layers,
    }

    # Only used by Python and Node.js runtimes
    if runtime_handler:
        update_kwargs["Handler"] = runtime_handler

    # Update the account id
    update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = str(
        input.nr_account_id
    )

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if runtime_handler and handler != runtime_handler:
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"] = handler

    if input.enable_extension and not utils.supports_lambda_extension(runtime):
        warning(
            "The %s runtime for %s does not support Lambda Extensions, reverting to a "
            "CloudWatch Logs based ingestion. Make sure you run `newrelic-lambda "
            "integrations install` command to install the New Relic log ingestion "
            "function and `newrelic-lambda subscriptions install` to create the log "
            "subscription filter." % (runtime, config["Configuration"]["FunctionName"])
        )

    if input.enable_extension and utils.supports_lambda_extension(runtime):
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LAMBDA_EXTENSION_ENABLED"
        ] = "true"

        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS"
        ] = ("true" if input.enable_extension_function_logs else "false")

        if input.nr_region == "staging":
            update_kwargs["Environment"]["Variables"][
                "NEW_RELIC_TELEMETRY_ENDPOINT"
            ] = "https://staging-cloud-collector.newrelic.com/aws/lambda/v1"
            update_kwargs["Environment"]["Variables"][
                "NEW_RELIC_LOG_ENDPOINT"
            ] = "https://staging-log-api.newrelic.com/log/v1"

        if nr_license_key:
            update_kwargs["Environment"]["Variables"][
                "NEW_RELIC_LICENSE_KEY"
            ] = nr_license_key
    else:
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LAMBDA_EXTENSION_ENABLED"
        ] = "false"

    return update_kwargs


def install(input, function_arn):
    assert isinstance(input, LayerInstall)

    client = input.session.client("lambda")

    config = get_function(input.session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    policy_arn = _get_license_key_policy_arn(input.session)
    if input.enable_extension and not policy_arn and not input.nr_api_key:
        raise click.UsageError(
            "In order to use `--enable-extension`, you must first run "
            "`newrelic-lambda integrations install` with the "
            "`--enable-license-key-secret` flag. This uses AWS Secrets Manager "
            "to securely store your New Relic license key in your AWS account. "
            "If you are unable to use AWS Secrets Manager, re-run this command with "
            "`--nr-api-key` argument with your New Relic API key to set your license "
            "key in a NEW_RELIC_LICENSE_KEY environment variable instead."
        )

    nr_license_key = None
    if not policy_arn and input.nr_api_key and input.nr_region:
        gql = api.validate_gql_credentials(input)
        nr_license_key = api.retrieve_license_key(gql)

    update_kwargs = _add_new_relic(input, config, nr_license_key)
    if isinstance(update_kwargs, bool):
        return update_kwargs

    try:
        res = client.update_function_configuration(**update_kwargs)
    except botocore.exceptions.ClientError as e:
        failure(
            "Failed to update configuration for '%s': %s"
            % (config["Configuration"]["FunctionArn"], e)
        )
        return False
    else:
        if input.enable_extension and policy_arn:
            _attach_license_key_policy(
                input.session, config["Configuration"]["Role"], policy_arn
            )

        if input.enable_extension_function_logs:
            subscriptions.remove_log_subscription(input, function_arn)

        if input.verbose:
            click.echo(json.dumps(res, indent=2))

        success("Successfully installed layer on %s" % function_arn)
        return True


def _remove_new_relic(input, config):
    assert isinstance(input, LayerUninstall)

    aws_region = input.session.region_name

    runtime = config["Configuration"]["Runtime"]
    if runtime not in utils.RUNTIME_CONFIG:
        failure(
            "Unsupported Lambda runtime for '%s': %s"
            % (config["Configuration"]["FunctionArn"], runtime)
        )
        return True

    handler = config["Configuration"]["Handler"]

    # Detect non-New Relic handler and error if necessary.
    if not utils.is_valid_handler(runtime, handler):
        failure(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function '%s'. Unrecognized handler in deployed function."
            % config["Configuration"]["FunctionArn"]
        )
        return False

    env_handler = (
        config["Configuration"]
        .get("Environment", {})
        .get("Variables", {})
        .get("NEW_RELIC_LAMBDA_HANDLER")
    )

    # Delete New Relic env vars
    config["Configuration"]["Environment"]["Variables"] = {
        key: value
        for key, value in config["Configuration"]
        .get("Environment", {})
        .get("Variables", {})
        .items()
        if key not in NEW_RELIC_ENV_VARS
    }

    # Remove New Relic layers
    layers = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers")
        if not layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    return {
        "FunctionName": config["Configuration"]["FunctionArn"],
        "Handler": env_handler if env_handler else config["Configuration"]["Handler"],
        "Environment": config["Configuration"]["Environment"],
        "Layers": layers,
    }


def uninstall(input, function_arn):
    assert isinstance(input, LayerUninstall)

    client = input.session.client("lambda")

    config = get_function(input.session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    update_kwargs = _remove_new_relic(input, config)

    if isinstance(update_kwargs, bool):
        return update_kwargs

    try:
        res = client.update_function_configuration(**update_kwargs)
    except botocore.exceptions.ClientError as e:
        failure(
            "Failed to update configuration for '%s': %s"
            % (config["Configuration"]["FunctionArn"], e)
        )
        return False
    else:
        policy_arn = _get_license_key_policy_arn(input.session)
        if policy_arn:
            _detach_license_key_policy(
                input.session, config["Configuration"]["Role"], policy_arn
            )

        if input.verbose:
            click.echo(json.dumps(res, indent=2))

        success("Successfully uninstalled layer on %s" % function_arn)
        return True


def _attach_license_key_policy(session, role_arn, policy_arn):
    """Attaches the license key secret policy to the specified role"""
    _, role_name = role_arn.rsplit("/", 1)
    client = session.client("iam")
    try:
        client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except botocore.exceptions.ClientError as e:
        failure("Failed to attach %s policy to %s: %s" % (policy_arn, role_arn, e))
        return False
    else:
        return True


def _detach_license_key_policy(session, role_arn, policy_arn):
    """Detaches the license key secret policy from the specified role"""
    _, role_name = role_arn.rsplit("/", 1)
    client = session.client("iam")
    try:
        client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except botocore.exceptions.ClientError as e:
        failure("Failed to detach %s policy to %s: %s" % (policy_arn, role_arn, e))
        return False
    else:
        return True
