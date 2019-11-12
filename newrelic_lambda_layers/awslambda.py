from . import utils


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


class MultipleLayersException(Exception):
    pass


class UpdateLambdaException(Exception):
    pass


def _add_new_relic(config, region, function_arn, layer_arn, account_id, allow_upgrade):
    info = config.copy()
    runtime = info.get("Configuration", {}).get("Runtime", "")
    orig_handler = info.get("Configuration", {}).get("Handler")
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get("Handler")

    if not account_id:
        raise (UpdateLambdaException("Account ID missing from parameters."))

    if not allow_upgrade and orig_handler == runtime_handler:
        raise (
            UpdateLambdaException(
                "Already installed. Pass --upgrade (or -u) to allow upgrade or "
                "reinstall to latest layer version."
            )
        )

    if runtime not in utils.RUNTIME_CONFIG:
        raise UpdateLambdaException("Unsupported Lambda runtime: %s" % (runtime,))

    existing_layers = [
        layer.get("Arn")
        for layer in info.get("Configuration", {}).get("Layers", [])
        if not layer.get("Arn").startswith(utils.get_arn_prefix(region))
    ]

    new_relic_layers = []
    if layer_arn:
        new_relic_layers = [layer_arn]
    else:
        # discover compatible layers...
        disco_layers = utils.get_layers(region, runtime)
        if len(new_relic_layers) > 1:
            print("Discovered layers for runtime (%s)" % (runtime,))
            for layer in disco_layers:
                print(
                    "%s\t%s"
                    % (
                        layer.get("LatestMatchingVersion", {}).get(
                            "LayerVersionArn", ""
                        ),
                        layer.get("Description", ""),
                    )
                )
            raise MultipleLayersException()
        new_relic_layers = [
            disco_layers[0].get("LatestMatchingVersion", {}).get("LayerVersionArn", "")
        ]

    update_kwargs = {
        "FunctionName": function_arn,
        "Handler": runtime_handler,
        "Environment": {
            "Variables": info.get("Configuration", {})
            .get("Environment", {})
            .get("Variables", {})
        },
        "Layers": new_relic_layers + existing_layers,
    }

    # Update the account id
    update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = str(account_id)

    # Update the NEW_RELIC_LAMBDA_HANDLER envvars only when it's a new install.
    if orig_handler != runtime_handler:
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_LAMBDA_HANDLER"
        ] = orig_handler

    return update_kwargs


def install(session, function_arn, layer_arn, account_id, allow_upgrade):
    client = session.client("lambda")
    info = client.get_function(FunctionName=function_arn)
    update_kwargs = _add_new_relic(
        info, session.region_name, function_arn, layer_arn, account_id, allow_upgrade
    )
    return client.update_function_configuration(**update_kwargs)


def _remove_new_relic(config, region, function_arn, layer_arn):
    info = config.copy()
    runtime = info.get("Configuration", {}).get("Runtime", "")
    orig_handler = info.get("Configuration", {}).get("Handler", "")

    if runtime not in utils.RUNTIME_CONFIG:
        raise UpdateLambdaException("Unsupported Lambda runtime: %s" % (runtime,))

    # Detect non-New Relic handler and error if necessary.
    if not utils.is_valid_handler(runtime, orig_handler):
        raise UpdateLambdaException(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function.\n"
            "Error: Unrecognized handler in deployed function."
        )

    env_handler = (
        info.get("Configuration", {})
        .get("Environment", {})
        .get("Variables", {})
        .get("NEW_RELIC_LAMBDA_HANDLER")
    )

    if not env_handler:
        raise UpdateLambdaException(
            "New Relic installation (via layers) not auto-detected for the specified "
            "function.\n"
            "Error: Environment variable NEW_RELIC_LAMBDA_HANDLER not "
            "found."
        )

    # Delete New Relic env vars
    info["Configuration"]["Environment"]["Variables"] = {
        key: value
        for key, value in info["Configuration"]["Environment"]
        .get("Variables", {})
        .items()
        if not key.startswith("NEW_RELIC")
    }

    # Remove New Relic layers
    layers = [
        layer["Arn"]
        for layer in info["Configuration"].get("Layers", [])
        if not layer["Arn"].startswith(utils.get_arn_prefix(region))
    ]

    return {
        "FunctionName": function_arn,
        "Handler": env_handler,
        "Environment": info["Configuration"]["Environment"],
        "Layers": layers,
    }


def uninstall(session, function_arn, layer_arn):
    client = session.client("lambda")
    info = client.get_function(FunctionName=function_arn)
    update_kwargs = _remove_new_relic(
        info, session.region_name, function_arn, layer_arn
    )
    return client.update_function_configuration(**update_kwargs)
