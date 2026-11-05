from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..core.database import get_db
from ..core.security import verify_password, create_access_token, get_current_user

router = APIRouter()

@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(400, "username and password required")
    row = db.execute(text("SELECT id, username, role, agent_name, password_hash FROM users WHERE username=:u"), {"u": username}).mappings().first()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": row["username"], "role": row["role"], "id": row["id"]})
    # NEVER return password_hash
    return {"access_token": token, "token_type": "bearer", "user": {"id": row["id"], "username": row["username"], "role": row["role"], "agent_name": row["agent_name"]}}

@router.get("/me")
def me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT id, username, role, agent_name FROM users WHERE username=:u"), {"u": current["username"]}).mappings().first()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)
