from app.db.database import Base

# Import models here so Alembic detects them
from app.models.user import User
from app.models.field import Field
from app.models.field_analysis import FieldAnalysis
