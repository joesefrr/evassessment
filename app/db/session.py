from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session and guarantee cleanup after request handling."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
