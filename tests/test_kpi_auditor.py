import pytest
from dekapelo.auditor.kpi_auditor import KPIAuditor, AuditResult


def test_auditor_math_pumiu_pass():
    auditor = KPIAuditor()
    kpi_data = {
        "suma_pum_i_puu": 1000.0,
        "pum": 800.0,
        "puu": 200.0
    }
    results = auditor.audit_phase(kpi_data)
    pumiu_res = [r for r in results if r.rule_name == "Bilans PUM i PUU"]
    assert len(pumiu_res) == 1
    assert pumiu_res[0].status == "PASS"


def test_auditor_math_pumiu_fail():
    auditor = KPIAuditor()
    kpi_data = {
        "suma_pum_i_puu": 1200.0,  # Błędna suma
        "pum": 800.0,
        "puu": 200.0
    }
    results = auditor.audit_phase(kpi_data)
    pumiu_res = [r for r in results if r.rule_name == "Bilans PUM i PUU"]
    assert len(pumiu_res) == 1
    assert pumiu_res[0].status == "FAIL"


def test_auditor_pc_balance():
    auditor = KPIAuditor()
    kpi_data = {
        "powierzchnia_calkowita": 5000.0,
        "pow_calkowita_nadziemia": 3500.0,
        "pow_calkowita_podziemia": 1500.0
    }
    results = auditor.audit_phase(kpi_data)
    pc_res = [r for r in results if "Pc = Pcn + Pcp" in r.rule_name]
    assert len(pc_res) == 1
    assert pc_res[0].status == "PASS"


def test_auditor_parking_deficit():
    auditor = KPIAuditor()
    kpi_data = {
        "suma_miejsc_parkingowych": 50,
        "wymagana_ilosc_mp": 60  # Niedobór 10 miejsc
    }
    results = auditor.audit_phase(kpi_data)
    mp_res = [r for r in results if "Wymogu Miejsc Parkingowych" in r.rule_name]
    assert len(mp_res) == 1
    assert mp_res[0].status == "FAIL"


def test_cross_phase_audit():
    auditor = KPIAuditor()
    phases_data = {
        "APK": {"pum": 1000.0, "ilosc_lokali_mieszkalnych": 20},
        "PB": {"pum": 1100.0, "ilosc_lokali_mieszkalnych": 22}  # Wzrost o 10%
    }
    results = auditor.audit_cross_phases(phases_data)
    pum_change = [r for r in results if "Zmiana PUM" in r.rule_name]
    assert len(pum_change) == 1
    assert pum_change[0].status == "WARNING"
