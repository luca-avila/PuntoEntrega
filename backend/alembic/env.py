import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
import features.models_registry  # noqa: F401
from features.auth.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
ALEMBIC_VERSION_MAX_LENGTH = 255


def get_database_url() -> str:
    """Resolve database URL from env first, then alembic.ini fallback."""
    database_url = os.getenv("DATABASE_URL") or config.get_main_option(
        "sqlalchemy.url"
    )
    if not database_url or database_url.startswith("driver://"):
        raise RuntimeError(
            "DATABASE_URL is not configured. Set DATABASE_URL or configure sqlalchemy.url in alembic.ini."
        )
    return database_url


database_url = get_database_url()
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    ensure_alembic_version_column_capacity(connection)
    # ensure_alembic_version_column_capacity may open an implicit transaction.
    # Commit it so Alembic can manage its own migration transaction boundary.
    if connection.in_transaction():
        connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def ensure_alembic_version_column_capacity(connection: Connection) -> None:
    """Ensure alembic_version.version_num can store long revision ids.

    Alembic creates version_num with VARCHAR(32) by default, but this project
    uses descriptive revision identifiers longer than 32 chars.
    """
    if connection.dialect.name != "postgresql":
        return

    connection.exec_driver_sql(
        f"""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR({ALEMBIC_VERSION_MAX_LENGTH}) NOT NULL PRIMARY KEY
        )
        """
    )
    current_length = connection.exec_driver_sql(
        """
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'alembic_version'
          AND column_name = 'version_num'
        """
    ).scalar_one_or_none()
    if current_length is not None and current_length < ALEMBIC_VERSION_MAX_LENGTH:
        connection.exec_driver_sql(
            f"""
            ALTER TABLE alembic_version
            ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_MAX_LENGTH})
            """
        )


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
