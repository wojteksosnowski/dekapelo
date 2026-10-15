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
    """Inicjalizacja schematu bazy danych z automatyczną migracją brakujących kolumn."""
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(target_engine)
        if "project_kpi" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("project_kpi")}
            with target_engine.connect() as conn:
                if "pum_iso" not in existing_cols:
                    conn.execute(text("ALTER TABLE project_kpi ADD COLUMN pum_iso FLOAT"))
                if "pum_pnb" not in existing_cols:
                    conn.execute(text("ALTER TABLE project_kpi ADD COLUMN pum_pnb FLOAT"))
                conn.commit()
        if "investment_projects" in inspector.get_table_names():
            existing_proj_cols = {col["name"] for col in inspector.get_columns("investment_projects")}
            with target_engine.connect() as conn:
                if "powierzchnia_dzialki" not in existing_proj_cols:
                    conn.execute(text("ALTER TABLE investment_projects ADD COLUMN powierzchnia_dzialki FLOAT"))
                conn.commit()
        if "project_phases" in inspector.get_table_names():
            existing_phase_cols = {col["name"] for col in inspector.get_columns("project_phases")}
            with target_engine.connect() as conn:
                if "stage_name" not in existing_phase_cols:
                    conn.execute(text("ALTER TABLE project_phases ADD COLUMN stage_name VARCHAR(100)"))
                if "plot_type" not in existing_phase_cols:
                    conn.execute(text("ALTER TABLE project_phases ADD COLUMN plot_type VARCHAR(50) DEFAULT 'nieokreslona'"))
                conn.commit()
    except Exception:
        pass

