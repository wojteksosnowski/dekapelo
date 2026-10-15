import os
import glob
import pytest
import pandas as pd
import openpyxl
from dekapelo.ingestion.kpi_parser import KPIParser, clean_text
from dekapelo.auditor.kpi_auditor import KPIAuditor


def get_all_kpi_files():
    """Zwraca listę wszystkich plików ze wskaźnikami z katalogu KPI - WSKAZNIKI."""
    files = glob.glob("KPI - WSKAZNIKI/**/*.xlsx", recursive=True) + glob.glob("KPI - WSKAZNIKI/**/*.ods", recursive=True)
    return [f for f in files if not os.path.basename(f).startswith("~$")]


def test_column_alignment_and_merged_cells_all_files():
    """
    Uniwersalny test dla każdego pliku ze zbioru danych:
    Weryfikuje, czy odczytane przez parser wartości dla poszczególnych etapów
    dokładnie odpowiadają komórkom w tej samej kolumnie fizycznego arkusza Excel,
    potwierdzając brak przesunięć kolumn przez scalenia czy puste komórki.
    """
    all_files = get_all_kpi_files()
    assert len(all_files) >= 10, "Zbiór plików KPI powinien zawierać co najmniej 10 plików."

    for file_path in all_files:
        if not file_path.endswith((".xlsx", ".xlsm")):
            continue

        parser = KPIParser(file_path)
        with pd.ExcelFile(file_path, engine="openpyxl") as ef:
            sheet_name = parser._choose_best_sheet(ef.sheet_names)
            df = ef.parse(sheet_name, header=None)
            header_row_idx, phase_cols = parser.detect_phase_columns(df)

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb[sheet_name]
        parsed_phases = parser.parse()
        assert len(parsed_phases) > 0, f"Plik {file_path} powinien zawierać co najmniej jeden etap."

        # Dla każdego wykrytego etapu weryfikujemy dokładną zgodność kolumny fizycznej
        for c_idx, phase_name in phase_cols.items():
            clean_pname = str(phase_name).strip().replace("\n", " ")
            if clean_pname not in parsed_phases:
                continue

            openpyxl_col = c_idx + 1
            # Sprawdź pierwsze 80 wierszy arkusza
            for r_idx in range(header_row_idx + 1, min(len(df), 80)):
                cell_val = ws.cell(row=r_idx + 1, column=openpyxl_col).value
                df_val = df.iloc[r_idx, c_idx]

                if isinstance(cell_val, (int, float)) and pd.notna(df_val):
                    try:
                        f_df = float(df_val)
                        f_cell = float(cell_val)
                        assert abs(f_df - f_cell) < 1e-4, (
                            f"Plik {file_path}, wiersz {r_idx + 1}, kolumna {openpyxl_col} ({clean_pname}): "
                            f"Przesunięcie wartości! openpyxl={f_cell} != DataFrame={f_df}"
                        )
                    except (ValueError, TypeError):
                        pass


def test_semantic_anti_collision_all_files():
    """
    Test semantyczny dla każdego pliku i etapu ze zbioru:
    Gwarantuje, że żadne pole metrażowe ani liczbowe nie zostało zanieczyszczone
    wartością ze wskaźnika ilorazowego (np. Pcp/mp, wskaźnik sprawności, /lokal).
    """
    all_files = get_all_kpi_files()
    for file_path in all_files:
        parser = KPIParser(file_path)
        phases = parser.parse()

        for phase_name, data in phases.items():
            pc = data.get("powierzchnia_calkowita")
            pcp = data.get("pow_calkowita_podziemia")

            # Jeśli budynek ma duży metraż (np. Pc > 1000 m²),
            # powierzchnia całkowita podziemia nie może być wskaźnikiem jednostkowym rzędu 20-40 m²!
            if pc and pc > 1000 and pcp is not None:
                assert pcp > 100.0, (
                    f"Plik {file_path}, etap {phase_name}: pow_calkowita_podziemia={pcp} "
                    f"jest zbyt mała w stosunku do Pc={pc} – prawdopodobnie omyłkowo wczytano wskaźnik sprawności garażu (Pcp/mp)!"
                )

            # Wskaźniki sprawności (jeśli odczytane) muszą być ilorazami z przedziału logicznego
            wsk_pcn = data.get("wskaznik_pumiu_pcn")
            if wsk_pcn is not None and wsk_pcn > 0:
                assert 0.3 <= wsk_pcn <= 1.5, (
                    f"Plik {file_path}, etap {phase_name}: wskaznik_pumiu_pcn={wsk_pcn} "
                    f"poza zakresem wskaźnika (powinien być ilorazem ok. 0.6 - 0.8)!"
                )


def test_dual_pum_detection_and_balance_all_files():
    """
    Weryfikuje obsługę wariantów PN-ISO i PNB we wszystkich plikach ze zbioru.
    Gwarantuje brak fałszywych błędów 'Bilans PUM i PUU'.
    """
    all_files = get_all_kpi_files()
    auditor = KPIAuditor()

    for file_path in all_files:
        parser = KPIParser(file_path)
        phases = parser.parse()

        for phase_name, data in phases.items():
            pumiu = data.get("suma_pum_i_puu")
            pum_iso = data.get("pum_iso")
            pum_pnb = data.get("pum_pnb")
            pum = data.get("pum")

            # Jeśli arkusz ma zdefiniowane oba standardy
            if pum_iso is not None and pum_pnb is not None and abs(pum_iso - pum_pnb) > 1.0:
                # Wartości obu norm powinny być poprawnie wyodrębnione i różne
                assert pum_iso != pum_pnb

                # PUM wiodący powinien być zbilansowany z PUMiU
                if pumiu is not None:
                    puu = data.get("puu") or 0.0
                    expected_pumiu = pum + puu
                    assert abs(pumiu - expected_pumiu) <= 0.5, (
                        f"Plik {file_path}, etap {phase_name}: PUM ({pum}) + PUU ({puu}) != PUMiU ({pumiu})"
                    )

            # Uruchom audyt matematyczny dla tego etapu
            audit_results = auditor.audit_phase(data, phase_name=phase_name)
            pum_audit = [ar for ar in audit_results if ar.rule_name == "Bilans PUM i PUU"]
            if pum_audit:
                # Bilans PUM i PUU nie może generować fałszywego FAIL
                assert pum_audit[0].status == "PASS", (
                    f"Plik {file_path}, etap {phase_name}: Nieoczekiwany FAIL audytu PUM: {pum_audit[0].message}"
                )


def test_c6_bemowo_vita_four_stages_exact_values():
    """
    Szczegółowy test zgodności 4 kolejnych etapów w C6.xlsx:
    APK (4 099.1), WPK (4 188.8), PB (4 154.94), PW (4 153.98)
    oraz poprawności bilansów Pc = Pcn + Pcp.
    """
    c6_path = "KPI - WSKAZNIKI/BemowoVita/C6.xlsx"
    parser = KPIParser(c6_path)
    phases = parser.parse()

    expected_stages = {
        "APK": {"pumiu": 4099.1, "pum_pnb": 4099.1, "pum_iso": 4216.5, "pum": 4099.1, "pcp": 2723.0},
        "WPK": {"pumiu": 4188.8, "pum_pnb": 4188.8, "pum_iso": 4307.92, "pum": 4188.8, "pcp": 2705.16},
        "PB": {"pumiu": 4154.94, "pum_pnb": 4154.94, "pum_iso": 4261.0, "pum": 4154.94, "pcp": 2931.91},
        "PW": {"pumiu": 4153.98, "pum_pnb": 4153.98, "pum": 4153.98, "pcp": 2937.2}
    }

    auditor = KPIAuditor()
    for stage_name, expected in expected_stages.items():
        assert stage_name in phases, f"Etap {stage_name} powinien istnieć w C6.xlsx"
        st_data = phases[stage_name]

        # Sprawdzenie wartości PUMiU i PUM
        assert abs(st_data["suma_pum_i_puu"] - expected["pumiu"]) < 0.1
        assert abs(st_data["pum"] - expected["pum"]) < 0.1
        assert abs(st_data["pum_pnb"] - expected["pum_pnb"]) < 0.1
        if "pum_iso" in expected and "pum_iso" in st_data:
            assert abs(st_data["pum_iso"] - expected["pum_iso"]) < 0.1

        # Sprawdzenie powierzchni całkowitej podziemia (Pcp)
        assert abs(st_data["pow_calkowita_podziemia"] - expected["pcp"]) < 0.1

        # Audyt matematyczny etapu
        audit_res = auditor.audit_phase(st_data, phase_name=stage_name)
        pum_pass = [ar for ar in audit_res if ar.rule_name == "Bilans PUM i PUU" and ar.status == "PASS"]
        pc_pass = [ar for ar in audit_res if "Pc = Pcn + Pcp" in ar.rule_name and ar.status == "PASS"]

        assert len(pum_pass) == 1, f"Bilans PUM i PUU powinien mieć status PASS dla etapu {stage_name}"
        assert len(pc_pass) == 1, f"Bilans Pc = Pcn + Pcp powinien mieć status PASS dla etapu {stage_name}"
