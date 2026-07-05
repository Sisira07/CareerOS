from __future__ import annotations

import argparse
import os
from datetime import date
from typing import Any

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from db import (
    fetch_pending_opportunities,
    mark_processing,
    mark_processing_failed,
    save_enrichment,
)
from models import OpportunityEnrichment


load_dotenv()

PROMPT_VERSION = "opportunity-enrichment-v1"

CATEGORIES = [
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


def build_prompt(opportunity: dict[str, Any], retry_note: str | None = None) -> str:
    posted_date = opportunity.get("posted_date")
    location = opportunity.get("location") or "Not specified"
    existing_work_mode = opportunity.get("work_mode") or "Unspecified"

    retry_section = ""
    if retry_note:
        retry_section = f"""
The previous response failed validation:
{retry_note}

Correct the response without adding unsupported information.
"""

    return f"""
You extract structured facts from job and internship descriptions.

Return information only when it is supported by the supplied opportunity.
Do not invent skills, deadlines, eligibility rules, or work arrangements.

Instructions:
1. Write a factual two-to-four-sentence summary.
2. Extract only explicitly required or preferred skills and technologies.
3. Use canonical skill names and remove duplicates.
4. Select exactly one category from: {", ".join(CATEGORIES)}.
5. Select work_mode as Remote, Hybrid, On-site, or Unspecified.
6. Return eligibility as null when it is not stated.
7. Return deadline as null when an application deadline is not stated.
8. Do not treat the posted date as an application deadline.
9. Do not include general responsibilities as skills.
10. Keep promotional language out of the summary.

Title: {opportunity["title"]}
Organization: {opportunity["organization"]}
Location: {location}
Existing work-mode hint: {existing_work_mode}
Posted date: {posted_date}

Description:
{opportunity["description"]}
{retry_section}
""".strip()


class GeminiOpportunityProcessor:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing.")

        self.model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.client = genai.Client(api_key=api_key)

    def process(
        self,
        opportunity: dict[str, Any],
        retry_note: str | None = None,
    ) -> OpportunityEnrichment:
        interaction = self.client.interactions.create(
            model=self.model,
            input=build_prompt(opportunity, retry_note),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": OpportunityEnrichment.model_json_schema(),
            },
        )

        enrichment = OpportunityEnrichment.model_validate_json(
            interaction.output_text
        )
        self._validate_business_rules(opportunity, enrichment)
        return enrichment

    @staticmethod
    def _validate_business_rules(
        opportunity: dict[str, Any],
        enrichment: OpportunityEnrichment,
    ) -> None:
        if enrichment.deadline:
            posted_date = opportunity.get("posted_date")
            if posted_date and hasattr(posted_date, "date"):
                posted_day: date = posted_date.date()
                if enrichment.deadline < posted_day:
                    raise ValueError(
                        "The extracted deadline is earlier than the posted date."
                    )


def process_pending(limit: int = 20) -> dict[str, int]:
    processor = GeminiOpportunityProcessor()
    records = fetch_pending_opportunities(limit)

    completed = 0
    failed = 0

    for record in records:
        opportunity_id = int(record["id"])
        mark_processing(opportunity_id)

        try:
            try:
                enrichment = processor.process(record)
            except (ValidationError, ValueError) as first_error:
                enrichment = processor.process(record, retry_note=str(first_error))

            save_enrichment(
                opportunity_id,
                enrichment,
                prompt_version=PROMPT_VERSION,
            )
            completed += 1

        except Exception as error:
            mark_processing_failed(opportunity_id, str(error))
            failed += 1

    return {
        "retrieved": len(records),
        "completed": completed,
        "failed": failed,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich PostgreSQL opportunities with Gemini."
    )
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if args.limit < 1:
        raise SystemExit("--limit must be greater than zero.")

    result = process_pending(args.limit)

    print("=" * 52)
    print("Gemini opportunity processing completed")
    print("=" * 52)
    for key, value in result.items():
        print(f"{key.replace('_', ' ').title():20} {value}")


if __name__ == "__main__":
    main()
