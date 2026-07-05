from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, join_location


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    company_domain = str(config["company_domain"]).strip()
    organization = str(config["organization"]).strip()
    api_key = str(config["api_key"]).strip()

    data = fetch_json(
        (
            f"https://{company_domain}.bamboohr.com/"
            "api/v1/applicant_tracking/jobs"
        ),
        params={"statusGroups": "Open"},
        headers={"Accept": "application/json"},
        auth=(api_key, "x"),
    )

    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    results: list[NormalizedJob] = []

    for job in jobs or []:
        job_id = job.get("id") or job.get("jobOpeningId")
        if job_id is None:
            continue

        source_url = (
            job.get("jobOpeningUrl")
            or job.get("url")
            or (
                f"https://{company_domain}.bamboohr.com/careers/"
                f"{job_id}"
            )
        )

        location = join_location(
            job.get("location")
            or job.get("jobLocation")
        )

        results.append(
            NormalizedJob(
                external_id=str(job_id),
                title=(
                    job.get("postingTitle")
                    or job.get("title")
                    or "Untitled opportunity"
                ),
                organization=organization,
                description=clean_html(
                    job.get("jobDescription")
                    or job.get("description")
                ),
                location=location,
                source="bamboohr",
                source_url=source_url,
                posted_date=(
                    job.get("created")
                    or job.get("createdAt")
                    or job.get("datePosted")
                ),
                work_mode=infer_work_mode(
                    job.get("remote"),
                    location,
                ),
                raw_payload=job,
            )
        )

    return results
