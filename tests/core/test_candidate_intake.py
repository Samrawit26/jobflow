"""
Unit tests for candidate_intake.py

Tests the deterministic parsing of candidate application Excel files.
"""

from pathlib import Path

import pytest

from jobflow.app.core.candidate_intake import (
    parse_application_info_xlsx,
    _extract_skill_name,
    _extract_years,
)


@pytest.fixture
def sample_application_path():
    """Path to sample application fixture."""
    return Path(__file__).parent.parent / "fixtures" / "sample_application.xlsx"


def test_parse_application_basic_info(sample_application_path):
    """Test extraction of basic personal information."""
    profile = parse_application_info_xlsx(sample_application_path)

    assert profile["first_name"] == "John"
    assert profile["last_name"] == "Doe"
    assert profile["email"] == "john.doe@example.com"
    assert profile["phone"] == "+1-555-123-4567"


def test_parse_application_address_and_country(sample_application_path):
    """Test extraction of address and country."""
    profile = parse_application_info_xlsx(sample_application_path)

    assert profile["address"] == "123 Main St, Anytown, CA 12345"
    assert profile["country"] == "United States"


def test_parse_application_work_authorization(sample_application_path):
    """Test extraction of work authorization/citizenship."""
    profile = parse_application_info_xlsx(sample_application_path)

    assert profile["work_authorization"] == "US Citizen"


def test_parse_application_education(sample_application_path):
    """Test extraction of education level."""
    profile = parse_application_info_xlsx(sample_application_path)

    assert profile["education_level"] == "Bachelor's Degree"


def test_parse_application_skills_years(sample_application_path):
    """Test extraction of skills with years of experience."""
    profile = parse_application_info_xlsx(sample_application_path)

    skills = profile["skills_years"]

    # Verify at least 3 skills extracted
    assert len(skills) >= 3

    # Verify specific skills
    assert "Python" in skills
    assert skills["Python"] == 5

    assert "Java" in skills
    assert skills["Java"] == 3

    assert "Sql" in skills or "SQL" in skills
    # Handle case variations
    sql_years = skills.get("Sql") or skills.get("SQL")
    assert sql_years == 7


def test_parse_application_decimal_years(sample_application_path):
    """Test extraction of decimal years (e.g., 2.5)."""
    profile = parse_application_info_xlsx(sample_application_path)

    skills = profile["skills_years"]

    assert "Machine Learning" in skills
    assert skills["Machine Learning"] == 2.5


def test_parse_application_resilient_to_blank_rows(sample_application_path):
    """Test that parser handles blank rows without errors."""
    # Should not raise any exceptions
    profile = parse_application_info_xlsx(sample_application_path)

    # Basic sanity check
    assert profile["first_name"] == "John"


def test_parse_application_resilient_to_section_headers(sample_application_path):
    """Test that parser ignores section headers like 'PERSONAL INFORMATION'."""
    profile = parse_application_info_xlsx(sample_application_path)

    # Section headers should not appear as field values
    assert profile["first_name"] != "PERSONAL INFORMATION"
    assert profile["email"] != "CONTACT DETAILS"


def test_parse_application_missing_file():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        parse_application_info_xlsx("nonexistent.xlsx")

    assert "not found" in str(exc_info.value)


def test_parse_application_returns_all_required_keys(sample_application_path):
    """Test that result contains all required keys."""
    profile = parse_application_info_xlsx(sample_application_path)

    required_keys = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "address",
        "country",
        "work_authorization",
        "education_level",
        "skills_years"
    ]

    for key in required_keys:
        assert key in profile


def test_extract_skill_name():
    """Test skill name extraction from various question formats."""
    # Standard format
    assert _extract_skill_name("How many years of Python experience do you have?") == "Python"

    # Variation with "with"
    assert _extract_skill_name("Years of experience with Java?") == "Java"

    # Variation with "in"
    assert _extract_skill_name("How many years of experience in SQL?") == "Sql"

    # Multi-word skill
    skill = _extract_skill_name("How many years of Machine Learning experience do you have?")
    assert "Machine" in skill or "Learning" in skill


def test_extract_years_from_number():
    """Test years extraction from direct numbers."""
    assert _extract_years(5) == 5
    assert _extract_years(3.5) == 3.5
    assert _extract_years(0) == 0


def test_extract_years_from_string():
    """Test years extraction from string values."""
    assert _extract_years("5") == 5
    assert _extract_years("3.5") == 3.5
    assert _extract_years("5 years") == 5
    assert _extract_years("3.5 years") == 3.5


def test_extract_years_from_range():
    """Test years extraction from ranges."""
    # Should take midpoint
    result = _extract_years("3-5 years")
    assert result == 4.0  # (3+5)/2

    result = _extract_years("1-3")
    assert result == 2.0


def test_extract_years_returns_none_for_invalid():
    """Test that invalid inputs return None."""
    assert _extract_years(None) is None
    assert _extract_years("") is None
    assert _extract_years("no experience") is None
    assert _extract_years("N/A") is None


def test_parse_application_fast_execution(sample_application_path):
    """Test that parsing is fast (< 1 second for local execution)."""
    import time

    start = time.time()
    parse_application_info_xlsx(sample_application_path)
    elapsed = time.time() - start

    # Should be very fast for a small file
    assert elapsed < 1.0, f"Parsing took {elapsed:.2f}s, expected < 1s"
