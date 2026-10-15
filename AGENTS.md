# Dekapelo - Project Rules & Guidelines

## 1. Workspace Boundary & Isolation
- **Strict Isolation**: ALL operations, searches, file views, and command executions MUST remain strictly within this project's root directory (`C:\py\dekapelo`).
- NEVER scan, search, or navigate to parent directories or adjacent directories on disk (e.g., `C:\py\*`, other projects).

## 2. Real Estate Development KPI & Stage Domain Model
- **Primary Unit of Study**: The fundamental unit of analysis is the **Etap Inwestycji** (Investment Stage, e.g. `APK`, `WPK`, `Projekt Budowlany`, `Projekt Wykonawczy`), linked to a uniform investment name (`investment_name`).
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
- **Land Absorptiveness (Chłonność)**: Always calculate absorptiveness strictly as: $\text{Chłonność} = \frac{PUMiU}{\text{Powierzchnia działki}}$.

## 3. Dataset-Wide Integrity & Dynamic Parsing Invariants
- **No Rigid Row or Column Numbers**: Spreadsheets are manually edited by different authors and vary from 60 to 1000+ rows. NEVER assume parameters reside at fixed row or column indices. Parsing must always be dynamic and semantic.
- **No Tautological or Single-File Tests**: Automated tests must NOT be tailored to a single file. Test suites must dynamically iterate and assert dataset invariants across ALL files in `KPI - WSKAZNIKI/`.

## 4. Secrets & Environment Variables
- Tokens, passwords, and Personal Access Tokens (PAT) must be stored ONLY in `.env`.
- Ensure `.env` and `*.env` are in `.gitignore` and never committed to version control.
