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
    # Spełnienie Wymogu Miejsc Parkingowych nie jest walidacją matematyczną tylko merytoryczną i nie jest brane pod uwagę przy audycie
    auditor = KPIAuditor()
    kpi_data = {
        "suma_miejsc_parkingowych": 50,
        "wymagana_ilosc_mp": 60  # Niedobór 10 miejsc
    }
    results = auditor.audit_phase(kpi_data)
    mp_res = [r for r in results if "Wymogu Miejsc Parkingowych" in r.rule_name]
    assert len(mp_res) == 0, "Spełnienie wymogu MP nie powinno być w audycie"


def test_auditor_rigid_ratio_detection_0_70():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 1000.0,
        "pum": 700.0  # Dokładnie 0.700000000000000
    }
    results = auditor.audit_phase(kpi_data)
    rigid_res = [r for r in results if "Sztywnego Wskaźnika" in r.rule_name]
    assert len(rigid_res) == 1
    assert rigid_res[0].status == "WARNING"
    assert "0.70" in rigid_res[0].message


def test_auditor_rigid_ratio_detection_0_72():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pum": 3600.0  # Dokładnie 0.720000000000000 (3600 / 5000 = 0.72)
    }
    results = auditor.audit_phase(kpi_data)
    rigid_res = [r for r in results if "Sztywnego Wskaźnika" in r.rule_name]
    assert len(rigid_res) == 1
    assert rigid_res[0].status == "WARNING"
    assert "0.72" in rigid_res[0].message


def test_auditor_non_rigid_ratio():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pum": 3567.89  # Rzeczywisty bilans architektoniczny (0.713578)
    }
    results = auditor.audit_phase(kpi_data)
    rigid_res = [r for r in results if "Sztywnego Wskaźnika" in r.rule_name]
    assert len(rigid_res) == 0


def test_auditor_rigid_ratio_detection_pumiu():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pum": 3000.0,
        "puu": 500.0,
        "suma_pum_i_puu": 3500.0  # 3500 / 5000 = 0.700000000000000
    }
    results = auditor.audit_phase(kpi_data)
    rigid_res = [r for r in results if "Sztywnego Wskaźnika" in r.rule_name]
    assert len(rigid_res) == 1
    assert "0.70" in rigid_res[0].message


def test_auditor_rigid_ratio_from_raw_indicator():
    auditor = KPIAuditor()
    kpi_data = {
        "wskaznik_pumiu_pcn": 0.700000000000000
    }
    results = auditor.audit_phase(kpi_data)
    rigid_res = [r for r in results if "Sztywnego Wskaźnika" in r.rule_name]
    assert len(rigid_res) == 1
    assert "0.70" in rigid_res[0].message


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


def test_auditor_pcnb_balance_pass():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pow_calkowita_balkonow_loggii": 450.0,
        "pow_calkowita_nadziemia_z_balkonami": 5450.0
    }
    results = auditor.audit_phase(kpi_data)
    pcnb_res = [r for r in results if "Pcnb = Pcn + Plb" in r.rule_name]
    assert len(pcnb_res) == 1
    assert pcnb_res[0].status == "PASS"


def test_auditor_pcnb_balance_fail():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pow_calkowita_balkonow_loggii": 450.0,
        "pow_calkowita_nadziemia_z_balkonami": 5800.0  # Niezgodne (powinno być 5450)
    }
    results = auditor.audit_phase(kpi_data)
    pcnb_res = [r for r in results if "Pcnb = Pcn + Plb" in r.rule_name]
    assert len(pcnb_res) == 1
    assert pcnb_res[0].status == "FAIL"
    assert "Rozbieżność bilansu Pcnb" in pcnb_res[0].message


def test_auditor_pcnb_logic_smaller_than_pcn():
    auditor = KPIAuditor()
    kpi_data = {
        "pow_calkowita_nadziemia": 5000.0,
        "pow_calkowita_nadziemia_z_balkonami": 4800.0  # Pcnb < Pcn to błąd logiczny
    }
    results = auditor.audit_phase(kpi_data)
    logic_res = [r for r in results if "Relacja Pcnb do Pcn" in r.rule_name]
    assert len(logic_res) == 1
    assert logic_res[0].status == "FAIL"
    assert "Błąd logiczny" in logic_res[0].message


def test_auditor_pcb_balance_pass():
    auditor = KPIAuditor()
    kpi_data = {
        "powierzchnia_calkowita": 7000.0,
        "pow_calkowita_balkonow_loggii": 500.0,
        "pow_calkowita_z_balkonami": 7500.0
    }
    results = auditor.audit_phase(kpi_data)
    pcb_res = [r for r in results if "Pcb = Pc + Plb" in r.rule_name]
    assert len(pcb_res) == 1
    assert pcb_res[0].status == "PASS"


def test_auditor_wskaznik_pcnb_ratio():
    auditor = KPIAuditor()
    kpi_data = {
        "suma_pum_i_puu": 3500.0,
        "pow_calkowita_nadziemia_z_balkonami": 5000.0,
        "wskaznik_pumiu_pcnb": 0.700  # 3500 / 5000 = 0.700
    }
    results = auditor.audit_phase(kpi_data)
    wsk_res = [r for r in results if "PUMiU / Pcnb" in r.rule_name]
    assert len(wsk_res) == 1
    assert wsk_res[0].status == "PASS"


def test_cross_phase_audit_skips_different_stages():
    """Weryfikuje, że audyt międzyfazowy nie porównuje odrębnych etapów inwestycji (np. Etap 1 vs Etap 2)."""
    auditor = KPIAuditor()
    phases_data = {
        "Etap 1 (PW)": {"stage_name": "Etap 1", "phase_name": "PW", "pum": 3000.0, "ilosc_lokali_mieszkalnych": 40},
        "Etap 2 (PB)": {"stage_name": "Etap 2", "phase_name": "PB", "pum": 1500.0, "ilosc_lokali_mieszkalnych": 20}
    }
    results = auditor.audit_cross_phases(phases_data)
    # Różne etapy NIE mogą wywołać fałszywego ostrzeżenia o drastycznym spadku PUM
    assert len(results) == 0


def test_auditor_plot_dedicated_vs_shared():
    """Weryfikuje obsługę działki własnej etapu vs etapu realizowanego na części działki inwestycji."""
    auditor = KPIAuditor()

    # 1. Etap z własną działką
    kpi_wlasna = {
        "powierzchnia_dzialki": 2000.0,
        "suma_pum_i_puu": 3000.0,
        "wskaznik_pumiu_pd": 1.5,
        "plot_type": "wlasna"
    }
    res_wlasna = auditor.audit_phase(kpi_wlasna)
    chlonnosc_res = [r for r in res_wlasna if "Chłonności Działki" in r.rule_name]
    assert len(chlonnosc_res) == 1
    assert chlonnosc_res[0].status == "PASS"

    # 2. Etap na części działki inwestycji (brak dedykowanej działki etapu)
    kpi_czesc = {
        "powierzchnia_dzialki": None,
        "suma_pum_i_puu": 1500.0,
        "plot_type": "czesc_dzialki"
    }
    res_czesc = auditor.audit_phase(kpi_czesc)
    dzialka_res = [r for r in res_czesc if "Działka Inwestycji i Etapu" in r.rule_name]
    assert len(dzialka_res) == 1
    assert dzialka_res[0].status == "PASS"
    assert "części działki" in dzialka_res[0].message

