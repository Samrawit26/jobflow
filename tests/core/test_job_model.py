"""
Unit tests for job_model.py

Tests the canonical Job domain model with normalization and fingerprinting.
"""

import pytest

from jobflow.app.core.job_model import JobPosting


def test_job_posting_creation_basic():
    """Test basic JobPosting creation with required fields."""
    job = JobPosting(
        title="Software Engineer",
        company="Tech Corp",
        location="San Francisco, CA",
        description="Build amazing software",
        requirements=["Python", "AWS"],
    )

    assert job.title == "Software Engineer"
    assert job.company == "Tech Corp"
    assert job.location == "San Francisco, CA"
    assert job.description == "Build amazing software"
    assert job.requirements == ["Python", "AWS"]
    assert job.url is None
    assert job.source is None
    assert job.tags == []


def test_from_raw_normalizes_alternative_keys():
    """Test from_raw handles alternative key names."""
    raw = {
        "job_title": "Data Scientist",  # alternative to "title"
        "employer": "AI Inc",  # alternative to "company"
        "job_location": "Remote",  # alternative to "location"
        "job_description": "Analyze data",  # alternative to "description"
        "skills": ["Python", "ML"],  # alternative to "requirements"
        "apply_url": "https://example.com/apply",  # alternative to "url"
        "provider": "linkedin",  # alternative to "source"
        "date_posted": "2025-01-15",  # alternative to "posted_date"
    }

    job = JobPosting.from_raw(raw)

    assert job.title == "Data Scientist"
    assert job.company == "AI Inc"
    assert job.location == "Remote"
    assert job.description == "Analyze data"
    assert job.requirements == ["Python", "ML"]
    assert job.url == "https://example.com/apply"
    assert job.source == "linkedin"
    assert job.posted_date == "2025-01-15"


def test_from_raw_normalizes_strings_with_whitespace():
    """Test that from_raw strips whitespace from string fields."""
    raw = {
        "title": "  Software Engineer  ",
        "company": "\nTech Corp\t",
        "location": "  San Francisco  ",
        "description": "  Build software  ",
    }

    job = JobPosting.from_raw(raw)

    assert job.title == "Software Engineer"
    assert job.company == "Tech Corp"
    assert job.location == "San Francisco"
    assert job.description == "Build software"


def test_from_raw_requirements_from_string_newlines():
    """Test requirements parsing from string with newlines."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "requirements": "Python\nAWS\nDocker\n\nKubernetes",
    }

    job = JobPosting.from_raw(raw)

    assert job.requirements == ["Python", "AWS", "Docker", "Kubernetes"]


def test_from_raw_requirements_from_string_semicolons():
    """Test requirements parsing from string with semicolons."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "requirements": "Python; AWS; Docker; Kubernetes",
    }

    job = JobPosting.from_raw(raw)

    assert job.requirements == ["Python", "AWS", "Docker", "Kubernetes"]


def test_from_raw_requirements_from_list():
    """Test requirements parsing from list."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "requirements": ["  Python  ", "AWS", "", "Docker"],
    }

    job = JobPosting.from_raw(raw)

    # Should strip whitespace and remove empty items
    assert job.requirements == ["Python", "AWS", "Docker"]


def test_from_raw_requirements_missing():
    """Test requirements defaults to empty list when missing."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
    }

    job = JobPosting.from_raw(raw)

    assert job.requirements == []


def test_from_raw_salary_from_integers():
    """Test salary parsing from integer values."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "salary_min": 80000,
        "salary_max": 120000,
        "currency": "USD",
    }

    job = JobPosting.from_raw(raw)

    assert job.salary_min == 80000.0
    assert job.salary_max == 120000.0
    assert job.currency == "USD"


def test_from_raw_salary_from_floats():
    """Test salary parsing from float values."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "salary_min": 80000.5,
        "salary_max": 120000.75,
        "currency": "USD",
    }

    job = JobPosting.from_raw(raw)

    assert job.salary_min == 80000.5
    assert job.salary_max == 120000.75


def test_from_raw_salary_from_string_with_dollar():
    """Test salary parsing from string like '$80,000'."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "salary_min": "$80,000",
        "salary_max": "$120,000",
        "currency": "USD",
    }

    job = JobPosting.from_raw(raw)

    assert job.salary_min == 80000.0
    assert job.salary_max == 120000.0


def test_from_raw_salary_from_string_with_euro():
    """Test salary parsing from string like '€75,000'."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "Berlin",
        "description": "Work",
        "salary_min": "€75,000",
        "salary_max": "€95,000",
        "currency": "EUR",
    }

    job = JobPosting.from_raw(raw)

    assert job.salary_min == 75000.0
    assert job.salary_max == 95000.0
    assert job.currency == "EUR"


def test_from_raw_salary_from_nested_dict():
    """Test salary parsing from nested salary_range dict."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "salary_range": {"min": 80000, "max": 120000, "currency": "USD"},
    }

    job = JobPosting.from_raw(raw)

    assert job.salary_min == 80000.0
    assert job.salary_max == 120000.0
    assert job.currency == "USD"


def test_from_raw_salary_nested_overrides_direct():
    """Test that nested salary_range takes precedence over direct keys."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "salary_min": 50000,
        "salary_max": 60000,
        "salary_range": {"min": 80000, "max": 120000, "currency": "USD"},
    }

    job = JobPosting.from_raw(raw)

    # Nested should win
    assert job.salary_min == 80000.0
    assert job.salary_max == 120000.0


def test_from_raw_tags_from_string():
    """Test tags parsing from comma-separated string."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "tags": "Python, AWS, Remote, python",  # duplicate "python"
    }

    job = JobPosting.from_raw(raw)

    # Should lowercase, trim, and deduplicate
    assert job.tags == ["python", "aws", "remote"]


def test_from_raw_tags_from_list():
    """Test tags parsing from list."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "tags": ["Python", "AWS", "  Remote  ", "PYTHON"],
    }

    job = JobPosting.from_raw(raw)

    # Should lowercase, trim, and deduplicate (preserving first occurrence)
    assert job.tags == ["python", "aws", "remote"]


def test_from_raw_tags_preserves_first_occurrence_order():
    """Test that tags deduplication preserves first occurrence."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "tags": ["zebra", "apple", "Zebra", "banana", "APPLE"],
    }

    job = JobPosting.from_raw(raw)

    # First occurrence order preserved
    assert job.tags == ["zebra", "apple", "banana"]


def test_from_raw_tags_missing():
    """Test tags defaults to empty list when missing."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
    }

    job = JobPosting.from_raw(raw)

    assert job.tags == []


def test_from_raw_employment_type():
    """Test employment_type normalization."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "employment_type": "  full-time  ",
    }

    job = JobPosting.from_raw(raw)

    assert job.employment_type == "full-time"


def test_from_raw_remote_boolean():
    """Test remote field as boolean."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "remote": True,
    }

    job = JobPosting.from_raw(raw)

    assert job.remote is True


def test_from_raw_remote_truthy():
    """Test remote field coerces truthy values to bool."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "remote": 1,
    }

    job = JobPosting.from_raw(raw)

    assert job.remote is True


def test_from_raw_stores_raw_input():
    """Test that from_raw stores original raw input."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
        "custom_field": "custom_value",
    }

    job = JobPosting.from_raw(raw)

    assert job.raw is raw
    assert job.raw["custom_field"] == "custom_value"


def test_to_dict_excludes_raw_when_none():
    """Test that to_dict excludes 'raw' key when raw is None."""
    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
        raw=None,
    )

    result = job.to_dict()

    assert "raw" not in result


def test_to_dict_includes_raw_when_not_none():
    """Test that to_dict includes 'raw' key when raw is not None."""
    raw = {"title": "Engineer", "custom": "value"}
    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
        raw=raw,
    )

    result = job.to_dict()

    assert "raw" in result
    assert result["raw"] == raw


def test_to_dict_defensive_copy_requirements():
    """Test that to_dict returns defensive copy of requirements."""
    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python", "AWS"],
    )

    result = job.to_dict()

    # Modify returned list
    result["requirements"].append("Docker")

    # Original should be unchanged
    assert job.requirements == ["Python", "AWS"]


def test_to_dict_defensive_copy_tags():
    """Test that to_dict returns defensive copy of tags."""
    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=[],
        tags=["python", "aws"],
    )

    result = job.to_dict()

    # Modify returned list
    result["tags"].append("docker")

    # Original should be unchanged
    assert job.tags == ["python", "aws"]


def test_fingerprint_is_deterministic():
    """Test that same job produces same fingerprint."""
    job1 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python", "AWS"],
        salary_min=80000.0,
        salary_max=120000.0,
        currency="USD",
        tags=["python", "remote"],
    )

    job2 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python", "AWS"],
        salary_min=80000.0,
        salary_max=120000.0,
        currency="USD",
        tags=["python", "remote"],
    )

    assert job1.fingerprint() == job2.fingerprint()


def test_fingerprint_changes_with_content():
    """Test that changing meaningful field changes fingerprint."""
    job1 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
    )

    job2 = JobPosting(
        title="Senior Engineer",  # Different title
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
    )

    assert job1.fingerprint() != job2.fingerprint()


def test_fingerprint_excludes_raw():
    """Test that raw field does NOT affect fingerprint."""
    job1 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
        raw={"custom": "value1"},
    )

    job2 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
        raw={"custom": "value2"},  # Different raw
    )

    job3 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
        raw=None,  # No raw
    )

    # All should have same fingerprint despite different raw
    assert job1.fingerprint() == job2.fingerprint()
    assert job1.fingerprint() == job3.fingerprint()


def test_fingerprint_format():
    """Test that fingerprint is 64-character hex string (SHA-256)."""
    job = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python"],
    )

    fp = job.fingerprint()

    assert isinstance(fp, str)
    assert len(fp) == 64
    # Should be valid hex
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_requirements_order_matters():
    """Test that requirements order affects fingerprint."""
    job1 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["Python", "AWS"],
    )

    job2 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=["AWS", "Python"],  # Different order
    )

    # Different order should produce different fingerprint
    assert job1.fingerprint() != job2.fingerprint()


def test_fingerprint_excludes_provenance_fields():
    """Test that provenance fields (source, url, posted_date, tags) do NOT affect fingerprint."""
    job1 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=[],
        source="linkedin",
        url="https://linkedin.com/job1",
        posted_date="2025-01-01",
        tags=["python", "aws"],
    )

    job2 = JobPosting(
        title="Engineer",
        company="Corp",
        location="NYC",
        description="Work",
        requirements=[],
        source="indeed",  # Different source
        url="https://indeed.com/job2",  # Different URL
        posted_date="2025-01-15",  # Different date
        tags=["java", "docker"],  # Different tags
    )

    # Should have same fingerprint despite different provenance
    assert job1.fingerprint() == job2.fingerprint()


def test_from_raw_missing_optional_fields():
    """Test from_raw with only required fields."""
    raw = {
        "title": "Engineer",
        "company": "Corp",
        "location": "NYC",
        "description": "Work",
    }

    job = JobPosting.from_raw(raw)

    assert job.title == "Engineer"
    assert job.company == "Corp"
    assert job.location == "NYC"
    assert job.description == "Work"
    assert job.requirements == []
    assert job.url is None
    assert job.source is None
    assert job.posted_date is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.currency is None
    assert job.employment_type is None
    assert job.remote is None
    assert job.tags == []


def test_from_raw_empty_strings_normalized():
    """Test that empty strings are normalized to empty string (not None)."""
    raw = {
        "title": "",
        "company": "",
        "location": "",
        "description": "",
    }

    job = JobPosting.from_raw(raw)

    # Required fields should be empty strings, not None
    assert job.title == ""
    assert job.company == ""
    assert job.location == ""
    assert job.description == ""


def test_from_raw_comprehensive():
    """Test from_raw with all fields populated."""
    raw = {
        "title": "Senior Software Engineer",
        "company": "Tech Corp",
        "location": "San Francisco, CA",
        "description": "Build amazing products",
        "requirements": ["Python", "AWS", "Docker"],
        "url": "https://example.com/jobs/123",
        "source": "linkedin",
        "posted_date": "2025-01-15",
        "salary_min": 120000,
        "salary_max": 180000,
        "currency": "USD",
        "employment_type": "full-time",
        "remote": True,
        "tags": ["python", "backend", "remote"],
    }

    job = JobPosting.from_raw(raw)

    assert job.title == "Senior Software Engineer"
    assert job.company == "Tech Corp"
    assert job.location == "San Francisco, CA"
    assert job.description == "Build amazing products"
    assert job.requirements == ["Python", "AWS", "Docker"]
    assert job.url == "https://example.com/jobs/123"
    assert job.source == "linkedin"
    assert job.posted_date == "2025-01-15"
    assert job.salary_min == 120000.0
    assert job.salary_max == 180000.0
    assert job.currency == "USD"
    assert job.employment_type == "full-time"
    assert job.remote is True
    assert job.tags == ["python", "backend", "remote"]
    assert job.raw == raw
