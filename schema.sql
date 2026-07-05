CREATE TABLE IF NOT EXISTS opportunities (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    organization TEXT NOT NULL,
    description TEXT,
    location TEXT,
    source TEXT,
    source_url TEXT UNIQUE,
    posted_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS external_id TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS summary TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS skills JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS category TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS work_mode TEXT NOT NULL DEFAULT 'Unspecified';

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS eligibility TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS deadline DATE;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS processing_status TEXT NOT NULL DEFAULT 'pending';

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS processing_error TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS prompt_version TEXT;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS is_saved BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE opportunities
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_source_external_id
ON opportunities(source, external_id)
WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_opportunities_category
ON opportunities(category);

CREATE INDEX IF NOT EXISTS idx_opportunities_work_mode
ON opportunities(work_mode);

CREATE INDEX IF NOT EXISTS idx_opportunities_saved
ON opportunities(is_saved);

CREATE INDEX IF NOT EXISTS idx_opportunities_skills
ON opportunities USING GIN(skills);

CREATE INDEX IF NOT EXISTS idx_opportunities_processing_status
ON opportunities(processing_status);
