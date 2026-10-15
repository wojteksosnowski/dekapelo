import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd


def clean_text(val: Any) -> str:
    """Oczyszcza tekst z nadmiarowych spacji, nowych linii i białych znaków."""
    if val is None or pd.isna(val):
        return ""
    text = str(val).strip().replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).lower()


def parse_float(val: Any) -> Optional[float]:
    """Konwertuje dowolną wartość liczbową/tekstową na float."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(" ", "").replace(",", ".")
    # Wyodrębnienie pierwszej sekwencji liczbowej (np. '1234.56' z '1234.56m2')
    match = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


def parse_int(val: Any) -> Optional[int]:
    """Konwertuje wartość na int."""
    f = parse_float(val)
    return int(round(f)) if f is not None else None


# Słownik reguł mapowania etykiet tekstowych na pola modelu ProjectKPI
KPI_FIELD_MAPPINGS: Dict[str, List[str]] = {
    # 1. Działka i Teren
    "powierzchnia_dzialki": [
        "powierzchnia działki", "powierzchnia dzialki", "area of the plot", "powierzchnia działki objęta pnb"
    ],
    "powierzchnia_zabudowy": [
        "powierzchnia zabudowy", "building footprint"
    ],
    "wspolczynnik_powierzchni_zabudowy": [
        "współczynnik powierzchni zabudowy", "wspolczynnik powierzchni zabudowy", "building foorprint %"
    ],
    "powierzchnia_utwardzona": [
        "powierzchnia utwardzona"
    ],
    "pow_parter_budynku": [
        "powierzchnia zajęta przez parter budynku"
    ],
    "pow_obiekty_infrastruktury": [
        "powierzchnia zajęta przez obiekty infrastruktury"
    ],
    "pow_chodnikow": [
        "powierzchnia chodników", "powierzchnia chodnikow", "area of walkways"
    ],
    "pow_drog": [
        "powierzchnia dróg", "powierzchnia drog", "area of roads"
    ],
    "pow_zjazdow_garaz": [
        "powierzchnia zjazdów do garaży podziemnych", "powierzchnia zjazdow do garazy"
    ],
    "pow_ciagow_pieszo_jezdnych": [
        "powierzchnia ciągów pieszo-jezdnych", "powierzchnia ciagow pieszo-jezdnych"
    ],
    "pow_nawierzchni_zwirowej": [
        "powierzchnia naw. żwirowej", "powierzchnia nawierzchni zwirowej"
    ],
    "pow_sciezek_kamiennych": [
        "powierzchnia ścieżek kamiennych", "powierzchnia sciezek kamiennych"
    ],
    "pow_bezpieczna_plac_zabaw": [
        "powierzchnia naw. bezpiecznej placu zabaw", "powierzchnia placu zabaw"
    ],
    "pow_murow_oporowych": [
        "powierzchnia murów oporowych", "powierzchnia murow oporowych"
    ],
    "pow_deskowan": [
        "powierzchnia deskowań", "powierzchnia deskowan"
    ],
    "powierzchnia_biologicznie_czynna": [
        "powierzchnia biologicznie czynna", "biologically active area"
    ],
    "pow_bio_grunt_100": [
        "powierzchnia biologicznie czynna (zieleń) 100%", "powierzchnia zielona na gruncie rodzimym", "biologicznie czynna 100%"
    ],
    "pow_bio_ogrody_deszczowe_100": [
        "powierzchnia biologicznie czynna (ogrody deszczowe) 100%", "ogrody deszczowe"
    ],
    "pow_bio_50": [
        "powierzchnia biologicznie czynna 50%"
    ],
    "pow_bio_plyta_garazu_50": [
        "powierzchnia biologicznie czynna na płycie garażu 50%", "powierzchnia zielona na płycie garażu"
    ],
    "pow_bio_plyta_garazu_25": [
        "powierzchnia biologicznie czynna na płycie garażu 25%"
    ],
    "dachy_tarasy_zielone_50": [
        "dachy i tarasy zielone 50%", "powierzchnia zielona na dachu"
    ],
    "wskaznik_pow_biologicznie_czynnej": [
        "wskaźnik pow. biologicznie czynnej", "wskaznik pow. biologicznie czynnej", "% powierzchni biologicznie czynnej"
    ],

    # 2. Powierzchnie Użytkowe i Mieszkaniowe
    "suma_pum_i_puu": [
        "suma powierzchni użytkowej mieszkań i usług", "powierzchnia użytkowa (pumiu)", "usable area (pumiu)", "pumiu"
    ],
    "suma_lokali": [
        "suma lokali mieszkalnych i usługowych", "suma lokali"
    ],
    "ilosc_lokali_mieszkalnych": [
        "ilość lokali mieszkalnych", "ilosc lokali mieszkalnych", "liczba mieszkań", "liczba mieszkan", "no of apartments"
    ],
    "pum_iso": [
        "powierzchnia użytkowa mieszkań (pum) wg iso", "mieszkań wg iso", "mieszkan wg iso", "pum wg iso", "wg pn-iso", "pn-iso 9836", "pn-iso", "pum iso", "iso 9836", "duży pum", "duzy pum"
    ],
    "pum_pnb": [
        "powierzchnia użytkowa mieszkań (pum) wg pn-70", "mieszkań wg pn-70", "pn-70/b-02365", "pn-70/b", "pn-70", "pum wg pn", "wg pnb", "pum pnb", "pum pn", "wg pn-b", "mały pum", "maly pum"
    ],
    "pum": [
        "powierzchnia użytkowa lokali mieszkalnych", "powierzchnia uzytkowa lokali mieszkalnych", "powierzchnia użytkowa mieszkań", "powierzchnia uzytkowa mieszkan", "usable area of apartments", "housing usable area (pum)", "(pum)"
    ],
    "srednia_wielkosc_mieszkania": [
        "średnia wielkość lokalu mieszkalnego", "srednia wielkosc lokalu mieszkalnego", "średnia powierzchnia mieszkania", "average apartment area"
    ],
    "ilosc_lokali_uslugowych": [
        "ilość lokali usługowych", "ilosc lokali uslugowych", "liczba lokali usługowych", "no of retail units"
    ],
    "puu": [
        "powierzchnia lokali usługowych", "powierzchnia uzytkowa usług", "powierzchnia użytkowa usług", "powierzchnia użytkowa lokali usługowych", "powierzchnia uzytkowa lokali uslugowych", "retail usable area (puu)", "(puu)"
    ],
    "powierzchnia_czesci_wspolnych": [
        "powierzchnia części wspólnych", "powierzchnia czesci wspolnych"
    ],
    "powierzchnia_czesci_wspolnych_bez_klatek": [
        "powierzchnia części wspólnych (bez powierzchni klatek", "powierzchnia pomieszczeń wspólnych"
    ],
    "powierzchnia_komunikacji_pionowej": [
        "powierzchnia komunikacji pionowej"
    ],
    "powierzchnia_komunikacji_poziomej": [
        "powierzchnia komunikacji poziomej"
    ],

    # 3. Miejsca Parkingowe i Komórki
    "suma_miejsc_parkingowych": [
        "suma miejsc parkingowych zewn. i miejsc postojowych w garażu", "liczba miejsc parkingowych zaprojektowanych"
    ],
    "wskaznik_mp": [
        "wskaźnik mp", "wskaznik mp"
    ],
    "wymagana_ilosc_mp": [
        "wymagana ilość miejsc parkingowych", "liczba miejsc parkingowych wymaganych"
    ],
    "mp_zewnetrzne_sprzedaz": [
        "ilość miejsc parkingowych zewnętrznych w sprzedaży"
    ],
    "mp_zewnetrzne_wszystkie": [
        "ilość miejsc parkingowych zewnętrznych (wszystkich)", "liczba miejsc parkingowych w terenie"
    ],
    "mp_garaz_wszystkie": [
        "ilość miejsc postojowych w garażu", "liczba miejsc parkingowych w garażu"
    ],
    "mp_rodzinne_zalezne": [
        "w tym tzw. miejsca rodzinne (zależne)", "liczba samochodów na miejscach rodzinnych", "liczba miejsc postojowych zależnych"
    ],
    "powierzchnia_mp_garaz": [
        "powierzchnia miejsc postojowych w garażu"
    ],
    "suma_komorek_i_boksow": [
        "sumaryczna ilość komórek lokatorskich i boksów", "liczba komórek lokatorskich"
    ],
    "ilosc_miejsc_rowerowych_garaz": [
        "ilość miejsc rowerowych w garażu", "liczba boksów rowerowych w garażu"
    ],
    "ilosc_komorek_tradycyjnych": [
        "ilość komórek lokatorskich tradycyjnych", "w garażu"
    ],
    "ilosc_boksow_jednoslady": [
        "ilość boksów na jednoślady"
    ],
    "ilosc_miejsc_rowerownie": [
        "ilość miejsc na jednoślady w rowerowniach"
    ],
    "powierzchnia_komorek_boksow_garaz": [
        "powierzchnia komórek lokatorskich/boksów/rowerowni w garażu", "powierzchnia komórek lokatorskich"
    ],
    "pow_wspolna_hali_garazowej": [
        "powierzchnia wspólna hali garażowej"
    ],
    "pow_uzytkowa_hali_garazowej": [
        "powierzchnia użytkowa hali garażowej", "powierzchnia użytkowa hali garażowej (bez pomieszczeń technicznych)"
    ],
    "pow_techniczna_hali_garazowej": [
        "powierzchnia pomieszczeń technicznych w hali garażowej"
    ],
    "ilosc_komorek_nadziemie": [
        "ilość komórek lokatorskich na kodygnacjach naziemnych", "w nadziemiu"
    ],

    # 4. Kubatura i Dane Techniczne
    "ilosc_klatek_schodowych": [
        "ilość klatek schodowych", "ilosc klatek schodowych", "liczba klatek schodowych", "no of staircases"
    ],
    "wysokosc_budynku": [
        "wysokość budynku", "wysokosc budynku", "building height"
    ],
    "wysokosc_parteru_netto": [
        "wysokość parteru netto", "wysokosc parteru netto"
    ],
    "wysokosc_kondygnacji_mieszkalnych_netto": [
        "wysokość kondygnacji mieszkalnych netto", "wysokość kondygancji w świetle"
    ],
    "ilosc_kondygnacji_nadziemnych": [
        "ilość kondygnacji nadziemnych", "liczba kondygnacji nadziemnych", "overground floors"
    ],
    "ilosc_kondygnacji_podziemnych": [
        "ilość kondygnacji podziemnych", "liczba kondygnacji podziemnych", "underground floors"
    ],
    "ilosc_wind": [
        "ilość wind", "ilosc wind", "liczba dźwigów windowych", "no of elevators"
    ],
    "powierzchnia_calkowita": [
        "powierzchnia całkowita (bez balkonów i loggi)", "powierzchnia całkowita (bez balkonów", "powierzchnia całkowita bez balkonów", "powierzchnia całkowita (pc)", "gross area (pc)"
    ],
    "pow_calkowita_balkonow_loggii": [
        "powierzchnia całkowita balkonów i loggi", "powierzchnia całkowita balkonów i loggii", "powierzchnia loggi i balkonów", "powierzchnia balkonów i loggii", "area of balconies and loggias", "plb"
    ],
    "pow_calkowita_tarasow": [
        "powierzchnia całkowita tarasów", "powierzchnia tarasów", "area of terraces"
    ],
    "pow_calkowita_z_balkonami": [
        "powierzchnia całkowita (z uwzględnieniem balkonów i loggii)", "powierzchnia całkowita (z uwzględnieniem balkonów", "powierzchnia całkowita z balkonami", "pcb"
    ],
    "pow_calkowita_nadziemia_z_balkonami": [
        "powierzchnia całkowita nadziemia (z uwzględnieniem balkonów i loggii)", "powierzchnia całkowita nadziemia (z uwzględnieniem balkonów", "powierzchnia całkowita nadziemia (z balkonami", "powierzchnia całkowita nadziemia z balkonami", "pcnb"
    ],
    "pow_calkowita_nadziemia": [
        "powierzchnia całkowita nadziemia (bez balkonów i loggi)", "powierzchnia całkowita nadziemia (bez balkonów", "powierzchnia całkowita nadziemia bez balkonów", "powierzchnia całkowita nadziemna", "overground gross area", "pcn"
    ],
    "pow_calkowita_podziemia": [
        "powierzchnia całkowita części podziemnej (garażu)", "powierzchnia całkowita podziemna", "underground gross area", "(pcp)", "(pcg)"
    ],
    "powierzchnia_elewacji": [
        "powierzchnia elewacji", "facade area", "pe"
    ],

    # 5. Wskaźniki Sprawności i Urbanistyczne
    "wskaznik_pumiu_pcn": [
        "wskaźnik (pum + puu) / pcn", "sprawność nadziemia"
    ],
    "wskaznik_pumiu_pcnb": [
        "wskaźnik (pum + puu) / pcnb"
    ],
    "wskaznik_pumiu_pc": [
        "wskaźnik (pum + puu) / pc", "sprawność całkowita"
    ],
    "wskaznik_pumiu_pcb": [
        "wskaźnik (pum + puu) / pcb"
    ],
    "wskaznik_pcg_impg": [
        "wskaźnik pcg / impg", "wskaznik pcg / impg", "sprawność całkowita garażu"
    ],
    "wskaznik_pumiu_pd": [
        "wskaźnik (pum + puu) / pd", "plot efficiency"
    ],
    "wskaznik_pumiu_klatka": [
        "wskaźnik (pum + puu) /klatkę schodową", "wskaźnik (pum + puu) / klatkę"
    ],
    "wskaznik_ilm_iw": [
        "wskaźnik il.m./ iw", "ilośc mieszkań / windę", "wskaznik il.m./ iw"
    ],
    "wskaznik_pc_pcg": [
        "wskaźnik pc/pcg", "wskaznik pc/pcg"
    ],
    "wskaznik_ilm_iks": [
        "wskaźnik ii.m./iks", "wskaźnik il.m./iks", "wskaznik ii.m./iks"
    ],
    "wskaznik_pe_pumiu": [
        "wskaźnik pe/(pum+puu)", "pow.elewacji / pum", "wskaznik pe/(pum+puu)"
    ]
}

RATIO_INDICATOR_FIELDS = {
    "wskaznik_pow_biologicznie_czynnej",
    "wspolczynnik_powierzchni_zabudowy",
    "wskaznik_mp",
    "wskaznik_pumiu_pcn",
    "wskaznik_pumiu_pcnb",
    "wskaznik_pumiu_pc",
    "wskaznik_pumiu_pcb",
    "wskaznik_pcg_impg",
    "wskaznik_pumiu_pd",
    "wskaznik_pumiu_klatka",
    "wskaznik_ilm_iw",
    "wskaznik_pc_pcg",
    "wskaznik_ilm_iks",
    "wskaznik_pe_pumiu",
    "srednia_wielkosc_mieszkania",
}

RATIO_LABEL_KEYWORDS = [
    "/", "sprawność", "sprawnosc", "wskaźnik", "wskaznik", "współczynnik", "wspolczynnik", "iloraz", "per", "stosunek", "efficiency"
]


STAGE_KEYWORDS = ["etap", "teren", "zadanie", "budynek"]
SUMMARY_KEYWORDS = ["suma", "razem", "total", "średnia", "srednia"]
KNOWN_PHASE_MARKERS = [
    "apk", "wpk", "projekt budowlany", "pb", "projekt wykonawczy", "wykonawczy", "pw", "koncepcja", "bazowy ppp", "umowy ppp"
]


def normalize_phase_name(raw: str, default: str = "Koncepcja") -> str:
    """Normalizuje surowy tekst fazy do standardowych oznaczeń domenowych."""
    c = clean_text(raw)
    if not c or any(k in c for k in ["arkusz", "sheet", "tabela", "wskaznik", "zest"]):
        return default
    if "pb" in c or "budowlany" in c:
        return "PB"
    if "pw" in c or "wykonawczy" in c:
        return "PW"
    if "apk" in c:
        return "APK"
    if "wpk" in c:
        return "WPK"
    if "bazowy ppp" in c or "umowy ppp" in c or re.search(r"\bppp\b", c):
        if not re.search(r"(?:/|\boc[kp]\b|\bocp\b|\d{4})", str(raw)):
            return "Bazowy PPP"
    if "koncepcja" in c:
        return "Koncepcja"
    return raw.strip() if raw and raw.strip() else default


def derive_stage_from_filename(filename: Optional[str]) -> Optional[str]:
    """Próbuje wywnioskować nazwę etapu lub budynku z nazwy pliku."""
    if not filename:
        return None
    stem = Path(filename).stem
    # Budynki np. C1C2, C1-C2, C3, C6, Budynek A
    m_bud = re.search(r"(?i)\b(c\d+(?:[c-]\d+)?)\b", stem)
    if m_bud:
        b_val = m_bud.group(1).upper()
        if "C" in b_val[1:]:
            b_val = re.sub(r"C(\d+)C(\d+)", r"C\1-C\2", b_val)
        return f"Budynek {b_val}"
    # Tereny np. T15, Teren 15, T10-T14
    m_t = re.search(r"(?i)\b(?:teren\s*)?(t\d+(?:[-_]t?\d+)?)\b", stem)
    if m_t:
        t_clean = re.sub(r"(?i)t", "", m_t.group(1)).strip()
        return f"Teren {t_clean}"
    # Etap rzymski lub arabski np. V - VI, Etap 2
    m_et = re.search(r"(?i)etap\s+([0-9ivxlcdm]+(?:\s*-\s*[0-9ivxlcdm]+)?)", stem)
    if m_et:
        return f"Etap {m_et.group(1).strip()}"
    m_roman = re.search(r"\b([IVXLCDM]+\s*-\s*[IVXLCDM]+|[IVXLCDM]{2,})\b", stem)
    if m_roman and not any(k in m_roman.group(0).lower() for k in ["kpi", "wsk"]):
        return f"Etap {m_roman.group(0).strip()}"
    # Oznaczenia inwestycji/etapu z numerem na końcu, np. OCK 1, OCK 2, OCK-1
    m_code = re.search(r"(?i)\b([a-ząćęłńóśźż]{2,6})\s*[-_]?\s*(\d+)\b", stem)
    if m_code:
        code_name = m_code.group(1).upper()
        num_val = m_code.group(2)
        if code_name not in ["KPI", "WSK", "ZEST", "TABELA"]:
            return f"{code_name} {num_val}"
    return None


def derive_stage_and_phase(
    raw_label: str,
    filename: Optional[str] = None,
    sheet_name: Optional[str] = None,
    default_phase: str = "PB"
) -> Tuple[str, str, str]:
    """
    Rozdziela surową etykietę kolumny/arkusza na:
    (stage_name, phase_name, display_name)
    
    Zasady domenowe:
    - Fazy projektowe to APK, WPK, PB, PW, Koncepcja.
    - Etapy to części inwestycji (Etap 1, Teren 10, Budynek C1-C2, Całość).
    - Nigdy nie zwraca pustego stringa, None ani 'undefined'.
    """
    clean_lbl = clean_text(raw_label)
    
    # 1. Wykrycie fazy projektowej
    phase_name = None
    if "apk" in clean_lbl:
        phase_name = "APK"
    elif "wpk" in clean_lbl:
        phase_name = "WPK"
    elif "pw" in clean_lbl or "wykonawczy" in clean_lbl:
        phase_name = "PW"
    elif "pb" in clean_lbl or "budowlany" in clean_lbl:
        phase_name = "PB"
    elif "koncepcja" in clean_lbl:
        phase_name = "Koncepcja"
    elif "bazowy ppp" in clean_lbl or "umowy ppp" in clean_lbl or (re.search(r"\bppp\b", clean_lbl) and not re.search(r"(?:/|\boc[kp]\b|\bocp\b|\d{4})", str(raw_label))):
        phase_name = "Bazowy PPP"
    
    # 2. Usunięcie oznaczeń fazy z etykiety etapu
    stage_candidate = re.sub(
        r"(?i)\s*[\(\[\{]?(?:projekt budowlany|projekt wykonawczy|koncepcja z umowy ppp|koncepcja urbanistyczna|koncepcja|apk|wpk|pb|pw|bazowy ppp|standard|sprzeda[zż]|przetarg)[\)\]\}]?",
        "",
        str(raw_label).strip()
    ).strip(" -_()[]{}")
    
    # Jeśli etykieta zawierała tylko fazę (lub była pusta)
    if not stage_candidate or len(stage_candidate) < 2 or clean_text(stage_candidate) in KNOWN_PHASE_MARKERS or clean_text(stage_candidate) in ["sprzedaz", "sprzedazowa"]:
        if sheet_name and any(k in clean_text(sheet_name) for k in STAGE_KEYWORDS):
            stage_candidate = sheet_name.strip()
        else:
            stage_candidate = derive_stage_from_filename(filename) or "Całość"
            
    final_phase = phase_name or default_phase
    display_name = (
        f"{stage_candidate} ({final_phase})"
        if final_phase.lower() != stage_candidate.lower()
        else stage_candidate
    )
    
    return stage_candidate, final_phase, display_name


def is_excluded_phase_name(text: str) -> bool:
    """Sprawdza czy nazwa kolumny odpowiada wykluczonym fazom ('PLANNING requirements', 'KU')."""
    t = text.lower().strip()
    if not t:
        return False
    if "planning" in t or "planning requirements" in t:
        return True
    if "koncepcja urbanistyczna" in t:
        return True
    alnum = re.sub(r"[^a-z0-9]", "", t)
    if alnum == "ku":
        return True
    tokens = re.split(r"[\s\-_/.,;:()]+", t)
    if "ku" in tokens:
        return True
    return False


class KPIParser:
    """Parser tabel parametrów i wskaźników inwestycji z plików Excel (.xlsx, .ods)."""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        if file_path:
            self.file_path = Path(file_path)
            if not self.file_path.exists():
                raise FileNotFoundError(f"Plik {file_path} nie istnieje.")
        else:
            self.file_path = None

    def detect_multistage(self) -> List[Dict[str, Any]]:
        """
        Wykrywa etapy w wieloetapowych plikach Excel.
        Obsługuje:
        - Wzorzec A: dwupoziomowy nagłówek (etapy w wierszu R, fazy PB/PW w wierszu R+1, np. Morska Vita)
        - Wzorzec B: kolumny terenów/etapów z fazą zdefiniowaną na poziomie arkusza lub etykiety (np. OCK5)
        """
        extension = self.file_path.suffix.lower()
        if extension == ".ods":
            with pd.ExcelFile(self.file_path, engine="odf") as excel_file:
                sheets = excel_file.sheet_names
                sheets_data = {s: excel_file.parse(s, header=None) for s in sheets}
        else:
            with pd.ExcelFile(self.file_path, engine="openpyxl") as excel_file:
                sheets = excel_file.sheet_names
                sheets_data = {s: excel_file.parse(s, header=None) for s in sheets}

        all_candidates: List[Dict[str, Any]] = []

        for sheet_name in sheets:
            df = sheets_data[sheet_name]
            if len(df) < 3 or df.shape[1] < 2:
                continue

            sheet_default_phase = normalize_phase_name(sheet_name, default="Koncepcja")

            for r_idx in range(min(12, len(df))):
                row_vals = [clean_text(df.iloc[r_idx, c]) if c < df.shape[1] else "" for c in range(df.shape[1])]
                stage_indices = [c for c, v in enumerate(row_vals) if any(k in v for k in STAGE_KEYWORDS)]

                if len(stage_indices) >= 2:
                    # Sprawdzenie wiersza poniżej na obecność faz (Wzorzec A)
                    next_row_phases = {}
                    if r_idx + 1 < len(df):
                        next_row_clean = [clean_text(df.iloc[r_idx + 1, c]) if c < df.shape[1] else "" for c in range(df.shape[1])]
                        for c in stage_indices:
                            val = next_row_clean[c] if c < len(next_row_clean) else ""
                            if any(p in val for p in KNOWN_PHASE_MARKERS):
                                next_row_phases[c] = normalize_phase_name(val)

                    is_pattern_a = len(next_row_phases) >= 2
                    data_start_row = r_idx + (2 if is_pattern_a else 1)

                    # Ustalenie kolumny z etykietami parametrów
                    param_col_idx = 0
                    for test_r in range(data_start_row, min(data_start_row + 8, len(df))):
                        col0 = clean_text(df.iloc[test_r, 0])
                        col1 = clean_text(df.iloc[test_r, 1]) if df.shape[1] > 1 else ""
                        if any(k in col1 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col_idx = 1
                            break
                        elif any(k in col0 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col_idx = 0
                            break

                    # Kolumny etapów oraz sąsiadujące kolumny sumaryczne (np. SUMA E1-E8)
                    all_cols = stage_indices.copy()
                    min_col = min(stage_indices)
                    for c in range(min_col, df.shape[1]):
                        if c not in all_cols:
                            v = row_vals[c]
                            if any(k in v for k in SUMMARY_KEYWORDS) or any(k in v for k in STAGE_KEYWORDS):
                                all_cols.append(c)
                    all_cols.sort()

                    for c in all_cols:
                        raw_label = str(df.iloc[r_idx, c]).strip() if pd.notna(df.iloc[r_idx, c]) else f"Kolumna {c}"
                        clean_lbl = clean_text(raw_label)
                        is_sum = any(k in clean_lbl for k in SUMMARY_KEYWORDS)

                        if is_pattern_a:
                            phase_val = next_row_phases.get(c, "" if is_sum else sheet_default_phase)
                        else:
                            phase_val = sheet_default_phase
                            if "koncepcja" in clean_lbl:
                                phase_val = "Koncepcja"
                            elif "apk" in clean_lbl:
                                phase_val = "APK"
                            elif "pw" in clean_lbl or "wykonawczy" in clean_lbl:
                                phase_val = "PW"
                            elif "pb" in clean_lbl or "budowlany" in clean_lbl:
                                phase_val = "PB"

                        clean_st_cand, final_ph, disp_name = derive_stage_and_phase(
                            raw_label=raw_label,
                            filename=self.file_path.name,
                            sheet_name=sheet_name,
                            default_phase=phase_val or sheet_default_phase
                        )
                        if is_pattern_a and next_row_phases.get(c):
                            final_ph = next_row_phases[c]
                            disp_name = f"{clean_st_cand} ({final_ph})" if final_ph.lower() != clean_st_cand.lower() else clean_st_cand

                        is_excl = is_excluded_phase_name(clean_lbl) or (is_excluded_phase_name(final_ph) if final_ph else False)

                        # Odczyt parametrów poglądowych
                        pum_preview = None
                        lokale_preview = None
                        dzialka_preview = None

                        for pr in range(data_start_row, len(df)):
                            raw_pname = df.iloc[pr, param_col_idx]
                            if raw_pname is None or pd.isna(raw_pname):
                                continue
                            fld = self._match_field(clean_text(raw_pname))
                            val = df.iloc[pr, c]
                            f_val = parse_float(val)
                            if f_val is not None:
                                if fld in ("pum", "suma_pum_i_puu") and pum_preview is None:
                                    pum_preview = f_val
                                elif fld == "powierzchnia_dzialki" and dzialka_preview is None:
                                    dzialka_preview = f_val
                                elif fld == "ilosc_lokali_mieszkalnych" and lokale_preview is None:
                                    lokale_preview = parse_int(val)

                        has_data = any(x is not None and x > 0 for x in [pum_preview, dzialka_preview, lokale_preview])
                        selected = has_data and not is_sum and not is_excl
                        plot_type = "wlasna" if (dzialka_preview is not None and dzialka_preview > 0) else "czesc_dzialki"

                        all_candidates.append({
                            "id": f"stage_{sheet_name}_{c}",
                            "stage_name": clean_st_cand,
                            "phase_name": final_ph,
                            "display_name": disp_name,
                            "sheet_name": sheet_name,
                            "pattern": "A" if is_pattern_a else "B",
                            "col_idx": c,
                            "data_start_row": data_start_row,
                            "param_col_idx": param_col_idx,
                            "is_summary": is_sum,
                            "is_excluded": is_excl,
                            "has_data": has_data,
                            "pum_preview": pum_preview,
                            "lokale_preview": lokale_preview,
                            "dzialka_preview": dzialka_preview,
                            "plot_type": plot_type,
                            "selected": selected
                        })
                    break  # znaleziono wiersz nagłówkowy dla tego arkusza

        # Wzorzec C: Poszczególne arkusze skoroszytu reprezentują osobne etapy (np. 'etap 4', 'etap 5', 'etap 6')
        if not all_candidates:
            stage_sheets = [s for s in sheets if any(k in clean_text(s) for k in STAGE_KEYWORDS)]
            if len(stage_sheets) >= 2:
                for sname in stage_sheets:
                    s_df = sheets_data[sname]
                    if len(s_df) < 3 or s_df.shape[1] < 2:
                        continue
                    hdr_row, ph_cols = self.detect_phase_columns(s_df)
                    param_col = 0
                    for tr in range(hdr_row + 1, min(hdr_row + 8, len(s_df))):
                        col0 = clean_text(s_df.iloc[tr, 0])
                        col1 = clean_text(s_df.iloc[tr, 1]) if s_df.shape[1] > 1 else ""
                        if any(k in col1 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col = 1
                            break
                        elif any(k in col0 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col = 0
                            break

                    for c_idx, ph_raw in ph_cols.items():
                        c_clean = str(ph_raw).strip()
                        if is_excluded_phase_name(c_clean):
                            continue
                        st_cand, ph_cand, disp = derive_stage_and_phase(
                            raw_label=c_clean,
                            filename=self.file_path.name,
                            sheet_name=sname,
                            default_phase="PB"
                        )
                        # Odczyt podglądu parametrów
                        pum_prv = None
                        lok_prv = None
                        dz_prv = None
                        for pr in range(hdr_row + 1, len(s_df)):
                            raw_pn = s_df.iloc[pr, param_col]
                            if raw_pn is None or pd.isna(raw_pn):
                                continue
                            fld = self._match_field(clean_text(raw_pn))
                            v = s_df.iloc[pr, c_idx]
                            fv = parse_float(v)
                            if fv is not None:
                                if fld in ("pum", "suma_pum_i_puu") and pum_prv is None:
                                    pum_prv = fv
                                elif fld == "powierzchnia_dzialki" and dz_prv is None:
                                    dz_prv = fv
                                elif fld == "ilosc_lokali_mieszkalnych" and lok_prv is None:
                                    lok_prv = parse_int(v)

                        has_data = any(x is not None and x > 0 for x in [pum_prv, dz_prv, lok_prv])
                        is_sum = any(k in clean_text(c_clean) for k in SUMMARY_KEYWORDS)
                        plot_t = "wlasna" if (dz_prv is not None and dz_prv > 0) else "czesc_dzialki"
                        all_candidates.append({
                            "id": f"stage_{sname}_{c_idx}",
                            "stage_name": sname.strip(),
                            "phase_name": ph_cand,
                            "display_name": f"{sname.strip()} ({ph_cand})",
                            "sheet_name": sname,
                            "pattern": "C",
                            "col_idx": c_idx,
                            "data_start_row": hdr_row + 1,
                            "param_col_idx": param_col,
                            "is_summary": is_sum,
                            "is_excluded": False,
                            "has_data": has_data,
                            "pum_preview": pum_prv,
                            "lokale_preview": lok_prv,
                            "dzialka_preview": dz_prv,
                            "plot_type": plot_t,
                            "selected": has_data and not is_sum
                        })

        # Wzorzec D: Kolumny wielu faz projektowych w ramach tego samego arkusza (np. OCK 1, OCK 2, C1C2, C3, C6, Dąbka Vita)
        if not all_candidates:
            best_sheet = self._choose_best_sheet(sheets)
            df = sheets_data[best_sheet]
            if len(df) >= 3 and df.shape[1] >= 2:
                hdr_row, ph_cols = self.detect_phase_columns(df)
                if len(ph_cols) >= 2:
                    param_col = 0
                    for tr in range(hdr_row + 1, min(hdr_row + 8, len(df))):
                        col0 = clean_text(df.iloc[tr, 0])
                        col1 = clean_text(df.iloc[tr, 1]) if df.shape[1] > 1 else ""
                        if any(k in col1 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col = 1
                            break
                        elif any(k in col0 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc", "lokali"]):
                            param_col = 0
                            break

                    for c_idx, ph_raw in ph_cols.items():
                        c_clean = str(ph_raw).strip().replace("\n", " ")
                        if is_excluded_phase_name(c_clean):
                            continue
                        st_cand, ph_cand, disp = derive_stage_and_phase(
                            raw_label=c_clean,
                            filename=self.file_path.name,
                            sheet_name=best_sheet,
                            default_phase="PB"
                        )
                        # Odczyt podglądu parametrów
                        pum_prv = None
                        lok_prv = None
                        dz_prv = None
                        for pr in range(hdr_row + 1, len(df)):
                            raw_pn = df.iloc[pr, param_col]
                            if raw_pn is None or pd.isna(raw_pn):
                                continue
                            fld = self._match_field(clean_text(raw_pn))
                            v = df.iloc[pr, c_idx]
                            fv = parse_float(v)
                            if fv is not None:
                                if fld in ("pum", "suma_pum_i_puu") and pum_prv is None:
                                    pum_prv = fv
                                elif fld == "powierzchnia_dzialki" and dz_prv is None:
                                    dz_prv = fv
                                elif fld == "ilosc_lokali_mieszkalnych" and lok_prv is None:
                                    lok_prv = parse_int(v)

                        has_data = any(x is not None and x > 0 for x in [pum_prv, dz_prv, lok_prv])
                        is_sum = any(k in clean_text(c_clean) for k in SUMMARY_KEYWORDS)
                        plot_t = "wlasna" if (dz_prv is not None and dz_prv > 0) else "czesc_dzialki"
                        all_candidates.append({
                            "id": f"stage_{best_sheet}_{c_idx}",
                            "stage_name": st_cand,
                            "phase_name": ph_cand,
                            "display_name": disp,
                            "sheet_name": best_sheet,
                            "pattern": "D",
                            "col_idx": c_idx,
                            "data_start_row": hdr_row + 1,
                            "param_col_idx": param_col,
                            "is_summary": is_sum,
                            "is_excluded": False,
                            "has_data": has_data,
                            "pum_preview": pum_prv,
                            "lokale_preview": lok_prv,
                            "dzialka_preview": dz_prv,
                            "plot_type": plot_t,
                            "selected": has_data and not is_sum
                        })

        # Zasada hierarchii faz: wyznaczamy wiodącą fazę (APK < WPK < PB < PW)
        from dekapelo.database.models import get_phase_rank
        by_stage: Dict[str, List[Dict[str, Any]]] = {}
        for cand in all_candidates:
            cand["phase_rank"] = get_phase_rank(cand.get("phase_name"))
            st_key = clean_text(cand.get("stage_name", ""))
            by_stage.setdefault(st_key, []).append(cand)

        for st_key, c_list in by_stage.items():
            valid_list = [c for c in c_list if c.get("has_data") and not c.get("is_summary")]
            if valid_list:
                max_rank = max(c.get("phase_rank", 0) for c in valid_list)
                for c in c_list:
                    c["is_leading"] = (c.get("phase_rank", 0) == max_rank and c.get("has_data", False))

        return all_candidates

    def parse(self, selected_stages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Parsuje plik.
        Jeśli podano selected_stages, parsuje tylko wybrane etapy/kolumny.
        Jeśli nie podano, automatycznie sprawdza czy plik jest wieloetapowy (Wzorzec A) i wczytuje aktywne etapy.
        Dla plików jednofazowych działa w tradycyjnym trybie jednoarkuszowym.
        """
        extension = self.file_path.suffix.lower()

        # Tryb ze wskazanymi etapami przez użytkownika
        if selected_stages:
            results: Dict[str, Dict[str, Any]] = {}
            with (pd.ExcelFile(self.file_path, engine="odf") if extension == ".ods" else pd.ExcelFile(self.file_path, engine="openpyxl")) as excel_file:
                sheets_cache = {}
                for stage_info in selected_stages:
                    sname = stage_info.get("sheet_name") or excel_file.sheet_names[0]
                    if sname not in sheets_cache:
                        sheets_cache[sname] = excel_file.parse(sname, header=None)
                    df = sheets_cache[sname]
                    c_idx = stage_info.get("col_idx", 3)
                    param_col_idx = stage_info.get("param_col_idx", 0)
                    data_start_row = stage_info.get("data_start_row", 3)
                    stage_name = stage_info.get("stage_name", f"Etap_{c_idx}")
                    phase_name = stage_info.get("phase_name", "Standard")
                    disp_name = stage_info.get("display_name") or (f"{stage_name} ({phase_name})" if phase_name.lower() != stage_name.lower() else stage_name)

                    stage_id = stage_info.get("id") or f"stage_{sname}_{c_idx}"
                    extracted = self._extract_single_column_data(
                        df=df,
                        col_idx=c_idx,
                        param_col_idx=param_col_idx,
                        data_start_row=data_start_row,
                        stage_name=stage_name,
                        phase_name=phase_name,
                        display_name=disp_name,
                        sheet_name=sname,
                        stage_id=stage_id
                    )
                    if len(extracted.get("raw_parameters", {})) > 0:
                        results[disp_name] = extracted
            if results:
                return results

        # Sprawdzenie automatyczne czy plik jest wieloetapowy (Wzorzec A: etapy nad fazami PB/PW, np. Morska Vita)
        multistage = self.detect_multistage()
        pattern_a_stages = [s for s in multistage if s.get("selected") and s.get("pattern") == "A"]
        if len(pattern_a_stages) >= 2:
            return self.parse(selected_stages=pattern_a_stages)

        # Standardowy tryb jednoarkuszowy (kompatybilność wsteczna)
        if extension == ".ods":
            with pd.ExcelFile(self.file_path, engine="odf") as excel_file:
                sheet_name = excel_file.sheet_names[0]
                df = excel_file.parse(sheet_name, header=None)
        else:
            with pd.ExcelFile(self.file_path, engine="openpyxl") as excel_file:
                sheet_name = self._choose_best_sheet(excel_file.sheet_names)
                df = excel_file.parse(sheet_name, header=None)

        return self._extract_phases_and_data(df)

    def _choose_best_sheet(self, sheet_names: List[str]) -> str:
        """Wybiera arkusz zawierający zestawienie lub wskaźniki."""
        for s in sheet_names:
            s_clean = clean_text(s)
            if any(k in s_clean for k in ["zestawienie", "zest", "wskazniki", "parametr", "arkusz1", "arkusz2"]):
                return s
        return sheet_names[0]

    def detect_phase_columns(self, df: pd.DataFrame) -> Tuple[int, Dict[int, str]]:
        """Lokalizuje wiersz nagłówkowy z fazami i zwraca (header_row_idx, phase_columns)."""
        # Sprawdzenie czy mamy do czynienia z wieloma etapami w tym arkuszu (Wzorzec A)
        for r_idx in range(min(12, len(df))):
            row_vals = [clean_text(df.iloc[r_idx, c]) if c < df.shape[1] else "" for c in range(df.shape[1])]
            stage_indices = [c for c, v in enumerate(row_vals) if any(k in v for k in STAGE_KEYWORDS)]
            if len(stage_indices) >= 2:
                next_row_phases = {}
                if r_idx + 1 < len(df):
                    next_row_clean = [clean_text(df.iloc[r_idx + 1, c]) if c < df.shape[1] else "" for c in range(df.shape[1])]
                    for c in stage_indices:
                        val = next_row_clean[c] if c < len(next_row_clean) else ""
                        if any(p in val for p in KNOWN_PHASE_MARKERS):
                            next_row_phases[c] = normalize_phase_name(val)
                if len(next_row_phases) >= 2:
                    phase_cols = {}
                    for c in stage_indices:
                        raw_st = str(df.iloc[r_idx, c]).strip()
                        ph = next_row_phases.get(c, "")
                        disp = f"{raw_st} ({ph})" if ph else raw_st
                        phase_cols[c] = disp
                    return r_idx + 1, phase_cols

        best_row_idx = None
        best_phase_columns: Dict[int, str] = {}
        best_score = -1

        for r_idx in range(min(15, len(df))):
            row_raw = [str(df.iloc[r_idx, c]) if pd.notna(df.iloc[r_idx, c]) else "" for c in range(df.shape[1])]
            row_clean = [clean_text(v) for v in row_raw]

            # Ignorowanie wierszy metadanych / numerów umów / szablonów
            row_text = " ".join(row_clean)
            if any(k in row_text for k in ["ostatnia aktualizacja", "wzoru zalacznika", "zalacznik nr", "do umowy", "dnia 20"]):
                continue

            has_param_header = any(k in v for v in row_clean for k in ["parametr", "opis", "wskaznik", "cecha", "nazwa"])

            detected_phases = {}
            for c_idx, val in enumerate(row_clean):
                if is_excluded_phase_name(val):
                    continue
                for marker in KNOWN_PHASE_MARKERS:
                    if marker in val:
                        if any(p in val for p in ["powierzchnia", "wspolczynnik", "lokal", "miejsc", "koszt", "parametr", "opis"]):
                            continue
                        detected_phases[c_idx] = row_raw[c_idx]
                        break

            if detected_phases:
                score = len(detected_phases) * 10 + (5 if has_param_header else 0)
                if score > best_score:
                    best_score = score
                    best_row_idx = r_idx
                    best_phase_columns = detected_phases

        if best_phase_columns and best_row_idx is not None:
            return best_row_idx, best_phase_columns

        header_row_idx = 2 if len(df) > 2 else 0
        phase_columns = {}
        for c_idx in range(2, min(df.shape[1], 6)):
            phase_columns[c_idx] = f"Faza {c_idx - 1}"

        return header_row_idx, phase_columns

    def _extract_single_column_data(
        self,
        df: pd.DataFrame,
        col_idx: int,
        param_col_idx: int,
        data_start_row: int,
        stage_name: str,
        phase_name: str,
        display_name: str,
        sheet_name: str = "",
        stage_id: str = ""
    ) -> Dict[str, Any]:
        """Ekstrahuje wskaźniki dla pojedynczej kolumny etapu z danego arkusza."""
        data: Dict[str, Any] = {
            "stage_id": stage_id,
            "stage_name": stage_name,
            "phase_name": phase_name,
            "display_name": display_name,
            "sheet_name": sheet_name,
            "raw_parameters": {}
        }
        for r_idx in range(data_start_row, len(df)):
            raw_param_name = df.iloc[r_idx, param_col_idx]
            if raw_param_name is None or pd.isna(raw_param_name):
                continue
            cleaned_label = clean_text(raw_param_name)
            if not cleaned_label or len(cleaned_label) < 2:
                continue

            matched_field = self._match_field(cleaned_label)
            if col_idx < df.shape[1]:
                val = df.iloc[r_idx, col_idx]
                f_val = parse_float(val)
                if f_val is not None:
                    data["raw_parameters"][str(raw_param_name).strip()] = f_val
                    if matched_field and matched_field not in data:
                        if any(k in matched_field for k in ["ilosc", "suma_lokali", "suma_miejsc", "mp_", "suma_komorek"]):
                            data[matched_field] = parse_int(val)
                        else:
                            data[matched_field] = f_val

        self._reconcile_pum(data)
        self._calculate_derived_kpis(data)
        pd_val = data.get("powierzchnia_dzialki")
        data["plot_type"] = "wlasna" if (pd_val is not None and pd_val > 0) else "czesc_dzialki"
        return data

    def _reconcile_pum(self, pdata: Dict[str, Any]):
        """Inteligentne uzgadnianie wariantu wiodącego PUM (PNB vs PN-ISO) dla danego etapu."""
        pumiu = pdata.get("suma_pum_i_puu")
        puu = pdata.get("puu") or 0.0
        pum_pnb = pdata.get("pum_pnb")
        pum_iso = pdata.get("pum_iso")
        curr_pum = pdata.get("pum")

        if pum_pnb is not None or pum_iso is not None:
            if pumiu is not None:
                expected_from_pumiu = pumiu - puu
                pnb_diff = abs(pum_pnb - expected_from_pumiu) if pum_pnb is not None else float("inf")
                iso_diff = abs(pum_iso - expected_from_pumiu) if pum_iso is not None else float("inf")
                if pnb_diff <= 1.0 and pnb_diff < iso_diff:
                    pdata["pum"] = pum_pnb
                elif iso_diff <= 1.0 and iso_diff < pnb_diff:
                    pdata["pum"] = pum_iso
                elif pum_pnb is not None and (curr_pum is None or curr_pum == 0):
                    pdata["pum"] = pum_pnb
                elif pum_iso is not None and (curr_pum is None or curr_pum == 0):
                    pdata["pum"] = pum_iso
            else:
                if curr_pum is None or curr_pum == 0:
                    pdata["pum"] = pum_pnb if (pum_pnb is not None and pum_pnb > 0) else pum_iso

    def _calculate_derived_kpis(self, data: Dict[str, Any]):
        """Algebraiczne wyliczenie wskaźników i sprawności z surowych danych fizycznych (m², sztuki)."""
        # 1. PUM i PUU
        pum = data.get("pum")
        puu = data.get("puu") or 0.0
        pumiu = data.get("suma_pum_i_puu")

        if pum is not None and pum > 0:
            pumiu = round(pum + puu, 2)
            data["suma_pum_i_puu"] = pumiu
        elif pumiu is not None and pumiu > 0 and (pum is None or pum == 0):
            pum = round(pumiu - puu, 2)
            data["pum"] = pum

        # Lokale sumaryczne
        ilm = data.get("ilosc_lokali_mieszkalnych")
        ilu = data.get("ilosc_lokali_uslugowych")
        if data.get("suma_lokali") is None or data.get("suma_lokali") == 0:
            if ilm is not None:
                data["suma_lokali"] = ilm + (ilu or 0)

        # 2. Nadziemie i balkony
        pcn = data.get("pow_calkowita_nadziemia")
        plb = data.get("pow_calkowita_balkonow_loggii")
        pcnb = data.get("pow_calkowita_nadziemia_z_balkonami")

        if pcn is not None and plb is not None:
            pcnb = round(pcn + plb, 2)
            data["pow_calkowita_nadziemia_z_balkonami"] = pcnb
        elif pcnb is not None and plb is not None and (pcn is None or pcn == 0):
            pcn = round(pcnb - plb, 2)
            data["pow_calkowita_nadziemia"] = pcn

        # 3. Powierzchnia całkowita (Pc) i z balkonami (Pcb)
        pcp = data.get("pow_calkowita_podziemia")
        pc = data.get("powierzchnia_calkowita")
        pcb = data.get("pow_calkowita_z_balkonami")

        if (pc is None or pc == 0) and pcn is not None and pcp is not None:
            pc = round(pcn + pcp, 2)
            data["powierzchnia_calkowita"] = pc

        if pc is not None and plb is not None:
            pcb = round(pc + plb, 2)
            data["pow_calkowita_z_balkonami"] = pcb
        elif pcb is not None and plb is not None and (pc is None or pc == 0):
            pc = round(pcb - plb, 2)
            data["powierzchnia_calkowita"] = pc

        # 4. Sprawności i ilorazy
        if pumiu is not None and pumiu > 0:
            if pcn is not None and pcn > 0:
                data["wskaznik_pumiu_pcn"] = round(pumiu / pcn, 4)
            if pcnb is not None and pcnb > 0:
                data["wskaznik_pumiu_pcnb"] = round(pumiu / pcnb, 4)
            if pc is not None and pc > 0:
                data["wskaznik_pumiu_pc"] = round(pumiu / pc, 4)
            if pcb is not None and pcb > 0:
                data["wskaznik_pumiu_pcb"] = round(pumiu / pcb, 4)

        # Miejsca parkingowe / lokale
        mp_total = data.get("suma_miejsc_parkingowych")
        locales = data.get("suma_lokali") or ilm
        if mp_total is not None and locales and locales > 0:
            data["wskaznik_mp"] = round(mp_total / locales, 2)

        # Średnia wielkość mieszkania
        if pum is not None and pum > 0 and ilm and ilm > 0:
            data["srednia_wielkosc_mieszkania"] = round(pum / ilm, 2)

        # Wskaźniki działkowe (Pd)
        pd = data.get("powierzchnia_dzialki")
        if pd and pd > 0:
            if pumiu is not None and pumiu > 0:
                data["wskaznik_pumiu_pd"] = round(pumiu / pd, 4)
            pz = data.get("powierzchnia_zabudowy")
            if pz and pz > 0:
                data["wspolczynnik_powierzchni_zabudowy"] = round(pz / pd, 4)
            pbc = data.get("powierzchnia_biologicznie_czynna")
            if pbc and pbc > 0:
                data["wskaznik_pow_biologicznie_czynnej"] = round(pbc / pd, 4)

        # Windy i klatki
        iw = data.get("ilosc_wind")
        iks = data.get("ilosc_klatek_schodowych")
        if ilm and ilm > 0:
            if iw and iw > 0:
                data["wskaznik_ilm_iw"] = round(ilm / iw, 1)
            if iks and iks > 0:
                data["wskaznik_ilm_iks"] = round(ilm / iks, 1)

        if pumiu and pumiu > 0 and iks and iks > 0:
            data["wskaznik_pumiu_klatka"] = round(pumiu / iks, 2)

        if pc and pc > 0 and pcp and pcp > 0:
            data["wskaznik_pc_pcg"] = round(pc / pcp, 2)

        mp_garaz = data.get("mp_garaz_wszystkie")
        if pcp and pcp > 0 and mp_garaz and mp_garaz > 0:
            data["wskaznik_pcg_impg"] = round(pcp / mp_garaz, 2)

        pe = data.get("powierzchnia_elewacji")
        if pe and pe > 0 and pumiu and pumiu > 0:
            data["wskaznik_pe_pumiu"] = round(pe / pumiu, 2)

    def _extract_phases_and_data(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Lokalizuje wiersz nagłówkowy z fazami i mapuje wiersze parametrów (tryb tradycyjny)."""
        header_row_idx, phase_columns = self.detect_phase_columns(df)
        param_col_idx = 0

        # Ustalenie, w której kolumnie znajduje się nazwa parametru (0 lub 1)
        for r_idx in range(header_row_idx + 1, min(header_row_idx + 8, len(df))):
            col0 = clean_text(df.iloc[r_idx, 0])
            col1 = clean_text(df.iloc[r_idx, 1]) if df.shape[1] > 1 else ""
            if any(k in col1 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc"]):
                param_col_idx = 1
                break
            elif any(k in col0 for k in ["powierzchnia", "współczynnik", "działki", "pum", "miejsc"]):
                param_col_idx = 0
                break

        # Przygotowanie struktur na poszczególne fazy
        results: Dict[str, Dict[str, Any]] = {}
        for c_idx, phase_name in phase_columns.items():
            clean_phase_name = str(phase_name).strip().replace("\n", " ")
            if is_excluded_phase_name(clean_phase_name):
                continue
            if not clean_phase_name:
                clean_phase_name = f"Faza_Kolumna_{c_idx}"
            
            st_cand, ph_cand, disp = derive_stage_and_phase(
                clean_phase_name,
                filename=self.file_path.name if hasattr(self, "file_path") and self.file_path else None
            )
            results[clean_phase_name] = {
                "stage_name": st_cand,
                "phase_name": ph_cand,
                "display_name": disp,
                "col_idx": c_idx,
                "raw_parameters": {}
            }

        # Iteracja po wierszach z danymi
        for r_idx in range(header_row_idx + 1, len(df)):
            raw_param_name = df.iloc[r_idx, param_col_idx]
            if raw_param_name is None or pd.isna(raw_param_name):
                continue
            
            cleaned_label = clean_text(raw_param_name)
            if not cleaned_label or len(cleaned_label) < 2:
                continue

            # Sprawdzenie czy etykieta pasuje do zdefiniowanych pól
            matched_field = self._match_field(cleaned_label)

            # Odczyt wartości dla każdej zidentyfikowanej fazy
            for c_idx, phase_name in phase_columns.items():
                clean_phase_name = str(phase_name).strip().replace("\n", " ")
                if c_idx < df.shape[1]:
                    val = df.iloc[r_idx, c_idx]
                    f_val = parse_float(val)
                    if f_val is not None:
                        # Zapis do raw_parameters
                        results[clean_phase_name]["raw_parameters"][str(raw_param_name).strip()] = f_val
                        # Jeśli przyporządkowano pole modelu i jeszcze nie ustawiono
                        if matched_field and matched_field not in results[clean_phase_name]:
                            if any(k in matched_field for k in ["ilosc", "suma_lokali", "suma_miejsc", "mp_", "suma_komorek"]):
                                results[clean_phase_name][matched_field] = parse_int(val)
                            else:
                                results[clean_phase_name][matched_field] = f_val

        # Uzgadnianie PUM i ustalenie typu działki
        for clean_phase_name, pdata in results.items():
            self._reconcile_pum(pdata)
            self._calculate_derived_kpis(pdata)
            pd_val = pdata.get("powierzchnia_dzialki")
            pdata["plot_type"] = "wlasna" if (pd_val is not None and pd_val > 0) else "czesc_dzialki"

        # Usunięcie faz, które nie zawierają żadnych wczytanych parametrów
        filtered_results = {
            k: v for k, v in results.items() if len(v.get("raw_parameters", {})) > 0
        }

        return filtered_results if filtered_results else results

    def _is_ratio_label(self, cleaned_label: str) -> bool:
        """Sprawdza czy etykieta reprezentuje wskaźnik ilorazowy lub sprawność."""
        norm_free = cleaned_label.replace("pn-70/b-02365", "").replace("pn-70/b", "").replace("pn-70/", "").replace("pn/b", "")
        return any(kw in norm_free for kw in RATIO_LABEL_KEYWORDS)

    def _match_field(self, cleaned_label: str) -> Optional[str]:
        """Dopasowuje oczyszczoną etykietę do pola modelu ProjectKPI z uwzględnieniem semantyki."""
        # 1. Specyficzne normy PUM (ISO vs PNB) mają najwyższy priorytet
        for high_prio in ["pum_iso", "pum_pnb"]:
            for pat in KPI_FIELD_MAPPINGS[high_prio]:
                if pat in cleaned_label:
                    return high_prio

        is_ratio = self._is_ratio_label(cleaned_label)

        # 2. Przeszukiwanie pozostałych pól z filtrem semantycznym (wielkości bezwzględne vs wskaźniki)
        for field, patterns in KPI_FIELD_MAPPINGS.items():
            if field in ("pum_iso", "pum_pnb"):
                continue

            is_field_ratio = field in RATIO_INDICATOR_FIELDS
            # Etykieta ze znakiem ilorazu/wskaźnika nie może pasować do metraży ani sztuk
            if is_ratio and not is_field_ratio:
                continue
            # Etykieta bez cech wskaźnika nie może pasować do pól wskaźnikowych (poza średnią pow. mieszkania)
            if not is_ratio and is_field_ratio and field != "srednia_wielkosc_mieszkania":
                continue

            for pat in patterns:
                if pat in cleaned_label:
                    return field
        return None
