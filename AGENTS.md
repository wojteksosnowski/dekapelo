# Dekapelo - Project Rules & Guidelines

## 1. Workspace Boundary & Isolation
- **Strict Isolation**: ALL operations, searches, file views, and command executions MUST remain strictly within this project's root directory (`C:\py\dekapelo`).
- NEVER scan, search, or navigate to parent directories or adjacent directories on disk (e.g., `C:\py\*`, other projects).
- **No External Runtime Scanning**: NEVER search, scan, or probe the filesystem, user profile (`$env:USERPROFILE`), PATH, or WindowsApps for Python binaries or packages. The entire runtime is local to this workspace.

## 2. Real Estate Development KPI, Stage & Phase Domain Model
- **Design Phases (Fazy Projektowe) vs Investment Stages (Etapy Inwestycji)**:
  - **Fazy projektowe** (*Design Phases*): `APK` (Analiza Przedkoncepcyjna), `WPK` (Wstępna Koncepcja Pokonkursowa / Koncepcja), `PB` (Projekt Budowlany), `PW` (Projekt Wykonawczy). Oznaczają stopień zaawansowania i stadium opracowania dokumentacji projektowej.
  - **Etapy inwestycji** (*Investment Stages*): części zamierzenia inwestycyjnego, opracowywane i realizowane osobno (np. `Etap 1`, `Etap 2`, `Teren 10`, `Zadanie B`, `Budynek A`). W przypadku inwestycji jednoetapowych etap to całe zamierzenie (np. `Całość` lub `Etap I`).
  - **Primary Unit of Study**: Podstawową jednostką analityczną i pomiarową jest **Etap Inwestycji w określonej Fazie Projektowej** (np. *Morska Vita – Etap 2 [PW]*), powiązany z jednolitą nazwą inwestycji (`investment_name`).
- **Plot Allocation & Land Absorptiveness (Działka i Chłonność)**:
  - Etapy mogą mieć **własną działkę** (wydzieloną geodezyjnie/bilansowo powierzchnię działki dla danego etapu $Pd_{\text{etapu}}$) LUB być realizowane na **części działek inwestycji** (wspólna działka/udział w terenie inwestycji $Pd_{\text{inwestycji}}$).
  - Gdy etap ma własną działkę: $\text{Chłonność etapu} = \frac{PUMiU_{\text{etapu}}}{Pd_{\text{etapu}}}$.
  - Gdy etap jest realizowany na części działki inwestycji: brak indywidualnej działki dla etapu w arkuszu jest zjawiskiem prawidłowym (nie wolno traktować tego jako błąd audytu); chłonność odnosi się do terenu całej inwestycji lub sumy zrealizowanych etapów. Nie wolno bezkrytycznie dzielić $PUMiU$ cząstkowego etapu przez $Pd$ całej inwestycji bez oznaczenia, że to działka wspólna.
- **Phase Hierarchy & Leading Stage Resolution (Hierarchia Faz: APK < WPK < PB < PW)**:
  - Każdy etap jest w określonej fazie projektowej.
  - Obowiązuje ścisła hierarchia zaawansowania dokumentacji projektowej: $APK < WPK < PB < PW$.
  - W zestawieniach portfela, benchmarkingu BI, obliczeniach sumarycznych inwestycji (np. łączny PUM, lokale) oraz analizach bierzemy pod uwagę **wyłącznie fazę najwyżej w hierarchii dla danego etapu**.
  - Niższe fazy tego samego etapu (np. PB gdy dostępny jest PW) służą do audytu międzyfazowego (*Cross-Phase Audit*), lecz nie mogą dublować metrażu ani wskaźników etapu w zestawieniach analitycznych.
- **Cross-Phase Audit Boundary**:
  - Audyt międzyfazowy (*Cross-Phase Audit*) służy do porównywania kolejnych faz projektowych **tego samego etapu** (np. `Etap 1 (PB)` -> `Etap 1 (PW)`).
  - NIGDY nie porównuj różnych etapów (np. `Etap 1` vs `Etap 2`) jako rzekomych kolejnych faz w audycie międzyfazowym.
- **Phase Exclusions**: Columns or tables labeled `PLANNING requirements`, `KU`, or `Koncepcja Urbanistyczna` are not measurement stages and must be excluded from parsing and database ingestion.
- **Mathematical vs. Merit Audit**:
  - The mathematical audit strictly verifies algebraic consistency ($PUM + PUU == PUMiU$, $Pc == Pcn + Pcp$, $Pcnb == Pcn + Plb$, ratio recalculations).
  - External quota compliance (e.g. required parking count from WZ/MPZP) is a merit/legal assessment, NOT a mathematical audit check.
- **Dual Residential Usable Area Standards (PN-ISO vs PNB)**:
  - Always recognize and distinguish between the two parallel residential usable area standards:
    - $PUM_{PN-ISO}$ (PN-ISO 9836, "duży PUM" / new standard)
    - $PUM_{PNB}$ (PN-70/B-02365 / PN-B, "mały PUM" / traditional standard with deductions)
  - Both variants must be extracted when present in the spreadsheet (`pum_iso` and `pum_pnb`).
  - When verifying $PUM + PUU == PUMiU$, dynamically determine which standard was summed in the architect's spreadsheet and audit against it, while noting the alternative variant in the audit report.
- **Semantic Boundary (Absolute Areas vs Ratios)**:
  - Labels containing division symbols (`/`, e.g. `/mp`, `/lokal`, `/pcn`, `(Pcp/mp)`) or keywords like `sprawność`, `wskaźnik`, `współczynnik`, `iloraz`, `per` MUST NEVER be mapped to absolute area metrics ($m^2$, such as $Pcp$, $PUM$, $PUU$, $Pc$). They must strictly map to indicator fields.
- **Overground Areas ($Pcn$ vs $Pcnb$)**:
  - Always distinguish overground gross area without balconies/loggias ($Pcn$) from overground gross area including balconies/loggias ($Pcnb$).
  - Mathematical balance: $Pcnb == Pcn + Plb$ ($\pm 0.5\text{ m}^2$) where $Plb$ is balcony and loggia area.
  - Distinguish $(PUM+PUU)/Pcn$ (efficiency without balconies) from $(PUM+PUU)/Pcnb$ (efficiency with balconies).
- **Rigid Ratio Detection**: Always check whether $PUM$ or $PUMiU$ is calculated via rigid multiplier from overground gross area ($Pcn$) (e.g. exactly 0.70 or 0.72) and flag as a warning indicating an estimate rather than actual unit schedule.
- **Stage-Level Presentation & Multi-Stage Granularity**:
  - Ingestion, database storage, and UI catalog/BI views MUST NEVER collapse or truncate a multi-stage investment to a single phase (e.g. `phases[0]`).
  - All stages of an investment must be presented and inspectable (e.g. via accordion or sub-table) with their individual metrics ($PUM_{ISO}$, $PUM_{PNB}$, $PUU$, $PUMiU$, $Pcn$, $Pcnb$, $Plb$, Chłonność, and MP).

## 3. Dataset-Wide Integrity & Dynamic Parsing Invariants
- **No Rigid Row or Column Numbers**: Spreadsheets are manually edited by different authors and vary from 60 to 1000+ rows. NEVER assume parameters reside at fixed row or column indices. Parsing must always be dynamic and semantic.
- **No Tautological or Single-File Tests**: Automated tests must NOT be tailored to a single file. Test suites must dynamically iterate and assert dataset invariants across ALL files in `KPI - WSKAZNIKI/`.

## 4. Secrets & Environment Variables
- Tokens, passwords, and Personal Access Tokens (PAT) must be stored ONLY in `.env`.
- Ensure `.env` and `*.env` are in `.gitignore` and never committed to version control.

## 5. Python Environment & Execution Invariants
- **Always Use Local `.venv`**: ALL scripts, tests, commands, and app servers MUST run exclusively against the project's local virtual environment (`C:\py\dekapelo\.venv`).
- **Standard Command Invocation**:
  Always set `$env:PYTHONPATH` to `.venv\Lib\site-packages` and project root, executing via `.\.pybin\python.exe`:
  ```powershell
  $env:PYTHONPATH = "C:\py\dekapelo\.venv\Lib\site-packages;C:\py\dekapelo"
  .\.pybin\python.exe -m pytest
  ```
- **Zero Tolerance for System Scanning**: NEVER run `where.exe python`, `Get-Command python`, or any search across external drives or user profile directories.

## 6. Frontend Architecture & DOM Invariants
- **Strict SPA Tab Sibling Isolation**:
  - All tab containers (`.tab-content` toggled via `classList.add('hidden')` / `remove('hidden')`) MUST be strictly top-level sibling elements within `<main>`.
  - NEVER nest a `.tab-content` container inside another `.tab-content` section. An unclosed or nested section causes child views to inherit `display: none` silently when switching tabs, without producing JavaScript runtime errors.
  - Test suites must include structural DOM regression tests (e.g. `test_tabs_dom_structure`) asserting proper tag closure and non-nesting of navigation tabs.
- **Offline & CDN Resilience**:
  - Visualisation engines (e.g. Chart.js) loaded via CDN must be guarded by checks (`typeof Chart !== 'undefined'`) and error boundaries. Data tables and tabular benchmarks MUST always render completely even if external CDN scripts fail to load.


