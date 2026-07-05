from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, join_location


def _headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = config.get("api_key")
    if api_key:
        headers["X-SmartToken"] = str(api_key)
    return headers


def _description(detail: dict[str, Any]) -> str:
    job_ad = detail.get("jobAd") or {}
    sections = job_ad.get("sections") or {}

    parts: list[str] = []

    if isinstance(sections, dict):
        for value in sections.values():
            if isinstance(value, dict):
                heading = value.get("title") or ""
                text = value.get("text") or value.get("content") or ""
                cleaned = clean_html(text)
                if cleaned:
                    parts.append(f"{heading}\n{cleaned}".strip())
            elif value:
                cleaned = clean_html(value)
                if cleaned:
                    parts.append(cleaned)

    for key in (
        "description",
        "jobDescription",
        "qualifications",
        "additionalInformation",
    ):
        value = detail.get(key) or job_ad.get(key)
        if value:
            cleaned = clean_html(value.get("text") if isinstance(value, dict) else value)
            if cleaned:
                parts.append(cleaned)

    return "\n\n".join(dict.fromkeys(parts))


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    company_identifier = str(config["company_identifier"]).strip()
    organization = str(config["organization"]).strip()
    headers = _headers(config)

    base_url = (
        "https://api.smartrecruiters.com/v1/companies/"
        f"{company_identifier}/postings"
    )

    results: list[NormalizedJob] = []
    offset = 0
    limit = 100

    while True:
        page = fetch_json(
            base_url,
            params={
                "limit": limit,
                "offset": offset,
                "destination": "PUBLIC",
            },
            headers=headers,
        )

        postings = (
            page.get("content")
            or page.get("postings")
            or page.get("jobs")
            or []
        )

        for posting in postings:
            posting_id = (
                posting.get("id")
                or posting.get("uuid")
                or posting.get("postingId")
            )
            if posting_id is None:
                continue

            detail = fetch_json(
                f"{base_url}/{posting_id}",
                headers=headers,
            )

            location_data = detail.get("location") or posting.get("location")
            location = join_location(location_data)

            source_url = (
                detail.get("jobAdUrl")
                or detail.get("applyUrl")
                or posting.get("jobAdUrl")
                or posting.get("applyUrl")
            )
            if not source_url:
                continue

            results.append(
                NormalizedJob(
                    external_id=str(posting_id),
                    title=(
                        detail.get("name")
                        or detail.get("title")
                        or posting.get("name")
                        or posting.get("title")
                        or "Untitled opportunity"
                    ),
                    organization=(
                        (detail.get("company") or {}).get("name")
                        if isinstance(detail.get("company"), dict)
                        else organization
                    ) or organization,
                    description=_description(detail),
                    location=location,
                    source="smartrecruiters",
                    source_url=source_url,
                    posted_date=(
                        detail.get("releasedDate")
                        or detail.get("postedDate")
                        or posting.get("releasedDate")
                        or posting.get("postedDate")
                    ),
                    work_mode=infer_work_mode(
                        detail.get("locationType"),
                        posting.get("locationType"),
                        location,
                    ),
                    raw_payload=detail,
                )
            )

        total = int(page.get("totalFound") or page.get("total") or len(postings))
        offset += len(postings)

        if not postings or offset >= total:
            break

    return results
