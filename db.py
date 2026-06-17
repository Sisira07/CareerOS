import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname="careeros",
        user="postgres",
        password=os.getenv("DB_PASSWORD"),
        host="localhost"
    )

def save_job(job):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO opportunities (title, organization, description, location, source, source_url, posted_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_url) DO NOTHING
    """, (
        job["title"], job["organization"], job["description"],
        job["location"], job["source"], job["source_url"], job["posted_date"]
    ))
    conn.commit()
    cur.close()
    conn.close()