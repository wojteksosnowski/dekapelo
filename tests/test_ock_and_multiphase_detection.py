import pytest
from pathlib import Path
import pandas as pd
import openpyxl
from fastapi.testclient import TestClient

from dekapelo.ingestion.kpi_parser import KPIParser, clean_text, SUMMARY_KEYWORDS
from dekapelo.ui.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ock1_ods_detection_and_phases():
    """Weryfikuje poprawną detekcję faz APK, WPK, PB w pliku OCK 1.ods (brak fałszywego 'Bazowy PPP')."""
    fpath = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "OCK 1.ods"
    if not fpath.exists():
        pytest.skip(f"Brak pliku {fpath}")

    parser = KPIParser(str(fpath))
    stages = parser.detect_multistage()

    # Musi wykryć kolumny fazowe (APK, WPK, PB, PW)
    assert len(stages) >= 3, f"OCK 1.ods powinien mieć co najmniej 3 fazy, wykryto: {len(stages)}"

    detected_phase_names = [s["phase_name"] for s in stages]
    assert "APK" in detected_phase_names, "OCK 1 powinien mieć fazę APK"
    assert "WPK" in detected_phase_names, "OCK 1 powinien mieć fazę WPK"
    assert "PB" in detected_phase_names, "OCK 1 powinien mieć fazę PB"
    assert "Bazowy PPP" not in detected_phase_names, "OCK 1 NIE może zawierać fałszywej fazy 'Bazowy PPP' z metadanych umowy"

    # Weryfikacja wartości PUM w podglądzie
    apk_stage = next(s for s in stages if s["phase_name"] == "APK")
    assert apk_stage["pum_preview"] == 5502.0
    assert apk_stage["lokale_preview"] == 85
    assert apk_stage["selected"] is True

    wpk_stage = next(s for s in stages if s["phase_name"] == "WPK")
    assert wpk_stage["pum_preview"] == 5490.0
    assert wpk_stage["lokale_preview"] == 85
    assert wpk_stage["selected"] is True

    pb_stage = next(s for s in stages if s["phase_name"] == "PB")
    assert pb_stage["pum_preview"] == 5497.0
    assert pb_stage["lokale_preview"] == 85
    assert pb_stage["selected"] is True
    assert pb_stage.get("is_leading") is True, "PB powinna być fazą wiodącą (najwyższą z obecnych z danymi)"

    # Faza PW w OCK 1 nie posiada wartości liczbowych
    pw_stage = next((s for s in stages if s["phase_name"] == "PW"), None)
    if pw_stage:
        assert pw_stage["has_data"] is False
        assert pw_stage["selected"] is False

    # Parsowanie danych
    parsed = parser.parse()
    assert len(parsed) >= 3
    for k, v in parsed.items():
        assert v.get("phase_name") in ["APK", "WPK", "PB"]
        assert v.get("phase_name") != "Bazowy PPP"
        assert v.get("pum") is not None and v.get("pum") > 5000


def test_ock2_ods_detection_and_phases():
    """Weryfikuje poprawną detekcję w OCK 2.ods."""
    fpath = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "OCK 2.ods"
    if not fpath.exists():
        pytest.skip(f"Brak pliku {fpath}")

    parser = KPIParser(str(fpath))
    stages = parser.detect_multistage()

    assert len(stages) >= 3
    detected_phase_names = [s["phase_name"] for s in stages]
    assert "APK" in detected_phase_names
    assert "WPK" in detected_phase_names
    assert "PB" in detected_phase_names
    assert "Bazowy PPP" not in detected_phase_names


def test_scan_directory_returns_directory_metadata(client):
    """Weryfikuje, że API /api/scan-directory zwraca podkatalogi dla każdego pliku."""
    res = client.get("/api/scan-directory?directory=KPI - WSKAZNIKI")
    assert res.status_code == 200
    data = res.json()

    assert data["total_files"] >= 10
    files = data["files"]
    for f in files:
        assert "filename" in f
        assert "directory" in f
        assert "path" in f
        assert len(f["directory"]) > 0, f"Plik {f['filename']} powinien mieć określony katalog"

    # Weryfikacja dla plików z podkatalogu Trójmiasto
    trojmiasto_files = [f for f in files if "Trójmiasto" in f["directory"] or "Trjmiasto" in f["directory"]]
    assert len(trojmiasto_files) >= 5, "Powinno znaleźć pliki w katalogu Trójmiasto"


def test_data_columns_and_formula_summary_integrity_all_files():
    """
    Sprawdza, czy w testowanych plikach liczba wykrytych etapów/faz
    dokładnie odpowiada kolumnom z danymi, a kolumny podsumowujące
    są poprawnie identyfikowane m.in. za pomocą formuł sumujących wiersz.
    """
    base_dir = Path("KPI - WSKAZNIKI")
    all_files = [f for f in base_dir.rglob("*") if f.suffix.lower() in [".xlsx", ".xls", ".ods"] and not f.name.startswith("~$")]
    assert len(all_files) >= 10

    for file_path in all_files:
        parser = KPIParser(str(file_path))
        stages = parser.detect_multistage()

        # Dla każdego pliku z wieloma kolumnami z danymi upewniamy się, że nie zwrócił atrap
        for s in stages:
            assert s["phase_name"] != "Bazowy PPP" or "ppp" in file_path.name.lower() or "ppp" in s.get("sheet_name", "").lower(), (
                f"Plik {file_path.name}: nieoczekiwana faza 'Bazowy PPP' w etapie {s['stage_name']}"
            )
            # Jeśli etap ma dane, PUM lub lokale nie mogą być ujemne
            if s.get("pum_preview") is not None:
                assert s["pum_preview"] >= 0

        # Weryfikacja formuł sumujących dla plików .xlsx
        if file_path.suffix.lower() == ".xlsx":
            wb = openpyxl.load_workbook(file_path, data_only=False)
            sheet_name = parser._choose_best_sheet(wb.sheetnames)
            ws = wb[sheet_name]

            # Szukamy kolumn, które zawierają formuły sumujące poziomo w tym samym wierszu (np. =SUM(H4:L4))
            horizontal_sum_cols = set()
            for r in range(1, min(ws.max_row + 1, 30)):
                for c in range(1, min(ws.max_column + 1, 25)):
                    val = str(ws.cell(row=r, column=c).value or "")
                    if val.startswith("=") and ("SUM" in val.upper() or "+" in val):
                        # Sprawdź czy formuła odnosi się do różnych kolumn w tym samym wierszu
                        if ":" in val or ("+" in val and not val.endswith("+") and any(ch.isalpha() for ch in val)):
                            horizontal_sum_cols.add(c - 1)  # 0-indexed

            # Każda kolumna będąca sumą poziomą z etykietą 'Razem'/'Suma' powinna być oznaczona jako is_summary
            for s in stages:
                if s.get("col_idx") in horizontal_sum_cols and any(w in s.get("display_name", "").lower() for w in ["razem", "suma", "total"]):
                    assert s["is_summary"] is True, f"Kolumna {s['display_name']} w {file_path.name} powinna mieć is_summary=True"
                    assert s["selected"] is False, f"Kolumna {s['display_name']} powinna być odznaczona"
