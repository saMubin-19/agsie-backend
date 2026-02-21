from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class FieldAnalysis(Base):
    __tablename__ = "field_analysis"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id", ondelete="CASCADE"))
    ndvi_mean = Column(Float, nullable=False)
    scene_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    field = relationship("Field", back_populates="analyses")