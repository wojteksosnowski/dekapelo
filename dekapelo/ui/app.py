import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from sqlalchemy.orm import Session

from dekapelo.database.connection import get_db, init_db, SessionLocal
from dekapelo.database.models import InvestmentProject, ProjectPhase, ProjectKPI, AuditLog
from dekapelo.ingestion.kpi_parser import KPIParser, clean_text
from dekapelo.auditor.kpi_auditor import KPIAuditor
from dekapelo.analytics.bi_engine import BIEngine

# Inicjalizacja bazy przy starcie
init_db()

app = FastAPI(title="dekapelo - System Wskaźników Inwestycji Deweloperskich")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, db: Session = Depends(get_db)):
    """Główny widok dashboardu z Tailwind CSS."""
    bi = BIEngine(db)
    projects = bi.get_all_projects_summary()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"projects": projects}
    )


def build_project_audit_context(project_name: str, phases_data: dict, db: Session) -> dict:
    clean_name = project_name.strip().lower() if project_name else ""
    existing_projects = db.query(InvestmentProject).all()
    matched_proj = None

    if clean_name:
        for p in existing_projects:
            if p.name.strip().lower() == clean_name:
                matched_proj = p
                break
        if not matched_proj:
            for p in existing_projects:
                p_clean = p.name.strip().lower()
                if p_clean in clean_name or clean_name in p_clean:
                    matched_proj = p
                    break

    # Obliczenie benchmarków portfela z bazy
    all_kpis = db.query(ProjectKPI).all()
    pcn_ratios = [k.wskaznik_pumiu_pcn for k in all_kpis if k.wskaznik_pumiu_pcn]
    srm_values = [k.srednia_wielkosc_mieszkania for k in all_kpis if k.srednia_wielkosc_mieszkania]
    mp_values = [k.wskaznik_mp for k in all_kpis if k.wskaznik_mp]

    benchmarks = {
        "avg_sprawnosc_nadziemia": round(sum(pcn_ratios) / len(pcn_ratios), 3) if pcn_ratios else 0.72,
        "avg_srednia_pow_mieszkania": round(sum(srm_values) / len(srm_values), 2) if srm_values else 52.0,
        "avg_wskaznik_mp": round(sum(mp_values) / len(mp_values), 2) if mp_values else 1.2,
        "total_projects": len(existing_projects),
        "total_stages": len(all_kpis)
    }

    field_suggestions = []
    existing_phases_summary = []
    combined_phases_for_audit = {}

    reimport_analysis = {
        "is_existing_project": matched_proj is not None,
        "matched_project_name": matched_proj.name if matched_proj else None,
        "is_exact_file_duplicate": False,
        "has_new_phases": False,
        "all_phases_already_imported": False,
        "new_phases_detected": [],
        "duplicate_phases": [],
        "updated_phases": [],
        "summary_message": ""
    }

    if matched_proj:
        from dekapelo.database.models import get_phase_rank
        for ph in matched_proj.phases:
            k = ph.kpi
            existing_phases_summary.append({
                "phase_name": ph.phase_name,
                "stage_name": ph.stage_name,
                "display_name": ph.display_name,
                "is_leading": ph.is_leading,
                "phase_rank": ph.phase_rank,
                "pum": k.pum if k else None,
                "puu": k.puu if k else None,
                "pumiu": k.suma_pum_i_puu if k else None,
                "lokale": k.ilosc_lokali_mieszkalnych if k else None,
                "dzialka": k.powierzchnia_dzialki if k else None,
                "pcn": k.pow_calkowita_nadziemia if k else None
            })
            if k and ph.phase_name not in phases_data and ph.display_name not in phases_data:
                combined_phases_for_audit[f"{ph.display_name} (z bazy)"] = {
                    "pum": k.pum,
                    "puu": k.puu,
                    "suma_pum_i_puu": k.suma_pum_i_puu,
                    "ilosc_lokali_mieszkalnych": k.ilosc_lokali_mieszkalnych,
                    "powierzchnia_dzialki": k.powierzchnia_dzialki,
                    "powierzchnia_calkowita": k.powierzchnia_calkowita,
                    "pow_calkowita_nadziemia": k.pow_calkowita_nadziemia,
                    "pow_calkowita_podziemia": k.pow_calkowita_podziemia
                }

        # Podpowiedź powierzchni działki jeśli brakuje w wgrywanej fazie
        known_dzialka = matched_proj.powierzchnia_dzialki or next(
            (ph.kpi.powierzchnia_dzialki for ph in matched_proj.phases if ph.kpi and ph.kpi.powierzchnia_dzialki), None
        )
        if known_dzialka:
            for p_name, p_vals in phases_data.items():
                if not p_vals.get("powierzchnia_dzialki"):
                    field_suggestions.append({
                        "field": "powierzchnia_dzialki",
                        "phase": p_name,
                        "suggested_value": known_dzialka,
                        "label": f"Etap na części działki inwestycji – wspólna działka w bazie wynosi {known_dzialka:.2f} m²",
                        "plot_type": "czesc_dzialki"
                    })

        # Analiza powtórzeń i nowych faz projektowych
        if phases_data:
            for p_key, p_vals in phases_data.items():
                inc_st = (p_vals.get("stage_name") or "").strip()
                inc_ph = (p_vals.get("phase_name") or p_key).strip()
                inc_disp = p_vals.get("display_name") or f"{inc_st} ({inc_ph})"
                inc_rank = get_phase_rank(inc_ph)

                clean_inc_st = clean_text(inc_st)
                # Dopasowanie etapu z bazy
                matching_db_phases = [
                    ph for ph in matched_proj.phases
                    if clean_text(ph.stage_name) == clean_inc_st or (clean_text(ph.stage_name) in ("całość", "") and clean_inc_st in ("całość", ""))
                ]
                if not matching_db_phases and len(matched_proj.phases) == 1 and len(phases_data) == 1:
                    matching_db_phases = list(matched_proj.phases)

                if matching_db_phases:
                    exact_ph = next(
                        (ph for ph in matching_db_phases if clean_text(ph.phase_name) == clean_text(inc_ph)),
                        None
                    )
                    if exact_ph:
                        k = exact_ph.kpi
                        pum_inc = p_vals.get("pum") or 0.0
                        pum_db = (k.pum if k else 0.0) or 0.0
                        puu_inc = p_vals.get("puu") or 0.0
                        puu_db = (k.puu if k else 0.0) or 0.0
                        pumiu_inc = p_vals.get("suma_pum_i_puu") or 0.0
                        pumiu_db = (k.suma_pum_i_puu if k else 0.0) or 0.0
                        dz_inc = p_vals.get("powierzchnia_dzialki") or 0.0
                        dz_db = (k.powierzchnia_dzialki if k else 0.0) or 0.0
                        lok_inc = p_vals.get("ilosc_lokali_mieszkalnych") or 0
                        lok_db = (k.ilosc_lokali_mieszkalnych if k else 0) or 0
                        pcn_inc = p_vals.get("pow_calkowita_nadziemia") or 0.0
                        pcn_db = (k.pow_calkowita_nadziemia if k else 0.0) or 0.0

                        is_metrics_identical = (
                            abs(pum_inc - pum_db) <= 0.1 and
                            abs(puu_inc - puu_db) <= 0.1 and
                            abs(pumiu_inc - pumiu_db) <= 0.1 and
                            abs(dz_inc - dz_db) <= 0.1 and
                            lok_inc == lok_db and
                            abs(pcn_inc - pcn_db) <= 0.1
                        )
                        if is_metrics_identical:
                            reimport_analysis["duplicate_phases"].append({
                                "phase_key": p_key,
                                "stage_name": inc_st or exact_ph.stage_name,
                                "phase_name": inc_ph,
                                "display_name": inc_disp,
                                "status": "EXACT_DUPLICATE",
                                "message": f"Faza '{inc_ph}' dla etapu '{inc_st or exact_ph.stage_name}' znajduje się już w bazie z identycznymi parametrami."
                            })
                        else:
                            reimport_analysis["updated_phases"].append({
                                "phase_key": p_key,
                                "stage_name": inc_st or exact_ph.stage_name,
                                "phase_name": inc_ph,
                                "display_name": inc_disp,
                                "status": "DATA_UPDATED",
                                "message": f"Faza '{inc_ph}' dla etapu '{inc_st or exact_ph.stage_name}' istnieje w bazie ze zmienionymi wskaźnikami (aktualizacja danych)."
                            })
                    else:
                        leading_db = max(matching_db_phases, key=lambda x: x.phase_rank)
                        is_upgrade = inc_rank > leading_db.phase_rank
                        reimport_analysis["new_phases_detected"].append({
                            "phase_key": p_key,
                            "stage_name": inc_st or leading_db.stage_name,
                            "new_phase": inc_ph,
                            "existing_phase": leading_db.phase_name,
                            "display_name": inc_disp,
                            "is_hierarchy_upgrade": is_upgrade,
                            "status": "NEW_PHASE",
                            "message": f"Nowa faza projektowa {inc_ph} dla etapu '{inc_st or leading_db.stage_name}' (dotychczas w bazie: {leading_db.phase_name})."
                        })
                else:
                    reimport_analysis["new_phases_detected"].append({
                        "phase_key": p_key,
                        "stage_name": inc_st,
                        "new_phase": inc_ph,
                        "existing_phase": None,
                        "display_name": inc_disp,
                        "is_hierarchy_upgrade": True,
                        "status": "NEW_STAGE",
                        "message": f"Nowy etap '{inc_st}' ({inc_ph}) dla inwestycji '{matched_proj.name}'."
                    })

            total_inc = len(phases_data)
            if len(reimport_analysis["duplicate_phases"]) == total_inc and total_inc > 0:
                reimport_analysis["is_exact_file_duplicate"] = True
                reimport_analysis["summary_message"] = f"Wykryto powtórzony plik! Wszystkie etapy inwestycji '{matched_proj.name}' ({total_inc}) znajdują się już w bazie danych z identycznymi wskaźnikami."
            elif len(reimport_analysis["new_phases_detected"]) > 0:
                reimport_analysis["has_new_phases"] = True
                new_str = ", ".join(f"{x['stage_name']} [{x['new_phase']}]" for x in reimport_analysis["new_phases_detected"])
                reimport_analysis["summary_message"] = f"Wykryto nowe fazy projektowe / etapy: {new_str} dla inwestycji '{matched_proj.name}'."
            elif len(reimport_analysis["duplicate_phases"]) + len(reimport_analysis["updated_phases"]) == total_inc:
                reimport_analysis["all_phases_already_imported"] = True
                reimport_analysis["summary_message"] = f"Wszystkie etapy dla '{matched_proj.name}' były już wcześniej zaimportowane (część zawiera zmodyfikowane wskaźniki)."

    combined_phases_for_audit.update(phases_data)
    auditor = KPIAuditor()
    cross_phase_audit = [
        res.__dict__ for res in auditor.audit_cross_phases(combined_phases_for_audit)
    ]

    # Podpowiedź fazy projektowej (APK, WPK, PB, PW)
    suggested_phase = "PB"
    if matched_proj:
        known_phase_names = [ph.phase_name.upper() for ph in matched_proj.phases]
        if "APK" in known_phase_names and "WPK" not in known_phase_names:
            suggested_phase = "WPK"
        elif ("WPK" in known_phase_names or "APK" in known_phase_names) and not any(p in known_phase_names for p in ["PB", "PROJEKT BUDOWLANY"]):
            suggested_phase = "PB"
        elif any(p in known_phase_names for p in ["PB", "PROJEKT BUDOWLANY"]) and not any(p in known_phase_names for p in ["PW", "PROJEKT WYKONAWCZY"]):
            suggested_phase = "PW"

    # Podpowiedź etapu inwestycji (np. Etap 1, Etap 2, Teren 10, Całość)
    suggested_stage = "Całość"
    if matched_proj:
        existing_stage_nums = []
        for ph in matched_proj.phases:
            m = re.search(r"\d+", ph.stage_name)
            if m:
                existing_stage_nums.append(int(m.group(0)))
        if existing_stage_nums:
            suggested_stage = f"Etap {max(existing_stage_nums) + 1}"
        elif matched_proj.phases:
            suggested_stage = f"Etap {len(matched_proj.phases) + 1}"

    if phases_data:
        first_phase_data = list(phases_data.values())[0]
        detected_st = first_phase_data.get("stage_name")
        detected_ph = first_phase_data.get("phase_name")
        if detected_st and not detected_st.startswith("Faza ") and detected_st.upper() not in ["APK", "WPK", "PB", "PW"]:
            suggested_stage = detected_st
        if detected_ph and detected_ph.upper() in ["APK", "WPK", "PB", "PW", "KONCEPCJA", "BAZOWY PPP"]:
            suggested_phase = detected_ph

    return {
        "matched_project_name": matched_proj.name if matched_proj else None,
        "city": matched_proj.city if matched_proj else "",
        "district": matched_proj.district if matched_proj else "",
        "developer": matched_proj.developer if matched_proj else "",
        "notes": matched_proj.notes if matched_proj else "",
        "existing_project_found": matched_proj is not None,
        "existing_phases": [ph.phase_name for ph in matched_proj.phases] if matched_proj else [],
        "existing_phases_summary": existing_phases_summary,
        "suggested_stage_name": suggested_stage,
        "suggested_phase_name": suggested_phase,
        "field_suggestions": field_suggestions,
        "benchmarks": benchmarks,
        "cross_phase_audit": cross_phase_audit,
        "reimport_analysis": reimport_analysis
    }



WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def _process_kpi_file(parser: KPIParser, filename: str, db: Session) -> dict:
    """Wspólna logika parsowania arkusza KPI, wykrywania etapów i audytu."""
    multistage_stages = parser.detect_multistage()
    is_multistage = len(multistage_stages) >= 2

    if is_multistage:
        active_stages = [s for s in multistage_stages if s.get("selected")]
        if not active_stages:
            active_stages = [s for s in multistage_stages if not s.get("is_summary") and not s.get("is_excluded")]
        phases_data = parser.parse(selected_stages=active_stages if active_stages else multistage_stages)
    else:
        phases_data = parser.parse()

    auditor = KPIAuditor()
    audit_by_phase = {}
    for phase_name, data in phases_data.items():
        audit_by_phase[phase_name] = [
            res.__dict__ for res in auditor.audit_phase(data, phase_name)
        ]

    # Podpowiedź nazwy projektu na podstawie nazwy pliku
    base_name = Path(filename).stem
    suggested_name = base_name.replace("Tabela parametrów i wskaźników inwestycji", "").strip(" -_") or base_name

    audit_ctx = build_project_audit_context(suggested_name, phases_data, db)
    all_stages = sorted(list({ph.phase_name for ph in db.query(ProjectPhase).all()} | {"APK", "WPK", "Projekt Budowlany", "PW", "Koncepcja"}))

    # Oznaczenie etapów w multistage jeśli to powtórzony plik lub nowe fazy
    reimport_info = audit_ctx.get("reimport_analysis", {})
    if reimport_info.get("is_existing_project") and multistage_stages:
        dup_st_keys = {clean_text(d["stage_name"]): d for d in reimport_info.get("duplicate_phases", [])}
        new_st_keys = {clean_text(n["stage_name"]): n for n in reimport_info.get("new_phases_detected", [])}
        for s in multistage_stages:
            st_clean = clean_text(s.get("stage_name", ""))
            if st_clean in dup_st_keys:
                s["is_duplicate"] = True
                s["reimport_status"] = "EXACT_DUPLICATE"
                s["selected"] = False
            elif st_clean in new_st_keys:
                s["is_new_phase"] = True
                s["reimport_status"] = "NEW_PHASE"
                s["selected"] = True

    # Przygotowanie czytelnego podsumowania wykrytych etapów i faz
    detected_phases_summary = []
    for s in multistage_stages:
        detected_phases_summary.append({
            "stage_name": s.get("stage_name"),
            "phase_name": s.get("phase_name"),
            "display_name": s.get("display_name"),
            "pum": s.get("pum_preview"),
            "lokale": s.get("lokale_preview"),
            "dzialka": s.get("dzialka_preview"),
            "plot_type": s.get("plot_type"),
            "has_data": s.get("has_data", False),
            "selected": s.get("selected", False),
            "is_leading": s.get("is_leading", False)
        })

    # Inteligentna podpowiedź nazwy etapu z wykrytych pozycji
    unique_stages = list(dict.fromkeys(s["stage_name"] for s in multistage_stages if s.get("stage_name") and not s.get("is_summary")))
    suggested_stage = audit_ctx["suggested_stage_name"]
    if unique_stages:
        if len(unique_stages) == 1:
            suggested_stage = unique_stages[0]
        else:
            suggested_stage = f"Wieloetapowy ({len(unique_stages)} etapów)"

    # Podpowiedź wiodącej fazy projektowej (APK < WPK < PB < PW)
    leading_phases = [s["phase_name"] for s in multistage_stages if s.get("is_leading")]
    suggested_phase = leading_phases[0] if leading_phases else audit_ctx.get("suggested_phase_name", "PB")

    return {
        "filename": filename,
        "is_multistage": is_multistage,
        "detected_stages": multistage_stages,
        "detected_phases_summary": detected_phases_summary,
        "suggested_project_name": audit_ctx["matched_project_name"] or suggested_name,
        "suggested_stage_name": suggested_stage,
        "suggested_phase_name": suggested_phase,
        "suggested_city": audit_ctx["city"],
        "suggested_district": audit_ctx["district"],
        "suggested_developer": audit_ctx["developer"],
        "suggested_notes": audit_ctx["notes"],
        "existing_project_found": audit_ctx["existing_project_found"],
        "existing_phases": audit_ctx["existing_phases"],
        "existing_phases_summary": audit_ctx["existing_phases_summary"],
        "reimport_analysis": reimport_info,
        "field_suggestions": audit_ctx["field_suggestions"],
        "benchmarks": audit_ctx["benchmarks"],
        "all_known_stages": all_stages,
        "phases_data": phases_data,
        "audit_by_phase": audit_by_phase,
        "cross_phase_audit": audit_ctx["cross_phase_audit"]
    }


@app.post("/api/parse-staging")
async def parse_staging(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Wczytuje przesłany plik Excel do strefy buforowej (Staging Area) i wykonuje audyt z podpowiedziami z bazy."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".xlsx", ".xls", ".ods"]:
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku. Wymagany .xlsx, .xls lub .ods.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parser = KPIParser(tmp_path)
        result = _process_kpi_file(parser, file.filename, db)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd parsowania arkusza: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.get("/api/scan-directory")
async def scan_directory(directory: str = Query("KPI - WSKAZNIKI")):
    """Skanuje katalog w obrębie workspace w poszukiwaniu plików .xlsx, .xls, .ods."""
    clean_dir = directory.strip().replace("\\", "/")
    target_path = (WORKSPACE_ROOT / clean_dir).resolve()

    # Strażnik izolacji: tylko katalogi wewnątrz workspace
    try:
        target_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ścieżka musi znajdować się wewnątrz katalogu projektu.")

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Katalog '{clean_dir}' nie istnieje.")

    valid_extensions = {".xlsx", ".xls", ".ods"}
    found_files = []

    for file_path in target_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
            # Pomijanie plików tymczasowych Excela (~$)
            if file_path.name.startswith("~$"):
                continue
            rel_path = file_path.relative_to(WORKSPACE_ROOT).as_posix()
            parent_dir = file_path.parent.relative_to(WORKSPACE_ROOT).as_posix()
            found_files.append({
                "path": rel_path,
                "directory": parent_dir,
                "filename": file_path.name,
                "size": file_path.stat().st_size
            })

    # Sortowanie alfabetyczne po nazwie pliku
    found_files.sort(key=lambda x: x["filename"].lower())

    return JSONResponse({
        "directory": clean_dir,
        "total_files": len(found_files),
        "files": found_files
    })


@app.post("/api/parse-server-file")
async def parse_server_file(payload: dict, db: Session = Depends(get_db)):
    """Parsuje plik znajdujący się na dysku serwera wewnątrz repozytorium."""
    filepath = payload.get("filepath", "").strip().replace("\\", "/")
    if not filepath:
        raise HTTPException(status_code=400, detail="Parametr 'filepath' jest wymagany.")

    target_path = (WORKSPACE_ROOT / filepath).resolve()

    # Strażnik izolacji: tylko pliki wewnątrz workspace
    try:
        target_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ścieżka pliku musi znajdować się wewnątrz katalogu projektu.")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail=f"Plik '{filepath}' nie został znaleziony.")

    suffix = target_path.suffix.lower()
    if suffix not in [".xlsx", ".xls", ".ods"]:
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku.")

    try:
        parser = KPIParser(str(target_path))
        result = _process_kpi_file(parser, target_path.name, db)
        result["directory"] = Path(filepath).parent.as_posix()
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd parsowania arkusza '{target_path.name}': {str(e)}")


@app.post("/api/project-audit-context")
async def api_project_audit_context(payload: dict, db: Session = Depends(get_db)):
    """Automatyczne podpowiedzi i audyt międzyfazowy na podstawie wybranej nazwy inwestycji i bazy danych."""
    project_name = payload.get("project_name", "")
    phases_data = payload.get("phases_data", {})
    context = build_project_audit_context(project_name, phases_data, db)
    return JSONResponse(context)


@app.get("/api/suggestions")
async def get_suggestions(db: Session = Depends(get_db)):
    """Zwraca podpowiedzi istniejących inwestycji, etapów, faz projektowych, miast, dzielnic i deweloperów z bazy."""
    projects = db.query(InvestmentProject).all()
    phases = db.query(ProjectPhase.phase_name).distinct().all()
    all_phases = sorted(list({p[0] for p in phases if p[0]} | {"APK", "WPK", "PB", "PW", "Koncepcja", "Projekt Budowlany", "Projekt Wykonawczy"}))
    stages = db.query(ProjectPhase._stage_name).distinct().all()
    all_stages = sorted(list({s[0] for s in stages if s[0]} | set(all_phases) | {"Etap 1", "Etap 2", "Etap 3", "Całość"}))
    return JSONResponse({
        "projects": [
            {
                "name": p.name,
                "city": p.city or "",
                "district": p.district or "",
                "developer": p.developer or "",
                "notes": p.notes or "",
                "powierzchnia_dzialki": p.powierzchnia_dzialki,
                "phases": [ph.phase_name for ph in p.phases],
                "stages": [ph.stage_name for ph in p.phases]
            }
            for p in projects
        ],
        "stages": all_stages,
        "phases": all_phases,
        "cities": sorted(list({p.city for p in projects if p.city})),
        "districts": sorted(list({p.district for p in projects if p.district})),
        "developers": sorted(list({p.developer for p in projects if p.developer}))
    })


@app.post("/api/save-project")
async def save_project(payload: dict, db: Session = Depends(get_db)):
    """Zapisuje dane ze strefy buforowej do trwałej bazy SQLite."""
    project_name = payload.get("project_name", "").strip()
    if not project_name:
        raise HTTPException(status_code=400, detail="Nazwa projektu jest wymagana.")

    stage_name = payload.get("stage_name", "").strip()
    phase_name_input = payload.get("phase_name", "").strip()
    phases_data = payload.get("phases_data", {})
    if not phases_data:
        raise HTTPException(status_code=400, detail="Brak danych faz do zapisu.")

    # Jeśli podano etap (stage_name) lub fazę i mamy 1 fazę w phases_data, przypisz nazwę etapu i fazy
    if (stage_name or phase_name_input) and len(phases_data) == 1:
        first_key = list(phases_data.keys())[0]
        p_dict = phases_data[first_key]
        if stage_name:
            p_dict["stage_name"] = stage_name
        if phase_name_input:
            p_dict["phase_name"] = phase_name_input
        phases_data = {stage_name or first_key: p_dict}

    # Sprawdzenie czy projekt już istnieje
    existing = db.query(InvestmentProject).filter(InvestmentProject.name == project_name).first()
    if existing:
        project = existing
        project.city = payload.get("city", project.city)
        project.district = payload.get("district", project.district)
        project.developer = payload.get("developer", project.developer)
        project.notes = payload.get("notes", project.notes)
        if payload.get("powierzchnia_dzialki") is not None:
            project.powierzchnia_dzialki = payload.get("powierzchnia_dzialki")
    else:
        project = InvestmentProject(
            name=project_name,
            city=payload.get("city"),
            district=payload.get("district"),
            developer=payload.get("developer"),
            powierzchnia_dzialki=payload.get("powierzchnia_dzialki"),
            notes=payload.get("notes")
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    # Audytor do logowania
    auditor = KPIAuditor()
    source_filename = payload.get("source_filename", "manual_import.xlsx")

    # Zapis faz (obsługa formatu słownikowego lub listy wybranych etapów)
    items_to_save = []
    if isinstance(phases_data, list):
        for data in phases_data:
            ph_key = data.get("phase_name") or data.get("stage_name") or "Standard"
            items_to_save.append((ph_key, data))
    elif isinstance(phases_data, dict):
        items_to_save = list(phases_data.items())

    for phase_name, data in items_to_save:
        st_name = data.get("stage_name") or stage_name or "Całość"
        ph_name = data.get("phase_name") or phase_name_input or phase_name
        plot_type = data.get("plot_type")

        # Usunięcie starej fazy o tej samej nazwie jeśli istniała
        old_phase = db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project.id,
            ((ProjectPhase.phase_name == phase_name) | 
             ((ProjectPhase._stage_name == st_name) & (ProjectPhase.phase_name == ph_name)))
        ).first()
        if old_phase:
            db.delete(old_phase)
            db.commit()

        # Tworzenie obiektu KPI
        kpi_fields = {k: v for k, v in data.items() if hasattr(ProjectKPI, k) and k != "raw_parameters"}
        if not plot_type:
            plot_type = "wlasna" if (kpi_fields.get("powierzchnia_dzialki") and kpi_fields.get("powierzchnia_dzialki") > 0) else "czesc_dzialki"

        new_phase = ProjectPhase(
            project_id=project.id,
            stage_name=st_name,
            phase_name=ph_name if ph_name != st_name else phase_name,
            plot_type=plot_type,
            source_file=source_filename
        )
        db.add(new_phase)
        db.commit()
        db.refresh(new_phase)

        # Tworzenie obiektu KPI
        kpi_fields = {k: v for k, v in data.items() if hasattr(ProjectKPI, k) and k != "raw_parameters"}
        kpi = ProjectKPI(
            phase_id=new_phase.id,
            raw_parameters=data.get("raw_parameters", {}),
            **kpi_fields
        )
        db.add(kpi)

        # Logi audytu dla fazy
        audit_res = auditor.audit_phase(data, phase_name)
        for ar in audit_res:
            log = AuditLog(
                phase_id=new_phase.id,
                category=ar.category,
                rule_name=ar.rule_name,
                status=ar.status,
                message=ar.message,
                expected_value=ar.expected_value,
                actual_value=ar.actual_value
            )
            db.add(log)

        db.commit()

    return JSONResponse({"status": "OK", "project_id": project.id, "message": f"Projekt '{project.name}' pomyślnie zapisany w bazie."})


@app.get("/api/projects")
async def list_projects(db: Session = Depends(get_db)):
    """Lista projektów i ich wskaźników."""
    bi = BIEngine(db)
    return JSONResponse(bi.get_all_projects_summary())


@app.get("/api/stages")
async def list_stages(db: Session = Depends(get_db)):
    """Lista wszystkich etapów inwestycji jako podstawowych jednostek analitycznych."""
    bi = BIEngine(db)
    return JSONResponse(bi.get_all_stages())


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Usuwa projekt z bazy danych."""
    project = db.query(InvestmentProject).filter(InvestmentProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nie znaleziony.")
    db.delete(project)
    db.commit()
    return JSONResponse({"status": "OK", "message": f"Projekt '{project.name}' został usunięty."})


@app.delete("/api/stages/{stage_id}")
async def delete_stage(stage_id: int, db: Session = Depends(get_db)):
    """Usuwa pojedynczy etap z bazy danych."""
    phase = db.query(ProjectPhase).filter(ProjectPhase.id == stage_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Etap nie znaleziony.")
    project = phase.project
    stage_name = phase.display_name
    db.delete(phase)
    db.commit()
    if project and len(project.phases) == 0:
        db.delete(project)
        db.commit()
    return JSONResponse({"status": "OK", "message": f"Etap '{stage_name}' został usunięty."})


@app.post("/api/compare")
async def compare_phases(payload: dict, db: Session = Depends(get_db)):
    """Zwraca dane do wykresów porównawczych dla wybranych faz."""
    phase_ids = payload.get("phase_ids", [])
    if not phase_ids:
        raise HTTPException(status_code=400, detail="Wybierz co najmniej jedną fazę do porównania.")
    bi = BIEngine(db)
    return JSONResponse(bi.compare_projects(phase_ids))
