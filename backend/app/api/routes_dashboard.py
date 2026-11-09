from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db

router = APIRouter()

@router.get("/kpis")
def kpis(date_from: str = None, date_to: str = None, team: str = None, db: Session = Depends(get_db)):
    # Uses v_stats_all view which unions history + realtime
    sql = text("""
        SELECT 
          COUNT(*) as total_calls,
          SUM(CASE WHEN answered=1 THEN 1 ELSE 0 END) as answered,
          SUM(CASE WHEN answered=0 THEN 1 ELSE 0 END) as missed,
          AVG(duration_total) as avg_duration,
          AVG(waiting_time) as avg_wait
        FROM v_stats_all
        WHERE (:team IS NULL OR team_name=:team)
          AND (:d1 IS NULL OR date >= :d1)
          AND (:d2 IS NULL OR date <= :d2)
    """)
    row = db.execute(sql, {"team": team, "d1": date_from, "d2": date_to}).mappings().first()
    return dict(row) if row else {}

@router.get("/by-team")
def by_team(date_from: date | None = None, date_to: date | None = None, team: str | None = None, db: Session = Depends(get_db)):
    sql = text("""
        SELECT team_name, COUNT(*) as calls, SUM(answered) as answered, AVG(duration_total) as avg_dur
        FROM v_stats_all
        WHERE date >= COALESCE(:d1, CURDATE() - INTERVAL 30 DAY)
          AND (:d2 IS NULL OR date <= :d2)
          AND (:team IS NULL OR team_name = :team)
        GROUP BY team_name
        ORDER BY calls DESC
    """)
    return [dict(r) for r in db.execute(sql, {"d1": date_from, "d2": date_to, "team": team}).mappings()]

@router.get("/by-result")
def by_result(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)):
    sql = text("""
        SELECT
          DATE(datetime_tz_offset_incl) AS call_date,
          COALESCE(team_name, 'Sans équipe') AS team_name,
          SUM(CASE WHEN answered = 1 THEN 1 ELSE 0 END) AS answered,
          SUM(CASE
                WHEN COALESCE(answered, 0) <> 1
                  AND (
                    LOWER(COALESCE(missed_call_reason, '')) LIKE '%outside%'
                    OR LOWER(COALESCE(missed_call_reason, '')) LIKE '%hour%'
                    OR LOWER(COALESCE(missed_call_reason, '')) LIKE '%horaire%'
                  )
                THEN 1 ELSE 0
              END) AS outside_hours,
          SUM(CASE
                WHEN COALESCE(answered, 0) <> 1
                  AND LOWER(COALESCE(missed_call_reason, '')) LIKE '%abandon%'
                THEN 1 ELSE 0
              END) AS abandoned,
          SUM(CASE
                WHEN COALESCE(answered, 0) <> 1
                  AND LOWER(COALESCE(missed_call_reason, '')) NOT LIKE '%outside%'
                  AND LOWER(COALESCE(missed_call_reason, '')) NOT LIKE '%hour%'
                  AND LOWER(COALESCE(missed_call_reason, '')) NOT LIKE '%horaire%'
                  AND LOWER(COALESCE(missed_call_reason, '')) NOT LIKE '%abandon%'
                THEN 1 ELSE 0
              END) AS missed
        FROM data
        WHERE (:d1 IS NULL OR DATE(datetime_tz_offset_incl) >= :d1)
          AND (:d2 IS NULL OR DATE(datetime_tz_offset_incl) <= :d2)
        GROUP BY DATE(datetime_tz_offset_incl), team_name
        ORDER BY call_date, team_name
    """)
    return [dict(row) for row in db.execute(sql, {"d1": date_from, "d2": date_to}).mappings()]

@router.get("/effectif")
def effectif(date: str = None, db: Session = Depends(get_db)):
    sql = text("SELECT * FROM v_effectif_etp WHERE date = COALESCE(:d, CURDATE())")
    return [dict(r) for r in db.execute(sql, {"d": date}).mappings()]
