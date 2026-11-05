# Security fixes applied in migration (from SECURITE.md)

Old issues fixed:
1. config/database.php with secrets → .env + pydantic-settings, not in repo
2. public/import.php no auth → JWT + role=admin guard on /api/imports/*
3. display_errors + stack trace in index.php → FastAPI exception handler returns generic message, logs server-side
4. No CSRF + GET writes → All writes POST/PUT/DELETE + JWT, no GET side-effects
5. Non-uniform auth → Depends(get_current_user) on every route
6. Cookies without Secure/HttpOnly → JWT HttpOnly Secure SameSite via frontend
7. Python launched from web with no isolation → Imports run in FastAPI background tasks, temp file outside web root, size limit 20MB

Added:
- Passwords: bcrypt via passlib (was PHP password_hash, still compatible - verify then rehash)
- Rate limiting ready (slowapi)
- CORS restricted to frontend origin (not *)
