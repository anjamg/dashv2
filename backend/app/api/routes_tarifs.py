from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..core.database import get_db

router = APIRouter()

@router.get("/departements")
def deps(db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM departements ORDER BY code")).mappings()]

@router.get("/prestataire/{type}")
def tarifs_prest(type: str, departement_id: int = None, db: Session = Depends(get_db)):
    table_map = {"standard":"tarifs_prestataire_standard","apa":"tarifs_prestataire_apa","carsat":"tarifs_prestataire_carsat","pch":"tarifs_prestataire_pch"}
    table = table_map.get(type, "tarifs_prestataire_standard")
    sql = text(f"SELECT t.*, d.code as dept_code, d.nom FROM {table} t JOIN departements d ON d.id=t.departement_id WHERE (:did IS NULL OR t.departement_id=:did) ORDER BY d.code, tranche_heures")
    return [dict(r) for r in db.execute(sql, {"did": departement_id}).mappings()]

@router.get("/mandataire/horaire")
def mand_horaire(departement_id: int = None, db: Session = Depends(get_db)):
    sql = text("SELECT * FROM tarifs_mandataire_horaire WHERE (:did IS NULL OR departement_id=:did)")
    return [dict(r) for r in db.execute(sql, {"did": departement_id}).mappings()]

@router.get("/agences")
def agences(db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM agences ORDER BY Nom")).mappings()]
