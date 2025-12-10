from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from api.db.base_model import Base
from api.v1.models.user import User
from api.v1.models.wallet import Wallet
from api.v1.models.api_key import APIKey
from api.v1.models.transaction import Transaction
from api.v1.models.webhook_log import WebhookLog

config = context.config

# Set sqlalchemy.url from environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DATABASE_URLS = {
    "development": os.getenv("DATABASE_URL"),
    "staging": os.getenv("STAGING_DATABASE_URL"),
    "production": os.getenv("PRODUCTION_DATABASE_URL")
}
DATABASE_URL = DATABASE_URLS.get(ENVIRONMENT)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

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
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()