import requests
from normalizer import normalize_greenhouse
from db import save_job

companies = [
    {"name": "Stripe", "board_token": "stripe"},
    {"name": "Airbnb", "board_token": "airbnb"},
]

def fetch_jobs(board_token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    response = requests.get(url)
    return response.json().get("jobs", [])

def run_ingestion():
    for company in companies:
        jobs = fetch_jobs(company["board_token"])
        print(f"{company['name']}: {len(jobs)} jobs fetched")
        for job in jobs:
            normalized = normalize_greenhouse(job)
            save_job(normalized)

if __name__ == "__main__":
    run_ingestion()