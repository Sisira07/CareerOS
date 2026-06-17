def normalize_greenhouse(job):
    return {
        "title": job.get("title", "").strip(),
        "organization": job.get("company_name", "Unknown"),
        "description": "",  # not in list endpoint — fetch separately if needed
        "location": job.get("location", {}).get("name", "Unknown"),
        "source": "greenhouse",
        "source_url": job.get("absolute_url", ""),
        "posted_date": job.get("updated_at"),
    }