import json
import requests


def index(region, runtime):
    req = requests.get(
        "https://%s.layers.iopipe.com/get-layers?CompatibleRuntime=%s"
        % (region, runtime)
    )
    layers_response = json.loads(req.content)
    return layers_response.get("Layers", [])
