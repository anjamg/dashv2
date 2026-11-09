from datetime import datetime, timezone
import io
import re
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models import Data

router = APIRouter()
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
IMPORT_CHUNK_SIZE = 1000

TEAM_MAP = {
    "SVI 1 Astreinte & Urgence": "DEB",
    "SVI 2 Admin": "DEB",
    "SVI 3 Commercial": "CDN",
    "Vitalliance SEA": "CDN",
    "Num HP Vitalliance": "CDN",
    "New FR Mobile": "N2",
    "Vitalliance DEB -N2": "N2",
    "Vitalliance - Suivi qualité": "Suivi Qualité",
    "Vitalliance - QS": "Suivi Qualité",
}

DATA_COLUMNS = (
    "line",
    "datetime_tz_offset_incl",
    "number_timezone",
    "datetime_utc",
    "country_code",
    "direction",
    "from",
    "to",
    "answered",
    "missed_call_reason",
    "user",
    "duration_total",
    "duration_in_call",
    "voicemail",
    "recording",
    "comments",
    "tags",
    "call_quality",
    "team",
    "call_direction_type",
    "call_start_time",
    "call_end_time",
    "aircall_number",
    "customer_number",
    "in_call_duration",
    "call_id",
    "call_type",
    "waiting_time",
    "time_to_answer",
    "time_in_ivr",
    "call_id_internal",
    "disconnected_by",
    "ivr_branch",
    "ivr_widget",
    "call_timeline",
    "callback_details",
    "callback_failure",
    "automatic_callback_pending_time",
    "time_with_ai_voice_agent",
    "entry_number",
    "ai_voice_agent_transfer_branch",
    "ai_voice_agent",
    "waiting_time_sec",
    "time_to_answer_sec",
    "time_in_ivr_sec",
    "duration_total_sec",
    "duration_in_call_sec",
    "team_name",
    "user_norm",
)

QUOTED_DATA_COLUMNS = ", ".join(f"`{column}`" for column in DATA_COLUMNS)
UPSERT_DATA = text(
    f"INSERT INTO data ({QUOTED_DATA_COLUMNS}) "
    f"VALUES ({', '.join(f':{column}' for column in DATA_COLUMNS)}) "
    "ON DUPLICATE KEY UPDATE "
    + ", ".join(
        f"`{column}` = VALUES(`{column}`)"
        for column in DATA_COLUMNS
        if column != "call_id"
    )
)
UPSERT_STATS = text("""
    INSERT INTO data_stats (
        id, date, user, team, team_name, direction,
        answered, duration_total, duration_in_call,
        waiting_time, time_to_answer, hour_local, weekday
    )
    SELECT
        d.id,
        DATE(d.datetime_tz_offset_incl),
        d.user,
        d.team,
        d.team_name,
        d.direction,
        d.answered,
        d.duration_total_sec,
        d.duration_in_call_sec,
        d.waiting_time_sec,
        d.time_to_answer_sec,
        HOUR(d.datetime_tz_offset_incl),
        DAYOFWEEK(d.datetime_tz_offset_incl)
    FROM data AS d
    WHERE d.id IN :data_ids
    ON DUPLICATE KEY UPDATE
        `date` = VALUES(`date`),
        `user` = VALUES(`user`),
        `team` = VALUES(`team`),
        `team_name` = VALUES(`team_name`),
        `direction` = VALUES(`direction`),
        answered = VALUES(answered),
        duration_total = VALUES(duration_total),
        duration_in_call = VALUES(duration_in_call),
        waiting_time = VALUES(waiting_time),
        time_to_answer = VALUES(time_to_answer),
        hour_local = VALUES(hour_local),
        weekday = VALUES(weekday)
""").bindparams(bindparam("data_ids", expanding=True))


def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value):
            return value
    return None


def _clean_str(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _to_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _to_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _to_seconds(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    if not pd.isna(numeric):
        return int(numeric)
    duration = pd.to_timedelta(str(value), errors="coerce")
    if pd.isna(duration):
        return None
    return int(duration.total_seconds())


def _to_datetime(value: Any, *, as_utc: bool = False) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    result = parsed.to_pydatetime()
    if result.tzinfo is not None:
        if as_utc:
            result = result.astimezone(timezone.utc)
        result = result.replace(tzinfo=None)
    return result


def _to_bool(value: Any) -> bool | None:
    cleaned = _clean_str(value)
    if cleaned is None:
        return None
    normalized = cleaned.lower()
    if normalized in {"yes", "true", "1", "answered"}:
        return True
    if normalized in {"no", "false", "0", "missed", "unanswered"}:
        return False
    return None


def normalize_user(name: str | None) -> str | None:
    cleaned = _clean_str(name)
    if cleaned is None:
        return None
    normalized = re.sub(
        r"^(?:Niveau\s*2\s*-\s*)?Vitalliance\s*-\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return normalized.strip() or None


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = (
        frame.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[().-]", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )
    if frame.columns.duplicated().any():
        raise HTTPException(
            status_code=422,
            detail="The workbook contains duplicate columns after column-name normalization.",
        )
    return frame


def _map_row(row: dict[str, Any]) -> dict[str, Any]:
    line = _clean_str(_value(row, "line"))
    raw_user = _clean_str(_value(row, "user"))
    call_id = _clean_str(_value(row, "call_id"))
    total_duration = _to_int(_value(row, "duration_total", "duration_total_sec"))
    talk_duration = _to_int(_value(row, "duration_in_call", "duration_in_call_sec"))
    waiting_seconds = _to_seconds(_value(row, "waiting_time_sec", "waiting_time"))
    answer_seconds = _to_seconds(_value(row, "time_to_answer_sec", "time_to_answer"))
    ivr_seconds = _to_seconds(_value(row, "time_in_ivr_sec", "time_in_ivr"))
    datetime_utc = _to_datetime(_value(row, "datetime_utc", "date"), as_utc=True)
    datetime_local = _to_datetime(
        _value(row, "datetime_tz_offset_incl", "datetime_utc", "date")
    )
    explicit_team_name = _clean_str(_value(row, "team_name"))
    if explicit_team_name is None:
        explicit_team_name = _clean_str(_value(row, "team"))

    return {
        "line": line,
        "datetime_tz_offset_incl": datetime_local,
        "number_timezone": _clean_str(_value(row, "number_timezone")),
        "datetime_utc": datetime_utc or datetime_local,
        "country_code": _clean_str(_value(row, "country_code")),
        "direction": _clean_str(_value(row, "direction")),
        "from": _clean_str(_value(row, "from")),
        "to": _to_int(_value(row, "to")),
        "answered": _to_bool(_value(row, "answered")),
        "missed_call_reason": _clean_str(_value(row, "missed_call_reason")),
        "user": raw_user,
        "duration_total": total_duration,
        "duration_in_call": _to_number(_value(row, "duration_in_call")),
        "voicemail": _clean_str(_value(row, "voicemail")),
        "recording": _clean_str(_value(row, "recording")),
        "comments": _clean_str(_value(row, "comments")),
        "tags": _clean_str(_value(row, "tags")),
        "call_quality": _to_number(_value(row, "call_quality")),
        "team": _clean_str(_value(row, "team")),
        "call_direction_type": _clean_str(
            _value(row, "call_direction_type", "call_direction_type_")
        ),
        "call_start_time": _to_datetime(_value(row, "call_start_time")),
        "call_end_time": _to_datetime(_value(row, "call_end_time")),
        "aircall_number": _clean_str(_value(row, "aircall_number")),
        "customer_number": _clean_str(_value(row, "customer_number")),
        "in_call_duration": _to_seconds(_value(row, "in_call_duration")),
        "call_id": call_id,
        "call_type": _clean_str(_value(row, "call_type")),
        "waiting_time": _clean_str(_value(row, "waiting_time")),
        "time_to_answer": _clean_str(_value(row, "time_to_answer")),
        "time_in_ivr": _clean_str(_value(row, "time_in_ivr")),
        "call_id_internal": _to_int(_value(row, "call_id_internal")),
        "disconnected_by": _clean_str(_value(row, "disconnected_by")),
        "ivr_branch": _clean_str(_value(row, "ivr_branch")),
        "ivr_widget": _clean_str(_value(row, "ivr_widget")),
        "call_timeline": _clean_str(_value(row, "call_timeline")),
        "callback_details": _clean_str(_value(row, "callback_details")),
        "callback_failure": _clean_str(_value(row, "callback_failure")),
        "automatic_callback_pending_time": _to_seconds(
            _value(row, "automatic_callback_pending_time")
        ),
        "time_with_ai_voice_agent": _to_seconds(
            _value(row, "time_with_ai_voice_agent")
        ),
        "entry_number": _clean_str(_value(row, "entry_number")),
        "ai_voice_agent_transfer_branch": _clean_str(
            _value(row, "ai_voice_agent_transfer_branch")
        ),
        "ai_voice_agent": _clean_str(_value(row, "ai_voice_agent")),
        "waiting_time_sec": waiting_seconds,
        "time_to_answer_sec": answer_seconds,
        "time_in_ivr_sec": ivr_seconds,
        "duration_total_sec": total_duration,
        "duration_in_call_sec": talk_duration,
        "team_name": TEAM_MAP.get(line or "", explicit_team_name),
        "user_norm": normalize_user(raw_user),
    }


@router.post("/aircall")
async def import_aircall(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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
        raise HTTPException(
            status_code=400,
            detail="The file could not be read as an Excel workbook.",
        ) from exc

    frame = _normalize_columns(frame)
    columns = set(frame.columns)
    if not ({"datetime_utc", "date", "datetime_tz_offset_incl"} & columns) or "user" not in columns:
        raise HTTPException(
            status_code=422,
            detail="The workbook must include a date/datetime_utc column and a User/user column.",
        )
    if frame.empty:
        raise HTTPException(status_code=400, detail="The workbook contains no rows.")

    records: list[dict[str, Any]] = []
    skipped = 0
    without_user = 0
    for raw_row in frame.to_dict(orient="records"):
        row = {str(key): value for key, value in raw_row.items()}
        raw_date = _value(row, "datetime_utc", "date", "datetime_tz_offset_incl")
        raw_user = _value(row, "user")
        if raw_date is None and raw_user is None:
            skipped += 1
            continue
        if _to_datetime(raw_date) is None:
            raise HTTPException(
                status_code=422,
                detail="Every populated row must have a valid date.",
            )
        if raw_user is None:
            without_user += 1
        records.append(_map_row(row))

    if not records:
        raise HTTPException(
            status_code=400,
            detail="The workbook contains no valid call records.",
        )

    inserted = 0
    updated = 0
    without_call_id = 0
    stats_synced = 0
    for start in range(0, len(records), IMPORT_CHUNK_SIZE):
        chunk = records[start : start + IMPORT_CHUNK_SIZE]
        call_ids = list(dict.fromkeys(
            record["call_id"] for record in chunk if record["call_id"] is not None
        ))
        existing_ids: set[str] = set()
        if call_ids:
            existing_ids = set(
                db.scalars(
                    select(Data.call_id).where(Data.call_id.in_(call_ids))
                ).all()
            )

        seen_ids = set(existing_ids)
        for record in chunk:
            call_id = record["call_id"]
            if call_id is None:
                inserted += 1
                without_call_id += 1
            elif call_id in seen_ids:
                updated += 1
            else:
                inserted += 1
                seen_ids.add(call_id)
        db.execute(UPSERT_DATA, chunk)
        if call_ids:
            data_ids = db.scalars(
                select(Data.id).where(Data.call_id.in_(call_ids))
            ).all()
            if data_ids:
                db.execute(UPSERT_STATS, {"data_ids": data_ids})
                stats_synced += len(data_ids)

    db.execute(
        text("""
            INSERT INTO import_history (filename, imported_at, rows_inserted, rows_skipped, status)
            VALUES (:filename, :imported_at, :inserted, :skipped, 'success')
        """),
        {
            "filename": filename,
            "imported_at": datetime.now(),
            "inserted": inserted + updated,
            "skipped": skipped,
        },
    )
    db.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "without_user": without_user,
        "without_call_id": without_call_id,
        "stats_synced": stats_synced,
        "filename": filename,
    }


@router.get("/history")
def history(db: Session = Depends(get_db)):
    return [
        dict(row)
        for row in db.execute(
            text("SELECT * FROM import_history ORDER BY imported_at DESC LIMIT 100")
        ).mappings()
    ]
