from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _use_psycopg3(url: str) -> str:
    # Managed Postgres providers (Render, Heroku-style hosts, etc.) hand back
    # "postgres://" or bare "postgresql://" — SQLAlchemy resolves either to the
    # psycopg2 driver by default, but only psycopg (v3) is installed here.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix) and "+psycopg" not in url.split("://", 1)[0]:
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


database_url = _use_psycopg3(settings.database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

