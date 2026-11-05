from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..core.database import get_db

router = APIRouter()

@router.get("/entries")
def entries(date_from: str = None, date_to: str = None, team: str = None, db: Session = Depends(get_db)):
    sql = text("""
      SELECT te.*, p.code, p.name as project_name FROM time_entries te LEFT JOIN projects p ON p.id=te.project_id
      WHERE (:d1 IS NULL OR te.date>=:d1) AND (:d2 IS NULL OR te.date<=:d2) AND (:team IS NULL OR te.team_name=:team)
      ORDER BY te.date DESC LIMIT 500
    """)
    return [dict(r) for r in db.execute(sql, {"d1": date_from, "d2": date_to, "team": team}).mappings()]

@router.get("/projects")
def projects(db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM projects WHERE active=1")).mappings()]

@router.get("/v-time-etp")
def v_time_etp(date: str = None, db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM v_time_etp WHERE date=COALESCE(:d, CURDATE())"), {"d": date}).mappings()]
