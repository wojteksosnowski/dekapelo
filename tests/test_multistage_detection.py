import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from dekapelo.ingestion.kpi_parser import KPIParser
from dekapelo.ui.app import app
from dekapelo.database.connection import SessionLocal
from dekapelo.database.models import InvestmentProject, ProjectPhase


@pytest.fixture
def client():
    return TestClient(app)


def test_detect_multistage_morska_vita():
    """Weryfikuje detekcję wieloetapowości (Pattern A) w Morska Vita II - VIII.xlsx."""
    file_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Morska Vita II - VIII.xlsx"
    if not file_path.exists():
        pytest.skip(f"Brak pliku {file_path}")

    parser = KPIParser(str(file_path))
    stages = parser.detect_multistage()

    assert len(stages) >= 7, "Powinno wykryć co najmniej 7 etapów w Morska Vita"

    # Weryfikacja powiązania etapu z fazą projektu
    etap_2 = next((s for s in stages if "ETAP 2" in s["stage_name"].upper()), None)
    assert etap_2 is not None, "Powinien wykryć ETAP 2"
    assert etap_2["phase_name"] == "PW", f"ETAP 2 powinien mieć fazę PW, ma {etap_2['phase_name']}"
    assert etap_2["pum_preview"] is not None and etap_2["pum_preview"] > 0, "ETAP 2 powinien mieć wyliczony PUM"

    etap_4 = next((s for s in stages if "ETAP 4" in s["stage_name"].upper()), None)
    assert etap_4 is not None, "Powinien wykryć ETAP 4"
    assert etap_4["phase_name"] == "PB", f"ETAP 4 powinien mieć fazę PB, ma {etap_4['phase_name']}"

    # Weryfikacja odznaczenia sum i zestawień całościowych
    sum_stages = [s for s in stages if any(w in s["stage_name"].upper() for w in ["SUMA", "RAZEM", "CAŁOŚĆ"])]
    for ss in sum_stages:
        assert ss["selected"] is False, f"Kolumna podsumowania {ss['stage_name']} powinna być domyślnie odznaczona"


def test_detect_multistage_ock5():
    """Weryfikuje detekcję wieloetapowości (Pattern B) w OCK5 - T10, T11, T12.xlsx."""
    file_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "OCK5 - T10, T11, T12.xlsx"
    if not file_path.exists():
        pytest.skip(f"Brak pliku {file_path}")

    parser = KPIParser(str(file_path))
    stages = parser.detect_multistage()

    assert len(stages) >= 3, "Powinno wykryć co najmniej 3 tereny/etapy w OCK5"

    stage_names = [s["stage_name"] for s in stages]
    assert any("10" in name for name in stage_names), "Powinien wykryć Teren 10"
    assert any("11" in name for name in stage_names), "Powinien wykryć Teren 11"
    assert any("12" in name for name in stage_names), "Powinien wykryć Teren 12"


def test_selective_parsing_morska_vita():
    """Weryfikuje wybiórcze parsowanie wybranych etapów (np. użytkownik odznacza niechciane etapy)."""
    file_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Morska Vita II - VIII.xlsx"
    if not file_path.exists():
        pytest.skip(f"Brak pliku {file_path}")

    parser = KPIParser(str(file_path))
    stages = parser.detect_multistage()

    # Wybieramy tylko pierwsze dwa wyselekcjonowane etapy
    selected = [s for s in stages if s.get("selected", True)][:2]
    assert len(selected) == 2

    # Parsujemy tylko te 2 etapy
    parsed = parser.parse(selected_stages=selected)
    assert len(parsed) == 2, f"Oczekiwano sparsowania dokładnie 2 etapów, sparsowano: {len(parsed)}"

    for phase_key, pdata in parsed.items():
        assert "stage_name" in pdata, "Dane etapu powinny zawierać pole stage_name"
        assert pdata["pum"] is not None and pdata["pum"] > 0


def test_api_multistage_flow(client):
    """Weryfikuje pełny przepływ API: /api/parse-staging z plikiem wieloetapowym i /api/save-project."""
    file_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Morska Vita II - VIII.xlsx"
    if not file_path.exists():
        pytest.skip(f"Brak pliku {file_path}")

    with open(file_path, "rb") as f:
        response = client.post(
            "/api/parse-staging",
            files={"file": ("Morska Vita II - VIII.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 200
    data = response.json()

    assert data["is_multistage"] is True
    assert len(data["detected_stages"]) >= 7
    assert len(data["phases_data"]) >= 7

    # Symulujemy użytkownika, który wybiera do importu tylko 2 konkretne etapy z własnymi nazwami
    phases_list = list(data["phases_data"].values())
    chosen_phases = [
        {
            **phases_list[0],
            "stage_name": "Etap II (Zatwierdzony)",
            "phase_name": "PW"
        },
        {
            **phases_list[1],
            "stage_name": "Etap III (Planowany)",
            "phase_name": "PB"
        }
    ]

    save_payload = {
        "project_name": "Morska Vita Test MultiStage",
        "city": "Gdynia",
        "district": "Grabówek",
        "developer": "Develia",
        "notes": "Test wieloetapowego importu z UI",
        "source_filename": "Morska Vita II - VIII.xlsx",
        "phases_data": chosen_phases
    }

    save_res = client.post("/api/save-project", json=save_payload)
    assert save_res.status_code == 200
    save_json = save_res.json()
    assert save_json["status"] == "OK"
    project_id = save_json["project_id"]

    try:
        # Weryfikacja w bazie danych
        with SessionLocal() as session:
            proj = session.query(InvestmentProject).filter_by(id=project_id).first()
            assert proj is not None
            assert len(proj.phases) == 2

            phase_stages = [ph.stage_name for ph in proj.phases]
            assert "Etap II (Zatwierdzony)" in phase_stages
            assert "Etap III (Planowany)" in phase_stages

            # Weryfikacja display_name
            for ph in proj.phases:
                assert f"({ph.phase_name})" in ph.display_name

    finally:
        # Sprzątanie po teście
        del_res = client.delete(f"/api/projects/{project_id}")
        assert del_res.status_code == 200
