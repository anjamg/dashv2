# VITA 2.0 - Modern Stack

Migrated from PHP 8.1 + Python + MariaDB to **FastAPI + React + MariaDB** (seamless DB integration)

Original: 22 tables, 3 views (vita-no_data.sql, MariaDB 10.11.14), 160MB production DB
New: FastAPI backend reusing existing `vita` DB, no data migration needed.

## Quick Start

```bash
# 1. Configure the backend environment (PowerShell)
Copy-Item backend/.env.example backend/.env
# Local API development uses the MariaDB port localhost:3307.
# Replace SECRET_KEY and database credentials before deployment.

# 2. Docker (recommended)
docker-compose up --build
# API: http://localhost:8000/docs
# Frontend: http://localhost:3000

# 3. Or local dev (Windows PowerShell)
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 5656

# In a second terminal
cd frontend
npm install
npm run dev
```

## Modules (from old schema)

| Module | Old PHP | New API |
|---|---|---|
| Dashboard KPIs | index.php?action=overview | GET /api/dashboard/kpis |
| Calls table | action=calls_table | GET /api/calls |
| By team | by_team | GET /api/dashboard/by-team |
| Time/ETP | v_time_etp, v_effectif_etp (fixed OVER clause) | GET /api/time/v-time-etp |
| Leaves | leaves.php + LeaveModel | GET /api/leaves/requests |
| Tarifs | 5 tarif tables + departements | GET /api/tarifs/* |
| Agences | agences (lat/lng) | GET /api/tarifs/agences |
| Meteo | meteo.php + meteo_export.php | GET /api/meteo/report, GET /api/meteo/export, POST /api/meteo/organization-note |
| Imports | import.php -> import_excel.py (SSE) | POST /api/imports/aircall |

## Current frontend functionality

- Calls can be filtered by team, user, answer status, and date range, with server-side pagination.
- Dashboard KPI cards and team activity can be filtered by date range.
- Leave requests, tariff tables, time entries, daily effectif, the N2/SVI/SQ weather report, organization notes, and import history load from the API with loading and error states.
- Aircall imports accept `.xlsx` files up to 15 MB. The workbook must include a date (`Date` or `datetime_utc`) and user (`User` or `user`) column.
- Set `VITE_API_URL` to the API origin when the frontend and API are not served from the same host. Local development defaults to `http://localhost:5656`.
- The Météo report reuses the legacy reporting queries in `backend/app/sql/meteo/`; the database must include the `team_memberships`, `leave_requests`, `meteo_daily_notes`, and source call-data schema.

## Security Fixed (from SECURITE.md)
- Secrets moved from config/database.php to .env
- Auth: JWT (bcrypt) instead of PHP sessions
- All writes POST only, no GET side-effects
- import.php auth guard added
- display_errors removed

## Push to GitHub

```bash
git init
git add .
git commit -m "feat: VITA 2.0 migration"
gh repo create vita-modern-stack --private --source=. --push
# or
git remote add origin https://github.com/USERNAME/vita-modern-stack.git
git push -u origin main
```

## DB Notes
- The Docker database starts empty; load the legacy VITA schema and views before using data-backed pages.
- Keep your 160MB production DB as-is
- Generated columns date_only, hour, out_of_hours, user_norm kept
- Fix for v_time_etp: original dump had `sum(hours) ( partition by ...)` -> fixed to `SUM(hours) OVER (PARTITION BY agent, date)`
