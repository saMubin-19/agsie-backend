from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape, mapping

import io
import zipfile
import shapefile

from app.db.session import get_db
from app.models.field import Field
from app.models.user import User
from app.schemas.field import FieldCreate
from app.services.ndvi_engine import calculate_ndvi_status
from app.api.v1 import auth

from app.services.satellite.sentinel_loader import search_latest_scene
from app.services.satellite.ndvi_processor import compute_ndvi

router = APIRouter()



# =========================
# CRS VALIDATION HELPER
# =========================
def validate_geometry_crs(geom_shape):
    if geom_shape.geom_type != "Polygon":
        raise HTTPException(
            status_code=400,
            detail="Only Polygon geometries are supported"
        )

    for x, y in geom_shape.exterior.coords:
        if not (-180 <= x <= 180 and -90 <= y <= 90):
            raise HTTPException(
                status_code=400,
                detail="Coordinates must be in WGS84 (EPSG:4326)"
            )



# =========================
# CREATE FIELD (POST)
# =========================
@router.post("/fields")
def create_field(
    payload: FieldCreate,
    db: Session = Depends(get_db),
   current_user: User = Depends(auth.get_current_user)
):
    try:
        geom_shape = shape(payload.geometry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GeoJSON geometry")
    
    validate_geometry_crs(geom_shape)
    # Accurate PostGIS area calculation
    wkt = geom_shape.wkt
    area_m2 = db.query(
        func.ST_Area(func.ST_GeogFromText(wkt))
    ).scalar()

    if area_m2 is None:
        raise HTTPException(status_code=400, detail="Failed to calculate area")

    area_ha = area_m2 / 10000
    ndvi = calculate_ndvi_status(area_ha)

    field = Field(
        area_hectares=round(area_ha, 2),
        ndvi_status=ndvi,
        geometry=from_shape(geom_shape, srid=4326),
        user_id=current_user.id,
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
def list_fields(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    # Prevent abuse
    limit = min(limit, 100)

    fields = (
        db.query(Field)
        .filter(Field.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(Field).filter(
        Field.user_id == current_user.id
    ).count()

    result = []
    for f in fields:
        geom = to_shape(f.geometry)
        result.append({
            "id": f.id,
            "area_hectares": f.area_hectares,
            "ndvi_status": f.ndvi_status,
            "geometry": mapping(geom),
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result,
    }



# =========================
# UPDATE FIELD
# =========================
@router.patch("/fields/{field_id}")
def update_field_geometry(
    field_id: int,
    payload: FieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    try:
        geom_shape = shape(payload.geometry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GeoJSON geometry")
    
    validate_geometry_crs(geom_shape)
    wkt = geom_shape.wkt
    area_m2 = db.query(
        func.ST_Area(func.ST_GeogFromText(wkt))
    ).scalar()

    if area_m2 is None:
        raise HTTPException(status_code=400, detail="Failed to calculate area")

    area_ha = area_m2 / 10000
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
# EXPORT GEOJSON
# =========================
@router.get("/fields/{field_id}/export/geojson")
def export_field_geojson(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

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
# EXPORT SHAPEFILE
# =========================
@router.get("/fields/{field_id}/export/shapefile")
def export_field_shapefile(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

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
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    db.delete(field)
    db.commit()

    return {
        "message": "Field deleted",
        "id": field_id,
    }


# =========================
# ANALYZE FIELD (NDVI)
# =========================
@router.post("/fields/{field_id}/analyze")
def analyze_field_ndvi(
    field_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    field = db.query(Field).filter(
        Field.id == field_id,
        Field.user_id == current_user.id
    ).first()

    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    geom = to_shape(field.geometry)
    bbox = list(geom.bounds)

    scene = search_latest_scene(bbox)

    if not scene:
        raise HTTPException(status_code=404, detail="No satellite image found")

    ndvi_value = compute_ndvi(
        scene["red"],
        scene["nir"],
        geom
    )

    return {
        "field_id": field.id,
        "scene_date": scene["date"],
        "ndvi_mean": ndvi_value,
    }