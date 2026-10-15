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
    stage = saved.phases[0]
    assert stage.kpi.pum == 4500.0
    assert stage.investment_name == "Osiedle Testowe"
    assert stage.stage_name == "Projekt Budowlany"

    # Test silnika BI
    bi = BIEngine(db_session)
    summary = bi.get_all_projects_summary()
    assert len(summary) == 1
    assert summary[0]["project_name"] == "Osiedle Testowe"
    assert summary[0]["phases"][0]["pum"] == 4500.0

    # Test pobrania etapów jako jednostki podstawowej
    stages = bi.get_all_stages()
    assert len(stages) == 1
    assert stages[0]["investment_name"] == "Osiedle Testowe"
    assert stages[0]["stage_name"] == "Projekt Budowlany"
    assert stages[0]["pum"] == 4500.0


def test_phase_hierarchy_and_leading_stages(db_session):
    """Weryfikuje regułę: każdy etap jest w jakiejś fazie, bierzemy pod uwagę tylko fazę najwyżej w hierarchii APK < WPK < PB < PW."""
    from dekapelo.database.models import get_phase_rank

    # 1. Weryfikacja rang hierarchii
    assert get_phase_rank("APK") < get_phase_rank("WPK") < get_phase_rank("PB") < get_phase_rank("PW")
    assert get_phase_rank("Koncepcja") <= get_phase_rank("WPK")
    assert get_phase_rank("Projekt Budowlany") == get_phase_rank("PB")
    assert get_phase_rank("Projekt Wykonawczy") == get_phase_rank("PW")

    # 2. Utworzenie projektu z etapami posiadającymi wiele faz
    proj = InvestmentProject(name="Hierarchia Test Project", city="Wrocław")
    db_session.add(proj)
    db_session.commit()

    # Etap 1: w fazach APK, PB oraz PW
    ph_e1_apk = ProjectPhase(project_id=proj.id, stage_name="Etap 1", phase_name="APK")
    ph_e1_pb = ProjectPhase(project_id=proj.id, stage_name="Etap 1", phase_name="PB")
    ph_e1_pw = ProjectPhase(project_id=proj.id, stage_name="Etap 1", phase_name="PW")

    # Etap 2: w fazach WPK i PB
    ph_e2_wpk = ProjectPhase(project_id=proj.id, stage_name="Etap 2", phase_name="WPK")
    ph_e2_pb = ProjectPhase(project_id=proj.id, stage_name="Etap 2", phase_name="PB")

    db_session.add_all([ph_e1_apk, ph_e1_pb, ph_e1_pw, ph_e2_wpk, ph_e2_pb])
    db_session.commit()

    # Dodanie KPI
    db_session.add_all([
        ProjectKPI(phase_id=ph_e1_apk.id, pum=1000.0, ilosc_lokali_mieszkalnych=20),
        ProjectKPI(phase_id=ph_e1_pb.id, pum=1100.0, ilosc_lokali_mieszkalnych=22),
        ProjectKPI(phase_id=ph_e1_pw.id, pum=1150.0, ilosc_lokali_mieszkalnych=23),  # najwyższa dla Etap 1
        ProjectKPI(phase_id=ph_e2_wpk.id, pum=2000.0, ilosc_lokali_mieszkalnych=40),
        ProjectKPI(phase_id=ph_e2_pb.id, pum=2100.0, ilosc_lokali_mieszkalnych=42),   # najwyższa dla Etap 2
    ])
    db_session.commit()

    # Weryfikacja leading_phases modelu
    assert len(proj.phases) == 5
    leading = proj.leading_phases
    assert len(leading) == 2

    e1_lead = next(ph for ph in leading if ph.stage_name == "Etap 1")
    assert e1_lead.phase_name == "PW"
    assert e1_lead.kpi.pum == 1150.0
    assert e1_lead.is_leading is True

    e2_lead = next(ph for ph in leading if ph.stage_name == "Etap 2")
    assert e2_lead.phase_name == "PB"
    assert e2_lead.kpi.pum == 2100.0
    assert e2_lead.is_leading is True

    # Weryfikacja poprzednich faz
    assert ph_e1_apk.is_leading is False
    assert ph_e1_pb.is_leading is False
    assert ph_e2_wpk.is_leading is False

    # Weryfikacja w silniku BI: sumaryczny PUM projektu liczy tylko fazy wiodące
    bi = BIEngine(db_session)
    summaries = bi.get_all_projects_summary()
    proj_summary = next(s for s in summaries if s["project_id"] == proj.id)
    assert proj_summary["leading_stages_count"] == 2
    # PUM wiodący to 1150 + 2100 = 3250 m² (nie 7350 m²)
    assert proj_summary["total_leading_pum"] == 3250.0
    assert proj_summary["total_leading_units"] == 65

    # Weryfikacja filtrowania etapów w get_all_stages(only_leading=True)
    all_stages = bi.get_all_stages(only_leading=False)
    assert len(all_stages) == 5
    leading_only = bi.get_all_stages(only_leading=True)
    assert len(leading_only) == 2
    assert {s["phase_name"] for s in leading_only} == {"PW", "PB"}
