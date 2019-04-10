# Copy-pasta from Stackoverflow: https://stackoverflow.com/questions/39997469/how-to-deep-merge-dicts
def combine_dict(map1: dict, map2: dict):
    def update(d: dict, u: dict):
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                r = update(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

    _result = {}
    update(_result, map1)
    update(_result, map2)
    return _result
