import requests


STAC_URL = "https://earth-search.aws.element84.com/v1/search"


def search_latest_scene(bbox):
    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "limit": 1,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }

    response = requests.post(STAC_URL, json=payload)
    response.raise_for_status()

    data = response.json()

    if not data["features"]:
        return None

    item = data["features"][0]

    return {
        "red": item["assets"]["B04"]["href"],
        "nir": item["assets"]["B08"]["href"],
        "date": item["properties"]["datetime"],
    }