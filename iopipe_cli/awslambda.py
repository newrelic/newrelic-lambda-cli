from . import layers
from . import utils


def list_functions(region, quiet, filter_choice):
    AwsLambda = utils.get_lambda_client(region)

    # set all if the filter_choice is "all" or there is no filter_choice active.
    all = filter_choice == "all" or not filter_choice

    next_marker = None
    while True:
        list_func_args = {}
        if next_marker:
            list_func_args = {'Marker': next_marker}
        func_resp = AwsLambda.list_functions(**list_func_args)
        next_marker = func_resp.get("NextMarker", None)
        funcs = func_resp.get("Functions", [])

        for f in funcs:
            runtime = f.get("Runtime")
            if is_valid_handler(runtime, f.get("Handler")):
                f["-x-iopipe-enabled"] = True
                if not all and filter_choice != "installed":
                    continue
            elif not all and filter_choice == "installed":
                continue
            yield f

        if not next_marker:
            break

class MultipleLayersException(Exception):
    pass

class UpdateLambdaException(Exception):
    pass

def apply_function_api(region, function_arn, layer_arn, token, java_type):
    AwsLambda = utils.get_lambda_client(region)
    info = AwsLambda.get_function(FunctionName=function_arn)
    runtime = info.get('Configuration', {}).get('Runtime', '')
    orig_handler = info.get('Configuration', {}).get('Handler')
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get('Handler')

    if runtime.startswith('java'):
        if not java_type:
            raise UpdateLambdaException("Must specify a handler type for java functions.")
        runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get('Handler', {}).get(java_type)

    if runtime == 'provider' or runtime not in utils.RUNTIME_CONFIG.keys():
        raise UpdateLambdaException("Unsupported Lambda runtime: %s" % (runtime,))
    if orig_handler == runtime_handler:
        raise UpdateLambdaException("Already configured.")

    iopipe_layers = []
    existing_layers = []
    if layer_arn:
        iopipe_layers = [layer_arn]
    else:
        # compatible layers:
        disco_layers = utils.get_layers(region, runtime)
        if len(iopipe_layers) > 1:
            print("Discovered layers for runtime (%s)" % (runtime,))
            for layer in disco_layers:
                print("%s\t%s" % (layer.get("LatestMatchingVersion", {}).get("LayerVersionArn", ""), layer.get("Description", "")))
            raise MultipleLayersException()
        iopipe_layers = [ disco_layers[0].get("LatestMatchingVersion", {}).get("LayerVersionArn", "") ]
        existing_layers = info.get('Configuration', {}).get('Layers', [])

    update_kwargs = {
        'FunctionName': function_arn,
        'Handler': runtime_handler,
        'Environment': {
            'Variables': {
                'IOPIPE_TOKEN': token
            }
        },
        'Layers': iopipe_layers + existing_layers
    }
    if runtime.startswith('java'):
        update_kwargs['Environment']['Variables']['IOPIPE_GENERIC_HANDLER'] = orig_handler
    else:
        update_kwargs['Environment']['Variables']['IOPIPE_HANDLER'] = orig_handler
    return AwsLambda.update_function_configuration(**update_kwargs)

def is_valid_handler(runtime, handler):
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get('Handler', None)
    if isinstance(runtime_handler, dict):
        for _, valid_handler in runtime_handler.items():
            if handler == valid_handler:
                return True
        return False
    elif handler == runtime_handler:
        return True
    return False

def remove_function_api(region, function_arn, layer_arn):
    AwsLambda = utils.get_lambda_client(region)
    info = AwsLambda.get_function(FunctionName=function_arn)
    runtime = info.get('Configuration', {}).get('Runtime', '')
    orig_handler = info.get('Configuration', {}).get('Handler', '')

    if runtime == 'provider' or runtime not in utils.RUNTIME_CONFIG.keys():
        raise UpdateLambdaException("Unsupported Lambda runtime: %s" % (runtime,))

    # Detect non-IOpipe handler and error if necessary.
    if not is_valid_handler(runtime, orig_handler):
        raise UpdateLambdaException(
            "IOpipe installation (via layers) not auto-detected for the specified function.\n" \
            "Error: Unrecognized handler in deployed function."
        )

    env_handler = info.get('Configuration', {}).get('Environment', {}).get('Variables', {}).get('IOPIPE_HANDLER')
    env_alt_handler = info.get('Configuration', {}).get('Environment', {}).get('Variables', {}).get('IOPIPE_GENERIC_HANDLER')
    if not (env_handler or env_alt_handler):
        raise UpdateLambdaException(
            "IOpipe installation (via layers) not auto-detected for the specified function.\n" + \
            "Error: Environment variable IOPIPE_HANDLER or IOPIPE_GENERIC_HANDLER not found."
        )

    # Delete IOpipe env vars
    for key in ['IOPIPE_HANDLER', 'IOPIPE_GENERIC_HANDLER', 'IOPIPE_TOKEN']:
        try:
            del info['Configuration']['Environment']['Variables'][key]
        except KeyError:
            pass

    # Remove IOpipe layers
    layers = info.get('Configuration', {}).get('Layers', [])
    for layer_idx, layer_arn in enumerate(layers):
        if layer_arn['Arn'].startswith(utils.get_arn_prefix(region)):
            del layers[layer_idx]

    return AwsLambda.update_function_configuration(
        FunctionName=function_arn,
        Handler=env_handler,
        Environment=info['Configuration']['Environment'],
        Layers=layers
    )
