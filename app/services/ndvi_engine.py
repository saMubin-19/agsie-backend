import random

def calculate_ndvi_status(area_hectares: float) -> str:
    """
    Mock AI NDVI logic (upgrade later to real Sentinel-2)
    """

    if area_hectares < 0.5:
        return "Poor"
    elif area_hectares < 2:
        return "Moderate"
    else:
        return "Healthy"


def get_recommendation(ndvi_status: str) -> str:
    if ndvi_status == "Healthy":
        return "Maintain irrigation"
    elif ndvi_status == "Moderate":
        return "Monitor crop stress"
    else:
        return "Immediate intervention required"
