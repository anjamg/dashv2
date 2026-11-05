from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..services.meteo import build_report, create_excel_report

router = APIRouter()


def _period(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    today = date.today()
    start = date_from or today
    end = date_to or today
    if start > end:
        raise HTTPException(status_code=422, detail="date_from must be before or equal to date_to")
    return start, end


@router.get("/report")
def meteo_report(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    start, end = _period(date_from, date_to)
    return build_report(db, start, end)


@router.get("/export")
def export_meteo(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    start, end = _period(date_from, date_to)
    report = build_report(db, start, end)
    content = create_excel_report(report)
    filename = f"meteo_{start.isoformat()}_{end.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class OrganizationNotePayload(BaseModel):
    report_date: date
    organization_text: str = Field(max_length=10000)


@router.post("/organization-note")
def save_organization_note(
    payload: OrganizationNotePayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db.execute(text("""
        INSERT INTO meteo_daily_notes (report_date, organization_text)
        VALUES (:report_date, :organization_text)
        ON DUPLICATE KEY UPDATE organization_text = VALUES(organization_text)
    """), payload.model_dump())
    db.commit()
    return {"ok": True, "report_date": payload.report_date}
