from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.models.scan import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS repository_url TEXT"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS deployment_approved BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS critical_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS high_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS medium_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS low_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE scans ADD COLUMN IF NOT EXISTS secrets_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE scans ALTER COLUMN project_id DROP NOT NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans(scan_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scans_started_at ON scans(started_at)"))
