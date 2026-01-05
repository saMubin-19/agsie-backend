from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
import random

from app.db.session import get_db
from app.models.field import Field
from app.schemas.field import FieldCreate

router = APIRouter()

@router.post("/fields")
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    geom_shape = shape(payload.geometry)

    area_ha = geom_shape.area * 12365  # rough lat/lon → hectares
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


@router.get("/fields")
def list_fields(db: Session = Depends(get_db)):
    fields = db.query(Field).all()

    return [
        {
            "id": f.id,
            "area_hectares": f.area_hectares,
            "ndvi_status": f.ndvi_status,
        }
        for f in fields
    ]



