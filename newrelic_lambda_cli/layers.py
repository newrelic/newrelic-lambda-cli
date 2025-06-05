# -*- coding: utf-8 -*-
#
import sys  #

import botocore
import click
import json
import requests


from newrelic_lambda_cli import api, subscriptions, utils
from newrelic_lambda_cli.cliutils import failure, success, warning
from newrelic_lambda_cli.functions import get_function
from newrelic_lambda_cli.integrations import _get_license_key_outputs
from newrelic_lambda_cli.types import LayerInstall, LayerUninstall
from newrelic_lambda_cli.utils import catch_boto_errors


NEW_RELIC_ENV_VARS = (
    "NEW_RELIC_ACCOUNT_ID",
    "NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS",
    "NEW_RELIC_LAMBDA_EXTENSION_ENABLED",
    "NEW_RELIC_LAMBDA_HANDLER",
    "NEW_RELIC_LICENSE_KEY",
    "NEW_RELIC_LOG_ENDPOINT",
    "NEW_RELIC_TELEMETRY_ENDPOINT",
    "NEW_RELIC_APM_LAMBDA_MODE",
)


def index(region, runtime, architecture):
    req = requests.get(
        "https://%s.layers.newrelic-external.com/get-layers"
        "?CompatibleRuntime=%s" % (region, runtime)
    )
    layers_response = req.json()
    return [
        layer
        for layer in layers_response.get("Layers", [])
        if architecture
        in layer.get("LatestMatchingVersion", {}).get(
            "CompatibleArchitectures", ["x86_64"]
        )
    ]


def layer_selection(available_layers, runtime, architecture):
    if len(available_layers) == 1:
        return available_layers[0]["LatestMatchingVersion"]["LayerVersionArn"]

    layer_options = [
        layer["LatestMatchingVersion"]["LayerVersionArn"] for layer in available_layers
    ]

    if sys.stdout.isatty():
        output = "\n".join(
            [
                "Discovered multiple layers for runtime %s (%s):"
                % (runtime, architecture),
                "",
            ]
            + ["%d: %s" % (i, layer) for i, layer in enumerate(layer_options)]
            + ["", "Select a layer"]
        )

        while True:
            value = click.prompt(output, default=0, type=int)
            try:
                selected_layer = layer_options[value]
                success("Layer %s selected" % selected_layer)
                return selected_layer
            except IndexError:
                failure("Invalid layer selection")
    else:
        raise click.UsageError(
            "Discovered multiple layers for runtime %s (%s):\n%s\n"
            "Pass --layer-arn to specify a layer ARN"
            % (runtime, architecture, "\n".join(layer_options))
        )


def _add_new_relic(input, config, nr_license_key):
    assert isinstance(input, LayerInstall)

    aws_region = input.session.region_name

    runtime = config["Configuration"]["Runtime"]
    if runtime not in utils.RUNTIME_CONFIG:
        failure(
            "Unsupported Lambda runtime for '%s': %s"
            % (config["Configuration"]["FunctionArn"], runtime)
        )
        return False

    architectures = config["Configuration"].get("Architectures", ["x86_64"])
    architecture = architectures[0]

    handler = config["Configuration"]["Handler"]
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get("Handler")

    if "java" in runtime:
        postfix = input.java_handler_method or "handleRequest"
        runtime_handler = runtime_handler + postfix
    if "nodejs" in runtime:
        prefix = (
            "/opt/nodejs/node_modules/newrelic-esm-lambda-wrapper/index"
            if input.esm
            else "newrelic-lambda-wrapper"
        )
        runtime_handler = prefix + ".handler"

    existing_newrelic_layer = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers", [])
        if layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    if not input.upgrade and existing_newrelic_layer:
        success(
            "Already installed on function '%s'. Pass --upgrade (or -u) to allow "
            "upgrade or reinstall to latest layer version."
            "Additionally pass --apm to enable APM Lambda mode."
            % config["Configuration"]["FunctionArn"]
        )
        return True

    existing_layers = [
        layer["Arn"]
        for layer in config["Configuration"].get("Layers", [])
        if not layer["Arn"].startswith(utils.get_arn_prefix(aws_region))
    ]

    new_relic_layer = []

    if input.layer_arn:
        new_relic_layer = input.layer_arn
    else:
        # discover compatible layers...
        available_layers = index(aws_region, runtime, architecture)

        if not available_layers:
            failure(
                "No Lambda layers published for %s (%s) runtime: %s"
                % (config["Configuration"]["FunctionArn"], runtime, architecture)
            )
            return False

        new_relic_layer = layer_selection(available_layers, runtime, architecture)

    update_kwargs = {
        "FunctionName": config["Configuration"]["FunctionArn"],
        "Environment": {
            "Variables": config["Configuration"]
            .get("Environment", {})
            .get("Variables", {})
        },
        "Layers": [new_relic_layer] + existing_layers,
    }

    # We don't want to modify the handler if the NewRelicLambdaExtension layer
    # has been selected
    if any("NewRelicLambdaExtension" in s for s in new_relic_layer):
        runtime_handler = None

    # Only used by Python, Node.js, Ruby, and Java runtimes not using the
    # NewRelicLambdaExtension layer
    if runtime_handler:
        update_kwargs["Handler"] = runtime_handler

    # Update the account id
    update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = str(
        input.nr_account_id
    )

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if runtime_handler and handler != runtime_handler:
        if "nodejs" in runtime:
            if handler not in [
                "newrelic-lambda-wrapper.handler",
                "/opt/nodejs/node_modules/newrelic-esm-lambda-wrapper/index.handler",
            ]:
                update_kwargs["Environment"]["Variables"][
                    "NEW_RELIC_LAMBDA_HANDLER"
                ] = handler
        else:
            update_kwargs["Environment"]["Variables"][
                "NEW_RELIC_LAMBDA_HANDLER"
            ] = handler

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

    if "dotnet" in runtime:
        update_kwargs["Environment"]["Variables"]["CORECLR_ENABLE_PROFILING"] = "1"
        update_kwargs["Environment"]["Variables"][
            "CORECLR_PROFILER"
        ] = "{36032161-FFC0-4B61-B559-F6C5D41BAE5A}"
        update_kwargs["Environment"]["Variables"][
            "CORECLR_NEWRELIC_HOME"
        ] = "/opt/lib/newrelic-dotnet-agent"
        update_kwargs["Environment"]["Variables"][
            "CORECLR_PROFILER_PATH"
        ] = "/opt/lib/newrelic-dotnet-agent/libNewRelicProfiler.so"

    if input.apm:
        success(
            "Enabling APM Lambda mode for function '%s' "
            % config["Configuration"]["FunctionArn"]
        )
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_APM_LAMBDA_MODE"] = "True"

    return update_kwargs


@catch_boto_errors
def install(input, function_arn):
    assert isinstance(input, LayerInstall)

    client = input.session.client("lambda")

    config = get_function(input.session, function_arn)
    if not config:
        failure("Could not find function: %s" % function_arn)
        return False

    _, nr_account_id, policy_arn = _get_license_key_outputs(input.session)

    # If a managed secret exists but it was created with a different NR account
    # id and license key We want to notify the user and point them to
    # documentation on how to proceed.
    if (
        policy_arn
        and nr_account_id
        and nr_account_id != str(input.nr_account_id)
        and not input.nr_api_key
    ):
        raise click.UsageError(
            "A managed secret already exists in this region for New Relic account {0}. "
            "Creating one managed secret per region is currently supported via "
            "the cli. To set up an additional secret for New Relic account {1} "
            "see our docs:\n{2}.\n"
            "Or you can re-run this command with "
            "`--nr-api-key` argument with your New Relic API key to set your license "
            "key in a NEW_RELIC_LICENSE_KEY environment variable instead.".format(
                nr_account_id, input.nr_account_id, utils.NR_DOCS_ACT_LINKING_URL
            )
        )
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
    if (
        not policy_arn
        or nr_account_id != str(input.nr_account_id)
        and input.nr_api_key
        and input.nr_region
    ):
        gql = api.validate_gql_credentials(input)
        nr_license_key = api.retrieve_license_key(gql)

    update_kwargs = _add_new_relic(input, config, nr_license_key)
    if isinstance(update_kwargs, bool):
        return update_kwargs

    try:
        res = client.update_function_configuration(**update_kwargs)
        if input.apm:
            client.tag_resource(
                Resource=config["Configuration"]["FunctionArn"],
                Tags={
                    "NR.Apm.Lambda.Mode": "true",
                },
            )
            success("Successfully added APM tag to the function")
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

        old_layers = config["Configuration"].get("Layers", [])
        old_layer_arn = old_layers[0]["Arn"].rsplit(":", 1)[0] if old_layers else "None"
        old_layer_version = (
            old_layers[0]["Arn"].split(":")[-1] if old_layers else "None"
        )
        new_layer = update_kwargs["Layers"][0]
        new_layer_arn = update_kwargs["Layers"][0].rsplit(":", 1)[0]
        new_layer_version = update_kwargs["Layers"][0].split(":")[-1]

        if old_layer_arn == "None":
            success(
                "Successfully installed Layer ARN %s for the function: %s"
                % (new_layer, function_arn)
            )
        else:
            success(
                "Successfully upgraded Layer ARN %s from version: %s to version: %s for the function: %s"
                % (new_layer_arn, old_layer_version, new_layer_version, function_arn)
            )
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

    # For java runtimes we need to remove the method name before
    # validating because method names are variable
    if "java" in runtime:
        handler = handler.split("::", 1)[0] + "::"

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


@catch_boto_errors
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
        _, _, policy_arn = _get_license_key_outputs(input.session)
        if policy_arn:
            _detach_license_key_policy(
                input.session, config["Configuration"]["Role"], policy_arn
            )

        if input.verbose:
            click.echo(json.dumps(res, indent=2))

        old_layers = config["Configuration"].get("Layers", [])
        old_layer_arn = old_layers[0]["Arn"] if old_layers else "None"
        success(
            "Successfully uninstalled Layer %s from %s" % (old_layer_arn, function_arn)
        )
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
