# Production-Ready Python Code Patterns for Spreadsheets

Zestaw gotowych do natychmiastowego wdrożenia szablonów kodu w Pythonie, optymalizujących czas pracy i zużycie tokenów.

---

## Wzorzec 1: Uniwersalny Adapter Pliku (Auto-wybór silnika .xlsx / .xls / .ods)

Gwarantuje otwarcie dowolnego formatu bez błędu nieobsługiwanego rozszerzenia:

```python
from pathlib import Path
import pandas as pd

def read_spreadsheet_universal(filepath: str, sheet_name=0) -> pd.DataFrame:
    """Uniwersalny odczyt tabeli do pandas DataFrame z automatycznym wyborem silnika."""
    ext = Path(filepath).suffix.lower()
    
    if ext in [".xlsx", ".xlsm", ".xltx"]:
        return pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")
    elif ext == ".xls":
        try:
            return pd.read_excel(filepath, sheet_name=sheet_name, engine="calamine")
        except Exception:
            return pd.read_excel(filepath, sheet_name=sheet_name, engine="xlrd")
    elif ext == ".ods":
        return pd.read_excel(filepath, sheet_name=sheet_name, engine="odf")
    else:
        raise ValueError(f"Nieobsługiwany format arkusza: {ext}")
```

---

## Wzorzec 2: Klasa `MergedCellResolver` dla `openpyxl`

Zapewnia automatyczne propagowanie wartości ze scalonych komórek do wszystkich pól w ich zasięgu:

```python
from typing import Any, Optional
from openpyxl.worksheet.worksheet import Worksheet

class MergedCellResolver:
    """Transparentny resolver scalonych komórek dla arkusza openpyxl."""
    
    def __init__(self, worksheet: Worksheet):
        self.ws = worksheet
        self.lookup: dict[tuple[int, int], Any] = {}
        self._build_lookup()
        
    def _build_lookup(self) -> None:
        for rng in self.ws.merged_cells.ranges:
            top_left_cell = self.ws.cell(row=rng.min_row, column=rng.min_col)
            val = top_left_cell.value
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    self.lookup[(r, c)] = val

    def get_value(self, row: int, col: int) -> Any:
        """Pobiera wartość komórki; jeśli leży w obszarze scalonym, zwraca wartość z lewej-górnej komórki."""
        if (row, col) in self.lookup:
            return self.lookup[(row, col)]
        return self.ws.cell(row=row, column=col).value
```

---

## Wzorzec 3: Dynamiczne Wykrywanie Wiersza Nagłówkowego (Bez sztywnych indeksów)

Algorytm heurystyczny szukający wiersza o największej gęstości etykiet tekstowych lub określonych słów kluczowych:

```python
from typing import List, Optional
import openpyxl

def detect_header_row(ws, max_scan_rows=15, keywords=None) -> int:
    """Wyszukuje indeks wiersza nagłówkowego na podstawie słów kluczowych lub gęstości tekstu.
    Zwraca numer wiersza (1-indexed).
    """
    if keywords is None:
        keywords = ["nazwa", "opis", "data", "powierzchnia", "ilość", "suma", "etap", "faza", "nr"]
    
    keywords_lower = [k.lower() for k in keywords]
    best_row = 1
    best_score = -1
    
    for r in range(1, min(max_scan_rows + 1, ws.max_row + 1)):
        row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        str_vals = [str(v).strip().lower() for v in row_vals if v is not None and str(v).strip()]
        
        if not str_vals:
            continue
            
        # Punktacja: dopasowania słów kluczowych (waga 3) + unikalne napisy niebędące liczbami (waga 1)
        score = sum(3 for s in str_vals if any(k in s for k in keywords_lower))
        score += sum(1 for s in str_vals if not s.replace(".", "").isdigit())
        
        if score > best_score:
            best_score = score
            best_row = r
            
    return best_row
```

---

## Wzorzec 4: Bezpieczny Odczyt Formuł i Wyliczeń (Podwójny Skoroszyt)

```python
from openpyxl import load_workbook

class DualWorkbookReader:
    """Umożliwia równoczesny dostęp do wyliczonych wartości oraz definicji formuł."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.wb_vals = load_workbook(filepath, data_only=True)
        self.wb_forms = load_workbook(filepath, data_only=False)
        
    def get_cell_pair(self, sheet_name: str, row: int, col: int) -> dict:
        ws_v = self.wb_vals[sheet_name]
        ws_f = self.wb_forms[sheet_name]
        
        val = ws_v.cell(row=row, column=col).value
        formula = ws_f.cell(row=row, column=col).value
        
        is_formula = isinstance(formula, str) and formula.startswith("=")
        return {
            "value": val,
            "formula": formula if is_formula else None,
            "has_formula": is_formula
        }
```

---

## Wzorzec 5: Pętla Strumieniowa dla Wielkich Zbiorów (`Streaming Reader`)

```python
from openpyxl import load_workbook

def stream_rows(filepath: str, sheet_name: str, batch_size=500):
    """Zwraca generator wierszy z minimalnym zużyciem pamięci RAM."""
    wb = load_workbook(filepath, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        batch = []
        for row in ws.iter_rows(values_only=True):
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
    finally:
        wb.close()
```
