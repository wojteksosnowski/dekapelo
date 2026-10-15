import os
from pathlib import Path
import pytest
from dekapelo.ingestion.kpi_parser import KPIParser
from dekapelo.auditor.kpi_auditor import KPIAuditor


def get_all_kpi_files():
    base_dir = Path("KPI - WSKAZNIKI")
    if not base_dir.exists():
        return []
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        for f in filenames:
            if f.lower().endswith((".xlsx", ".ods", ".xls")) and not f.startswith("~$"):
                files.append(Path(root) / f)
    return files


@pytest.mark.parametrize("file_path", get_all_kpi_files(), ids=lambda p: p.name)
def test_parse_and_audit_each_kpi_file(file_path):
    """Testuje, czy każdy plik ze wskaźnikami w katalogu jest poprawnie wczytywany i audytowany."""
    parser = KPIParser(str(file_path))
    phases_data = parser.parse()
    assert len(phases_data) > 0, f"Plik {file_path.name} powinien zawierać co najmniej jedną fazę danych"

    auditor = KPIAuditor()
    for phase_name, data in phases_data.items():
        assert "raw_parameters" in data
        audit_results = auditor.audit_phase(data, phase_name)
        assert isinstance(audit_results, list)

    cross_results = auditor.audit_cross_phases(phases_data)
    assert isinstance(cross_results, list)
