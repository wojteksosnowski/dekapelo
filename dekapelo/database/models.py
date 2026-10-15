from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from dekapelo.database.connection import Base


def utc_now():
    return datetime.now(timezone.utc)


class InvestmentProject(Base):
    """Główna encja projektu / inwestycji deweloperskiej."""
    __tablename__ = "investment_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    developer = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    phases = relationship("ProjectPhase", back_populates="project", cascade="all, delete-orphan")


class ProjectPhase(Base):
    """Etap projektowy danej inwestycji (np. Koncepcja, APK, WPK, Projekt Budowlany, PW).
    Podstawowa jednostka pomiarowa i analityczna w systemie.
    """
    __tablename__ = "project_phases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("investment_projects.id"), nullable=False)
    phase_name = Column(String(100), nullable=False)  # np. 'APK', 'WPK', 'PB', 'PW', 'Koncepcja', 'Bazowy'
    source_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("InvestmentProject", back_populates="phases")
    kpi = relationship("ProjectKPI", back_populates="phase", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="phase", cascade="all, delete-orphan")

    @property
    def investment_name(self) -> str:
        """Jednolita nazwa inwestycji, do której należy ten etap."""
        return self.project.name if self.project else ""

    @property
    def stage_name(self) -> str:
        """Nazwa etapu projektowego (np. APK, WPK, PB)."""
        return self.phase_name


# Aliasy domenowe: Podstawową jednostką badaną jest 'Etap' (InvestmentStage)
InvestmentStage = ProjectPhase


class ProjectKPI(Base):
    """Zestawienie parametrów i wskaźników inwestycji zgodne ze specyfikacją arkuszy."""
    __tablename__ = "project_kpi"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("project_phases.id"), unique=True, nullable=False)

    # 1. Parametry Działki i Zagospodarowania
    powierzchnia_dzialki = Column(Float, nullable=True)  # im / Pd / Pt
    powierzchnia_zabudowy = Column(Float, nullable=True)  # Pz
    wspolczynnik_powierzchni_zabudowy = Column(Float, nullable=True)  # Pz / Pd
    powierzchnia_utwardzona = Column(Float, nullable=True)  # całkowita utwardzona
    pow_parter_budynku = Column(Float, nullable=True)
    pow_obiekty_infrastruktury = Column(Float, nullable=True)
    pow_chodnikow = Column(Float, nullable=True)
    pow_drog = Column(Float, nullable=True)
    pow_zjazdow_garaz = Column(Float, nullable=True)
    pow_ciagow_pieszo_jezdnych = Column(Float, nullable=True)
    pow_nawierzchni_zwirowej = Column(Float, nullable=True)
    pow_sciezek_kamiennych = Column(Float, nullable=True)
    pow_bezpieczna_plac_zabaw = Column(Float, nullable=True)
    pow_murow_oporowych = Column(Float, nullable=True)
    pow_deskowan = Column(Float, nullable=True)
    
    # Powierzchnia biologicznie czynna
    powierzchnia_biologicznie_czynna = Column(Float, nullable=True)  # Pbc
    pow_bio_ogrody_deszczowe_100 = Column(Float, nullable=True)
    pow_bio_grunt_100 = Column(Float, nullable=True)
    pow_bio_50 = Column(Float, nullable=True)
    pow_bio_plyta_garazu_50 = Column(Float, nullable=True)
    pow_bio_plyta_garazu_25 = Column(Float, nullable=True)
    dachy_tarasy_zielone_50 = Column(Float, nullable=True)
    wskaznik_pow_biologicznie_czynnej = Column(Float, nullable=True)  # Pbc / Pd

    # 2. Powierzchnie Użytkowe i Mieszkaniowe
    suma_pum_i_puu = Column(Float, nullable=True)  # PUM + PUU
    suma_lokali = Column(Integer, nullable=True)
    ilosc_lokali_mieszkalnych = Column(Integer, nullable=True)  # im
    pum = Column(Float, nullable=True)  # Powierzchnia użytkowa mieszkań
    srednia_wielkosc_mieszkania = Column(Float, nullable=True)  # śrm
    ilosc_lokali_uslugowych = Column(Integer, nullable=True)  # iu
    puu = Column(Float, nullable=True)  # Powierzchnia usługowa
    
    powierzchnia_czesci_wspolnych = Column(Float, nullable=True)  # imp (z klatkami, windami, fitnessem)
    powierzchnia_czesci_wspolnych_bez_klatek = Column(Float, nullable=True)
    powierzchnia_komunikacji_pionowej = Column(Float, nullable=True)
    powierzchnia_komunikacji_poziomej = Column(Float, nullable=True)

    # 3. Miejsca Parkingowe i Komórki
    suma_miejsc_parkingowych = Column(Integer, nullable=True)
    wskaznik_mp = Column(Float, nullable=True)  # MP / lokal
    wymagana_ilosc_mp = Column(Integer, nullable=True)
    mp_zewnetrzne_sprzedaz = Column(Integer, nullable=True)
    mp_zewnetrzne_wszystkie = Column(Integer, nullable=True)
    mp_garaz_wszystkie = Column(Integer, nullable=True)
    mp_rodzinne_zalezne = Column(Integer, nullable=True)
    powierzchnia_mp_garaz = Column(Float, nullable=True)
    
    suma_komorek_i_boksow = Column(Integer, nullable=True)
    ilosc_miejsc_rowerowych_garaz = Column(Integer, nullable=True)
    ilosc_komorek_tradycyjnych = Column(Integer, nullable=True)
    ilosc_boksow_jednoslady = Column(Integer, nullable=True)
    ilosc_miejsc_rowerownie = Column(Integer, nullable=True)
    powierzchnia_komorek_boksow_garaz = Column(Float, nullable=True)
    
    pow_wspolna_hali_garazowej = Column(Float, nullable=True)
    pow_uzytkowa_hali_garazowej = Column(Float, nullable=True)
    pow_techniczna_hali_garazowej = Column(Float, nullable=True)
    ilosc_komorek_nadziemie = Column(Integer, nullable=True)

    # 4. Kubatura i Dane Techniczne
    ilosc_klatek_schodowych = Column(Integer, nullable=True)  # iks
    wysokosc_budynku = Column(Float, nullable=True)
    wysokosc_parteru_netto = Column(Float, nullable=True)
    wysokosc_kondygnacji_mieszkalnych_netto = Column(Float, nullable=True)
    ilosc_kondygnacji_nadziemnych = Column(Integer, nullable=True)
    ilosc_kondygnacji_podziemnych = Column(Integer, nullable=True)
    ilosc_wind = Column(Integer, nullable=True)  # iw
    
    powierzchnia_calkowita = Column(Float, nullable=True)  # Pc bez balkonów/loggii
    pow_calkowita_balkonow_loggii = Column(Float, nullable=True)
    pow_calkowita_tarasow = Column(Float, nullable=True)
    pow_calkowita_z_balkonami = Column(Float, nullable=True)
    pow_calkowita_nadziemia = Column(Float, nullable=True)  # Pcn bez balkonów
    pow_calkowita_nadziemia_z_balkonami = Column(Float, nullable=True)  # Pcnb
    pow_calkowita_podziemia = Column(Float, nullable=True)  # Pcp / Pcg
    powierzchnia_elewacji = Column(Float, nullable=True)  # Pe

    # 5. Kluczowe Wskaźniki Sprawności i Urbanistyczne
    wskaznik_pumiu_pcn = Column(Float, nullable=True)  # (PUM + PUU) / Pcn
    wskaznik_pumiu_pcnb = Column(Float, nullable=True)  # (PUM + PUU) / Pcnb
    wskaznik_pumiu_pc = Column(Float, nullable=True)  # (PUM + PUU) / Pc
    wskaznik_pumiu_pcb = Column(Float, nullable=True)  # (PUM + PUU) / Pcb
    wskaznik_pcg_impg = Column(Float, nullable=True)  # Pcg / impg
    wskaznik_pumiu_pd = Column(Float, nullable=True)  # (PUM + PUU) / Pd
    wskaznik_pumiu_klatka = Column(Float, nullable=True)  # (PUM + PUU) / iks
    wskaznik_ilm_iw = Column(Float, nullable=True)  # il.m. / iw
    wskaznik_pc_pcg = Column(Float, nullable=True)  # Pc / Pcg
    wskaznik_ilm_iks = Column(Float, nullable=True)  # il.m. / iks
    wskaznik_pe_pumiu = Column(Float, nullable=True)  # Pe / (PUM + PUU)

    # Surowe dane w JSON na wypadek nietypowych wierszy dodatkowych
    raw_parameters = Column(JSON, nullable=True)

    phase = relationship("ProjectPhase", back_populates="kpi")


class AuditLog(Base):
    """Historia audytu i kontroli poprawności wskaźników."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("project_phases.id"), nullable=False)
    category = Column(String(50), nullable=False)  # 'MATH', 'LOGIC', 'CROSS_PHASE'
    rule_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'PASS', 'WARNING', 'FAIL'
    message = Column(Text, nullable=False)
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    phase = relationship("ProjectPhase", back_populates="audit_logs")
