import click
import requests

from . import utils


def index(region, runtime):
    req = requests.get(
        f"https://{region}.nr-layers.iopipe.com/get-layers?CompatibleRuntime={runtime}"
    )
    layers_response = req.json()
    return layers_response.get("Layers", [])


def _add_new_relic(config, region, layer_arn, account_id, allow_upgrade):
    runtime = config["Configuration"]["Runtime"]
    if runtime not in utils.RUNTIME_CONFIG:
        raise click.UsageError("Unsupported Lambda runtime: %s" % runtime)

    handler = config["Configuration"]["Handler"]
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get("Handler")
    if not allow_upgrade and handler == runtime_handler:
        raise click.UsageError(
            "Already installed. Pass --upgrade (or -u) to allow upgrade or "
            "reinstall to latest layer version."
        )

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
        available_layers = utils.get_layers(region, runtime)

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
        "Handler": runtime_handler,
        "Environment": {
            "Variables": config["Configuration"]["Environment"]["Variables"]
        },
        "Layers": new_relic_layers + existing_layers,
    }

    # Update the account id
    update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = str(account_id)

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if handler != runtime_handler:
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"] = handler

    return update_kwargs


def install(session, function_arn, layer_arn, account_id, allow_upgrade):
    client = session.client("lambda")
    config = client.get_function(FunctionName=function_arn)
    region = session.region_name
    update_kwargs = _add_new_relic(config, region, layer_arn, account_id, allow_upgrade)
    return client.update_function_configuration(**update_kwargs)


def _remove_new_relic(config, region):
    runtime = config["Configuration"]["Runtime"]
    if runtime not in utils.RUNTIME_CONFIG:
        raise click.UsageError("Unsupported Lambda runtime: %s" % runtime)

    handler = config["Configuration"]["Handler"]

    # Detect non-New Relic handler and error if necessary.
    if not utils.is_valid_handler(runtime, handler):
        raise click.UsageError(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function.\n"
            "Error: Unrecognized handler in deployed function."
        )

    env_handler = config["Configuration"]["Environment"]["Variables"].get(
        "NEW_RELIC_LAMBDA_HANDLER"
    )

    if not env_handler:
        raise click.UsageError(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function.\n"
            "Error: Environment variable NEW_RELIC_LAMBDA_HANDLER not "
            "found."
        )

    # Delete New Relic env vars
    config["Configuration"]["Environment"]["Variables"] = {
        key: value
        for key, value in config["Configuration"]["Environment"]["Variables"].items()
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


def uninstall(session, function_arn):
    client = session.client("lambda")
    config = client.get_function(FunctionName=function_arn)
    region = session.region_name
    update_kwargs = _remove_new_relic(config, region)
    return client.update_function_configuration(**update_kwargs)
