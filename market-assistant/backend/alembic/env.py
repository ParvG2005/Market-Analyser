import asyncio
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def _run_migrations_online_sync() -> None:
    # command.upgrade() may be invoked from a test running inside an already
    # active asyncio event loop (e.g. pytest-asyncio). asyncio.run() cannot be
    # called from within a running loop, so run it on a dedicated thread with
    # its own loop when that's the case.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(run_migrations_online())
    else:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, run_migrations_online()).result()


if context.is_offline_mode():
    run_migrations_offline()
else:
    _run_migrations_online_sync()
