from sqlalchemy import Column, Integer, Float, String
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    area_hectares = Column(Float, nullable=False)
    ndvi_status = Column(String, nullable=False)

    geometry = Column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )
