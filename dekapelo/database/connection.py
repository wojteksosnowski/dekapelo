import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "dekapelo.db"
DATABASE_URL = os.environ.get("DEKAPELO_DB_URL", f"sqlite:///{DEFAULT_DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generator sesji bazy danych."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_override=None):
    """Inicjalizacja schematu bazy danych."""
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
