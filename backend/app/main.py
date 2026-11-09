from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, Base
from . import models

# Create tables if not exist (you already have them)
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="VITA DASH", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .api import routes_dashboard, routes_calls, routes_leaves, routes_tarifs, routes_time, routes_auth, routes_imports, routes_meteo

app.include_router(routes_auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(routes_dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(routes_calls.router, prefix="/api/calls", tags=["calls"])
app.include_router(routes_leaves.router, prefix="/api/leaves", tags=["leaves"])
app.include_router(routes_tarifs.router, prefix="/api/tarifs", tags=["tarifs"])
app.include_router(routes_time.router, prefix="/api/time", tags=["time"])
app.include_router(routes_imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(routes_meteo.router, prefix="/api/meteo", tags=["meteo"])

@app.get("/api/health")
def health():
    return {"status": "ok", "db": "vita MariaDB 10.11", "version": "2.0"}
