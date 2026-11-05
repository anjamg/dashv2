from datetime import datetime
import io
import re

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user

router = APIRouter()
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def normalize_user(name: str) -> str:
    return re.sub(r"^(Vitalliance - |Niveau 2 - Vitalliance - )", "", name).strip()


def _value(row: dict, *keys: str):
    for key in keys:
        value = row.get(key)
        if not pd.isna(value):
            return value
    return None


@router.post("/aircall")
async def import_aircall(file: UploadFile, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Upload an .xlsx Aircall export.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 15 MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        frame = pd.read_excel(io.BytesIO(content))
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail="The file could not be read as an Excel workbook.") from exc

    columns = set(frame.columns)
    if not ({"datetime_utc", "Date"} & columns) or not ({"user", "User"} & columns):
        raise HTTPException(status_code=422, detail="The workbook must include a Date/datetime_utc column and a User/user column.")
    if frame.empty:
        raise HTTPException(status_code=400, detail="The workbook contains no rows.")

    records = []
    skipped = 0
    for row in frame.to_dict(orient="records"):
        raw_date = _value(row, "datetime_utc", "Date")
        raw_user = _value(row, "user", "User")
        if raw_date is None and raw_user is None:
            skipped += 1
            continue
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(parsed_date) or raw_user is None:
            raise HTTPException(status_code=422, detail="Every populated row must have a valid date and user.")
        duration = pd.to_numeric(_value(row, "duration_total_sec", "duration_total"), errors="coerce")
        waiting = pd.to_numeric(_value(row, "waiting_time_sec", "waiting_time"), errors="coerce")
        raw_answered = str(_value(row, "answered") or "").strip().lower()
        records.append({
            "datetime": parsed_date.to_pydatetime(),
            "user": str(raw_user).strip(),
            "user_norm": normalize_user(str(raw_user)),
            "direction": _value(row, "direction"),
            "answered": raw_answered in {"1", "true", "yes", "answered"},
            "team_name": _value(row, "team_name", "Team"),
            "duration": int(duration) if not pd.isna(duration) else 0,
            "waiting": int(waiting) if not pd.isna(waiting) else 0,
        })

    if not records:
        raise HTTPException(status_code=400, detail="The workbook contains no valid call records.")

    db.execute(text("""
        INSERT INTO data (
            datetime_utc, datetime_tz_offset_incl, user, user_norm, direction, answered,
            team_name, duration_total_sec, waiting_time_sec
        ) VALUES (
            :datetime, :datetime, :user, :user_norm, :direction, :answered,
            :team_name, :duration, :waiting
        )
    """), records)
    db.execute(text("""
        INSERT INTO import_history (filename, imported_at, rows_inserted, rows_skipped, status)
        VALUES (:filename, :imported_at, :inserted, :skipped, 'success')
    """), {
        "filename": filename,
        "imported_at": datetime.now(),
        "inserted": len(records),
        "skipped": skipped,
    })
    db.commit()
    return {"inserted": len(records), "skipped": skipped, "filename": filename}


@router.get("/history")
def history(db: Session = Depends(get_db)):
    return [dict(row) for row in db.execute(
        text("SELECT * FROM import_history ORDER BY imported_at DESC LIMIT 100")
    ).mappings()]
