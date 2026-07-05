from __future__ import annotations

from typing import Any

from models import NormalizedJob

from .common import clean_html, fetch_json, infer_work_mode, join_location


def fetch(config: dict[str, Any]) -> list[NormalizedJob]:
    subdomain = str(config["subdomain"]).strip()
    organization = str(config["organization"]).strip()

    data = fetch_json(
        f"https://{subdomain}.recruitee.com/api/offers/",
        headers={"Accept": "application/json"},
    )

    if isinstance(data, dict):
        offers = data.get("offers") or data.get("jobs") or []
    elif isinstance(data, list):
        offers = data
    else:
        offers = []

    results: list[NormalizedJob] = []

    for offer in offers or []:
        source_url = (
            offer.get("careers_url")
            or offer.get("url")
            or offer.get("apply_url")
        )
        if not source_url:
            continue

        locations = (
            offer.get("locations")
            or offer.get("location")
            or offer.get("city")
        )
        location = join_location(locations)

        results.append(
            NormalizedJob(
                external_id=str(
                    offer.get("id")
                    or offer.get("slug")
                    or source_url
                ),
                title=offer.get("title") or "Untitled opportunity",
                organization=organization,
                description=clean_html(
                    offer.get("description")
                    or offer.get("description_html")
                    or offer.get("requirements")
                ),
                location=location,
                source="recruitee",
                source_url=source_url,
                posted_date=(
                    offer.get("published_at")
                    or offer.get("created_at")
                    or offer.get("updated_at")
                ),
                work_mode=infer_work_mode(
                    offer.get("remote"),
                    offer.get("workplace_type"),
                    location,
                ),
                raw_payload=offer,
            )
        )

    return results
