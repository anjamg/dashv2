from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter()

@router.get("")
def list_calls(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    team: str | None = None,
    user: str | None = None,
    answered: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit
    filters = """
        WHERE (:team IS NULL OR team_name=:team)
          AND (:user IS NULL OR user_norm=:user)
          AND (:ans IS NULL OR answered=:ans)
          AND (:d1 IS NULL OR DATE(datetime_tz_offset_incl) >= :d1)
          AND (:d2 IS NULL OR DATE(datetime_tz_offset_incl) <= :d2)
    """
    params = {"team": team, "user": user, "ans": answered, "d1": date_from, "d2": date_to}
    total = db.execute(
        text(f"SELECT COUNT(*) FROM data {filters}"),
        params,
    ).scalar_one()
    sql = text(f"""
        SELECT id, datetime_tz_offset_incl, direction, team_name, user, user_norm, answered,
               duration_total_sec, waiting_time_sec, time_to_answer_sec, call_id
        FROM data
        {filters}
        ORDER BY datetime_tz_offset_incl DESC LIMIT :lim OFFSET :off
    """)
    rows = db.execute(sql, {**params, "lim": limit, "off": offset}).mappings().all()
    return {"data": [dict(row) for row in rows], "page": page, "limit": limit, "total": total}

@router.get("/import-history")
def import_hist(db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT * FROM import_history ORDER BY imported_at DESC LIMIT 100")).mappings()]
