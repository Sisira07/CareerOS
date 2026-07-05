from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, RealDictCursor

from models import NormalizedJob, OpportunityEnrichment


load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing from the environment."
        )

    return psycopg2.connect(
        database_url,
        connect_timeout=10,
        application_name="careeros",
    )

@contextmanager
def database_cursor() -> Iterator[tuple[Any, RealDictCursor]]:
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def upsert_job(job: NormalizedJob) -> str:
    query = """
        INSERT INTO opportunities (
            external_id,
            title,
            organization,
            description,
            location,
            source,
            source_url,
            posted_date,
            work_mode,
            raw_payload,
            processing_status,
            updated_at
        )
        VALUES (
            %(external_id)s,
            %(title)s,
            %(organization)s,
            %(description)s,
            %(location)s,
            %(source)s,
            %(source_url)s,
            %(posted_date)s,
            %(work_mode)s,
            %(raw_payload)s,
            'pending',
            NOW()
        )
        ON CONFLICT (source_url)
        DO UPDATE SET
            external_id = EXCLUDED.external_id,
            title = EXCLUDED.title,
            organization = EXCLUDED.organization,
            description = EXCLUDED.description,
            location = EXCLUDED.location,
            source = EXCLUDED.source,
            posted_date = EXCLUDED.posted_date,
            work_mode = CASE
                WHEN opportunities.work_mode IS NULL
                  OR opportunities.work_mode = 'Unspecified'
                THEN EXCLUDED.work_mode
                ELSE opportunities.work_mode
            END,
            raw_payload = EXCLUDED.raw_payload,
            processing_status = CASE
                WHEN opportunities.description IS DISTINCT FROM EXCLUDED.description
                THEN 'pending'
                ELSE opportunities.processing_status
            END,
            processing_error = CASE
                WHEN opportunities.description IS DISTINCT FROM EXCLUDED.description
                THEN NULL
                ELSE opportunities.processing_error
            END,
            updated_at = NOW()
        RETURNING id
    """

    values = job.model_dump()
    values["raw_payload"] = Json(job.raw_payload)

    with database_cursor() as (_, cursor):
        cursor.execute(query, values)
        row = cursor.fetchone()

    return str(row["id"])


def fetch_pending_opportunities(limit: int = 20) -> list[dict[str, Any]]:
    query = """
        SELECT
            id,
            title,
            organization,
            description,
            location,
            posted_date,
            work_mode
        FROM opportunities
        WHERE processing_status IN ('pending', 'failed')
          AND COALESCE(description, '') <> ''
        ORDER BY updated_at ASC, id ASC
        LIMIT %s
    """

    with database_cursor() as (_, cursor):
        cursor.execute(query, (limit,))
        return list(cursor.fetchall())


def mark_processing(opportunity_id: int) -> None:
    with database_cursor() as (_, cursor):
        cursor.execute(
            """
            UPDATE opportunities
            SET processing_status = 'processing',
                processing_error = NULL,
                updated_at = NOW()
            WHERE id = %s
            """,
            (opportunity_id,),
        )


def save_enrichment(
    opportunity_id: int,
    enrichment: OpportunityEnrichment,
    prompt_version: str,
) -> None:
    with database_cursor() as (_, cursor):
        cursor.execute(
            """
            UPDATE opportunities
            SET
                summary = %s,
                skills = %s,
                category = %s,
                work_mode = %s,
                eligibility = %s,
                deadline = %s,
                processing_status = 'completed',
                processing_error = NULL,
                processed_at = NOW(),
                prompt_version = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                enrichment.summary,
                Json(enrichment.skills),
                enrichment.category,
                enrichment.work_mode,
                enrichment.eligibility,
                enrichment.deadline,
                prompt_version,
                opportunity_id,
            ),
        )


def mark_processing_failed(opportunity_id: int, message: str) -> None:
    with database_cursor() as (_, cursor):
        cursor.execute(
            """
            UPDATE opportunities
            SET processing_status = 'failed',
                processing_error = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (message[:2000], opportunity_id),
        )


def search_opportunities(
    *,
    query_text: str | None = None,
    category: str | None = None,
    skill: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    saved_only: bool = False,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    clauses = ["processing_status = 'completed'"]
    params: list[Any] = []

    if query_text:
        clauses.append(
            """
            (
                title ILIKE %s
                OR organization ILIKE %s
                OR COALESCE(summary, '') ILIKE %s
                OR COALESCE(description, '') ILIKE %s
            )
            """
        )
        pattern = f"%{query_text}%"
        params.extend([pattern, pattern, pattern, pattern])

    if category:
        clauses.append("category = %s")
        params.append(category)

    if skill:
        clauses.append("skills ? %s")
        params.append(skill)

    if location:
        clauses.append("COALESCE(location, '') ILIKE %s")
        params.append(f"%{location}%")

    if work_mode:
        clauses.append("work_mode = %s")
        params.append(work_mode)

    if saved_only:
        clauses.append("is_saved = TRUE")

    where_sql = " AND ".join(clauses)
    offset = (page - 1) * limit

    count_query = f"SELECT COUNT(*) AS total FROM opportunities WHERE {where_sql}"
    data_query = f"""
        SELECT
            id,
            title,
            organization,
            summary,
            skills,
            category,
            location,
            work_mode,
            eligibility,
            deadline,
            source,
            source_url,
            posted_date,
            is_saved
        FROM opportunities
        WHERE {where_sql}
        ORDER BY posted_date DESC NULLS LAST, created_at DESC
        LIMIT %s OFFSET %s
    """

    with database_cursor() as (_, cursor):
        cursor.execute(count_query, params)
        total = int(cursor.fetchone()["total"])

        cursor.execute(data_query, [*params, limit, offset])
        items = list(cursor.fetchall())

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
    }


def set_saved(opportunity_id: int, saved: bool) -> bool:
    with database_cursor() as (_, cursor):
        cursor.execute(
            """
            UPDATE opportunities
            SET is_saved = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING is_saved
            """,
            (saved, opportunity_id),
        )
        row = cursor.fetchone()

    if row is None:
        raise LookupError("Opportunity not found.")

    return bool(row["is_saved"])


def get_filter_values() -> dict[str, list[str]]:
    with database_cursor() as (_, cursor):
        cursor.execute(
            """
            SELECT DISTINCT category
            FROM opportunities
            WHERE category IS NOT NULL
            ORDER BY category
            """
        )
        categories = [row["category"] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT DISTINCT work_mode
            FROM opportunities
            WHERE work_mode IS NOT NULL
            ORDER BY work_mode
            """
        )
        work_modes = [row["work_mode"] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT DISTINCT jsonb_array_elements_text(skills) AS skill
            FROM opportunities
            WHERE jsonb_typeof(skills) = 'array'
            ORDER BY skill
            LIMIT 500
            """
        )
        skills = [row["skill"] for row in cursor.fetchall()]

    return {
        "categories": categories,
        "work_modes": work_modes,
        "skills": skills,
    }
