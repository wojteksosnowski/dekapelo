# Specyfikacja Funkcjonalna i Techniczna: Lokalny System Audytu i Analizy Projektów Deweloperskich (DevAudit & BI)

## 1. Cel Systemu
Stworzenie lokalnej aplikacji (działającej na komputerze użytkownika bez konieczności wysyłania wrażliwych danych do chmury), która służy do:
1. **Standaryzacji i importu** cenników/zestawień mieszkań z plików Excel (`.xlsx`).
2. **Automatycznego audytu (walidacji)** poprawności danych i wyliczeń matematycznych przed zapisaniem ich w bazie.
3. **Gromadzenia danych** z kilkudziesięciu projektów w jednej relacyjnej bazie danych.
4. **Analizy porównawczej (BI) i wizualizacji** struktury projektów oraz cen, z funkcją bezpośredniego eksportu wykresów do plików graficznych (`.png`).

---

## 2. Analiza Struktury Danych Źródłowych (na podstawie pliku `C1C2.xlsx`)
Przeanalizowany plik zawiera **124 rekordy (mieszkania)** w 2 budynkach (C1, C2), podzielone na 27 kolumn. Struktura pliku ujawnia specyficzne cechy, które aplikacja musi obsłużyć:

* **Wiersze nagłówkowe i podsumowania:** Właściwe dane zaczynają się od wiersza 3. Wiersz 127 zawiera podsumowania (SUM, AVERAGE), które parser musi zignorować podczas importu rekordów, ale może wykorzystać do krzyżowego sprawdzenia sum kontrolnych.
* **Złożona struktura powierzchni:** PUM (Powierzchnia Użytkowa Mieszkań) dzieli się na: *Powierzchnię mieszkalną*, *Powierzchnię ścian działowych* oraz *Powierzchnię pod ścianami nadającymi się do demontażu*.
* **Złożona struktura cenowa:** Ceny mieszkań, komórek lokatorskich (KL), miejsc postojowych (MP), ogrodów/tarasów/balkonów wyliczane są kaskadowo, a na końcu pomniejszane o procentowy rabat.
* **Wartości wielokrotne i tekstowe w polach liczbowych:** np. w kolumnie nr MP pojawiają się wartości łamane (`78/79` dla miejsc rodzinnych) lub tekstowe (`brak`).

---

## 3. Moduł 1: Importer i Silnik Audytu Danych (Kluczowy komponent)

Przed dodaniem pliku do bazy danych, plik trafia do **Strefy Buforowej (Staging Area)**, gdzie przechodzi automatyczny audyt. Użytkownik widzi raport z błędami (podświetlenie na czerwono – błąd krytyczny, na żółto – ostrzeżenie) i decyduje o zatwierdzeniu importu.

### 3.1. Reguły Walidacji Matematycznej (Cross-Check)
Aplikacja przelicza wartości od nowa i porównuje je z wartościami wczytanymi z Excela (z tolerancją błędu zaokrągleń $\pm 0.05\text{ PLN}$ lub $\pm 0.01\text{ m}^2$):

1. **Audyt PUM:**
   $$\text{PUM} == \text{Pow. mieszkalna} + \text{Pow. ścian działowych} + \text{Pow. pod ścianami do demontażu}$$
   *(W pliku `C1C2.xlsx` dla lokalu C1_1: $51.40 + 1.65 + 0.00 = 53.05\text{ m}^2$ – ZGODNE)*
2. **Audyt Ceny Mieszkania:**
   $$\text{Cena mieszkania} == \text{PUM} \times \text{Cena za m}^2\text{ PUM}$$
3. **Audyt Komórki Lokatorskiej (KL):**
   $$\text{Cena KL} == \text{Powierzchnia KL} \times \text{Cena za m}^2\text{ KL}$$
4. **Audyt Powierzchni Dodatkowych (Ogród / Taras / Balkon):**
   $$\text{Cena dodatkowa} == \text{Pow. dodatkowa} \times \text{Cena za m}^2\text{ pow. dodatkowej}$$
5. **Audyt Ceny Całkowitej (Przed rabatem):**
   $$\text{Cena z przynależnościami} == \text{Cena mieszkania} + \text{Cena KL} + \text{Cena MP} + \text{Cena pow. dodatkowej}$$
6. **Audyt Rabatu:**
   $$\text{Cena po rabacie} == \text{Cena z przynależnościami} \times (1 - \text{Rabat w \%})$$
7. **Audyt Wskaźnika Ceny Całkowitej na $\text{m}^2$ PUM:**
   $$\text{Cena całkowita na m}^2 == \frac{\text{Cena po rabacie}}{\text{PUM}}$$

### 3.2. Reguły Walidacji Logicznej i Biznesowej
1. **Unikalność:** Sprawdzenie, czy w obrębie projektu nie duplikują się numery mieszkań, numery KL lub numery MP (np. czy to samo miejsce postojowe nie zostało przypisane do dwóch różnych mieszkań).
2. **Spójność przynależności:**
   * Jeśli `Nr KL` == "brak", to `Powierzchnia KL` oraz `Cena KL` muszą wynosić $0$ (i odwrotnie: jeśli pow. $> 0$, musi istnieć numer).
   * Jeśli `Typ MP` == "brak", `Cena MP` musi wynosić $0$.
   * Jeśli `Typ MP` == "rodzinne", system sprawdza, czy w polu numeru są dwa numery (np. format `X/Y`) lub czy cena odpowiada cenie miejsca rodzinnego (w pliku: $36\,000\text{ PLN}$ vs $25\,000\text{ PLN}$ za pojedyncze).
3. **Spójność kondygnacji i powierzchni dodatkowych:**
   * Ostrzeżenie (żółte): Mieszkanie na piętrze $> 0$ posiada przypisany "Ogród" zamiast "Balkon/Taras", lub mieszkanie na parterze ($0$) posiada bardzo małą powierzchnię dodatkową typową dla balkonu, a oznaczoną jako ogród.
4. **Detekcja anomalii (Outliers):**
   * Ostrzeżenie, jeśli cena za $m^2$ PUM danego lokalu odchyla się o więcej niż $\pm 20\%$ od średniej dla danego projektu.
   * Ostrzeżenie, jeśli udział ścian działowych w PUM przekracza określony próg (np. $> 5\%$).

---

## 4. Moduł 2: Struktura Lokalnej Bazy Danych

Baza danych zostanie oparta na silniku **SQLite** (jeden plik na dysku, brak konieczności instalacji serwera bazodanowego, łatwy backup).

### Schemat Tabel:
1. **`Projects` (Projekty / Inwestycje)**
   * `id` (PK), `name` (Nazwa inwestycji), `city` (Miasto), `district` (Dzielnica), `developer` (Deweloper/Spółka celowa), `import_date` (Data dodania), `status` (W sprzedaży / Zakończony / Planowany), `notes`.
2. **`Units` (Lokale - tabela główna)**
   * `id` (PK), `project_id` (FK), `building` (Budynek, np. C1), `unit_number` (Nr mieszkania), `floor` (Piętro), `rooms` (Liczba pokoi).
   * **Powierzchnie ($m^2$):** `area_living` (mieszkalna), `area_walls` (ściany działowe), `area_demolishable_walls` (ściany do demontażu), `area_pum` (PUM całkowity).
   * **Ceny bazowe:** `price_per_m2_pum`, `price_base_unit` (Cena za mieszkanie).
   * **Komórki (KL):** `storage_number`, `storage_area`, `storage_price_m2`, `storage_price_total`.
   * **Miejsca postojowe (MP):** `parking_type` (pojedyncze/rodzinne/brak), `parking_number`, `parking_price`.
   * **Pow. dodatkowe:** `extra_area_type` (Ogród/Taras/Balkon), `extra_area`, `extra_area_price_m2`, `extra_area_price_total`.
   * **Podsumowanie finansowe:** `price_total_gross` (Cena z przynależnościami), `discount_rate` (Rabat %), `price_final` (Cena po rabacie), `effective_price_per_m2` (Cena całk. / PUM).
3. **`AuditLogs` (Historia importów i zaakceptowanych ostrzeżeń)**
   * Śledzenie, kiedy i z jakiego pliku zaimportowano projekt oraz jakie ostrzeżenia użytkownik zdecydował się zignorować.

---

## 5. Moduł 3: Analizy, Wykresy i Eksport do PNG

Moduł analityczny pozwoli na filtrowanie danych (po jednym projekcie, grupie projektów, budynkach, liczbie pokoi czy piętrach) oraz generowanie gotowych do prezentacji wykresów.

### 5.1. Zestaw Wbudowanych Analiz i Wykresów
1. **Struktura Mieszkań (Rozkład pokojowości i metraży):**
   * *Wykres kołowy / słupkowy:* Udział mieszkań 1-, 2-, 3-, 4-pokojowych w projekcie (lub porównanie struktury między projektami).
   * *Histogram PUM:* Rozkład powierzchni mieszkań (np. przedziały co $5\text{ m}^2$) – pozwala szybko wykryć, na jakie metraże nastawiony jest projekt (w pliku `C1C2` widać np. dużą koncentrację 2-pokojowych w okolicach $35\text{ m}^2$ oraz 3-pokojowych w okolicach $53\text{ m}^2$).
2. **Analiza Cenowa (Pricing Matrix):**
   * *Wykres pudełkowy (Boxplot):* Rozkład ceny bazowej za $m^2$ PUM oraz ceny efektywnej (z przynależnościami po rabacie) w podziale na projekty lub budynki.
   * *Wykres punktowy (Scatter plot):* Zależność ceny za $m^2$ od metrażu (PUM) oraz piętra (weryfikacja, jak małe mieszkania i wyższe piętra są premiowane cenowo).
3. **Analiza "Ukrytego PUM" (Ściany działowe):**
   * *Wykres słupkowy:* Średni procentowy udział powierzchni ścian działowych w PUM dla poszczególnych projektów (w `C1C2.xlsx` ściany stanowią średnio ok. $3.5\%$ PUM, co generuje realny przychód dla dewelopera).
4. **Analiza Przynależności (Wskaźniki nasycenia):**
   * Współczynnik miejsc postojowych i komórek lokatorskich na lokal, średni przychód z przynależności w stosunku do ceny bazowej mieszkania.

### 5.2. Eksport do PNG (Standard Prezentacyjny)
Każdy wykres oraz tabela podsumowująca posiada przycisk **"Eksportuj do PNG"**:
* **Wysoka rozdzielczość (300 DPI):** Wykresy generowane w jakości druku/prezentacji (np. $1920 \times 1080\text{ px}$ lub więcej).
* **Szablon graficzny:** Automatyczne dodawanie na dole lub górze wykresu czystego paska informacyjnego: *Tytuł analizy, Wybrane projekty, Liczba analizowanych lokali ($N$), Data wygenerowania*.
* **Opcja "Eksportuj Paczkę Raportową (ZIP)":** Jedno kliknięcie generuje komplet 6 głównych wykresów w formacie `.png` dla wybranego projektu i zapisuje je w wybranym folderze na dysku.

---

## 6. Proponowana Architektura Techniczna (Stos Technologiczny)

Ponieważ aplikacja ma działać **lokalnie**, być szybka, łatwa w utrzymaniu i świetnie radzić sobie z plikami Excel oraz wykresami, rekomenduję architekturę opartą na języku **Python**:

| Warstwa | Technologia | Uzasadnienie |
| :--- | :--- | :--- |
| **Interfejs Użytkownika (UI)** | **Streamlit** lub **PySide6 (Qt)** | **Streamlit** otwiera się w przeglądarce lokalnie (`localhost`), wygląda bardzo nowocześnie i pozwala na błyskawiczne budowanie dashboardów BI. **PySide6** to klasyczna aplikacja okienkowa `.exe`. |
| **Przetwarzanie Danych i Audyt** | **Pandas** + **OpenPyXL** | Standard branżowy do wczytywania plików `.xlsx`, czyszczenia danych i wykonywania szybkich operacji wektorowych (audyt 1000 wierszy trwa ułamek sekundy). |
| **Baza Danych** | **SQLite3** + **SQLAlchemy** | Wbudowana w Pythona, bezserwerowa baza danych. Cała baza kilkudziesięciu projektów zmieści się w jednym pliku `.db` o rozmiarze kilku megabajtów. |
| **Wykresy i Eksport PNG** | **Plotly** + **Kaleido** (lub **Matplotlib/Seaborn**) | **Plotly** daje interaktywne wykresy (można najechać myszką na konkretny lokal na wykresie), a silnik **Kaleido** pozwala jednym kliknięciem zapisać dowolny widok do krystalicznie czystego pliku `.png`. |

---

## 7. Przebieg Pracy Użytkownika (User Flow)

1. **Krok 1: Wczytanie pliku.** Użytkownik przeciąga plik typu `C1C2.xlsx` do okna aplikacji, wpisuje nazwę projektu (np. "Osiedle C - Etap 1") i wybiera mapowanie kolumn (jeśli inny plik ma nieco inną kolejność kolumn, aplikacja pozwoli zapisać szablony mapowań).
2. **Krok 2: Ekran Audytu.** Aplikacja wyświetla podsumowanie:
   * *Wczytano lokali: 124*
   * *Suma PUM: $6\,796.76\text{ m}^2$ (Zgodna z wierszem podsumowania w Excelu)*
   * *Błędy matematyczne: 0*
   * *Ostrzeżenia logiczne: X (np. lista lokali bez komórek lokatorskich)*
3. **Krok 3: Zapis do bazy.** Po kliknięciu "Zatwierdź i dodaj do bazy", rekordy trafiają do pliku `baza_deweloperska.db`.
4. **Krok 4: Analiza i Eksport.** Użytkownik przechodzi do zakładki "Analizy", zaznacza interesujące go projekty z listy, dostosowuje filtry i pobiera gotowe wykresy `.png` na dysk.