import pytest
from fastapi.testclient import TestClient
from dekapelo.ui.app import app
from pathlib import Path


@pytest.fixture
def client():
    return TestClient(app)


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "dekapelo" in response.text
    assert "Tailwind CSS" in response.text or "cdn.tailwindcss.com" in response.text


def test_parse_staging_and_save_api(client):
    dabka_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Dąbka Vita.xlsx"
    if not dabka_path.exists():
        pytest.skip(f"Brak pliku {dabka_path}")

    with open(dabka_path, "rb") as f:
        response = client.post(
            "/api/parse-staging",
            files={"file": ("Dąbka Vita.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "phases_data" in data
    assert "audit_by_phase" in data
    assert len(data["phases_data"]) > 0

    # Test zapisu do bazy
    save_payload = {
        "project_name": "Dąbka Vita Test API",
        "city": "Gdańsk",
        "district": "Orunia",
        "developer": "Develia",
        "notes": "Testowy zapis przez API",
        "source_filename": "Dąbka Vita.xlsx",
        "phases_data": data["phases_data"]
    }
    save_res = client.post("/api/save-project", json=save_payload)
    assert save_res.status_code == 200
    save_json = save_res.json()
    assert save_json["status"] == "OK"
    project_id = save_json["project_id"]

    # Test pobrania projektów
    projects_res = client.get("/api/projects")
    assert projects_res.status_code == 200
    all_projects = projects_res.json()
    saved = [p for p in all_projects if p["project_id"] == project_id]
    assert len(saved) == 1

    # Test usunięcia projektu
    del_res = client.delete(f"/api/projects/{project_id}")
    assert del_res.status_code == 200


def test_suggestions_api(client):
    res = client.get("/api/suggestions")
    assert res.status_code == 200
    data = res.json()
    assert "projects" in data
    assert "stages" in data
    assert "phases" in data
    assert "cities" in data
    assert "districts" in data
    assert "developers" in data
    assert "APK" in data["stages"]
    assert "APK" in data["phases"]
    assert "Projekt Budowlany" in data["stages"]


def test_compare_api_chlonnosc_scatter(client):
    # Najpierw zapisujemy projekt testowy z powierzchnią działki i PUM
    save_payload = {
        "project_name": "Test Scatter Project",
        "stage_name": "APK",
        "city": "Warszawa",
        "district": "Wola",
        "developer": "Deweloper Test",
        "notes": "Test chłonności",
        "source_filename": "test.xlsx",
        "phases_data": {
            "APK": {
                "powierzchnia_dzialki": 2000.0,
                "pum": 3000.0,
                "suma_pum_i_puu": 3200.0,
                "wskaznik_pumiu_pd": 1.6,
                "pow_calkowita_nadziemia": 4500.0,
                "ilosc_lokali_mieszkalnych": 50,
                "raw_parameters": {}
            }
        }
    }
    save_res = client.post("/api/save-project", json=save_payload)
    assert save_res.status_code == 200
    proj_id = save_res.json()["project_id"]

    # Pobieramy fazę
    projects = client.get("/api/projects").json()
    saved = next(p for p in projects if p["project_id"] == proj_id)
    phase_id = saved["phases"][0]["phase_id"]

    # Porównanie
    comp_res = client.post("/api/compare", json={"phase_ids": [phase_id]})
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "chlonnosc_scatter" in comp_data
    assert len(comp_data["chlonnosc_scatter"]) == 1
    pt = comp_data["chlonnosc_scatter"][0]
    assert pt["x"] == 2000.0
    assert pt["y"] == 1.6
    assert "Chłonność (PUMiU/Pd)" in comp_data["metrics"]

    # Cleanup
    client.delete(f"/api/projects/{proj_id}")


def test_project_audit_context_api(client):
    # Najpierw zapisujemy projekt
    save_payload = {
        "project_name": "Inwestycja Context Test",
        "stage_name": "APK",
        "city": "Gdańsk",
        "district": "Wrzeszcz",
        "developer": "Deweloper Pomorze",
        "notes": "Etap 1",
        "source_filename": "test.xlsx",
        "phases_data": {
            "APK": {
                "powierzchnia_dzialki": 5000.0,
                "pum": 3500.0,
                "suma_pum_i_puu": 3500.0,
                "pow_calkowita_nadziemia": 5000.0,
                "ilosc_lokali_mieszkalnych": 60,
                "raw_parameters": {}
            }
        }
    }
    save_res = client.post("/api/save-project", json=save_payload)
    assert save_res.status_code == 200
    proj_id = save_res.json()["project_id"]

    # Test zapytania o kontekst i podpowiedzi dla wgrywanego nowego etapu (WPK)
    context_payload = {
        "project_name": "Inwestycja Context Test",
        "phases_data": {
            "WPK": {
                # Celowo brak powierzchni działki w pliku WPK
                "pum": 3600.0,
                "suma_pum_i_puu": 3600.0,
                "ilosc_lokali_mieszkalnych": 62,
                "raw_parameters": {}
            }
        }
    }
    ctx_res = client.post("/api/project-audit-context", json=context_payload)
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()
    assert ctx_data["existing_project_found"] is True
    assert ctx_data["city"] == "Gdańsk"
    assert ctx_data["developer"] == "Deweloper Pomorze"
    assert "APK" in ctx_data["existing_phases"]
    # Podpowiedź brakującej powierzchni działki z etapu APK
    assert len(ctx_data["field_suggestions"]) >= 1
    assert ctx_data["field_suggestions"][0]["field"] == "powierzchnia_dzialki"
    assert ctx_data["field_suggestions"][0]["suggested_value"] == 5000.0
    # Audyt międzyfazowy WPK z APK z bazy
    assert len(ctx_data["cross_phase_audit"]) >= 1

    # Cleanup
    client.delete(f"/api/projects/{proj_id}")


def test_tabs_dom_structure(client):
    """Weryfikuje poprawność drzewa DOM - zakładki nie mogą być w sobie zagnieżdżone."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Sprawdzenie obecności wszystkich trzech zakładek
    assert 'id="import-tab"' in html
    assert 'id="catalog-tab"' in html
    assert 'id="bi-tab"' in html

    # Weryfikacja, że sekcje nie są zagnieżdżone
    import_pos = html.find('id="import-tab"')
    catalog_pos = html.find('id="catalog-tab"')
    bi_pos = html.find('id="bi-tab"')

    assert import_pos < catalog_pos < bi_pos

    # Pomiędzy import-tab a catalog-tab musi znajdować się tag zamykający </section>
    between_import_and_catalog = html[import_pos:catalog_pos]
    assert "</section>" in between_import_and_catalog

    # Pomiędzy catalog-tab a bi-tab musi znajdować się tag zamykający </section>
    between_catalog_and_bi = html[catalog_pos:bi_pos]
    assert "</section>" in between_catalog_and_bi

    # Po bi-tab musi znajdować się tag zamykający </section>
    after_bi = html[bi_pos:]
    assert "</section>" in after_bi


def test_delete_stage_api(client):
    """Test usuwania pojedynczego etapu inwestycji z bazy."""
    payload = {
        "project_name": "Test Two Stages Project",
        "city": "Wrocław",
        "source_filename": "test.xlsx",
        "phases_data": {
            "ETAP 1": {
                "stage_name": "ETAP 1",
                "phase_name": "PB",
                "pum": 2500.0,
                "powierzchnia_dzialki": 3000.0,
                "ilosc_lokali_mieszkalnych": 40
            },
            "ETAP 2": {
                "stage_name": "ETAP 2",
                "phase_name": "PW",
                "pum": 3000.0,
                "powierzchnia_dzialki": 3500.0,
                "ilosc_lokali_mieszkalnych": 50
            }
        }
    }
    save_res = client.post("/api/save-project", json=payload)
    assert save_res.status_code == 200
    proj_id = save_res.json()["project_id"]

    # Pobieramy etapy
    projects = client.get("/api/projects").json()
    proj = next(p for p in projects if p["project_id"] == proj_id)
    assert len(proj["phases"]) == 2
    stage1_id = proj["phases"][0]["phase_id"]
    stage2_id = proj["phases"][1]["phase_id"]

    # Usuwamy tylko pierwszy etap
    del_res = client.delete(f"/api/stages/{stage1_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "OK"

    # Sprawdzamy czy projekt ma teraz 1 etap
    projects = client.get("/api/projects").json()
    proj = next(p for p in projects if p["project_id"] == proj_id)
    assert len(proj["phases"]) == 1
    assert proj["phases"][0]["phase_id"] == stage2_id

    # Usuwamy drugi etap - projekt powinien zostać automatycznie usunięty
    del_res2 = client.delete(f"/api/stages/{stage2_id}")
    assert del_res2.status_code == 200

    projects = client.get("/api/projects").json()
    assert not any(p["project_id"] == proj_id for p in projects)


def test_compare_phases_with_null_pumiu(client):
    """Test weryfikujący, że /api/compare nie rzuca 500 gdy pumiu jest równe None."""
    payload = {
        "project_name": "Test Null Pumiu Compare Project",
        "city": "Kraków",
        "source_filename": "test_null_pum.xlsx",
        "phases_data": {
            "ETAP 1": {
                "stage_name": "ETAP 1",
                "phase_name": "Koncepcja",
                "pum": None,
                "puu": None,
                "suma_pum_i_puu": None,
                "powierzchnia_dzialki": 5000.0,
                "wskaznik_pumiu_pd": 1.25,
                "ilosc_lokali_mieszkalnych": None
            }
        }
    }
    save_res = client.post("/api/save-project", json=payload)
    assert save_res.status_code == 200
    proj_id = save_res.json()["project_id"]

    projects = client.get("/api/projects").json()
    proj = next(p for p in projects if p["project_id"] == proj_id)
    phase_id = proj["phases"][0]["phase_id"]

    # Wywołanie /api/compare - przed poprawką rzucało 500 Internal Server Error (TypeError on round(None, 2))
    compare_res = client.post("/api/compare", json={"phase_ids": [phase_id]})
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert "chlonnosc_scatter" in comp_data
    assert len(comp_data["detailed_rows"]) == 1
    assert comp_data["detailed_rows"][0]["pumiu"] is None

    # Czyszczenie
    client.delete(f"/api/projects/{proj_id}")


