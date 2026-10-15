from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AuditResult:
    category: str  # 'MATH', 'LOGIC', 'CROSS_PHASE'
    rule_name: str
    status: str    # 'PASS', 'WARNING', 'FAIL'
    message: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None


class KPIAuditor:
    """Silnik audytu matematycznego, logicznego i międzyfazowego wskaźników inwestycji."""

    def __init__(self, tolerance_surface: float = 0.5, tolerance_ratio: float = 0.05):
        self.tolerance_surface = tolerance_surface
        self.tolerance_ratio = tolerance_ratio

    def audit_phase(self, kpi_data: Dict[str, Any], phase_name: str = "") -> List[AuditResult]:
        """Przeprowadza pełny audyt pojedynczej fazy wskaźników."""
        results: List[AuditResult] = []
        
        # 1. Bilans Powierzchni Użytkowej (PUM + PUU == PUMiU)
        pumiu = kpi_data.get("suma_pum_i_puu")
        pum = kpi_data.get("pum")
        puu = kpi_data.get("puu") or 0.0

        if pumiu is not None and pum is not None:
            expected_pumiu = pum + puu
            diff = abs(pumiu - expected_pumiu)
            if diff <= self.tolerance_surface:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans PUM i PUU",
                    status="PASS",
                    message=f"PUM+PUU ({expected_pumiu:.2f} m²) jest zgodne z PUMiU ({pumiu:.2f} m²)",
                    expected_value=expected_pumiu,
                    actual_value=pumiu
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans PUM i PUU",
                    status="FAIL",
                    message=f"Rozbieżność sumy PUM+PUU: obliczono {expected_pumiu:.2f} m², w arkuszu podano {pumiu:.2f} m² (różnica {diff:.2f} m²)",
                    expected_value=expected_pumiu,
                    actual_value=pumiu
                ))

        # 2. Bilans Powierzchni Całkowitej (Pc == Pcn + Pcp)
        pc = kpi_data.get("powierzchnia_calkowita")
        pcn = kpi_data.get("pow_calkowita_nadziemia")
        pcnb = kpi_data.get("pow_calkowita_nadziemia_z_balkonami")
        pcb = kpi_data.get("pow_calkowita_z_balkonami")
        plb = kpi_data.get("pow_calkowita_balkonow_loggii")
        pcp = kpi_data.get("pow_calkowita_podziemia")

        if pc is not None and pcn is not None and pcp is not None:
            expected_pc = pcn + pcp
            diff = abs(pc - expected_pc)
            if diff <= self.tolerance_surface * 2:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans Powierzchni Całkowitej Pc = Pcn + Pcp",
                    status="PASS",
                    message=f"Suma nadziemia bez balkonów ({pcn:.2f} m²) i podziemia ({pcp:.2f} m²) zgodna z Pc ({pc:.2f} m²)",
                    expected_value=expected_pc,
                    actual_value=pc
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans Powierzchni Całkowitej Pc = Pcn + Pcp",
                    status="WARNING",
                    message=f"Niezgodność bilansu Pc: Pcn ({pcn:.2f}) + Pcp ({pcp:.2f}) = {expected_pc:.2f} m², a Pc = {pc:.2f} m² (różnica {diff:.2f} m²)",
                    expected_value=expected_pc,
                    actual_value=pc
                ))

        # 2b. Rozróżnienie i Bilans Nadziemia z Balkonami i Loggiami (Pcnb == Pcn + Plb)
        if pcn is not None and pcnb is not None:
            if plb is not None:
                expected_pcnb = pcn + plb
                diff_pcnb = abs(pcnb - expected_pcnb)
                if diff_pcnb <= self.tolerance_surface * 2:
                    results.append(AuditResult(
                        category="MATH",
                        rule_name="Bilans Nadziemia z Balkonami (Pcnb = Pcn + Plb)",
                        status="PASS",
                        message=f"Pcn ({pcn:.2f} m²) + balkony/loggie ({plb:.2f} m²) = {expected_pcnb:.2f} m² zgodne z Pcnb ({pcnb:.2f} m²)",
                        expected_value=expected_pcnb,
                        actual_value=pcnb
                    ))
                else:
                    results.append(AuditResult(
                        category="MATH",
                        rule_name="Bilans Nadziemia z Balkonami (Pcnb = Pcn + Plb)",
                        status="FAIL",
                        message=f"Rozbieżność bilansu Pcnb: Pcn ({pcn:.2f}) + Plb ({plb:.2f}) = {expected_pcnb:.2f} m², a w arkuszu Pcnb = {pcnb:.2f} m² (różnica {diff_pcnb:.2f} m²)",
                        expected_value=expected_pcnb,
                        actual_value=pcnb
                    ))

            if pcnb < pcn - self.tolerance_surface:
                results.append(AuditResult(
                    category="LOGIC",
                    rule_name="Relacja Pcnb do Pcn",
                    status="FAIL",
                    message=f"Błąd logiczny: Powierzchnia nadziemia z balkonami Pcnb ({pcnb:.2f} m²) jest mniejsza niż bez balkonów Pcn ({pcn:.2f} m²)",
                    expected_value=pcn,
                    actual_value=pcnb
                ))

        # 2c. Bilans Powierzchni Całkowitej z Balkonami (Pcb == Pc + Plb)
        if pc is not None and pcb is not None and plb is not None:
            expected_pcb = pc + plb
            diff_pcb = abs(pcb - expected_pcb)
            if diff_pcb <= self.tolerance_surface * 2:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans Całkowity z Balkonami (Pcb = Pc + Plb)",
                    status="PASS",
                    message=f"Pc ({pc:.2f} m²) + balkony/loggie ({plb:.2f} m²) = {expected_pcb:.2f} m² zgodne z Pcb ({pcb:.2f} m²)",
                    expected_value=expected_pcb,
                    actual_value=pcb
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Bilans Całkowity z Balkonami (Pcb = Pc + Plb)",
                    status="WARNING",
                    message=f"Rozbieżność Pcb: Pc ({pc:.2f}) + Plb ({plb:.2f}) = {expected_pcb:.2f} m², w arkuszu Pcb = {pcb:.2f} m² (różnica {diff_pcb:.2f} m²)",
                    expected_value=expected_pcb,
                    actual_value=pcb
                ))

        # 3. Średnia Powierzchnia Mieszkania (śrm == PUM / im)
        srm = kpi_data.get("srednia_wielkosc_mieszkania")
        im = kpi_data.get("ilosc_lokali_mieszkalnych")
        if srm is not None and pum is not None and im and im > 0:
            calc_srm = pum / im
            diff = abs(srm - calc_srm)
            if diff <= 0.1:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Średnia Powierzchnia Mieszkania",
                    status="PASS",
                    message=f"Średnia powierzchnia {srm:.2f} m² zgodna z PUM/im ({calc_srm:.2f} m²)",
                    expected_value=calc_srm,
                    actual_value=srm
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Średnia Powierzchnia Mieszkania",
                    status="WARNING",
                    message=f"Rozbieżność średniej pow. mieszkania: podano {srm:.2f} m², z przeliczenia PUM/im wynika {calc_srm:.2f} m²",
                    expected_value=calc_srm,
                    actual_value=srm
                ))

        # 4. Wskaźnik Miejsc Parkingowych (MP / lokal)
        wsk_mp = kpi_data.get("wskaznik_mp")
        suma_mp = kpi_data.get("suma_miejsc_parkingowych")
        if wsk_mp is not None and suma_mp is not None and im and im > 0:
            calc_wsk_mp = suma_mp / im
            diff = abs(wsk_mp - calc_wsk_mp)
            if diff <= self.tolerance_ratio:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Miejsc Parkingowych na Lokal",
                    status="PASS",
                    message=f"Wskaźnik MP {wsk_mp:.2f} zgodny z przeliczeniem ({calc_wsk_mp:.2f})",
                    expected_value=calc_wsk_mp,
                    actual_value=wsk_mp
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Miejsc Parkingowych na Lokal",
                    status="WARNING",
                    message=f"Wskaźnik MP podano {wsk_mp:.2f}, z ilorazu MP/im wynika {calc_wsk_mp:.2f}",
                    expected_value=calc_wsk_mp,
                    actual_value=wsk_mp
                ))

        # 5. Wykrywanie danych obliczonych sztywnymi wskaźnikami (np. PUM wynikający z PCn w stosunku równym np 0.700000000000000 lub 0.720000000000000)
        # 'Spełnienie Wymogu Miejsc Parkingowych' nie jest walidacją matematyczną tylko merytoryczną i nie powinno być brane pod uwagę przy audycie.
        candidates_to_check = []
        if pcn and pcn > 0:
            if pum is not None and pum > 0:
                candidates_to_check.append(("PUM", pum, pum / pcn))
            if pumiu is not None and pumiu > 0 and (pum is None or abs(pumiu - pum) > self.tolerance_surface):
                candidates_to_check.append(("PUMiU", pumiu, pumiu / pcn))

        rigid_targets = [0.70, 0.72, 0.68, 0.75, 0.80, 0.65]
        best_match = None
        for label, val, ratio in candidates_to_check:
            for rt in rigid_targets:
                if abs(ratio - rt) < 1e-4 or abs(val - round(pcn * rt, 2)) < 0.05:
                    best_match = (label, val, ratio, rt)
                    break
            if best_match and best_match[3] in (0.70, 0.72):
                break

        if not best_match:
            for label, val, ratio in candidates_to_check:
                if 0.65 <= ratio <= 0.85 and abs(ratio - round(ratio, 2)) < 1e-5:
                    best_match = (label, val, ratio, round(ratio, 2))
                    break

        detected_rigid = False
        if best_match:
            label, val, ratio, matched_rt = best_match
            detected_rigid = True
            results.append(AuditResult(
                category="LOGIC",
                rule_name="Wykrycie Sztywnego Wskaźnika PUM/PCn",
                status="WARNING",
                message=f"Wykryto dane obliczone sztywnym wskaźnikiem: {label}/PCn = {ratio:.6f} (~{matched_rt:.2f}). {label} ({val:.2f} m²) wynika bezpośrednio z PCn ({pcn:.2f} m²) za pomocą sztywnego przelicznika, co sugeruje szacunek zamiast rzeczywistego bilansu.",
                expected_value=None,
                actual_value=round(ratio, 4)
            ))

        if not detected_rigid:
            wsk_raw = kpi_data.get("wskaznik_pumiu_pcn")
            if wsk_raw is not None and 0.50 <= wsk_raw <= 0.90:
                for rt in [0.70, 0.72]:
                    if abs(wsk_raw - rt) < 1e-4:
                        results.append(AuditResult(
                            category="LOGIC",
                            rule_name="Wykrycie Sztywnego Wskaźnika PUM/PCn",
                            status="WARNING",
                            message=f"Wykryto sztywny wskaźnik sprawności nadziemia w arkuszu: {wsk_raw:.6f} (~{rt:.2f}), co wskazuje na przyjęcie wartości szacunkowej zamiast rzeczywistego bilansu.",
                            expected_value=None,
                            actual_value=round(wsk_raw, 4)
                        ))
                        break

        # 6. Wskaźnik Sprawności Nadziemia bez balkonów (PUMiU / Pcn)
        wsk_pcn = kpi_data.get("wskaznik_pumiu_pcn")
        uzytkowa = pumiu if pumiu is not None else pum
        if wsk_pcn is not None and uzytkowa is not None and pcn and pcn > 0:
            calc_wsk_pcn = uzytkowa / pcn
            diff = abs(wsk_pcn - calc_wsk_pcn)
            if diff <= self.tolerance_ratio:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Sprawności Nadziemia bez balkonów (PUMiU / Pcn)",
                    status="PASS",
                    message=f"Wskaźnik sprawności nadziemia bez balkonów {wsk_pcn:.3f} zgodny z formułą ({calc_wsk_pcn:.3f})",
                    expected_value=calc_wsk_pcn,
                    actual_value=wsk_pcn
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Sprawności Nadziemia bez balkonów (PUMiU / Pcn)",
                    status="WARNING",
                    message=f"Wskaźnik sprawności nadziemia bez balkonów podano {wsk_pcn:.3f}, z obliczeń PUMiU/Pcn wynika {calc_wsk_pcn:.3f}",
                    expected_value=calc_wsk_pcn,
                    actual_value=wsk_pcn
                ))

        # 6b. Wskaźnik Sprawności Nadziemia z balkonami (PUMiU / Pcnb)
        wsk_pcnb = kpi_data.get("wskaznik_pumiu_pcnb")
        if wsk_pcnb is not None and uzytkowa is not None and pcnb and pcnb > 0:
            calc_wsk_pcnb = uzytkowa / pcnb
            diff_wsk_pcnb = abs(wsk_pcnb - calc_wsk_pcnb)
            if diff_wsk_pcnb <= self.tolerance_ratio:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Sprawności Nadziemia z balkonami (PUMiU / Pcnb)",
                    status="PASS",
                    message=f"Wskaźnik sprawności nadziemia z balkonami {wsk_pcnb:.3f} zgodny z formułą ({calc_wsk_pcnb:.3f})",
                    expected_value=calc_wsk_pcnb,
                    actual_value=wsk_pcnb
                ))
            else:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Sprawności Nadziemia z balkonami (PUMiU / Pcnb)",
                    status="WARNING",
                    message=f"Wskaźnik sprawności nadziemia z balkonami podano {wsk_pcnb:.3f}, z obliczeń PUMiU/Pcnb wynika {calc_wsk_pcnb:.3f}",
                    expected_value=calc_wsk_pcnb,
                    actual_value=wsk_pcnb
                ))

        # 7. Wskaźnik Mieszkań na Windę (il.m. / iw)
        wsk_iw = kpi_data.get("wskaznik_ilm_iw")
        iw = kpi_data.get("ilosc_wind")
        if wsk_iw is not None and im is not None and iw and iw > 0:
            calc_wsk_iw = im / iw
            diff = abs(wsk_iw - calc_wsk_iw)
            if diff <= 0.5:
                results.append(AuditResult(
                    category="MATH",
                    rule_name="Wskaźnik Mieszkań na Windę (il.m. / iw)",
                    status="PASS",
                    message=f"Wskaźnik mieszkań na windę {wsk_iw:.1f} zgodny z przeliczeniem",
                    expected_value=calc_wsk_iw,
                    actual_value=wsk_iw
                ))

        return results

    def audit_cross_phases(self, phases_data: Dict[str, Dict[str, Any]]) -> List[AuditResult]:
        """Porównuje kolejne fazy inwestycji i wykrywa istotne odchylenia."""
        results: List[AuditResult] = []
        phase_names = list(phases_data.keys())
        if len(phase_names) < 2:
            return results

        # Porównanie par faz kolejno po sobie
        for i in range(len(phase_names) - 1):
            p1_name = phase_names[i]
            p2_name = phase_names[i + 1]
            d1 = phases_data[p1_name]
            d2 = phases_data[p2_name]

            # Porównanie PUM
            pum1 = d1.get("pum")
            pum2 = d2.get("pum")
            if pum1 and pum2 and pum1 > 0:
                delta_pum = pum2 - pum1
                pct_change = (delta_pum / pum1) * 100
                if abs(pct_change) > 3.0:
                    results.append(AuditResult(
                        category="CROSS_PHASE",
                        rule_name=f"Zmiana PUM: {p1_name} -> {p2_name}",
                        status="WARNING",
                        message=f"Istotna zmiana PUM między fazą {p1_name} ({pum1:.2f} m²) a {p2_name} ({pum2:.2f} m²): {delta_pum:+.2f} m² ({pct_change:+.2f}%)",
                        expected_value=pum1,
                        actual_value=pum2
                    ))
                else:
                    results.append(AuditResult(
                        category="CROSS_PHASE",
                        rule_name=f"Zmiana PUM: {p1_name} -> {p2_name}",
                        status="PASS",
                        message=f"PUM stabilny między fazą {p1_name} a {p2_name}: {delta_pum:+.2f} m² ({pct_change:+.2f}%)",
                        expected_value=pum1,
                        actual_value=pum2
                    ))

            # Porównanie liczby mieszkań
            im1 = d1.get("ilosc_lokali_mieszkalnych")
            im2 = d2.get("ilosc_lokali_mieszkalnych")
            if im1 and im2 and im1 != im2:
                results.append(AuditResult(
                    category="CROSS_PHASE",
                    rule_name=f"Zmiana Liczby Mieszkań: {p1_name} -> {p2_name}",
                    status="WARNING",
                    message=f"Liczba mieszkań uległa zmianie z {im1} ({p1_name}) na {im2} ({p2_name})",
                    expected_value=float(im1),
                    actual_value=float(im2)
                ))

        return results
