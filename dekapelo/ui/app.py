import os
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
from dekapelo.ingestion.kpi_parser import KPIParser
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

    if matched_proj:
        for ph in matched_proj.phases:
            k = ph.kpi
            existing_phases_summary.append({
                "phase_name": ph.phase_name,
                "pum": k.pum if k else None,
                "puu": k.puu if k else None,
                "pumiu": k.suma_pum_i_puu if k else None,
                "lokale": k.ilosc_lokali_mieszkalnych if k else None,
                "dzialka": k.powierzchnia_dzialki if k else None,
                "pcn": k.pow_calkowita_nadziemia if k else None
            })
            if k and ph.phase_name not in phases_data:
                combined_phases_for_audit[f"{ph.phase_name} (z bazy)"] = {
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
        known_dzialka = next((ph.kpi.powierzchnia_dzialki for ph in matched_proj.phases if ph.kpi and ph.kpi.powierzchnia_dzialki), None)
        if known_dzialka:
            for p_name, p_vals in phases_data.items():
                if not p_vals.get("powierzchnia_dzialki"):
                    field_suggestions.append({
                        "field": "powierzchnia_dzialki",
                        "phase": p_name,
                        "suggested_value": known_dzialka,
                        "label": f"Powierzchnia działki dla etapu {p_name} nieokreślona w pliku – w bazie wynosi {known_dzialka:.2f} m²"
                    })

    combined_phases_for_audit.update(phases_data)
    auditor = KPIAuditor()
    cross_phase_audit = [
        res.__dict__ for res in auditor.audit_cross_phases(combined_phases_for_audit)
    ]

    # Podpowiedź kolejnego etapu
    suggested_stage = "APK"
    if matched_proj:
        known_phase_names = [ph.phase_name.upper() for ph in matched_proj.phases]
        if "APK" in known_phase_names and "WPK" not in known_phase_names:
            suggested_stage = "WPK"
        elif ("WPK" in known_phase_names or "APK" in known_phase_names) and not any(p in known_phase_names for p in ["PB", "PROJEKT BUDOWLANY"]):
            suggested_stage = "Projekt Budowlany"
        elif any(p in known_phase_names for p in ["PB", "PROJEKT BUDOWLANY"]) and not any(p in known_phase_names for p in ["PW", "PROJEKT WYKONAWCZY"]):
            suggested_stage = "Projekt Wykonawczy"

    if phases_data:
        first_detected = list(phases_data.keys())[0]
        if not first_detected.startswith("Faza "):
            suggested_stage = first_detected

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
        "field_suggestions": field_suggestions,
        "benchmarks": benchmarks,
        "cross_phase_audit": cross_phase_audit
    }


@app.post("/api/parse-staging")
async def parse_staging(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Wczytuje plik Excel do strefy buforowej (Staging Area) i wykonuje audyt z podpowiedziami z bazy."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".xlsx", ".xls", ".ods"]:
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku. Wymagany .xlsx, .xls lub .ods.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parser = KPIParser(tmp_path)
        phases_data = parser.parse()

        auditor = KPIAuditor()
        audit_by_phase = {}
        for phase_name, data in phases_data.items():
            audit_by_phase[phase_name] = [
                res.__dict__ for res in auditor.audit_phase(data, phase_name)
            ]

        # Podpowiedź nazwy projektu na podstawie nazwy pliku
        base_name = Path(file.filename).stem
        suggested_name = base_name.replace("Tabela parametrów i wskaźników inwestycji", "").strip(" -_") or base_name

        audit_ctx = build_project_audit_context(suggested_name, phases_data, db)
        all_stages = sorted(list({ph.phase_name for ph in db.query(ProjectPhase).all()} | {"APK", "WPK", "Projekt Budowlany", "PW", "Koncepcja"}))

        return JSONResponse({
            "filename": file.filename,
            "suggested_project_name": audit_ctx["matched_project_name"] or suggested_name,
            "suggested_stage_name": audit_ctx["suggested_stage_name"],
            "suggested_city": audit_ctx["city"],
            "suggested_district": audit_ctx["district"],
            "suggested_developer": audit_ctx["developer"],
            "suggested_notes": audit_ctx["notes"],
            "existing_project_found": audit_ctx["existing_project_found"],
            "existing_phases": audit_ctx["existing_phases"],
            "existing_phases_summary": audit_ctx["existing_phases_summary"],
            "field_suggestions": audit_ctx["field_suggestions"],
            "benchmarks": audit_ctx["benchmarks"],
            "all_known_stages": all_stages,
            "phases_data": phases_data,
            "audit_by_phase": audit_by_phase,
            "cross_phase_audit": audit_ctx["cross_phase_audit"]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd parsowania arkusza: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.post("/api/project-audit-context")
async def api_project_audit_context(payload: dict, db: Session = Depends(get_db)):
    """Automatyczne podpowiedzi i audyt międzyfazowy na podstawie wybranej nazwy inwestycji i bazy danych."""
    project_name = payload.get("project_name", "")
    phases_data = payload.get("phases_data", {})
    context = build_project_audit_context(project_name, phases_data, db)
    return JSONResponse(context)


@app.get("/api/suggestions")
async def get_suggestions(db: Session = Depends(get_db)):
    """Zwraca podpowiedzi istniejących inwestycji, etapów, miast, dzielnic i deweloperów z bazy."""
    projects = db.query(InvestmentProject).all()
    stages = db.query(ProjectPhase.phase_name).distinct().all()
    all_stages = sorted(list({s[0] for s in stages if s[0]} | {"APK", "WPK", "Projekt Budowlany", "PW", "Koncepcja"}))
    return JSONResponse({
        "projects": [
            {
                "name": p.name,
                "city": p.city or "",
                "district": p.district or "",
                "developer": p.developer or "",
                "notes": p.notes or "",
                "phases": [ph.phase_name for ph in p.phases]
            }
            for p in projects
        ],
        "stages": all_stages,
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
    phases_data = payload.get("phases_data", {})
    if not phases_data:
        raise HTTPException(status_code=400, detail="Brak danych faz do zapisu.")

    # Jeśli podano etap (stage_name) i mamy 1 fazę w phases_data, przypisz nazwę etapu
    if stage_name and len(phases_data) == 1:
        first_key = list(phases_data.keys())[0]
        if first_key != stage_name:
            phases_data = {stage_name: phases_data[first_key]}

    # Sprawdzenie czy projekt już istnieje
    existing = db.query(InvestmentProject).filter(InvestmentProject.name == project_name).first()
    if existing:
        project = existing
        project.city = payload.get("city", project.city)
        project.district = payload.get("district", project.district)
        project.developer = payload.get("developer", project.developer)
        project.notes = payload.get("notes", project.notes)
    else:
        project = InvestmentProject(
            name=project_name,
            city=payload.get("city"),
            district=payload.get("district"),
            developer=payload.get("developer"),
            notes=payload.get("notes")
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    # Audytor do logowania
    auditor = KPIAuditor()
    source_filename = payload.get("source_filename", "manual_import.xlsx")

    # Zapis faz
    for phase_name, data in phases_data.items():
        # Usunięcie starej fazy o tej samej nazwie jeśli istniała
        old_phase = db.query(ProjectPhase).filter(
            ProjectPhase.project_id == project.id,
            ProjectPhase.phase_name == phase_name
        ).first()
        if old_phase:
            db.delete(old_phase)
            db.commit()

        new_phase = ProjectPhase(
            project_id=project.id,
            phase_name=phase_name,
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


@app.post("/api/compare")
async def compare_phases(payload: dict, db: Session = Depends(get_db)):
    """Zwraca dane do wykresów porównawczych dla wybranych faz."""
    phase_ids = payload.get("phase_ids", [])
    if not phase_ids:
        raise HTTPException(status_code=400, detail="Wybierz co najmniej jedną fazę do porównania.")
    bi = BIEngine(db)
    return JSONResponse(bi.compare_projects(phase_ids))
