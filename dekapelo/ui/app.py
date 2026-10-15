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


@app.post("/api/parse-staging")
async def parse_staging(file: UploadFile = File(...)):
    """Wczytuje plik Excel do strefy buforowej (Staging Area) i wykonuje audyt."""
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

        cross_phase_audit = [
            res.__dict__ for res in auditor.audit_cross_phases(phases_data)
        ]

        # Podpowiedź nazwy projektu na podstawie nazwy pliku
        base_name = Path(file.filename).stem
        suggested_name = base_name.replace("Tabela parametrów i wskaźników inwestycji", "").strip(" -_") or base_name

        return JSONResponse({
            "filename": file.filename,
            "suggested_project_name": suggested_name,
            "phases_data": phases_data,
            "audit_by_phase": audit_by_phase,
            "cross_phase_audit": cross_phase_audit
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd parsowania arkusza: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.post("/api/save-project")
async def save_project(payload: dict, db: Session = Depends(get_db)):
    """Zapisuje dane ze strefy buforowej do trwałej bazy SQLite."""
    project_name = payload.get("project_name", "").strip()
    if not project_name:
        raise HTTPException(status_code=400, detail="Nazwa projektu jest wymagana.")

    phases_data = payload.get("phases_data", {})
    if not phases_data:
        raise HTTPException(status_code=400, detail="Brak danych faz do zapisu.")

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
