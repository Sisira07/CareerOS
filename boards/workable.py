from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, join_location


def _normalize(
    job: dict[str, Any],
    organization: str,
) -> NormalizedJob | None:
    source_url = (
        job.get("url")
        or job.get("shortlink")
        or job.get("application_url")
    )
    if not source_url:
        return None

    location_data = job.get("location") or job.get("locations")
    location = join_location(location_data)

    return NormalizedJob(
        external_id=str(
            job.get("id")
            or job.get("shortcode")
            or source_url
        ),
        title=job.get("title") or job.get("full_title") or "Untitled opportunity",
        organization=organization,
        description=clean_html(
            job.get("description")
            or job.get("description_html")
            or job.get("full_description")
        ),
        location=location,
        source="workable",
        source_url=source_url,
        posted_date=job.get("created_at") or job.get("published"),
        work_mode=infer_work_mode(
            (job.get("location") or {}).get("workplace_type")
            if isinstance(job.get("location"), dict)
            else None,
            location,
        ),
        raw_payload=job,
    )


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    subdomain = str(config["subdomain"]).strip()
    organization = str(config["organization"]).strip()
    api_token = config.get("api_token")

    if api_token:
        data = fetch_json(
            f"https://{subdomain}.workable.com/spi/v3/jobs",
            params={"state": "published"},
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_token}",
            },
        )
        jobs = data.get("jobs", [])

        detailed_jobs: list[dict[str, Any]] = []
        for job in jobs:
            shortcode = job.get("shortcode")
            if not shortcode:
                detailed_jobs.append(job)
                continue

            try:
                detail = fetch_json(
                    f"https://{subdomain}.workable.com/spi/v3/jobs/{shortcode}",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {api_token}",
                    },
                )
                detailed_jobs.append(detail)
            except Exception:
                detailed_jobs.append(job)

        jobs = detailed_jobs
    else:
        data = fetch_json(
            f"https://www.workable.com/api/accounts/{subdomain}",
            params={"details": "true"},
        )
        jobs = data.get("jobs", []) if isinstance(data, dict) else data

    results: list[NormalizedJob] = []

    for job in jobs or []:
        normalized = _normalize(job, organization)
        if normalized:
            results.append(normalized)

    return results
