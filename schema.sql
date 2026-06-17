CREATE TABLE opportunities (
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