# CareerOS Multi-Board Pipeline

This project refactors a single Greenhouse collector into a reusable
multi-board pipeline.

Link to the website: https://career-esvsz7ru2-lane-asade.vercel.app/

## Supported adapters

- Greenhouse
- Lever
- Ashby
- SmartRecruiters
- Workable
- Recruitee
- BambooHR
- Generic JSON-LD `JobPosting` pages

Each adapter is one Python file under `boards/`. Every adapter returns the same
`NormalizedJob` model. Shared PostgreSQL, Gemini enrichment, search/filter API,
and UI logic remain centralized instead of being copied into every adapter.

## Pipeline

```text
Job-board API
    -> board adapter
    -> NormalizedJob validation
    -> PostgreSQL upsert
    -> Gemini structured enrichment
    -> FastAPI search/filter/save API
    -> browser UI
```

## 1. Create and activate an environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure PostgreSQL and Gemini

```powershell
Copy-Item .env.example .env
Copy-Item boards.example.json boards.json
```

Edit `.env` and `boards.json`.

## 3. Apply the database schema

```powershell
psql -U postgres -d careeros -f schema.sql
```

The schema is compatible with the earlier `opportunities` table and adds the
columns needed for Gemini enrichment and saved opportunities.

## 4. Configure boards

`boards.json` is a list. Enable only adapters with valid board identifiers or
credentials.

Public adapters normally do not need credentials:

- Greenhouse
- Lever
- Ashby
- Recruitee
- Generic JSON-LD
- Workable public careers endpoint

Some configurations may require credentials:

- SmartRecruiters
- Workable SPI
- BambooHR

Secret values can reference environment variables:

```json
{
  "api_key": "env:SMARTRECRUITERS_API_KEY"
}
```

## 5. Ingest opportunities

Run every enabled board:

```powershell
python ingest.py
```

Run one adapter:

```powershell
python ingest.py --board greenhouse
```

Ingest and then process 20 records with Gemini:

```powershell
python ingest.py --process --process-limit 20
```

## 6. Run Gemini enrichment separately

```powershell
python gemini_pipeline.py --limit 20
```

Gemini returns schema-constrained JSON, and Pydantic validates the response
before it is saved.

Generated fields:

- summary
- skills
- category
- work mode
- eligibility
- deadline

## 7. Start the API and UI

```powershell
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The UI includes:

- text search
- category filter
- skill filter
- work-mode filter
- extracted summary and skill display
- save/unsave opportunity
- saved-only view

## Adding another board

Create one file under `boards/` with:

```python
def fetch(config: dict) -> list[NormalizedJob]:
    ...
```

Then register it in `boards/__init__.py`.

## Important coverage note

No implementation can safely ingest literally every job board through one
method. Large marketplaces such as LinkedIn, Indeed, and Naukri do not provide
the same unrestricted public job-feed APIs as the supported ATS platforms.
Use their approved partner APIs, licensed feeds, or user-authorized exports
rather than scraping protected pages.
