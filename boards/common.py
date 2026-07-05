from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 30


def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    response = requests.get(
        url,
        params=params,
        headers=headers,
        auth=auth,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def clean_html(value: Any) -> str:
    if value is None:
        return ""

    raw = html.unescape(str(value))
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def stable_external_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def parse_milliseconds(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(
            float(value) / 1000,
            tz=timezone.utc,
        )
    except (TypeError, ValueError, OSError):
        return None


def infer_work_mode(*values: Any) -> str:
    text = " ".join(str(value) for value in values if value).casefold()

    if "hybrid" in text:
        return "Hybrid"
    if "remote" in text or "telecommut" in text:
        return "Remote"
    if "on-site" in text or "onsite" in text or "on site" in text:
        return "On-site"
    return "Unspecified"


def join_location(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None

    if isinstance(value, list):
        values = [join_location(item) for item in value]
        cleaned = [item for item in values if item]
        return " · ".join(dict.fromkeys(cleaned)) or None

    if isinstance(value, dict):
        preferred = (
            value.get("name")
            or value.get("location")
            or value.get("location_str")
        )
        if preferred:
            return join_location(preferred)

        fields = [
            value.get("city"),
            value.get("region"),
            value.get("state"),
            value.get("country"),
            value.get("country_name"),
            value.get("addressLocality"),
            value.get("addressRegion"),
            value.get("addressCountry"),
        ]
        cleaned = [
            str(item).strip()
            for item in fields
            if item not in (None, "")
        ]
        return ", ".join(dict.fromkeys(cleaned)) or None

    return str(value).strip() or None
