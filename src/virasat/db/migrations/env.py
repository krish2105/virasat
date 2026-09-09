from alembic import context
from sqlalchemy import engine_from_config, pool

from virasat.db.models import Base
from virasat.settings import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    # Never touch tables we do not own (PostGIS spatial_ref_sys, tiger, topology ...).
    if type_ == "table" and reflected and name not in target_metadata.tables:
        return False
    return True


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


run_migrations_online()
