"""
Unit tests for job_matcher.py

Tests deterministic candidate-to-job matching with dimension scoring.
"""

import pytest

from jobflow.app.core.job_matcher import match_job
from jobflow.app.core.job_model import JobPosting


def test_match_job_perfect_match():
    """Test perfect match scenario."""
    candidate = {
        "email": "jane@example.com",
        "skills": ["Python", "AWS", "Docker"],
        "desired_titles": ["Backend Engineer"],
        "years_experience": 5,
        "preferred_locations": ["San Francisco"],
        "remote_ok": False,
    }

    job = JobPosting(
        title="Backend Engineer",
        company="Tech Corp",
        location="San Francisco",
        description="Build scalable systems with Python and AWS",
        requirements=["Python", "AWS", "Docker"],
        salary_min=120000,
        salary_max=160000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job1",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should be strong fit
    assert result.decision == "strong_fit"
    assert result.overall_score >= 80
    assert result.candidate_id == "jane@example.com"
    assert result.job_fingerprint == job.fingerprint()

    # All dimensions should be high
    assert result.dimension_scores["skills_overlap"] >= 90
    assert result.dimension_scores["title_alignment"] >= 80
    assert result.dimension_scores["location_alignment"] == 100

    # Should have matched keywords
    assert "python" in result.matched_keywords
    assert "aws" in result.matched_keywords
    assert "docker" in result.matched_keywords

    # Should have reasons
    assert len(result.reasons) <= 3
    assert len(result.reasons) >= 1


def test_match_job_no_keyword_overlap():
    """Test match with minimal keyword overlap."""
    candidate = {
        "email": "john@example.com",
        "skills": ["Java", "Spring", "MySQL"],
        "desired_titles": ["Java Developer"],
    }

    job = JobPosting(
        title="Python Developer",
        company="Startup",
        location="Remote",
        description="Python backend development",
        requirements=["Python", "Django", "PostgreSQL"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=True,
        source="test",
        url="https://example.com/job2",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should be reject
    assert result.decision == "reject"
    assert result.overall_score < 45

    # Skills overlap should be low
    assert result.dimension_scores["skills_overlap"] < 30

    # Should have very few matched keywords (may match on generic terms like "developer")
    assert len(result.matched_keywords) <= 1

    # Should have missing keywords
    assert "python" in result.missing_keywords


def test_match_job_partial_overlap():
    """Test match with partial keyword overlap."""
    candidate = {
        "email": "alice@example.com",
        "skills": ["Python", "SQL", "Excel"],
        "desired_titles": ["Data Analyst"],
        "years_experience": 3,
    }

    job = JobPosting(
        title="Data Analyst",
        company="Corp",
        location="NYC",
        description="Analyze data with Python and SQL",
        requirements=["Python", "SQL", "Tableau", "Power BI"],
        salary_min=80000,
        salary_max=100000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job3",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should be possible_fit or weak_fit
    assert result.decision in {"possible_fit", "weak_fit"}
    assert 45 <= result.overall_score < 80

    # Some skills should overlap
    assert result.dimension_scores["skills_overlap"] > 0
    assert "python" in result.matched_keywords
    assert "sql" in result.matched_keywords

    # Some skills missing
    assert "tableau" in result.missing_keywords or "powerbi" in result.missing_keywords


def test_match_job_remote_alignment():
    """Test remote preference alignment."""
    candidate = {
        "email": "remote@example.com",
        "skills": ["Python"],
        "remote_ok": True,
        "preferred_locations": ["Remote"],
    }

    job = JobPosting(
        title="Engineer",
        company="RemoteCo",
        location="Remote",
        description="Work remotely",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=True,
        source="test",
        url="https://example.com/job4",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Location score should be perfect
    assert result.dimension_scores["location_alignment"] == 100.0


def test_match_job_remote_mismatch():
    """Test remote preference mismatch."""
    candidate = {
        "email": "onsite@example.com",
        "skills": ["Python"],
        "remote_ok": False,
        "preferred_locations": ["San Francisco"],
    }

    job = JobPosting(
        title="Engineer",
        company="RemoteCo",
        location="Remote",
        description="Work remotely",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=True,
        source="test",
        url="https://example.com/job5",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Location score should be low
    assert result.dimension_scores["location_alignment"] == 0.0


def test_match_job_seniority_junior_match():
    """Test junior candidate matching junior role."""
    candidate = {
        "email": "junior@example.com",
        "skills": ["Python"],
        "years_experience": 1,
    }

    job = JobPosting(
        title="Junior Python Developer",
        company="Startup",
        location="SF",
        description="Entry level position",
        requirements=["Python"],
        salary_min=70000,
        salary_max=90000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job6",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Seniority should align
    assert result.dimension_scores["seniority_alignment"] == 100.0


def test_match_job_seniority_senior_match():
    """Test senior candidate matching senior role."""
    candidate = {
        "email": "senior@example.com",
        "skills": ["Python"],
        "years_experience": 8,
    }

    job = JobPosting(
        title="Senior Python Developer",
        company="BigCo",
        location="NYC",
        description="Lead development",
        requirements=["Python"],
        salary_min=150000,
        salary_max=200000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job7",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Seniority should align
    assert result.dimension_scores["seniority_alignment"] == 100.0


def test_match_job_seniority_mismatch_overqualified():
    """Test overqualified candidate for junior role."""
    candidate = {
        "email": "overqualified@example.com",
        "skills": ["Python"],
        "years_experience": 10,
    }

    job = JobPosting(
        title="Junior Developer",
        company="Startup",
        location="SF",
        description="Entry level",
        requirements=["Python"],
        salary_min=70000,
        salary_max=90000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job8",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Seniority should be penalized
    assert result.dimension_scores["seniority_alignment"] < 50


def test_match_job_seniority_mismatch_underqualified():
    """Test underqualified candidate for senior role."""
    candidate = {
        "email": "underqualified@example.com",
        "skills": ["Python"],
        "years_experience": 1,
    }

    job = JobPosting(
        title="Senior Developer",
        company="BigCo",
        location="NYC",
        description="Lead team",
        requirements=["Python"],
        salary_min=150000,
        salary_max=200000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job9",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Seniority should be penalized
    assert result.dimension_scores["seniority_alignment"] < 40


def test_match_job_title_alignment_exact():
    """Test exact title match."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
        "desired_titles": ["Backend Engineer"],
    }

    job = JobPosting(
        title="Backend Engineer",
        company="Corp",
        location="SF",
        description="Build systems",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job10",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Title alignment should be high
    assert result.dimension_scores["title_alignment"] >= 80


def test_match_job_title_alignment_partial():
    """Test partial title match."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
        "desired_titles": ["Software Engineer"],
    }

    job = JobPosting(
        title="Backend Engineer",
        company="Corp",
        location="SF",
        description="Build systems",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job11",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Title alignment should be moderate (both have "engineer")
    assert result.dimension_scores["title_alignment"] > 0


def test_match_job_candidate_id_from_email():
    """Test candidate ID extracted from email."""
    candidate = {
        "email": "jane@example.com",
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job12",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    assert result.candidate_id == "jane@example.com"


def test_match_job_candidate_id_from_name():
    """Test candidate ID fallback to name."""
    candidate = {
        "full_name": "Jane Doe",
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job13",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    assert result.candidate_id == "Jane Doe"


def test_match_job_candidate_id_unknown():
    """Test candidate ID fallback to unknown."""
    candidate = {
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job14",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    assert result.candidate_id == "unknown_candidate"


def test_match_job_skills_from_skills_years():
    """Test skills extraction from skills_years dict."""
    candidate = {
        "email": "test@example.com",
        "skills_years": {"Python": 5, "AWS": 3, "Docker": 2},
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work with Python and AWS",
        requirements=["Python", "AWS"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job15",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should match skills from skills_years
    assert "python" in result.matched_keywords
    assert "aws" in result.matched_keywords


def test_match_job_keywords_normalized():
    """Test that keywords are normalized properly."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python", "AWS", "C++", "Node.js"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work with python, aws, c++, nodejs",
        requirements=["PYTHON", "aws", "C++", "Node.js"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job16",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should normalize and match despite case/punctuation differences
    assert "python" in result.matched_keywords
    assert "aws" in result.matched_keywords
    assert "c++" in result.matched_keywords or "c" in result.matched_keywords


def test_match_job_resume_text_keywords():
    """Test keyword extraction from resume text."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
        "resume_text": "Experienced with AWS, Docker, and Kubernetes. Built REST APIs with FastAPI.",
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work with AWS and Docker",
        requirements=["Python", "AWS", "Docker"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job17",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Should extract keywords from resume
    assert "aws" in result.matched_keywords
    assert "docker" in result.matched_keywords


def test_match_job_no_requirements():
    """Test matching when job has no requirements list."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Build things",
        requirements=[],  # No requirements list
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job18",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Skills score should be reasonable even with no explicit requirements
    # (keywords are still extracted from title/description)
    assert 0 <= result.dimension_scores["skills_overlap"] <= 100


def test_match_job_no_location_prefs():
    """Test location score when candidate has no preferences."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
        "preferred_locations": [],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job19",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Location score should be neutral
    assert result.dimension_scores["location_alignment"] == 50.0


def test_match_job_no_experience_info():
    """Test seniority score when candidate has no experience info."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job20",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Seniority score should be neutral
    assert result.dimension_scores["seniority_alignment"] == 50.0


def test_match_job_no_desired_titles():
    """Test title score when candidate has no desired titles."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
        "desired_titles": [],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job21",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Title score should be neutral
    assert result.dimension_scores["title_alignment"] == 50.0


def test_match_job_reasons_structure():
    """Test that reasons are structured correctly."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python", "AWS"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python", "AWS"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job22",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Reasons should be a list
    assert isinstance(result.reasons, list)
    # Should have 1-3 reasons
    assert 1 <= len(result.reasons) <= 3
    # Each reason should be a non-empty string
    for reason in result.reasons:
        assert isinstance(reason, str)
        assert len(reason) > 0


def test_match_job_meta_structure():
    """Test that meta dict has expected fields."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python"],
    }

    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="SF",
        description="Work",
        requirements=["Python"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job23",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    result = match_job(candidate, job)

    # Meta should have expected fields
    assert "candidate_keyword_count" in result.meta
    assert "job_keyword_count" in result.meta
    assert "overlap_count" in result.meta

    # All should be non-negative integers
    assert result.meta["candidate_keyword_count"] >= 0
    assert result.meta["job_keyword_count"] >= 0
    assert result.meta["overlap_count"] >= 0


def test_match_job_deterministic():
    """Test that matching is deterministic."""
    candidate = {
        "email": "test@example.com",
        "skills": ["Python", "AWS", "Docker"],
        "desired_titles": ["Backend Engineer"],
        "years_experience": 5,
    }

    job = JobPosting(
        title="Backend Engineer",
        company="Corp",
        location="SF",
        description="Build systems",
        requirements=["Python", "AWS"],
        salary_min=100000,
        salary_max=140000,
        currency="USD",
        employment_type="full-time",
        remote=False,
        source="test",
        url="https://example.com/job24",
        posted_date="2024-01-01",
        tags=[],
        raw={},
    )

    # Run matching twice
    result1 = match_job(candidate, job)
    result2 = match_job(candidate, job)

    # Results should be identical
    assert result1.overall_score == result2.overall_score
    assert result1.decision == result2.decision
    assert result1.dimension_scores == result2.dimension_scores
    assert result1.matched_keywords == result2.matched_keywords
    assert result1.missing_keywords == result2.missing_keywords
    assert result1.reasons == result2.reasons
