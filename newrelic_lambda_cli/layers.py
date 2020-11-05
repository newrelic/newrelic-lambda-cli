# -*- coding: utf-8 -*-

import botocore
import click
import json
import requests

from newrelic_lambda_cli import api, utils
from newrelic_lambda_cli.cliutils import failure, success
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.integrations import get_license_key_policy_arn


def index(region, runtime):
    req = requests.get(
        "https://%s.layers.newrelic-external.com/get-layers?CompatibleRuntime=%s"
        % (region, runtime)
    )
    layers_response = req.json()
    return layers_response.get("Layers", [])


def _add_new_relic(
    config,
    aws_region,
    layer_arn,
    nr_account_id,
    nr_license_key,
    allow_upgrade,
    enable_extension,
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
        if layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
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
        if not layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    new_relic_layers = []

    if layer_arn:
        new_relic_layers = [layer_arn]
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
        nr_account_id
    )

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if runtime_handler and handler != runtime_handler:
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"] = handler

    if enable_extension:
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LAMBDA_EXTENSION_ENABLED"
        ] = "true"

    if nr_license_key:
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LICENSE_KEY"
        ] = nr_license_key

    return update_kwargs

    return update_kwargs


def install(
    session,
    function_arn,
    layer_arn,
    nr_account_id,
    nr_api_key,
    nr_region,
    allow_upgrade,
    enable_extension,
    verbose,
):
    client = session.client("lambda")

    config = get_function(session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    aws_region = session.region_name

    policy_arn = get_license_key_policy_arn(session)
    if enable_extension and not policy_arn and not nr_api_key:
        raise click.UsageError(
            "In order to use `--enable-extension`, you must first run "
            "`newrelic-lambda integrations install` with the "
            "`--enable-license-key-secret` flag. This uses AWS Secrets Manager "
            "to securely store your New Relic license key in tyour AWS account. "
            "If you are unable to use AWS Secrets Manager, re-run this command with "
            "`--nr-api-key` argument with your New Relic API key to set your license "
            "key in a NEW_RELIC_LICENSE_KEY environment variable instead."
        )

    nr_license_key = None
    if not policy_arn and nr_api_key and nr_region:
        gql = api.validate_gql_credentials(nr_account_id, nr_api_key, nr_region)
        nr_license_key = api.retrieve_license_key(gql)

    update_kwargs = _add_new_relic(
        config,
        aws_region,
        layer_arn,
        nr_account_id,
        nr_license_key,
        allow_upgrade,
        enable_extension,
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
        if enable_extension and policy_arn:
            _attach_license_key_policy(
                session, config["Configuration"]["Role"], policy_arn
            )
        if verbose:
            click.echo(json.dumps(res, indent=2))
        success("Successfully installed layer on %s" % function_arn)
        return True


def _remove_new_relic(config, aws_region):
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
        if not layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
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

    aws_region = session.region_name

    update_kwargs = _remove_new_relic(config, aws_region)

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
        policy_arn = get_license_key_policy_arn(session)
        if policy_arn:
            _detach_license_key_policy(
                session, config["Configuration"]["Role"], policy_arn
            )
        if verbose:
            click.echo(json.dumps(res, indent=2))
        success("Successfully uninstalled layer on %s" % function_arn)
        return True


def _attach_license_key_policy(session, role_arn, policy_arn):
    """Attaches the license key secret policy to the specified role"""
    _, role_name = role_arn.lsplit("/", 1)
    client = session.client("iam")
    try:
        client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except botocore.exceptions.ClientError:
        failure("Failed to attach %s policy to %s" % (policy_arn, role_arn))
        return False
    else:
        return True


def _detach_license_key_policy(session, role_arn, policy_arn):
    """Detaches the license key secret policy from the specified role"""
    _, role_name = role_arn.lsplit("/", 1)
    client = session.client("iam")
    try:
        client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    except botocore.exceptions.ClientError:
        return False
    else:
        return True
