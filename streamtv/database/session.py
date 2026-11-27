"""Database session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from ..config import config

Base = declarative_base()

engine = create_engine(
    config.database.url,
    connect_args={"check_same_thread": False} if "sqlite" in config.database.url else {},
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    # Import all models to ensure they're registered
    from . import models
    Base.metadata.create_all(bind=engine)
    try:
        from streamtv.backup.hooks import register_db_hooks

        register_db_hooks()
    except Exception:
        pass
    try:
        from pathlib import Path
        import subprocess

        root = Path(__file__).resolve().parents[2]
        for script_name in (
            "add_epg_sync_class_migration.py",
            "add_cached_media_failure_columns.py",
        ):
            script = root / "scripts" / script_name
            if script.is_file():
                subprocess.run(
                    [__import__("sys").executable, str(script)],
                    check=False,
                    capture_output=True,
                )
    except Exception:
        pass
