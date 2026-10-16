import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


url = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
engine = create_engine(
    url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
)
if url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine)


def get_db():
    with SessionLocal() as db:
        yield db
