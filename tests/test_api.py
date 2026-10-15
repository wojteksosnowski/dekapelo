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
