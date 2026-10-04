from sqlalchemy import create_engine, text
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
engine_options = {"connect_args": connect_args}
if database_url.startswith("postgresql"):
    # Each API worker keeps a small, bounded pool. A managed PgBouncer pool in
    # production absorbs bursts across multiple service instances.
    engine_options.update(
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
    )
engine = create_engine(database_url, **engine_options)

# Render and the local Docker database both include pgvector. Creating the
# extension here makes a new managed database ready before SQLAlchemy creates
# the `vector(128)` embedding column during application startup.
if database_url.startswith("postgresql"):
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
