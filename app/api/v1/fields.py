from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape, mapping
import io
import zipfile
import shapefile  # pyshp

from app.db.session import get_db
from app.models.field import Field
from app.schemas.field import FieldCreate
from app.services.ndvi_engine import calculate_ndvi_status

router = APIRouter()




# =========================
# CREATE FIELD (POST)
# =========================
@router.post("/fields")
def create_field(payload: FieldCreate, db: Session = Depends(get_db)):
    try:
        geom_shape = shape(payload.geometry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GeoJSON geometry")

    area_ha = geom_shape.area * 12365  # mock conversion
    ndvi = calculate_ndvi_status(area_ha)

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
# LIST FIELDS (GET)
# =========================
@router.get("/fields")
def list_fields(db: Session = Depends(get_db)):
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
# UPDATE FIELD GEOMETRY (PATCH) — 4.5.1
# =========================
@router.patch("/fields/{field_id}")
def update_field_geometry(
    field_id: int,
    payload: FieldCreate,
    db: Session = Depends(get_db),
):
    field = db.query(Field).filter(Field.id == field_id).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    try:
        geom_shape = shape(payload.geometry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GeoJSON geometry")

    area_ha = geom_shape.area * 12365
    ndvi = calculate_ndvi_status(area_ha)

    field.geometry = from_shape(geom_shape, srid=4326)
    field.area_hectares = round(area_ha, 2)
    field.ndvi_status = ndvi

    db.commit()
    db.refresh(field)

    return {
        "message": "Field updated",
        "id": field.id,
        "area_hectares": field.area_hectares,
        "ndvi_status": field.ndvi_status,
    }


# =========================
# EXPORT FIELD — GEOJSON (4.4.1)
# =========================
@router.get("/fields/{field_id}/export/geojson")
def export_field_geojson(field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    geom = to_shape(field.geometry)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": field.id,
                    "area_hectares": field.area_hectares,
                    "ndvi_status": field.ndvi_status,
                },
                "geometry": mapping(geom),
            }
        ],
    }


# =========================
# EXPORT FIELD — SHAPEFILE (4.4.3)
# =========================
@router.get("/fields/{field_id}/export/shapefile")
def export_field_shapefile(field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    geom = to_shape(field.geometry)
    geojson_geom = mapping(geom)

    shp_io = io.BytesIO()
    shx_io = io.BytesIO()
    dbf_io = io.BytesIO()

    writer = shapefile.Writer(
        shp=shp_io,
        shx=shx_io,
        dbf=dbf_io,
        shapeType=shapefile.POLYGON,
    )

    writer.field("id", "N")
    writer.field("area_ha", "F", decimal=2)
    writer.field("ndvi", "C")

    writer.record(field.id, field.area_hectares, field.ndvi_status)
    writer.shape(geojson_geom)
    writer.close()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("field.shp", shp_io.getvalue())
        zipf.writestr("field.shx", shx_io.getvalue())
        zipf.writestr("field.dbf", dbf_io.getvalue())
        zipf.writestr(
            "field.prj",
            'GEOGCS["WGS 84",DATUM["WGS_1984",'
            'SPHEROID["WGS 84",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
        )

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=field-{field_id}.zip"
        },
    )


# =========================
# DELETE FIELD
# =========================
@router.delete("/fields/{field_id}")
def delete_field(field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    db.delete(field)
    db.commit()

    return {
        "message": "Field deleted",
        "id": field_id,
    }








