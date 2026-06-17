from fastapi import FastAPI
from db import get_connection

app = FastAPI()

@app.get("/opportunities")
def get_opportunities():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, organization, location, source, source_url FROM opportunities ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"title": r[0], "organization": r[1], "location": r[2], "source": r[3], "source_url": r[4]}
        for r in rows
    ]