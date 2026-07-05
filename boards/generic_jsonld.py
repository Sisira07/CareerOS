from __future__ import annotations

import json
from typing import Any, Iterable

from bs4 import BeautifulSoup

from models import NormalizedJob

from .common import (
    clean_html,
    fetch_text,
    infer_work_mode,
    join_location,
    stable_external_id,
)


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)

    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _is_job_posting(value: dict[str, Any]) -> bool:
    item_type = value.get("@type")
    if isinstance(item_type, list):
        return "JobPosting" in item_type
    return item_type == "JobPosting"


def _location(job: dict[str, Any]) -> str | None:
    location = job.get("jobLocation")
    if isinstance(location, list):
        return join_location([
            item.get("address") if isinstance(item, dict) else item
            for item in location
        ])

    if isinstance(location, dict):
        return join_location(location.get("address") or location)

    applicant_location = job.get("applicantLocationRequirements")
    return join_location(applicant_location)


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    url = str(config["career_url"]).strip()
    fallback_organization = str(
        config.get("organization", "Unknown organization")
    ).strip()

    page = fetch_text(
        url,
        headers={
            "User-Agent": (
                "CareerOS/1.0 (+job opportunity aggregation project)"
            )
        },
    )
    soup = BeautifulSoup(page, "html.parser")

    results: list[NormalizedJob] = []

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue

        for job in _walk_json(payload):
            if not _is_job_posting(job):
                continue

            source_url = (
                job.get("url")
                or job.get("sameAs")
                or url
            )

            hiring_organization = job.get("hiringOrganization") or {}
            organization = (
                hiring_organization.get("name")
                if isinstance(hiring_organization, dict)
                else None
            ) or fallback_organization

            identifier = job.get("identifier")
            if isinstance(identifier, dict):
                identifier = identifier.get("value") or identifier.get("name")

            location = _location(job)

            results.append(
                NormalizedJob(
                    external_id=str(
                        identifier
                        or job.get("@id")
                        or stable_external_id(source_url)
                    ),
                    title=job.get("title") or "Untitled opportunity",
                    organization=organization,
                    description=clean_html(job.get("description")),
                    location=location,
                    source="generic_jsonld",
                    source_url=source_url,
                    posted_date=job.get("datePosted"),
                    work_mode=infer_work_mode(
                        job.get("jobLocationType"),
                        location,
                    ),
                    raw_payload=job,
                )
            )

    return results
