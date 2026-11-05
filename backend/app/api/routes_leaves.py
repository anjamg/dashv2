from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter()

@router.get("/requests")
def leave_requests(status: str = None, db: Session = Depends(get_db)):
    sql = text("""
      SELECT lr.*, u.username, lt.name as leave_name FROM leave_requests lr
      JOIN users u ON u.id=lr.user_id JOIN leave_types lt ON lt.id=lr.leave_type_id
      WHERE (:st IS NULL OR lr.status=:st) ORDER BY lr.start_date DESC
    """)
    return [dict(r) for r in db.execute(sql, {"st": status}).mappings()]

@router.get("/balances/{user_id}")
def balances(user_id: int, year: int = 2026, db: Session = Depends(get_db)):
    sql = text("SELECT lb.*, lt.name FROM leave_balances lb JOIN leave_types lt ON lt.id=lb.leave_type_id WHERE user_id=:uid AND year=:y")
    return [dict(r) for r in db.execute(sql, {"uid": user_id, "y": year}).mappings()]

@router.post("/requests")
def create_request(payload: dict, db: Session = Depends(get_db)):
    sql = text("INSERT INTO leave_requests (user_id, leave_type_id, start_date, end_date, duration_days, reason) VALUES (:user_id, :leave_type_id, :start_date, :end_date, :duration_days, :reason)")
    db.execute(sql, payload)
    db.commit()
    return {"ok": True}
