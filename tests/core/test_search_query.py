"""
Unit tests for search_query.py

Tests job search query building from candidate profiles.
"""

import pytest

from jobflow.app.core.search_query import build_job_query


def test_build_query_basic_candidate():
    """Test query building from complete candidate profile."""
    candidate = {
        "desired_title": "Software Engineer",
        "alternate_titles": ["Backend Engineer", "Python Developer"],
        "desired_locations": ["San Francisco", "New York"],
        "remote_ok": True,
        "skills_years": {"Python": 5, "AWS": 3, "Docker": 2},
        "employment_type": "full-time",
    }

    query = build_job_query(candidate)

    assert query["titles"] == [
        "Software Engineer",
        "Backend Engineer",
        "Python Developer",
    ]
    assert query["locations"] == ["San Francisco", "New York"]
    assert query["remote_ok"] is True
    assert query["keywords"] == ["Python", "AWS", "Docker"]
    assert query["employment_type"] == "full-time"


def test_build_query_missing_all_fields():
    """Test query building with empty candidate dict."""
    candidate = {}

    query = build_job_query(candidate)

    assert query["titles"] == []
    assert query["locations"] == []
    assert query["remote_ok"] is False
    assert query["keywords"] == []
    assert query["employment_type"] is None


def test_build_query_missing_optional_fields():
    """Test query building with only required fields."""
    candidate = {
        "desired_title": "Data Scientist",
        "skills_years": {"Python": 3, "SQL": 5},
    }

    query = build_job_query(candidate)

    assert query["titles"] == ["Data Scientist"]
    assert query["locations"] == []
    assert query["remote_ok"] is False
    assert query["keywords"] == ["Python", "SQL"]
    assert query["employment_type"] is None


def test_build_query_title_from_job_title_field():
    """Test that job_title field works as fallback."""
    candidate = {"job_title": "DevOps Engineer"}

    query = build_job_query(candidate)

    assert query["titles"] == ["DevOps Engineer"]


def test_build_query_title_from_title_field():
    """Test that title field works as fallback."""
    candidate = {"title": "Frontend Developer"}

    query = build_job_query(candidate)

    assert query["titles"] == ["Frontend Developer"]


def test_build_query_desired_title_takes_precedence():
    """Test that desired_title takes precedence over other title fields."""
    candidate = {
        "desired_title": "Senior Engineer",
        "job_title": "Engineer",
        "title": "Junior Engineer",
    }

    query = build_job_query(candidate)

    assert query["titles"] == ["Senior Engineer"]


def test_build_query_alternate_titles_as_string():
    """Test alternate titles from comma-separated string."""
    candidate = {
        "desired_title": "Software Engineer",
        "alternate_titles": "Backend Engineer, Python Developer, Full Stack Engineer",
    }

    query = build_job_query(candidate)

    assert query["titles"] == [
        "Software Engineer",
        "Backend Engineer",
        "Python Developer",
        "Full Stack Engineer",
    ]


def test_build_query_titles_deduplicate():
    """Test that duplicate titles are removed."""
    candidate = {
        "desired_title": "Software Engineer",
        "alternate_titles": ["software engineer", "Backend Engineer", "BACKEND ENGINEER"],
    }

    query = build_job_query(candidate)

    # Should deduplicate case-insensitively, keeping first occurrence
    assert len(query["titles"]) == 2
    assert query["titles"][0] == "Software Engineer"
    assert query["titles"][1] == "Backend Engineer"


def test_build_query_titles_strip_whitespace():
    """Test that titles have whitespace stripped."""
    candidate = {
        "desired_title": "  Software Engineer  ",
        "alternate_titles": ["  Backend Engineer  ", "  Python Developer  "],
    }

    query = build_job_query(candidate)

    assert query["titles"] == [
        "Software Engineer",
        "Backend Engineer",
        "Python Developer",
    ]


def test_build_query_locations_from_string():
    """Test locations from comma-separated string."""
    candidate = {"desired_locations": "San Francisco, New York, Remote"}

    query = build_job_query(candidate)

    assert query["locations"] == ["San Francisco", "New York", "Remote"]


def test_build_query_locations_from_list():
    """Test locations from list."""
    candidate = {"desired_locations": ["Boston", "Seattle", "Austin"]}

    query = build_job_query(candidate)

    assert query["locations"] == ["Boston", "Seattle", "Austin"]


def test_build_query_locations_from_locations_field():
    """Test that locations field works as fallback."""
    candidate = {"locations": ["Chicago", "Denver"]}

    query = build_job_query(candidate)

    assert query["locations"] == ["Chicago", "Denver"]


def test_build_query_locations_from_location_field():
    """Test that location field works as fallback."""
    candidate = {"location": "Portland"}

    query = build_job_query(candidate)

    assert query["locations"] == ["Portland"]


def test_build_query_locations_deduplicate():
    """Test that duplicate locations are removed."""
    candidate = {"desired_locations": ["San Francisco", "san francisco", "New York", "NEW YORK"]}

    query = build_job_query(candidate)

    # Should deduplicate case-insensitively
    assert len(query["locations"]) == 2
    assert "San Francisco" in query["locations"]
    assert "New York" in query["locations"]


def test_build_query_locations_strip_whitespace():
    """Test that locations have whitespace stripped."""
    candidate = {"desired_locations": "  San Francisco  ,  New York  "}

    query = build_job_query(candidate)

    assert query["locations"] == ["San Francisco", "New York"]


def test_build_query_remote_ok_true():
    """Test remote_ok with True value."""
    candidate = {"remote_ok": True}

    query = build_job_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_remote_ok_false():
    """Test remote_ok with False value."""
    candidate = {"remote_ok": False}

    query = build_job_query(candidate)

    assert query["remote_ok"] is False


def test_build_query_remote_ok_string_true():
    """Test remote_ok from string 'true'."""
    candidate = {"remote_ok": "true"}

    query = build_job_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_remote_ok_string_yes():
    """Test remote_ok from string 'yes'."""
    candidate = {"remote_ok": "yes"}

    query = build_job_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_remote_ok_defaults_false():
    """Test remote_ok defaults to False when missing."""
    candidate = {}

    query = build_job_query(candidate)

    assert query["remote_ok"] is False


def test_build_query_remote_preference_fallback():
    """Test that remote_preference field works as fallback."""
    candidate = {"remote_preference": True}

    query = build_job_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_keywords_from_skills():
    """Test keywords extraction from skills_years."""
    candidate = {
        "skills_years": {
            "Python": 5,
            "JavaScript": 3,
            "AWS": 2,
            "Docker": 1,
        }
    }

    query = build_job_query(candidate)

    assert len(query["keywords"]) == 4
    assert "Python" in query["keywords"]
    assert "JavaScript" in query["keywords"]
    assert "AWS" in query["keywords"]
    assert "Docker" in query["keywords"]


def test_build_query_keywords_empty_skills():
    """Test keywords with empty skills_years."""
    candidate = {"skills_years": {}}

    query = build_job_query(candidate)

    assert query["keywords"] == []


def test_build_query_keywords_missing_skills():
    """Test keywords when skills_years is missing."""
    candidate = {}

    query = build_job_query(candidate)

    assert query["keywords"] == []


def test_build_query_keywords_deduplicate():
    """Test that duplicate keywords are removed."""
    candidate = {
        "skills_years": {
            "Python": 5,
            "python": 3,  # Duplicate with different case
            "AWS": 2,
        }
    }

    query = build_job_query(candidate)

    # Should deduplicate case-insensitively
    assert len(query["keywords"]) == 2
    assert "Python" in query["keywords"]
    assert "AWS" in query["keywords"]


def test_build_query_keywords_strip_whitespace():
    """Test that keywords have whitespace stripped."""
    candidate = {
        "skills_years": {
            "  Python  ": 5,
            "  AWS  ": 3,
        }
    }

    query = build_job_query(candidate)

    assert "Python" in query["keywords"]
    assert "AWS" in query["keywords"]


def test_build_query_employment_type():
    """Test employment_type extraction."""
    candidate = {"employment_type": "full-time"}

    query = build_job_query(candidate)

    assert query["employment_type"] == "full-time"


def test_build_query_employment_type_preference_fallback():
    """Test that employment_type_preference field works as fallback."""
    candidate = {"employment_type_preference": "contract"}

    query = build_job_query(candidate)

    assert query["employment_type"] == "contract"


def test_build_query_employment_type_missing():
    """Test employment_type defaults to None when missing."""
    candidate = {}

    query = build_job_query(candidate)

    assert query["employment_type"] is None


def test_build_query_employment_type_strip_whitespace():
    """Test that employment_type has whitespace stripped."""
    candidate = {"employment_type": "  full-time  "}

    query = build_job_query(candidate)

    assert query["employment_type"] == "full-time"


def test_build_query_complete_realistic_candidate():
    """Test with realistic complete candidate from candidate_intake."""
    candidate = {
        # From candidate_intake.py
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone": "+1-555-123-4567",
        "address": "123 Main St, San Francisco, CA",
        "country": "United States",
        "work_authorization": "US Citizen",
        "education_level": "Bachelor's Degree",
        "skills_years": {
            "Python": 5,
            "AWS": 3,
            "Docker": 2,
            "Kubernetes": 2,
            "SQL": 7,
        },
        # Job preferences (additional fields)
        "desired_title": "Senior Backend Engineer",
        "alternate_titles": ["Software Engineer", "Python Developer"],
        "desired_locations": ["San Francisco", "Remote"],
        "remote_ok": True,
        "employment_type": "full-time",
    }

    query = build_job_query(candidate)

    assert len(query["titles"]) == 3
    assert query["titles"][0] == "Senior Backend Engineer"
    assert len(query["locations"]) == 2
    assert query["remote_ok"] is True
    assert len(query["keywords"]) == 5
    assert "Python" in query["keywords"]
    assert "AWS" in query["keywords"]
    assert query["employment_type"] == "full-time"


def test_build_query_preserves_order():
    """Test that order is preserved in all lists."""
    candidate = {
        "desired_title": "First",
        "alternate_titles": ["Second", "Third", "Fourth"],
        "desired_locations": ["Loc1", "Loc2", "Loc3"],
        "skills_years": {"Skill1": 1, "Skill2": 2, "Skill3": 3},
    }

    query = build_job_query(candidate)

    # Order should be preserved
    assert query["titles"] == ["First", "Second", "Third", "Fourth"]
    assert query["locations"] == ["Loc1", "Loc2", "Loc3"]
    # Note: dict key order is preserved in Python 3.7+
    assert query["keywords"][0] == "Skill1"


def test_build_query_invalid_skills_years_type():
    """Test that invalid skills_years type is handled gracefully."""
    candidate = {"skills_years": "not a dict"}

    query = build_job_query(candidate)

    assert query["keywords"] == []


def test_build_query_invalid_locations_type():
    """Test that invalid locations type is handled gracefully."""
    candidate = {"desired_locations": 123}  # Not string or list

    query = build_job_query(candidate)

    assert query["locations"] == []


def test_build_query_empty_strings_filtered():
    """Test that empty strings are filtered out."""
    candidate = {
        "desired_title": "",
        "alternate_titles": ["Engineer", "", "Developer"],
        "desired_locations": ["SF", "", "NYC"],
        "skills_years": {"Python": 5, "": 0, "AWS": 3},
    }

    query = build_job_query(candidate)

    # Empty title means no primary title
    assert "Engineer" in query["titles"]
    assert "Developer" in query["titles"]
    assert "" not in query["titles"]

    assert "SF" in query["locations"]
    assert "NYC" in query["locations"]
    assert "" not in query["locations"]

    assert "Python" in query["keywords"]
    assert "AWS" in query["keywords"]
    assert "" not in query["keywords"]
