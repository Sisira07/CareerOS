from models import NormalizedJob, OpportunityEnrichment


def test_normalized_job():
    job = NormalizedJob(
        external_id="123",
        title="Software Engineer",
        organization="Example",
        description="Build reliable services.",
        source="greenhouse",
        source_url="https://example.com/jobs/123",
    )

    assert job.title == "Software Engineer"
    assert job.work_mode == "Unspecified"


def test_enrichment_deduplicates_skills():
    enrichment = OpportunityEnrichment(
        summary=(
            "This role develops reliable backend services. "
            "It collaborates with product and infrastructure teams."
        ),
        skills=["Python", "python", " SQL "],
        category="Software Development",
        work_mode="Hybrid",
    )

    assert enrichment.skills == ["Python", "SQL"]
