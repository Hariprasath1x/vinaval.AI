import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend directory to Python path so IDEs and Alembic can resolve 'app'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so Alembic can detect them
from app.models import *  # noqa
from app.core.database import Base
from app.core.config import get_settings

settings = get_settings()
config = context.config

# Build a SYNCHRONOUS URL for Alembic (replaces async drivers)
raw_url = settings.DATABASE_URL
if "postgresql+asyncpg" in raw_url:
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
elif "sqlite+aiosqlite" in raw_url:
    sync_url = raw_url.replace("sqlite+aiosqlite", "sqlite")
else:
    sync_url = raw_url

config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
