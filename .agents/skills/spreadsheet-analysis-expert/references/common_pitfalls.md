# Common Spreadsheet Pitfalls & Solutions

Kompleksowy zbiór 8 najczęstszych pułapek przy programistycznej analizie arkuszy Excel/ODS wraz z bezbłędnymi rozwiązaniami w Pythonie.

---

## 1. Komórki Scalone (`Merged Cells`) zwracające `None`

### Problem:
W Excelu scalony blok (np. `B2:D2` z tekstem `"ETAP 1"`) fizycznie przechowuje wartość wyłącznie w lewej-górnej komórce (`B2`). Komórki `C2` i `D2` mają wartość `None`. Standardowy odczyt kolumny `C` lub `D` daje pustą wartość nagłówka.

### Rozwiązanie: Mapa lookupu komórek scalonych
```python
def build_merged_cell_lookup(ws):
    """Tworzy słownik mapujący każdą komórkę ze scalonego obszaru na wartość lewej-górnej komórki."""
    lookup = {}
    for rng in ws.merged_cells.ranges:
        top_left_val = ws.cell(row=rng.min_row, column=rng.min_col).value
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                lookup[(r, c)] = top_left_val
    return lookup

def get_resolved_cell_value(ws, row, col, lookup):
    """Zwraca wartość komórki, transparentnie uwzględniając obszary scalone."""
    if (row, col) in lookup:
        return lookup[(row, col)]
    return ws.cell(row=row, column=col).value
```

---

## 2. Pułapka `data_only=True` zwracająca `None` (Brak Cache'u Formuł)

### Problem:
Gdy otwierasz arkusz z `openpyxl.load_workbook(..., data_only=True)`, biblioteka nie wylicza formuł w Pythonie – czyta jedynie wcześniej zbuforowany wynik (`<v>` w XML). Jeśli plik został wygenerowany programowo (np. przez `xlsxwriter` lub inne narzędzie bez uruchomienia i zapisania w MS Excel), bufor jest pusty i `cell.value` zwraca `None`.

### Rozwiązanie: Dwufazowy Fallback (Wartość -> Formuła)
```python
from openpyxl import load_workbook

def load_with_formula_fallback(filepath, sheet_name=None):
    wb_values = load_workbook(filepath, data_only=True)
    wb_formulas = load_workbook(filepath, data_only=False)
    
    ws_v = wb_values[sheet_name] if sheet_name else wb_values.active
    ws_f = wb_formulas[sheet_name] if sheet_name else wb_formulas.active
    
    def get_val_or_formula(r, c):
        val = ws_v.cell(r, c).value
        if val is None:
            formula = ws_f.cell(r, c).value
            return formula  # np. "=B5+B6"
        return val
    
    return get_val_or_formula
```

---

## 3. Polskie Formaty Liczb, Walut i Spacje Nierozdzielające (`\xa0`)

### Problem:
W polskich arkuszach liczby często zawierają:
- Spacje zwykłe (` `) lub twarde spacje nierozdzielające (`\xa0` / `&nbsp;`) jako separatory tysięcy (np. `"1 234,50"`).
- Przecinki zamiast kropek jako separator dziesiętny.
- Jednostki walutowe lub miary doklejone do tekstu (`"1 234,56 zł"`, `"500 m2"`, `"12,5%"`).
Funkcja `float("1 234,56")` wyrzuci błąd `ValueError`.

### Rozwiązanie: Bezpieczny parser liczb i procentów
```python
import re

def parse_polish_number(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    # Zamiana twardych spacji i usunięcie białych znaków
    s = str(val).replace("\xa0", " ").strip()
    
    # Obsługa procentów (np. "25,5%" -> 0.255 lub 25.5 zależnie od konwencji)
    is_percent = "%" in s
    s = s.replace("%", "").strip()
    
    # Usunięcie jednostek tekstowych (zł, m2, PLN, szt, itp.)
    s = re.sub(r"(?i)\s*(zł|pln|m2|m²|szt\.?|ha)\b", "", s).strip()
    
    # Usunięcie spacji tysięcznych
    s = s.replace(" ", "")
    # Zamiana przecinka dziesiętnego na kropkę
    s = s.replace(",", ".")
    
    try:
        num = float(s)
        return num / 100.0 if is_percent else num
    except ValueError:
        return None
```

---

## 4. Daty Seryjne w Excelu (Excel Serial Dates: 1900 vs 1904)

### Problem:
Excel przechowuje daty jako liczby zmiennoprzecinkowe reprezentujące liczbę dni od 1 stycznia 1900 roku (uwzględniając słynny błąd roku 1900, w którym Excel fałszywie traktował rok 1900 jako przestępny). Wartość `45230` to data `2023-10-31`.

### Rozwiązanie:
```python
from datetime import datetime, timedelta, date

def excel_serial_to_date(serial_val, date_mode_1904=False):
    if isinstance(serial_val, (datetime, date)):
        return serial_val if isinstance(serial_val, date) else serial_val.date()
    if not isinstance(serial_val, (int, float)):
        return None
    
    if date_mode_1904:
        # System dat Mac/1904
        epoch = datetime(1904, 1, 1)
        return (epoch + timedelta(days=serial_val)).date()
    else:
        # Domyślny system 1900 (z uwzględnieniem buga dnia 60 = 29.02.1900)
        epoch = datetime(1899, 12, 30)
        return (epoch + timedelta(days=serial_val)).date()
```

---

## 5. Nagłówki Wielopoziomowe (Hierarchiczne)

### Problem:
Arkusz zawiera kategorię nadrzędną w wierszu 1 (np. `KOSZTY BEZPOŚREDNIE`) obejmującą kolumny B-D, a w wierszu 2 podkategorie (np. `Materiały`, `Robocizna`, `Sprzęt`). Płaski odczyt wiersza 2 gubi kontekst nadrzędny.

### Rozwiązanie: Dynamiczne łączenie poziomów
```python
def extract_hierarchical_headers(ws, header_rows=[1, 2]):
    lookup = build_merged_cell_lookup(ws)
    headers = []
    max_col = ws.max_column
    
    for c in range(1, max_col + 1):
        levels = []
        for r in header_rows:
            val = get_resolved_cell_value(ws, r, c, lookup)
            clean = str(val).strip() if val is not None else ""
            if clean and clean not in levels:
                levels.append(clean)
        headers.append(" // ".join(levels) if levels else f"Col_{c}")
    return headers
```

---

## 6. Wiele Niezależnych Tabel na Jednym Arkuszu

### Problem:
Arkusz nie jest pojedynczą tabelą SQL, lecz "dashboardem", gdzie od wiersza 1 do 20 znajduje się tabela A, a od wiersza 25 do 50 tabela B.

### Rozwiązanie: Segmentacja po pustych separatorach wierszowych
```python
def segment_sheet_into_tables(ws, empty_row_threshold=2):
    """Dzieli arkusz na bloki tabel rozdzielone N pustymi wierszami."""
    tables = []
    current_start = None
    empty_count = 0
    
    for r in range(1, ws.max_row + 1):
        row_has_data = any(ws.cell(r, c).value is not None for c in range(1, ws.max_column + 1))
        if row_has_data:
            if current_start is None:
                current_start = r
            empty_count = 0
        else:
            if current_start is not None:
                empty_count += 1
                if empty_count >= empty_row_threshold:
                    tables.append((current_start, r - empty_count))
                    current_start = None
                    empty_count = 0
    if current_start is not None:
        tables.append((current_start, ws.max_row))
    return tables
```

---

## 7. Ukryte Arkusze, Kolumny i Wiersze

### Problem:
Arkusz zawiera kolumny robocze lub ukryte arkusze pomocnicze (np. `KU`, `Parametry_Baza`), które wprowadzają w błąd analizę danych.

### Rozwiązanie:
```python
# Sprawdzanie czy arkusz jest ukryty
for name in wb.sheetnames:
    ws = wb[name]
    is_hidden = ws.sheet_state != "visible"
    print(f"Sheet {name}: hidden={is_hidden}")

# Sprawdzanie ukrytych kolumn i wierszy
hidden_cols = [col_letter for col_letter, dim in ws.column_dimensions.items() if dim.hidden]
hidden_rows = [row_idx for row_idx, dim in ws.row_dimensions.items() if dim.hidden]
```

---

## 8. Duże Pliki i Ograniczenia Pamięci RAM

### Problem:
Ładowanie pliku 100MB przez `load_workbook()` tworzy miliony obiektów Pythona i zużywa kilka gigabajtów RAM.

### Rozwiązanie:
1. Używaj `load_workbook(filepath, read_only=True)`.
2. Zawsze zamykaj skoroszyt po zakończeniu: `wb.close()`.
3. Jeżeli potrzebujesz wyłącznie wartości liczbowo-tekstowych, używaj `python-calamine`.
