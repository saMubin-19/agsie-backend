from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
import random

from app.db.session import get_db
from app.models.field import Field
from app.schemas.field import FieldCreate

router = APIRouter()


# =========================
# CREATE FIELD (POST)
# =========================
@router.post("/fields")
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    """
    Save field geometry into PostGIS
    """
    try:
        geom_shape = shape(payload.geometry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GeoJSON geometry")

    # Rough conversion (mock but realistic for now)
    area_ha = geom_shape.area * 12365
    ndvi = random.choice(["Healthy", "Moderate", "Poor"])

    field = Field(
        area_hectares=round(area_ha, 2),
        ndvi_status=ndvi,
        geometry=from_shape(geom_shape, srid=4326),
    )

    db.add(field)
    db.commit()
    db.refresh(field)

    return {
        "message": "Field saved",
        "id": field.id,
        "area_hectares": field.area_hectares,
        "ndvi_status": field.ndvi_status,
    }


# =========================
# LIST FIELDS (GET) – GEOJSON
# =========================
@router.get("/fields")
def list_fields(db: Session = Depends(get_db)):
    """
    Return all fields with geometry as GeoJSON
    """
    fields = db.query(Field).all()

    return [
        {
            "id": f.id,
            "area_hectares": f.area_hectares,
            "ndvi_status": f.ndvi_status,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    list(to_shape(f.geometry).exterior.coords)
                ],
            },
        }
        for f in fields
    ]


# =========================
# DELETE FIELD (DELETE)
# =========================
@router.delete("/fields/{field_id}")
def delete_field(field_id: int, db: Session = Depends(get_db)):
    """
    Delete a field by ID
    """
    field = db.query(Field).filter(Field.id == field_id).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    db.delete(field)
    db.commit()

    return {
        "message": "Field deleted",
        "id": field_id,
    }





