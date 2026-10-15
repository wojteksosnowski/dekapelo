---
name: spreadsheet-analysis-expert
description: >-
  Ekspert w analizie, inspekcji i ekstrakcji danych z plików arkuszy kalkulacyjnych (.xlsx, .xls, .ods)
  za pomocą skryptów Python. Użyj, gdy masz zbadać strukturę nieznanego arkusza kalkulacyjnego,
  odczytać wartości ze scalonych komórek (merged cells), wyekstrahować wielopoziomowe nagłówki,
  przeliczyć formuły lub uniknąć typowych błędów odczytu w Excelu (spacje \xa0, None w data_only, formaty dat).
---

# Spreadsheet Analysis Expert (Python)

Ten skill dostarcza zoptymalizowane procedury, narzędzia CLI oraz bezbłędne wzorce kodu do pracy z arkuszami kalkulacyjnymi w Pythonie. Jego celem jest **maksymalne skrócenie czasu pracy agenta oraz eliminacja zbędnego zużycia tokenów** spowodowanego wielokrotnym pisaniem kodu inspekcyjnego od zera lub zrzucaniem zawartości całych arkuszy do kontekstu.

---

## 3-Krokowy Standard Pracy z Arkuszem Kalkulacyjnym

Nigdy nie zgaduj struktury arkusza ani nie wczytuj całego pliku bezpośrednio do promptu LLM. Zawsze postępuj według poniższego protokołu:

### Krok 1: Bezkosztowa Inspekcja Strukturalna (CLI)
Zamiast pisać własny skrypt badawczy w Pythonie, natychmiast uruchom dołączone narzędzie inspekcji:

```powershell
$env:PYTHONPATH = "C:\py\dekapelo\.venv\Lib\site-packages;C:\py\dekapelo"
.\.pybin\python.exe .agents/skills/spreadsheet-analysis-expert/scripts/inspect_spreadsheet.py "ścieżka/do/pliku.xlsx"
```
*Dla formatu JSON przekaż flagę `--json`. Dla konkretnego arkusza dodaj `--sheet "Nazwa" --rows 8`.*

**Co otrzymujesz w 1 sekundę:**
- Listę wszystkich arkuszy i ich status widoczności (`hidden`).
- Dokładne wymiary wierszy i kolumn.
- Liczbę i próbkę komórek scalonych (`merged_cells`).
- Informację, czy w pliku występują aktywne formuły (`=SUM`, `=B2*C2`).
- Zwięzły podgląd pierwszych wierszy z danymi.

---

### Krok 2: Precyzyjny Podgląd Wybranego Wycinka (CLI)
Jeśli chcesz zobaczyć konkretną tabelę lub nagłówek bez dumpowania setek wierszy:

```powershell
.\.pybin\python.exe .agents/skills/spreadsheet-analysis-expert/scripts/extract_table_slice.py "ścieżka/do/pliku.xlsx" --sheet "Arkusz1" --start-row 1 --end-row 20 --start-col 1 --end-col 10
```
*Skrypt automatycznie rozwiązuje scalone komórki (`merged cells`), dzięki czemu kolumny potomne nie zwracają pustych wartości `None`!*

---

### Krok 3: Wybór Właściwego Silnika i Wzorca Kodu

W zależności od rozszerzenia pliku i typu zadania, wybierz odpowiedni silnik i skopiuj gotowy wzorzec:

1. **Dobór silnika**: Zobacz [Engine Guide](./references/engine_guide.md)
   - `.xlsx` / `.xlsm` $\rightarrow$ `openpyxl` (lub `calamine` dla wielkich plików).
   - `.xls` (stary format binarny) $\rightarrow$ `xlrd` lub `calamine`. *(Pamiętaj: openpyxl zwróci błąd na plikach .xls!)*
   - `.ods` $\rightarrow$ `pandas` z silnikiem `odf` (`odfpy`).

2. **Unikanie pułapek**: Zobacz [Common Pitfalls](./references/common_pitfalls.md)
   - **Scalone komórki**: Użyj mapy lookupu `MergedCellResolver`.
   - **Brak cache'u wartości w formułach**: `data_only=True` zwraca `None`, jeśli plik nie był zapisany w MS Excel. Zastosuj dwufazowy odczyt (wartość $\rightarrow$ formuła).
   - **Polskie formaty liczb i walut**: Spacje twarde `\xa0`, przecinki dziesiętne, jednostki `zł`, `m2`.

3. **Gotowe szablony kodu**: Zobacz [Code Patterns](./references/code_patterns.md)
   - [Wzorzec 1: Uniwersalny adapter .xlsx / .xls / .ods](./references/code_patterns.md#wzorzec-1-uniwersalny-adapter-pliku-auto-wybór-silnika-xlsx--xls--ods)
   - [Wzorzec 2: Klasa MergedCellResolver](./references/code_patterns.md#wzorzec-2-klasa-mergedcellresolver-dla-openpyxl)
   - [Wzorzec 3: Dynamiczne wykrywanie nagłówka](./references/code_patterns.md#wzorzec-3-dynamiczne-wykrywanie-wiersza-nagłówkowego-bez-sztywnych-indeksów)
   - [Wzorzec 4: Podwójny odczyt (wartość + formuła)](./references/code_patterns.md#wzorzec-4-bezpieczny-odczyt-formuł-i-wyliczeń-podwójny-skoroszyt)
   - [Wzorzec 5: Pętla strumieniowa dla dużych plików](./references/code_patterns.md#wzorzec-5-pętla-strumieniowa-dla-wielkich-zbiorów-streaming-reader)

---

## Złote Reguły Bezpieczeństwa (Invariants)

1. **Nigdy nie zakładaj sztywnych numerów wierszy/kolumn**: Tabele mogą zaczynać się w wierszu 1, 5 lub 12, a kolumny mogą być przesunięte. Zawsze stosuj dynamiczną detekcję słów kluczowych lub skrypt `detect_header_row`.
2. **Zawsze weryfikuj obecność komórek scalonych**: Jeśli odczytujesz wiersz nagłówkowy, zawsze sprawdź `ws.merged_cells.ranges`. W przeciwnym razie kolumny 2, 3 i 4 otrzymają wartość `None`.
3. **Zawsze pracuj w lokalnym środowisku `.venv`**: Wywołuj Pythona wyłącznie przez `.\.pybin\python.exe` z ustawionym `$env:PYTHONPATH`. Nigdy nie skanuj dysku systemowego w poszukiwaniu interpreterów.
