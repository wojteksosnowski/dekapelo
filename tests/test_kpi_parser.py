import pytest
from pathlib import Path
from dekapelo.ingestion.kpi_parser import KPIParser, clean_text, parse_float, parse_int


def test_clean_text():
    assert clean_text("  POWIERZCHNIA   działki \n (im)  ") == "powierzchnia działki (im)"
    assert clean_text(None) == ""


def test_parse_float():
    assert parse_float("1 234,56 m2") == 1234.56
    assert parse_float(45.7) == 45.7
    assert parse_float("brak") is None
    assert parse_float(None) is None


def test_parse_int():
    assert parse_int("67") == 67
    assert parse_int("67.0") == 67
    assert parse_int(None) is None


def test_parse_c1c2():
    c1c2_path = Path("KPI - WSKAZNIKI") / "BemowoVita" / "C1C2.xlsx"
    if not c1c2_path.exists():
        pytest.skip(f"Plik {c1c2_path} nie istnieje")

    parser = KPIParser(str(c1c2_path))
    phases = parser.parse()
    assert len(phases) > 0, "Powinno wykryć co najmniej jedną fazę w C1C2.xlsx"

    # Sprawdzenie obecności kluczowych pól
    first_phase = list(phases.values())[0]
    assert "raw_parameters" in first_phase
    assert len(first_phase["raw_parameters"]) > 10, "Powinno wyekstrahować co najmniej 10 surowych parametrów"


def test_parse_dabka_vita():
    dabka_path = Path("KPI - WSKAZNIKI") / "09.2026 - Trójmiasto" / "Dąbka Vita.xlsx"
    if not dabka_path.exists():
        pytest.skip(f"Plik {dabka_path} nie istnieje")

    parser = KPIParser(str(dabka_path))
    phases = parser.parse()
    assert len(phases) >= 2, "Dąbka Vita ma fazy APK, WPK, PB"
    assert "APK" in phases
    apk = phases["APK"]
    assert apk.get("pum") == 5038.24
    assert apk.get("ilosc_lokali_mieszkalnych") == 99
