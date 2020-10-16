# -*- coding: utf-8 -*-

import botocore
import click
import json
import requests

from newrelic_lambda_cli import utils
from newrelic_lambda_cli.cliutils import failure, success
from newrelic_lambda_cli.functions import get_function


def index(region, runtime):
    req = requests.get(
        "https://%s.layers.newrelic-external.com/get-layers?CompatibleRuntime=%s"
        % (region, runtime)
    )
    layers_response = req.json()
    return layers_response.get("Layers", [])


def _add_new_relic(
    config, region, layer_arn, account_id, allow_upgrade, enable_extension
):
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
        if layer["Arn"].startswith(utils.get_arn_prefix(region))
    ]

    if not allow_upgrade and existing_newrelic_layer:
        success(
            "Already installed on function '%s'. Pass --upgrade (or -u) to allow "
            "upgrade or reinstall to latest layer version."
            % config["Configuration"]["FunctionArn"]
        )
        return True

    existing_layers = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers", [])
        if not layer["Arn"].startswith(utils.get_arn_prefix(region))
    ]

    new_relic_layers = []

    if layer_arn:
        new_relic_layers = [layer_arn]
    else:
        # discover compatible layers...
        available_layers = index(region, runtime)

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
    update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = str(account_id)

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if runtime_handler and handler != runtime_handler:
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"] = handler

    if enable_extension:
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LAMBDA_EXTENSION_ENABLED"
        ] = "true"

    return update_kwargs


def install(
    session,
    function_arn,
    layer_arn,
    account_id,
    allow_upgrade,
    enable_extension,
    verbose,
):
    client = session.client("lambda")
    config = get_function(session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    region = session.region_name

    update_kwargs = _add_new_relic(
        config, region, layer_arn, account_id, allow_upgrade, enable_extension
    )
    if not update_kwargs:
        return False

    try:
        res = client.update_function_configuration(**update_kwargs)
    except botocore.exceptions.ClientError as e:
        failure(
            "Failed to update configuration for '%s': %s"
            % (config["Configuration"]["FunctionArn"], e)
        )
        return False
    else:
        if verbose:
            click.echo(json.dumps(res, indent=2))
        success("Successfully installed layer on %s" % function_arn)
        return True


def _remove_new_relic(config, region):
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

    if not env_handler:
        failure(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function '%s'. Environment variable NEW_RELIC_LAMBDA_HANDLER not found."
            % config["Configuration"]["FunctionArn"]
        )
        return False

    # Delete New Relic env vars
    config["Configuration"]["Environment"]["Variables"] = {
        key: value
        for key, value in config["Configuration"]
        .get("Environment", {})
        .get("Variables", {})
        .items()
        if not key.startswith("NEW_RELIC")
    }

    # Remove New Relic layers
    layers = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers")
        if not layer["Arn"].startswith(utils.get_arn_prefix(region))
    ]

    return {
        "FunctionName": config["Configuration"]["FunctionArn"],
        "Handler": env_handler,
        "Environment": config["Configuration"]["Environment"],
        "Layers": layers,
    }


def uninstall(session, function_arn, verbose):
    client = session.client("lambda")

    config = get_function(session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    region = session.region_name

    update_kwargs = _remove_new_relic(config, region)
    if not update_kwargs:
        return False

    try:
        res = client.update_function_configuration(**update_kwargs)
    except botocore.exceptions.ClientError as e:
        failure(
            "Failed to update configuration for '%s': %s"
            % (config["Configuration"]["FunctionArn"], e)
        )
        return False
    else:
        if verbose:
            click.echo(json.dumps(res, indent=2))
        success("Successfully uninstalled layer on %s" % function_arn)
        return True
