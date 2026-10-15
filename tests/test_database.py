import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dekapelo.database.connection import Base
from dekapelo.database.models import InvestmentProject, ProjectPhase, ProjectKPI, AuditLog
from dekapelo.analytics.bi_engine import BIEngine


@pytest.fixture
def db_session():
    """In-memory SQLite session for fast isolated tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_project_with_kpi(db_session):
    project = InvestmentProject(
        name="Osiedle Testowe",
        city="Gdańsk",
        district="Przymorze",
        developer="Inwestor Deweloper"
    )
    db_session.add(project)
    db_session.commit()

    phase = ProjectPhase(
        project_id=project.id,
        phase_name="Projekt Budowlany",
        source_file="test.xlsx"
    )
    db_session.add(phase)
    db_session.commit()

    kpi = ProjectKPI(
        phase_id=phase.id,
        pum=4500.0,
        puu=250.0,
        suma_pum_i_puu=4750.0,
        ilosc_lokali_mieszkalnych=90,
        srednia_wielkosc_mieszkania=50.0,
        suma_miejsc_parkingowych=110,
        wskaznik_mp=1.22
    )
    db_session.add(kpi)
    db_session.commit()

    # Weryfikacja odczytu
    saved = db_session.query(InvestmentProject).filter_by(name="Osiedle Testowe").first()
    assert saved is not None
    assert len(saved.phases) == 1
    assert saved.phases[0].kpi.pum == 4500.0

    # Test silnika BI
    bi = BIEngine(db_session)
    summary = bi.get_all_projects_summary()
    assert len(summary) == 1
    assert summary[0]["project_name"] == "Osiedle Testowe"
    assert summary[0]["phases"][0]["pum"] == 4500.0
