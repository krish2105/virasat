from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from virasat.api import schemas
from virasat.api.routes import auth, field, queue, reports, runs
from virasat.db.session import engine
from virasat.llm.router import mode, model_spec
from virasat.settings import settings

app = FastAPI(
    title="VIRASAT",
    version="0.1.0",
    description=(
        "Heritage compliance evidence engine — every output is a recommendation to a named officer."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth.router, queue.router, runs.router, reports.router, field.router):
    app.include_router(r)

EVIDENCE = Path("data/processed/evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=EVIDENCE), name="evidence")

health_router = APIRouter()


@health_router.get("/health", response_model=schemas.Health)
def health() -> schemas.Health:
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False
    ollama_ok = False
    if mode() == "local":
        try:
            ollama_ok = (
                httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2).status_code == 200
            )
        except httpx.HTTPError:
            ollama_ok = False
    models = {n: model_spec(n)["model"] for n in ("assess", "verify")}
    ok = db_ok and (ollama_ok or mode() == "cloud")
    return schemas.Health(
        status="ok" if ok else "degraded",
        database=db_ok,
        ollama=ollama_ok,
        models=models,
        mode=mode(),
    )


app.include_router(health_router)
