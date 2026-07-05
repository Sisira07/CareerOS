from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from db import get_filter_values, search_opportunities, set_saved
from gemini_pipeline import process_pending



app = FastAPI(
    title="CareerOS Multi-Board API",
    version="1.0.0",
)


class SaveRequest(BaseModel):
    saved: bool

def verify_admin_secret(
    authorization: str | None,
) -> None:
    expected_secret = os.getenv("ADMIN_SECRET")

    if not expected_secret:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_SECRET is not configured.",
        )

    if authorization != f"Bearer {expected_secret}":
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials.",
        )

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/opportunities")
def list_opportunities(
    q: str | None = None,
    category: str | None = None,
    skill: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    saved: bool = False,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return search_opportunities(
        query_text=q,
        category=category,
        skill=skill,
        location=location,
        work_mode=work_mode,
        saved_only=saved,
        page=page,
        limit=limit,
    )


@app.get("/api/filters")
def filters():
    return get_filter_values()


@app.patch("/api/opportunities/{opportunity_id}/saved")
def update_saved(
    opportunity_id: int,
    request: SaveRequest,
):
    try:
        saved = set_saved(opportunity_id, request.saved)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "id": opportunity_id,
        "is_saved": saved,
    }


@app.post("/api/process")
def process_opportunities(
    limit: int = Query(default=10, ge=1, le=100),
    authorization: str | None = Header(default=None),
):
    verify_admin_secret(authorization)

    try:
        return process_pending(limit)
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error


