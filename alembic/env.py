from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# Alembic Config object
config = context.config

# Override DB URL from environment
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------
# IMPORT YOUR REAL BASE + MODELS
# -------------------------------------------------
from app.db.base import Base
from app.models import user, field  # important: import models so metadata registers

target_metadata = Base.metadata


# -------------------------------------------------
# FILTER OUT POSTGIS SYSTEM TABLES
# -------------------------------------------------
def include_object(object, name, type_, reflected, compare_to):
    # Ignore PostGIS system schemas
    if hasattr(object, "schema") and object.schema in ["tiger", "topology"]:
        return False

    # Ignore PostGIS internal tables
    if type_ == "table" and name in [
        "spatial_ref_sys",
        "geometry_columns",
        "geography_columns",
        "raster_columns",
        "raster_overviews",
        "pg_stat_statements",
        "pg_type",
        "pg_attribute",
        "pg_class",
        "pg_namespace",
        "pg_index",
        "pg_constraint",
        "pg_proc",
        "pg_depend",
        "pg_description",
        "pagc_gaz",
        "pagc_lex",
    ]:
        return False

    return True


# -------------------------------------------------
# OFFLINE MIGRATIONS
# -------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------
# ONLINE MIGRATIONS
# -------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# -------------------------------------------------
# RUN
# -------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

