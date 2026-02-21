from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agsie:agsie@db:5432/agsie_db"
)

engine = create_engine(DATABASE_URL, echo=True)

Base = declarative_base()

