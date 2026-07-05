from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import fetch_json, infer_work_mode, stable_external_id


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    job_board_name = str(config["job_board_name"]).strip()
    organization = str(config["organization"]).strip()

    data = fetch_json(
        (
            "https://api.ashbyhq.com/posting-api/job-board/"
            f"{job_board_name}"
        ),
        params={
            "includeCompensation": str(
                bool(config.get("include_compensation", True))
            ).lower()
        },
    )

    results: list[NormalizedJob] = []

    for job in data.get("jobs", []):
        if job.get("isListed") is False:
            continue

        source_url = job.get("jobUrl") or job.get("applyUrl")
        if not source_url:
            continue

        results.append(
            NormalizedJob(
                external_id=str(
                    job.get("id") or stable_external_id(source_url)
                ),
                title=job.get("title") or "Untitled opportunity",
                organization=organization,
                description=(
                    job.get("descriptionPlain")
                    or job.get("descriptionHtml")
                    or ""
                ),
                location=job.get("location"),
                source="ashby",
                source_url=source_url,
                posted_date=job.get("publishedAt"),
                work_mode=infer_work_mode(
                    job.get("workplaceType"),
                    job.get("isRemote"),
                    job.get("location"),
                ),
                raw_payload=job,
            )
        )

    return results
