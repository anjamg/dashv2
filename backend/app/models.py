from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, DateTime, Float, DECIMAL, Boolean, Enum, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import relationship
from .core.database import Base
import enum

class RoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"

# --- CORE ---
class Agence(Base):
    __tablename__ = "agences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    Agence = Column(String(100))
    DEPARTEMENT = Column(DECIMAL(10,0))
    MAPPING_TARIFAIRE = Column(String(100))
    Latitude = Column(DECIMAL(11,8))
    Longitude = Column(DECIMAL(11,8))
    Nom = Column(String(150))
    Adresse = Column(String(255))
    Tel = Column(String(50))
    Mail = Column(String(150))
    Resp_Agence = Column(String(100))
    Equipe = Column(String(100))
    lien_Vitacenter = Column(String(100))
    Code_Postal = Column(String(20))
    CDN = Column(String(8), nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default="user")
    agent_name = Column(String(150))
    agent_name_norm = Column(String(255))
    heures_attendues = Column(Integer, default=8)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

class Departement(Base):
    __tablename__ = "departements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), nullable=False)
    nom = Column(String(80), nullable=False)

# --- CALL DATA ---
class Data(Base):
    __tablename__ = "data"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    datetime_tz_offset_incl = Column(DateTime)
    datetime_utc = Column(DateTime)
    direction = Column(String(20))
    user = Column(String(100))
    team = Column(String(100))
    team_name = Column(String(50))
    answered = Column(Boolean)
    duration_total_sec = Column(Integer)
    duration_in_call_sec = Column(Integer)
    waiting_time_sec = Column(Integer)
    time_to_answer_sec = Column(Integer)
    user_norm = Column(String(255))
    # + 40 other columns kept as generic for performance - add as needed
    call_id = Column(String(100))

class DataStats(Base):
    __tablename__ = "data_stats"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date)
    user = Column(String(100))
    team_name = Column(String(50))
    direction = Column(String(20))
    answered = Column(Boolean)
    duration_total = Column(Integer)

class ImportHistory(Base):
    __tablename__ = "import_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255))
    imported_at = Column(DateTime)
    rows_inserted = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    status = Column(String(20))

class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric = Column(String(50), nullable=False)
    team_name = Column(String(50))
    threshold = Column(Float, nullable=False)
    window_min = Column(Integer, default=60)
    active = Column(Boolean, default=True)

# --- PROJECT / TIME ---
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True)
    name = Column(String(100))
    description = Column(Text)
    active = Column(Boolean, default=True)

class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent = Column(String(100), nullable=False)
    team_name = Column(String(50))
    project_id = Column(Integer, ForeignKey("projects.id"))
    date = Column(Date, nullable=False)
    hours = Column(DECIMAL(4,2), nullable=False)
    note = Column(Text)
    project = relationship("Project")

class TeamMembership(Base):
    __tablename__ = "team_memberships"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    team_name = Column(String(128))
    from_date = Column(Date)
    to_date = Column(Date)

# --- LEAVES ---
class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True)
    name = Column(String(100))
    requires_approval = Column(Boolean, default=True)

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"))
    year = Column(Integer)
    total_days = Column(DECIMAL(10,2), default=0)
    used_days = Column(DECIMAL(10,2), default=0)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    duration_days = Column(DECIMAL(10,2))
    status = Column(String(20), default="pending")
    reason = Column(Text)

# --- TARIFS ---
class TarifMandataireHoraire(Base):
    __tablename__ = "tarifs_mandataire_horaire"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    tranche_heures = Column(String(30))
    categorie = Column(String(20))
    tarif_ttc = Column(DECIMAL(6,2))
    cout_reel = Column(DECIMAL(6,2))

class TarifMandataireForfait(Base):
    __tablename__ = "tarifs_mandataire_forfait"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    libelle = Column(String(50))
    tarif_ttc = Column(DECIMAL(7,2))

class TarifPrestStandard(Base):
    __tablename__ = "tarifs_prestataire_standard"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    tranche_heures = Column(String(30))
    lun_sam_ttc = Column(DECIMAL(6,2))
    dim_feries_ttc = Column(DECIMAL(6,2))
    mai_dec_ttc = Column(DECIMAL(6,2))

# other tarif tables mapped similarly - reuse generic
class TarifPrestAPA(Base):
    __tablename__ = "tarifs_prestataire_apa"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    tranche_heures = Column(String(30))
    normal_ttc = Column(DECIMAL(6,2))

class TarifPrestCARSAT(Base):
    __tablename__ = "tarifs_prestataire_carsat"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    tranche_heures = Column(String(30))
    lun_sam_ttc = Column(DECIMAL(6,2))

class TarifPrestPCH(Base):
    __tablename__ = "tarifs_prestataire_pch"
    id = Column(Integer, primary_key=True, autoincrement=True)
    departement_id = Column(Integer, ForeignKey("departements.id"))
    tranche_heures = Column(String(30))
    normal_ttc = Column(DECIMAL(6,2))

class SuiviSQ(Base):
    __tablename__ = "suivi_sq"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime)
    agent_name = Column(String(120))
    followup_type = Column(String(20))
    result = Column(String(30))

class MeteoNote(Base):
    __tablename__ = "meteo_daily_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, unique=True)
    organization_text = Column(Text)
