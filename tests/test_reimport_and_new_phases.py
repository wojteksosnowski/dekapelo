import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dekapelo.database.connection import Base

from dekapelo.ingestion.kpi_parser import (
    KPIParser,
    derive_stage_from_filename,
    derive_stage_and_phase,
    clean_text
)
from dekapelo.database.models import InvestmentProject, ProjectPhase, ProjectKPI
from dekapelo.ui.app import build_project_audit_context, _process_kpi_file


@pytest.fixture
def db_session():
    """In-memory SQLite session for fast isolated tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()


def test_derive_stage_from_filename():
    """Weryfikuje wnioskowanie nazw etapów i budynków ze ścieżek/nazw plików."""
    assert derive_stage_from_filename("C1C2.xlsx") == "Budynek C1-C2"
    assert derive_stage_from_filename("C3.xlsx") == "Budynek C3"
    assert derive_stage_from_filename("C6.xlsx") == "Budynek C6"
    assert derive_stage_from_filename("OCK5 - T15.xlsx") == "Teren 15"
    assert derive_stage_from_filename("T10-T14.xlsx") == "Teren 10-14"
    assert derive_stage_from_filename("Południe Vita V - VI.xlsx") == "Etap V - VI"
    assert derive_stage_from_filename("Zamojska Vita.xlsx") is None  # Domyślny fallback to Całość


def test_derive_stage_and_phase_clean_separation():
    """Weryfikuje, że etykiety są poprawnie rozdzielane na etap i fazę oraz nigdy nie są 'undefined'."""
    # Sama faza projektowa w etykiecie
    st, ph, disp = derive_stage_and_phase("Projekt Wykonawczy", filename="Zamojska Vita.xlsx")
    assert st == "Całość"
    assert ph == "PW"
    assert disp == "Całość (PW)"

    # APK w pliku C1C2
    st, ph, disp = derive_stage_and_phase("APK", filename="C1C2.xlsx")
    assert st == "Budynek C1-C2"
    assert ph == "APK"
    assert disp == "Budynek C1-C2 (APK)"

    # Etykieta zawierająca etap i fazę
    st, ph, disp = derive_stage_and_phase("ETAP 2 (PB)", filename="Morska Vita.xlsx")
    assert st == "ETAP 2"
    assert ph == "PB"
    assert disp == "ETAP 2 (PB)"

    # Etykieta etapu bez fazy
    st, ph, disp = derive_stage_and_phase("TEREN 4", default_phase="Koncepcja")
    assert st == "TEREN 4"
    assert ph == "Koncepcja"
    assert disp == "TEREN 4 (Koncepcja)"


def test_no_undefined_stages_across_all_kpi_files():
    """Weryfikuje niezmiennik zbioru danych: żaden plik KPI nie może produkować etapów o nazwie 'undefined', pustych lub None."""
    base_dir = Path("KPI - WSKAZNIKI")
    if not base_dir.exists():
        pytest.skip("Katalog KPI - WSKAZNIKI nie istnieje")

    for f_path in base_dir.rglob("*.*"):
        if f_path.suffix.lower() in [".xlsx", ".xls", ".ods"] and not f_path.name.startswith("~$"):
            parser = KPIParser(str(f_path))
            
            # Weryfikacja multistage
            ms = parser.detect_multistage()
            for s in ms:
                assert s.get("stage_name") is not None, f"Brak stage_name w {f_path.name}"
                assert s.get("stage_name") != "undefined", f"'undefined' jako stage_name w {f_path.name}"
                assert len(s.get("stage_name", "").strip()) > 0, f"Pusty stage_name w {f_path.name}"
                assert s.get("display_name") != "undefined", f"'undefined' jako display_name w {f_path.name}"

            # Weryfikacja tradycyjnego parse
            parsed = parser.parse()
            for k, data in parsed.items():
                st_name = data.get("stage_name")
                ph_name = data.get("phase_name")
                disp_name = data.get("display_name")
                assert st_name is not None and st_name != "undefined" and len(st_name.strip()) > 0
                assert ph_name is not None and ph_name != "undefined" and len(ph_name.strip()) > 0
                assert disp_name is not None and disp_name != "undefined" and len(disp_name.strip()) > 0


def test_exact_duplicate_file_detection(db_session: Session):
    """Weryfikuje wykrywanie 100% zduplikowanego pliku z identycznymi danymi."""
    proj = InvestmentProject(
        name="Test Duplikat Project",
        city="Warszawa",
        district="Bemowo"
    )
    db_session.add(proj)
    db_session.commit()

    phase = ProjectPhase(
        project_id=proj.id,
        stage_name="Etap 1",
        phase_name="PB",
        plot_type="wlasna"
    )
    db_session.add(phase)
    db_session.commit()

    kpi = ProjectKPI(
        phase_id=phase.id,
        pum=5000.0,
        puu=200.0,
        suma_pum_i_puu=5200.0,
        powierzchnia_dzialki=10000.0,
        ilosc_lokali_mieszkalnych=100,
        pow_calkowita_nadziemia=7000.0
    )
    db_session.add(kpi)
    db_session.commit()

    # Wgrywamy plik z identycznymi danymi dla tego samego etapu
    incoming_phases = {
        "Etap 1 (PB)": {
            "stage_name": "Etap 1",
            "phase_name": "PB",
            "display_name": "Etap 1 (PB)",
            "pum": 5000.0,
            "puu": 200.0,
            "suma_pum_i_puu": 5200.0,
            "powierzchnia_dzialki": 10000.0,
            "ilosc_lokali_mieszkalnych": 100,
            "pow_calkowita_nadziemia": 7000.0
        }
    }

    ctx = build_project_audit_context("Test Duplikat Project", incoming_phases, db_session)
    reimport = ctx["reimport_analysis"]

    assert reimport["is_existing_project"] is True
    assert reimport["is_exact_file_duplicate"] is True
    assert reimport["has_new_phases"] is False
    assert len(reimport["duplicate_phases"]) == 1
    assert reimport["duplicate_phases"][0]["status"] == "EXACT_DUPLICATE"


def test_new_phase_recognition_hierarchy_upgrade(db_session: Session):
    """Weryfikuje wykrywanie nowej fazy w hierarchii projektowej (PW zamiast istniejącej w bazie PB)."""
    proj = InvestmentProject(
        name="Nowa Faza Project",
        city="Gdańsk"
    )
    db_session.add(proj)
    db_session.commit()

    phase = ProjectPhase(
        project_id=proj.id,
        stage_name="Etap 1",
        phase_name="PB",  # W bazie jest PB (rank 3)
        plot_type="wlasna"
    )
    db_session.add(phase)
    db_session.commit()

    kpi = ProjectKPI(
        phase_id=phase.id,
        pum=4000.0,
        puu=0.0,
        suma_pum_i_puu=4000.0,
        powierzchnia_dzialki=8000.0,
        ilosc_lokali_mieszkalnych=80
    )
    db_session.add(kpi)
    db_session.commit()

    # Wgrywamy ten sam etap, ale w nowszej fazie wykonawczej PW (rank 4)
    incoming_phases = {
        "Etap 1 (PW)": {
            "stage_name": "Etap 1",
            "phase_name": "PW",
            "display_name": "Etap 1 (PW)",
            "pum": 4050.0,
            "puu": 0.0,
            "suma_pum_i_puu": 4050.0,
            "powierzchnia_dzialki": 8000.0,
            "ilosc_lokali_mieszkalnych": 81
        }
    }

    ctx = build_project_audit_context("Nowa Faza Project", incoming_phases, db_session)
    reimport = ctx["reimport_analysis"]

    assert reimport["is_existing_project"] is True
    assert reimport["is_exact_file_duplicate"] is False
    assert reimport["has_new_phases"] is True
    assert len(reimport["new_phases_detected"]) == 1
    
    np_entry = reimport["new_phases_detected"][0]
    assert np_entry["stage_name"] == "Etap 1"
    assert np_entry["new_phase"] == "PW"
    assert np_entry["existing_phase"] == "PB"
    assert np_entry["is_hierarchy_upgrade"] is True


def test_multistage_preselection_for_duplicates_and_new_phases(db_session: Session):
    """Weryfikuje, że w trybie multistage zduplikowane fazy są odznaczone, a nowe fazy są zaznaczone."""
    proj = InvestmentProject(
        name="Morska Vita",
        city="Gdynia"
    )
    db_session.add(proj)
    db_session.commit()

    # W bazie jest już Etap 1 w fazie PB z identycznymi metrażami
    ph1 = ProjectPhase(
        project_id=proj.id,
        stage_name="ETAP 1",
        phase_name="PB"
    )
    db_session.add(ph1)
    db_session.commit()
    k1 = ProjectKPI(
        phase_id=ph1.id,
        pum=6368.36,
        puu=2767.63,
        suma_pum_i_puu=9135.99,
        powierzchnia_dzialki=6750.0,
        ilosc_lokali_mieszkalnych=108,
        pow_calkowita_nadziemia=8761.9
    )
    db_session.add(k1)
    db_session.commit()

    # Tworzymy parser pliku z wieloma etapami
    morska_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Morska Vita II - VIII.xlsx"
    if not morska_path.exists():
        pytest.skip(f"Brak pliku {morska_path}")

    parser = KPIParser(str(morska_path))
    result = _process_kpi_file(parser, morska_path.name, db_session)

    detected = result["detected_stages"]
    reimport = result["reimport_analysis"]

    assert reimport["is_existing_project"] is True
    # Powinno wykryć nowe etapy dla Morskiej Vity (np. Etap 2, Etap 3...)
    assert reimport["has_new_phases"] is True

    # Etap 1 z PB powinien być oznaczony jako duplikat i odznaczony
    e1_cand = next((s for s in detected if clean_text(s.get("stage_name")) == "etap 1" and s.get("phase_name") == "PB"), None)
    if e1_cand:
        assert e1_cand.get("is_duplicate") is True
        assert e1_cand.get("selected") is False

    # Nowe etapy (np. Etap 2, 3) powinny być zaznaczone
    active_new = [s for s in detected if s.get("selected") and s.get("has_data") and not s.get("is_summary")]
    assert len(active_new) > 0


def test_reimport_banner_and_tabs_dom_structure():
    """Weryfikuje strukturę DOM: obecność #reimport-banner oraz poprawność izolacji rodzeństwa zakładek SPA."""
    template_path = Path("dekapelo/ui/templates/index.html")
    content = template_path.read_text(encoding="utf-8")

    # Sprawdzenie obecności banera reimportu
    assert 'id="reimport-banner"' in content, "Brak elementu #reimport-banner w index.html"
    assert 'id="reimport-banner-title"' in content
    assert 'id="reimport-banner-message"' in content

    # Niezmiennik izolacji zakładek SPA: sekcje .tab-content muszą być rodzeństwem w <main>
    assert '<section id="import-tab"' in content
    assert '<section id="catalog-tab"' in content
    assert '<section id="bi-tab"' in content


def test_derived_kpis_algebra_from_raw_data():
    """Weryfikuje, że wskaźniki są wyliczane ściśle algebraicznie z surowych danych fizycznych (m², sztuki)."""
    parser = KPIParser(None)
    data = {
        "pum": 4500.0,
        "puu": 500.0,
        "ilosc_lokali_mieszkalnych": 90,
        "ilosc_lokali_uslugowych": 5,
        "pow_calkowita_nadziemia": 6800.0,
        "pow_calkowita_balkonow_loggii": 450.0,
        "pow_calkowita_podziemia": 2200.0,
        "powierzchnia_dzialki": 5000.0,
        "powierzchnia_zabudowy": 1600.0,
        "powierzchnia_biologicznie_czynna": 1250.0,
        "suma_miejsc_parkingowych": 114,
        "ilosc_wind": 3,
        "ilosc_klatek_schodowych": 3,
        "mp_garaz_wszystkie": 80,
        "powierzchnia_elewacji": 3500.0
    }

    parser._calculate_derived_kpis(data)

    # 1. PUM + PUU = PUMiU
    assert data["suma_pum_i_puu"] == 5000.0
    # Lokale sumaryczne = 90 + 5 = 95
    assert data["suma_lokali"] == 95

    # 2. Nadziemie i balkony: Pcnb = Pcn + Plb = 6800 + 450 = 7250
    assert data["pow_calkowita_nadziemia_z_balkonami"] == 7250.0

    # 3. Pc = Pcn + Pcp = 6800 + 2200 = 9000
    assert data["powierzchnia_calkowita"] == 9000.0
    # Pcb = Pc + Plb = 9000 + 450 = 9450
    assert data["pow_calkowita_z_balkonami"] == 9450.0

    # 4. Sprawności
    # PUMiU / Pcn = 5000 / 6800 = 0.7353
    assert data["wskaznik_pumiu_pcn"] == round(5000.0 / 6800.0, 4)
    # PUMiU / Pcnb = 5000 / 7250 = 0.6897
    assert data["wskaznik_pumiu_pcnb"] == round(5000.0 / 7250.0, 4)
    # PUMiU / Pc = 5000 / 9000 = 0.5556
    assert data["wskaznik_pumiu_pc"] == round(5000.0 / 9000.0, 4)

    # Wskaźnik MP = 114 / 95 = 1.2
    assert data["wskaznik_mp"] == 1.2
    # ŚRM = 4500 / 90 = 50.0
    assert data["srednia_wielkosc_mieszkania"] == 50.0

    # Chłonność = 5000 / 5000 = 1.0
    assert data["wskaznik_pumiu_pd"] == 1.0
    # Wskaźnik zabudowy = 1600 / 5000 = 0.32
    assert data["wspolczynnik_powierzchni_zabudowy"] == 0.32
    # Wskaźnik zieleni = 1250 / 5000 = 0.25
    assert data["wskaznik_pow_biologicznie_czynnej"] == 0.25

    # Lokale / winda = 90 / 3 = 30.0
    assert data["wskaznik_ilm_iw"] == 30.0
    # Lokale / klatka = 90 / 3 = 30.0
    assert data["wskaznik_ilm_iks"] == 30.0
    # PUMiU / klatka = 5000 / 3 = 1666.67
    assert data["wskaznik_pumiu_klatka"] == round(5000.0 / 3, 2)


def test_bi_stages_latest_phase_only_and_display_name(db_session: Session):
    """Weryfikuje, że w BI pokazywane są wyłącznie najnowsze fazy danych etapów w formacie Etap (Faza)."""
    from dekapelo.analytics.bi_engine import BIEngine

    proj = InvestmentProject(name="Kacze Buki", city="Gdynia")
    db_session.add(proj)
    db_session.flush()

    # Kacze Buki ma 1 etap realizowany w 2 kolejnych fazach: APK -> WPK
    ph_apk = ProjectPhase(project_id=proj.id, stage_name="Całość", phase_name="APK")
    db_session.add(ph_apk)
    db_session.flush()
    kpi_apk = ProjectKPI(phase_id=ph_apk.id, pum=3000.0, suma_pum_i_puu=3000.0)
    db_session.add(kpi_apk)

    ph_wpk = ProjectPhase(project_id=proj.id, stage_name="Całość", phase_name="WPK")
    db_session.add(ph_wpk)
    db_session.flush()
    kpi_wpk = ProjectKPI(phase_id=ph_wpk.id, pum=3200.0, suma_pum_i_puu=3200.0)
    db_session.add(kpi_wpk)

    db_session.commit()

    # Weryfikacja display_name i is_leading
    assert ph_apk.display_name == "Całość (APK)"
    assert ph_wpk.display_name == "Całość (WPK)"
    assert ph_apk.is_leading is False
    assert ph_wpk.is_leading is True

    # Weryfikacja BIEngine get_all_projects_summary
    bi = BIEngine(db_session)
    summaries = bi.get_all_projects_summary()
    assert len(summaries) == 1
    p_summary = summaries[0]

    # Powinien raportować dokładnie 1 etap inwestycji w fazie WPK
    assert p_summary["stages_count"] == 1
    assert p_summary["leading_stages_count"] == 1
    assert len(p_summary["stages"]) == 1
    st0 = p_summary["stages"][0]
    assert st0["stage_name"] == "Całość"
    assert st0["phase_name"] == "WPK"
    assert st0["display_name"] == "Całość (WPK)"
    assert st0["is_leading"] is True
    assert st0["pum"] == 3200.0

    # Natomiast w pełnej historii phases (do audytu międzyfazowego i akordeonu katalogu) są obie fazy
    assert p_summary["phases_count"] == 2

