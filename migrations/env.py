from __future__ import annotations
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from apps.control_api.models import Base
from packages.contracts_python.settings import get_settings
config=context.config
if config.config_file_name: fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url",get_settings().database_url.replace("%","%%"))
target_metadata=Base.metadata

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"),target_metadata=target_metadata,literal_binds=True,compare_type=True)
    with context.begin_transaction(): context.run_migrations()
async def run_async():
    connectable=async_engine_from_config(config.get_section(config.config_ini_section,{}),prefix="sqlalchemy.",poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(lambda conn: context.configure(connection=conn,target_metadata=target_metadata,compare_type=True))
        await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()
def run_migrations_online(): asyncio.run(run_async())
if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
