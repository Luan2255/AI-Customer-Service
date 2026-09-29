from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# Reuse pooled database connections and validate them before checkout.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# Keep request sessions explicit and prevent commits from expiring returned ORM objects.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request and always close it afterward."""
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()