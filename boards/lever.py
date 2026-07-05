from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, parse_milliseconds


def _description(job: dict[str, Any]) -> str:
    parts = [
        job.get("descriptionPlain"),
        job.get("additionalPlain"),
    ]

    for item in job.get("lists") or []:
        heading = str(item.get("text") or "").strip()
        content = clean_html(item.get("content"))
        if heading or content:
            parts.append(f"{heading}\n{content}".strip())

    return "\n\n".join(
        str(part).strip()
        for part in parts
        if part and str(part).strip()
    )


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    site = str(config["site"]).strip()
    organization = str(config["organization"]).strip()
    region = str(config.get("region", "global")).lower()

    host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
    base_url = f"https://{host}/v0/postings/{site}"

    results: list[NormalizedJob] = []
    skip = 0
    page_size = 100

    while True:
        jobs = fetch_json(
            base_url,
            params={
                "mode": "json",
                "skip": skip,
                "limit": page_size,
            },
            headers={"Accept": "application/json"},
        )

        if not isinstance(jobs, list):
            break

        for job in jobs:
            categories = job.get("categories") or {}
            location = categories.get("location")
            work_mode = infer_work_mode(
                job.get("workplaceType"),
                location,
            )

            results.append(
                NormalizedJob(
                    external_id=str(job["id"]),
                    title=job.get("text") or "Untitled opportunity",
                    organization=organization,
                    description=_description(job),
                    location=location,
                    source="lever",
                    source_url=job.get("hostedUrl") or job["applyUrl"],
                    posted_date=parse_milliseconds(job.get("createdAt")),
                    work_mode=work_mode,
                    raw_payload=job,
                )
            )

        if len(jobs) < page_size:
            break

        skip += page_size

    return results
