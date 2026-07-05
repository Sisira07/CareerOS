from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, join_location


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    board_token = str(config["board_token"]).strip()
    organization = str(config["organization"]).strip()

    data = fetch_json(
        f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs",
        params={"content": "true"},
    )

    results: list[NormalizedJob] = []

    for job in data.get("jobs", []):
        location = join_location(job.get("location"))

        results.append(
            NormalizedJob(
                external_id=str(job["id"]),
                title=job.get("title") or "Untitled opportunity",
                organization=organization,
                description=clean_html(job.get("content")),
                location=location,
                source="greenhouse",
                source_url=job["absolute_url"],
                posted_date=job.get("updated_at"),
                work_mode=infer_work_mode(location),
                raw_payload=job,
            )
        )

    return results
