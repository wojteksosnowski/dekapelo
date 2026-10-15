# Spreadsheet Engines Guide (Python)

Kompendium doboru i optymalizacji bibliotek Pythona do pracy z arkuszami kalkulacyjnymi `.xlsx`, `.xls` i `.ods`.

---

## 1. Tabela Szybkiego Doboru Silnika

| Format pliku | Rekomendowany silnik główny | Alternatywa / Do czego najlepsza | Ograniczenia i pułapki |
| :--- | :--- | :--- | :--- |
| **`.xlsx`** / **`.xlsm`** | **`openpyxl`** | **`calamine`** (python-calamine) – ultra szybki odczyt dużych plików | `openpyxl` bywa wolny dla plików > 50MB (wtedy użyj `read_only=True` lub `calamine`). |
| **`.xls`** (stary binarny Excel 97-2003 BIFF8) | **`xlrd`** (wersja wspierająca xls) / **`calamine`** | **`msoffcrypto-tool`** – jeśli plik jest zaszyfrowany hasłem | `openpyxl` w ogóle **nie obsługuje** `.xls`! Próba otwarcia zwróci `InvalidFileException`. |
| **`.ods`** (OpenDocument LibreOffice) | **`odfpy`** / **`pandas` (engine="odf")** | **`calamine`** – natywnie czyta ODS bez instalacji LibreOffice | Wymaga biblioteki `odf` w środowisku wirtualnym dla pandas. |
| **Tabele czyste (grid bez nagłówków złożonych)** | **`pandas.read_excel()`** | **`polars.read_excel()`** (używa `calamine` pod maską) | Pandas może zepsuć wielopoziomowe nagłówki i gubi scalenia, jeśli nie poda się `header=[0, 1]`. |

---

## 2. Szczegółowe Przewodniki po Silnikach

### A. `openpyxl` (Natywny standard dla `.xlsx`)

Zalecany do precyzyjnej analizy struktury, styli, scalonych komórek oraz formuł.

#### Tryby otwierania skoroszytu:
1. **Tryb pełny z formułami (`data_only=False` - domyślny)**:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook("plik.xlsx", data_only=False)
   ws = wb.active
   # Zwraca string formuły, np. "=SUM(B2:B10)"
   print(ws["B11"].value)
   ```
2. **Tryb wartości przeliczonych (`data_only=True`)**:
   ```python
   wb = openpyxl.load_workbook("plik.xlsx", data_only=True)
   ws = wb.active
   # Zwraca wyliczoną wartość, np. 1250.0 (lub None, jeśli plik nigdy nie był przeliczony w Excelu!)
   print(ws["B11"].value)
   ```
3. **Tryb strumieniowy dla wielkich plików (`read_only=True`)**:
   ```python
   # Zużywa minimalną ilość RAM nawet dla plików 500 MB
   wb = openpyxl.load_workbook("duzy_plik.xlsx", read_only=True, data_only=True)
   ws = wb.active
   for row in ws.iter_rows(values_only=True):
       pass
   wb.close() # Pamiętaj o zamknięciu w trybie read_only!
   ```

---

### B. `xlrd` (Dla starszych plików `.xls`)

Format `.xls` (BIFF8) nie jest formatem XML (jak xlsx), lecz binarnym strumieniem OLE2.

```python
import xlrd

book = xlrd.open_workbook("stary_plik.xls", formatting_info=True)
sheet = book.sheet_by_index(0)

# Liczba wierszy i kolumn
print(f"Rows: {sheet.nrows}, Cols: {sheet.ncols}")

# Odczyt komórki
cell_value = sheet.cell_value(rowx=0, colx=0)

# Obsługa dat w xlrd (zwracają liczby typu float!)
if sheet.cell_type(rowx=1, colx=1) == xlrd.XL_CELL_DATE:
    date_tuple = xlrd.xldate_as_tuple(sheet.cell_value(1, 1), book.datemode)
    # date_tuple = (rok, miesiac, dzien, godzina, minuta, sekunda)
```

---

### C. `python-calamine` (Nowoczesny, ultra-szybki odczyt w Rust)

Czyta formaty `.xlsx`, `.xls`, `.xlsb`, `.ods` z prędkością kilkunastokrotnie wyższą niż czysty Python, zużywając ułamek pamięci.

```python
from python_calamine import CalamineWorkbook

wb = CalamineWorkbook.from_path("plik.xlsx")
sheet_names = wb.sheet_names
rows = wb.get_sheet_by_name(sheet_names[0]).to_python()
# rows to prosta lista list: [[w1k1, w1k2], [w2k1, w2k2], ...]
```

---

### D. `odfpy` / `pandas` z silnikiem ODF (Dla `.ods`)

```python
import pandas as pd

# Odczyt arkusza OpenDocument przez pandas
df = pd.read_excel("dane.ods", engine="odf", sheet_name=0)
```
Lub bezpośrednio przez `odfpy`:
```python
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell

doc = load("dane.ods")
tables = doc.spreadsheet.getElementsByType(Table)
for table in tables:
    name = table.getAttribute("name")
    rows = table.getElementsByType(TableRow)
```
