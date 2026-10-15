from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dekapelo.database.models import InvestmentProject, ProjectPhase, ProjectKPI


class BIEngine:
    """Silnik analityczny i benchmarkingowy projektów deweloperskich."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_all_projects_summary(self) -> List[Dict[str, Any]]:
        """Zwraca podsumowanie wszystkich projektów wraz z ich najnowszą/główną fazą."""
        projects = self.db.query(InvestmentProject).all()
        summaries = []

        for p in projects:
            phases_data = []
            for ph in p.phases:
                k = ph.kpi
                phases_data.append({
                    "phase_id": ph.id,
                    "phase_name": ph.phase_name,
                    "source_file": ph.source_file,
                    "pum": k.pum if k else None,
                    "puu": k.puu if k else None,
                    "pumiu": k.suma_pum_i_puu if k else None,
                    "lokale": k.ilosc_lokali_mieszkalnych if k else None,
                    "srm": k.srednia_wielkosc_mieszkania if k else None,
                    "dzialka": k.powierzchnia_dzialki if k else None,
                    "pc": k.powierzchnia_calkowita if k else None,
                    "pcn": k.pow_calkowita_nadziemia if k else None,
                    "pcp": k.pow_calkowita_podziemia if k else None,
                    "miejsca_parkingowe": k.suma_miejsc_parkingowych if k else None,
                    "wskaznik_mp": k.wskaznik_mp if k else None,
                    "sprawnosc_nadziemia": k.wskaznik_pumiu_pcn if k else None,
                    "sprawnosc_calkowita": k.wskaznik_pumiu_pc if k else None,
                    "intensywnosc_dzialka": k.wskaznik_pumiu_pd if k else None,
                    "audit_warnings": len([a for a in ph.audit_logs if a.status == "WARNING"]),
                    "audit_fails": len([a for a in ph.audit_logs if a.status == "FAIL"])
                })

            summaries.append({
                "project_id": p.id,
                "project_name": p.name,
                "city": p.city,
                "district": p.district,
                "developer": p.developer,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
                "phases_count": len(p.phases),
                "phases": phases_data
            })

        return summaries

    def get_all_stages(self) -> List[Dict[str, Any]]:
        """Zwraca listę wszystkich etapów inwestycji jako podstawowych jednostek analitycznych."""
        stages = self.db.query(ProjectPhase).all()
        result = []
        for s in stages:
            k = s.kpi
            result.append({
                "stage_id": s.id,
                "stage_name": s.phase_name,
                "investment_name": s.investment_name,
                "full_name": f"{s.investment_name} ({s.phase_name})",
                "source_file": s.source_file,
                "city": s.project.city if s.project else None,
                "pum": k.pum if k else None,
                "puu": k.puu if k else None,
                "pumiu": k.suma_pum_i_puu if k else None,
                "lokale": k.ilosc_lokali_mieszkalnych if k else None,
                "srm": k.srednia_wielkosc_mieszkania if k else None,
                "dzialka": k.powierzchnia_dzialki if k else None,
                "pow_zabudowy": k.powierzchnia_zabudowy if k else None,
                "pc": k.powierzchnia_calkowita if k else None,
                "pcn": k.pow_calkowita_nadziemia if k else None,
                "pcp": k.pow_calkowita_podziemia if k else None,
                "miejsca_parkingowe": k.suma_miejsc_parkingowych if k else None,
                "wskaznik_mp": k.wskaznik_mp if k else None,
                "sprawnosc_nadziemia": k.wskaznik_pumiu_pcn if k else None,
                "sprawnosc_calkowita": k.wskaznik_pumiu_pc if k else None,
                "intensywnosc_dzialka": k.wskaznik_pumiu_pd if k else None,
                "chlonnosc": (
                    round(k.suma_pum_i_puu / k.powierzchnia_dzialki, 3)
                    if (k and k.powierzchnia_dzialki and k.suma_pum_i_puu and k.powierzchnia_dzialki > 0)
                    else (round(k.wskaznik_pumiu_pd, 3) if (k and k.wskaznik_pumiu_pd is not None) else None)
                ),
                "audit_warnings": len([a for a in s.audit_logs if a.status == "WARNING"]),
                "audit_fails": len([a for a in s.audit_logs if a.status == "FAIL"])
            })
        return result

    def compare_projects(self, phase_ids: List[int]) -> Dict[str, Any]:
        """Porównanie wybranych faz projektów w formie macierzy wskaźników do wykresów i tabel."""
        phases = self.db.query(ProjectPhase).filter(ProjectPhase.id.in_(phase_ids)).all()
        
        comparison = {
            "labels": [],
            "metrics": {
                "PUM (m²)": [],
                "Liczba Mieszkań": [],
                "Śr. Wielkość Mieszkania (m²)": [],
                "Wskaźnik MP": [],
                "Sprawność Nadziemia (PUMiU/Pcn)": [],
                "Sprawność Całkowita (PUMiU/Pc)": [],
                "Intensywność (PUMiU/Pd)": [],
                "Chłonność (PUMiU/Pd)": [],
                "Powierzchnia Działki (m²)": [],
                "Mieszkań na Windę": []
            },
            "chlonnosc_scatter": [],
            "scatter_chlonnosc": [],
            "detailed_rows": []
        }

        for ph in phases:
            label = f"{ph.project.name} ({ph.phase_name})"
            comparison["labels"].append(label)
            k = ph.kpi
            if not k:
                continue

            pd = k.powierzchnia_dzialki
            pumiu = k.suma_pum_i_puu if k.suma_pum_i_puu is not None else (((k.pum or 0.0) + (k.puu or 0.0)) if (k.pum is not None or k.puu is not None) else None)
            if pd and pd > 0 and pumiu and pumiu > 0:
                chlonnosc = pumiu / pd
            elif k.wskaznik_pumiu_pd is not None:
                chlonnosc = k.wskaznik_pumiu_pd
            else:
                chlonnosc = None

            comparison["metrics"]["PUM (m²)"].append(k.pum or 0.0)
            comparison["metrics"]["Liczba Mieszkań"].append(k.ilosc_lokali_mieszkalnych or 0)
            comparison["metrics"]["Śr. Wielkość Mieszkania (m²)"].append(k.srednia_wielkosc_mieszkania or 0.0)
            comparison["metrics"]["Wskaźnik MP"].append(k.wskaznik_mp or 0.0)
            comparison["metrics"]["Sprawność Nadziemia (PUMiU/Pcn)"].append(k.wskaznik_pumiu_pcn or 0.0)
            comparison["metrics"]["Sprawność Całkowita (PUMiU/Pc)"].append(k.wskaznik_pumiu_pc or 0.0)
            comparison["metrics"]["Intensywność (PUMiU/Pd)"].append(k.wskaznik_pumiu_pd or (chlonnosc or 0.0))
            comparison["metrics"]["Chłonność (PUMiU/Pd)"].append(round(chlonnosc, 3) if chlonnosc is not None else 0.0)
            comparison["metrics"]["Powierzchnia Działki (m²)"].append(pd or 0.0)
            comparison["metrics"]["Mieszkań na Windę"].append(k.wskaznik_ilm_iw or 0.0)

            if pd is not None and pd > 0 and chlonnosc is not None:
                point = {
                    "x": round(pd, 2),
                    "y": round(chlonnosc, 3),
                    "label": label,
                    "project": ph.project.name,
                    "phase": ph.phase_name,
                    "pumiu": round(pumiu, 2),
                    "dzialka": round(pd, 2),
                    "chlonnosc": round(chlonnosc, 3)
                }
                comparison["chlonnosc_scatter"].append(point)
                comparison["scatter_chlonnosc"].append(point)

            comparison["detailed_rows"].append({
                "label": label,
                "project": ph.project.name,
                "phase": ph.phase_name,
                "pum": k.pum,
                "puu": k.puu,
                "pumiu": pumiu,
                "dzialka": pd,
                "chlonnosc": round(chlonnosc, 3) if chlonnosc is not None else None,
                "lokale": k.ilosc_lokali_mieszkalnych,
                "srm": k.srednia_wielkosc_mieszkania,
                "mp": k.suma_miejsc_parkingowych,
                "wsk_mp": k.wskaznik_mp,
                "pcn": k.pow_calkowita_nadziemia,
                "pc": k.powierzchnia_calkowita,
                "elewacja": k.powierzchnia_elewacji,
                "sprawnosc_nadziemia": k.wskaznik_pumiu_pcn,
                "sprawnosc_calkowita": k.wskaznik_pumiu_pc
            })

        return comparison
