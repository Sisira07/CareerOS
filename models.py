from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Category = Literal[
    "AI/ML",
    "Data Science",
    "Software Development",
    "Web Development",
    "DevOps",
    "Cybersecurity",
    "Cloud",
    "Quant",
    "Business",
    "Research",
    "Other",
]

WorkMode = Literal["Remote", "Hybrid", "On-site", "Unspecified"]


class NormalizedJob(BaseModel):
    external_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=500)
    organization: str = Field(min_length=1, max_length=500)
    description: str = ""
    location: str | None = None
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=8)
    posted_date: datetime | None = None
    work_mode: WorkMode = "Unspecified"
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("external_id", "title", "organization", "source", "source_url")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("location")
    @classmethod
    def normalize_optional_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class OpportunityEnrichment(BaseModel):
    summary: str = Field(
        min_length=30,
        max_length=800,
        description="A factual two-to-four-sentence summary of the role.",
    )
    skills: list[str] = Field(default_factory=list, max_length=40)
    category: Category
    work_mode: WorkMode = "Unspecified"
    eligibility: str | None = Field(default=None, max_length=700)
    deadline: date | None = None

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = " ".join(str(value).split()).strip(" ,.;:-")
            key = cleaned.casefold()

            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)

        return result

    @field_validator("eligibility")
    @classmethod
    def normalize_eligibility(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None
