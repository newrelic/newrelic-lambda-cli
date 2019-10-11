import requests


def index(region, runtime):
    req = requests.get(
        f"https://{region}.layers.iopipe.com/get-layers?CompatibleRuntime={runtime}"
    )
    layers_response = req.json()
    return layers_response.get("Layers", [])
