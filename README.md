# dekapelo

**Lokalny System Audytu, Bazy i Analityki Wskaźników Projektów Deweloperskich (DevAudit & BI)**

Aplikacja stworzona do automatyzacji importu, weryfikacji matematycznej i spójności logicznej tabel parametrów i wskaźników inwestycyjnych z plików Excel (`.xlsx`, `.xls`, `.ods`), agregacji danych w relacyjnej bazie SQLite oraz interaktywnej analityki porównawczej (BI) w nowoczesnym interfejsie opartym na **Tailwind CSS**.

---

## Główne Funkcjonalności

1. **Parser Tabel Wskaźników:**
   - Inteligentne rozpoznawanie etapów i faz inwestycji (np. `Koncepcja`, `APK`, `WPK`, `Projekt Budowlany (PB)`, `Projekt Wykonawczy (PW)`).
   - Ścisłe wykluczenie kolumn niemających charakteru faz projektowych (`PLANNING requirements`, `KU` / Koncepcja Urbanistyczna).
   - Elastyczne mapowanie etykiet parametrów (powierzchnie działki, zabudowy, utwardzone, biologicznie czynne, PUM/PUU, kubatury, miejsca parkingowe, komórki, wskaźniki intensywności i sprawności).
   - Obsługa plików `.xlsx`, `.xls` oraz `.ods` (Trójmiasto, BemowoVita, A2).

2. **Silnik Audytu Matematycznego i Spójności:**
   - **Cross-check matematyczny:** walidacja bilansu PUM i PUU ($PUMiU == PUM + PUU$), bilansu powierzchni całkowitej ($Pc == Pcn + Pcp$), weryfikacja formuł wskaźników sprawności (nadziemia $PUMiU/Pcn$, całkowitej $PUMiU/Pc$, intensywności $PUMiU/Pd$).
   - **Detekcja sztywnych wskaźników:** wykrywanie wartości wyliczonych stałymi współczynnikami (np. PUM/PCn = 0.700000000000000 lub 0.720000000000000), sugerujących szacunek wskaźnikowy zamiast dokładnego bilansu.
   - **Wyłączenie walidacji merytorycznych:** spełnienie wymogu miejsc parkingowych (zaprojektowane vs wymagane MP) jest weryfikacją merytoryczną/prawną i nie obciąża audytu matematycznego.
   - **Audyt międzyfazowy (Cross-Phase):** automatyczne zestawianie wgrywanego pliku z historycznymi etapami z bazy i wykrywanie odchyleń PUM czy liczby mieszkań.

3. **Strefa Buforowa (Staging Area) & Autouzupełnianie:**
   - Weryfikacja pliku przed zapisem do bazy z podglądem parametrów i logów audytu.
   - Automatyczne podpowiadanie nazwy inwestycji, etapu, lokalizacji i dewelopera na podstawie bazy SQLite oraz podpowiedzi brakujących wartości parametrów (np. powierzchni działki z wcześniejszych etapów).
   - Dedykowane pole wyboru i nazwania etapu inwestycji (`stage_name`) jako podstawowej jednostki badawczej.

4. **Lokalna Baza Danych SQLite:**
   - Przechowywanie danych inwestycji, zarejestrowanych etapów, kompletnych wskaźników oraz historii logów audytu w jednym pliku `dekapelo.db`.
   - Pełna prywatność i praca on-premise (żadne dane wrażliwe nie trafiają do chmury).

5. **Interfejs Użytkownika z Tailwind CSS & Benchmarking BI:**
   - Jednolity, elegancki design z **Tailwind CSS**.
   - Wykresy analityczne (Chart.js): PUM vs lokale, wskaźniki sprawności, a także wykres punktowy relacji **Powierzchnia działki (oś X) vs Chłonność terenu PUMiU/Pd (oś Y)**.
   - Macierz porównawcza wskaźników w formie tabeli z parametrami powierzchni działki i chłonności.

---

## Wymagania i Instalacja

Aplikacja wymaga środowiska **Python 3.11+** (wspiera Python 3.13).

```powershell
# Klonowanie repozytorium
git clone https://github.com/wojteksosnowski/dekapelo.git
cd dekapelo

# Utworzenie i aktywacja środowiska wirtualnego
python -m venv .venv
.\.venv\Scripts\activate

# Instalacja zależności
pip install -e .
# lub:
pip install fastapi uvicorn python-multipart pandas openpyxl odfpy sqlalchemy jinja2 pytest httpx
```

---

## Uruchomienie Aplikacji

Aplikację uruchamia się jednym poleceniem:

```powershell
.\.venv\Scripts\python -m dekapelo.app
```

lub bezpośrednio przez uvicorn:

```powershell
.\.venv\Scripts\uvicorn dekapelo.ui.app:app --host 127.0.0.1 --port 8000
```

Po uruchomieniu otwórz przeglądarkę internetową pod adresem:
👉 **`http://127.0.0.1:8000`**

---

## Uruchamianie Testów Automatycznych

Do testów wykorzystywany jest katalog `KPI - WSKAZNIKI`, zawierający rzeczywiste arkusze projektów deweloperskich.

```powershell
.\.venv\Scripts\pytest -v
```

Zestaw testów obejmuje:
- Parsowanie i audyt każdego pliku z katalogu `KPI - WSKAZNIKI` (`test_all_indicator_files.py`),
- Testy reguł matematycznych i logicznych audytora (`test_kpi_auditor.py`),
- Testy bazy danych SQLite i silnika BI (`test_database.py`),
- Testy parsera i czyszczenia danych (`test_kpi_parser.py`),
- Testy integracyjne endpointów API FastAPI (`test_api.py`).

---

## Licencja i Prawa Autorskie
Projekt rozwijany w ramach analizy inwestycji deweloperskich.
Repozytorium GitHub: [https://github.com/wojteksosnowski/dekapelo](https://github.com/wojteksosnowski/dekapelo)
