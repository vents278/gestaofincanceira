import os

from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401 -- register model metadata for autogeneration
from app.database import Base

url = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url).connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()
