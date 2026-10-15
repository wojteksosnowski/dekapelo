import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
        "suma powierzchni użytkowej mieszkań i usług", "powierzchnia użytkowa (pumiu)", "usable area (pumiu)"
    ],
    "suma_lokali": [
        "suma lokali mieszkalnych i usługowych", "suma lokali"
    ],
    "ilosc_lokali_mieszkalnych": [
        "ilość lokali mieszkalnych", "ilosc lokali mieszkalnych", "liczba mieszkań", "liczba mieszkan", "no of apartments"
    ],
    "pum": [
        "powierzchnia użytkowa lokali mieszkalnych", "powierzchnia uzytkowa lokali mieszkalnych", "powierzchnia użytkowa mieszkań", "powierzchnia uzytkowa mieszkan", "usable area of apartments", "housing usable area (pum)", "(pum)", "pum wg"
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
        "powierzchnia wspólna hali garażowej", "powierzchnia całkowita podziemna"
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
        "powierzchnia całkowita części podziemnej (garażu)", "powierzchnia całkowita podziemna", "underground gross area", "pcp", "pcg"
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


class KPIParser:
    """Parser tabel parametrów i wskaźników inwestycji z plików Excel (.xlsx, .ods)."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Plik {file_path} nie istnieje.")

    def parse(self) -> Dict[str, Dict[str, Any]]:
        """
        Parsuje plik i zwraca słownik:
        {
            'APK': {'pum': 3279.79, 'ilosc_lokali_mieszkalnych': 67, ...},
            'Projekt Budowlany': {...}
        }
        """
        extension = self.file_path.suffix.lower()
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

    def _extract_phases_and_data(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Lokalizuje wiersz nagłówkowy z fazami i mapuje wiersze parametrów."""
        header_row_idx = None
        phase_columns: Dict[int, str] = {}  # {col_idx: 'APK', col_idx2: 'WPK', ...}
        param_col_idx = 0

        # Poszukiwanie wiersza nagłówkowego zawierającego fazy projektu
        # Fazy 'PLANNING requirements' oraz 'KU' nie występują jako fazy w naszych danych i są wykluczone
        known_phase_markers = [
            "apk", "wpk", "projekt budowlany", "pb", "projekt wykonawczy", "wykonawczy", "pw", "koncepcja", "bazowy"
        ]

        def is_excluded_phase_name(text: str) -> bool:
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

        for r_idx in range(min(15, len(df))):
            row_vals = [clean_text(v) for v in df.iloc[r_idx].values]
            detected_phases = {}
            for c_idx, val in enumerate(row_vals):
                if is_excluded_phase_name(val):
                    continue
                for marker in known_phase_markers:
                    if marker in val:
                        # Nazwa fazy (np. 'APK', 'Projekt Budowlany', 'PW')
                        detected_phases[c_idx] = df.iloc[r_idx, c_idx]
                        break

            if len(detected_phases) >= 1:
                header_row_idx = r_idx
                phase_columns = detected_phases
                break

        # Jeśli nie znaleziono standardowego nagłówka faz, sprawdźmy kolumny od indeksu 2 wzwyż
        if not phase_columns:
            header_row_idx = 2 if len(df) > 2 else 0
            # Załóżmy domyślną fazę z pierwszej dostępnej kolumny liczbowej
            for c_idx in range(2, min(df.shape[1], 6)):
                phase_columns[c_idx] = f"Faza {c_idx - 1}"

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
            results[clean_phase_name] = {
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
                            # Jeśli pole jest całkowite (int), np. lokale, miejsca, klatki
                            if any(k in matched_field for k in ["ilosc", "suma_lokali", "suma_miejsc", "mp_", "suma_komorek"]):
                                results[clean_phase_name][matched_field] = parse_int(val)
                            else:
                                results[clean_phase_name][matched_field] = f_val

        # Usunięcie faz, które nie zawierają żadnych wczytanych parametrów
        filtered_results = {
            k: v for k, v in results.items() if len(v.get("raw_parameters", {})) > 0
        }

        return filtered_results if filtered_results else results

    def _match_field(self, cleaned_label: str) -> Optional[str]:
        """Dopasowuje oczyszczoną etykietę do pola modelu ProjectKPI."""
        # Najpierw dopasowanie precyzyjne / podciągów
        for field, patterns in KPI_FIELD_MAPPINGS.items():
            for pat in patterns:
                if pat in cleaned_label:
                    return field
        return None
