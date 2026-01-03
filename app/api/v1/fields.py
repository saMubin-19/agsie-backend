from fastapi import APIRouter, HTTPException
from app.schemas.field import FieldCreate

router = APIRouter()

def calculate_area_hectares(coordinates):
    """
    Very simple polygon area estimation (demo logic)
    """
    points = coordinates[0]
    area = 0.0

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += (x1 * y2) - (x2 * y1)

    area = abs(area) / 2

    # rough conversion factor (mock)
    return round(area * 100, 2)

def ndvi_status_from_area(area):
    """
    Mock NDVI logic
    """
    if area < 1:
        return "Poor"
    elif area < 3:
        return "Moderate"
    else:
        return "Healthy"

@router.post("/fields")
def analyze_field(field: FieldCreate):
    if field.geometry.type != "Polygon":
        raise HTTPException(status_code=400, detail="Only Polygon supported")

    coords = field.geometry.coordinates
    area_ha = calculate_area_hectares(coords)
    ndvi_status = ndvi_status_from_area(area_ha)

    return {
        "message": "Field analyzed",
        "area_hectares": area_ha,
        "ndvi_status": ndvi_status,
        "recommendation": "Maintain irrigation" if ndvi_status == "Healthy" else "Increase monitoring"
    }


