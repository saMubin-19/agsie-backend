from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.db.database import Base   

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="fields")

    area_hectares = Column(Float, nullable=False)
    ndvi_status = Column(String, nullable=False)
    
    analyses = relationship(
    "FieldAnalysis",
    back_populates="field",
    cascade="all, delete"
)

    geometry = Column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False
    )



