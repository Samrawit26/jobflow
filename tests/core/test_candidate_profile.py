"""
Unit tests for candidate_profile.py

Tests candidate profile normalization and domain model.
"""

import pytest

from jobflow.app.core.candidate_profile import CandidateProfile


def test_candidate_profile_creation_basic():
    """Test basic CandidateProfile creation."""
    profile = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        location="San Francisco",
        desired_titles=["Software Engineer"],
        skills=["Python", "AWS"],
    )

    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane@example.com"
    assert profile.phone == "555-1234"
    assert profile.location == "San Francisco"
    assert profile.desired_titles == ["Software Engineer"]
    assert profile.skills == ["Python", "AWS"]


def test_from_dict_basic():
    """Test from_dict with standard keys."""
    raw = {
        "full_name": "John Smith",
        "email": "john@example.com",
        "phone": "555-5678",
        "location": "New York",
        "desired_titles": ["Data Scientist"],
        "skills": ["Python", "SQL"],
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "John Smith"
    assert profile.email == "john@example.com"
    assert profile.phone == "555-5678"
    assert profile.location == "New York"
    assert profile.desired_titles == ["Data Scientist"]
    assert profile.skills == ["Python", "SQL"]


def test_from_dict_alternate_keys():
    """Test from_dict handles alternative key names."""
    raw = {
        "name": "Alice Johnson",  # alternate to full_name
        "email_address": "alice@example.com",  # alternate to email
        "mobile": "555-9999",  # alternate to phone
        "city": "Boston",  # alternate to location
        "target_roles": ["Backend Engineer"],  # alternate to desired_titles
        "tech_stack": ["Java", "Spring"],  # alternate to skills
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "Alice Johnson"
    assert profile.email == "alice@example.com"
    assert profile.phone == "555-9999"
    assert profile.location == "Boston"
    assert profile.desired_titles == ["Backend Engineer"]
    assert profile.skills == ["Java", "Spring"]


def test_from_dict_skills_from_skills_years():
    """Test that skills can be extracted from skills_years dict."""
    raw = {
        "full_name": "Bob Jones",
        "email": "bob@example.com",
        "phone": "555-1111",
        "location": "Austin",
        "skills_years": {"Python": 5, "AWS": 3, "Docker": 2},
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.skills == ["Python", "AWS", "Docker"]


def test_from_dict_whitespace_trimming():
    """Test that whitespace is trimmed from all string fields."""
    raw = {
        "full_name": "  Jane   Doe  ",
        "email": "  jane@example.com  ",
        "phone": "  555-1234  ",
        "location": "  San Francisco  ",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "Jane Doe"  # Internal whitespace collapsed
    assert profile.email == "jane@example.com"
    assert profile.phone == "555-1234"
    assert profile.location == "San Francisco"


def test_from_dict_internal_whitespace_collapsed():
    """Test that internal whitespace is collapsed to single space."""
    raw = {
        "full_name": "Jane    Marie    Doe",
        "location": "San    Francisco",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "Jane Marie Doe"
    assert profile.location == "San Francisco"


def test_from_dict_list_from_string():
    """Test list normalization from comma-separated string."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "desired_titles": "Software Engineer, Backend Developer, Python Developer",
        "skills": "Python, AWS, Docker",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.desired_titles == [
        "Software Engineer",
        "Backend Developer",
        "Python Developer",
    ]
    assert profile.skills == ["Python", "AWS", "Docker"]


def test_from_dict_list_deduplication():
    """Test that lists are deduplicated (case-insensitive)."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "skills": ["Python", "python", "AWS", "aws", "Docker"],
    }

    profile = CandidateProfile.from_dict(raw)

    # Should deduplicate, keeping first occurrence
    assert profile.skills == ["Python", "AWS", "Docker"]


def test_from_dict_list_preserves_order():
    """Test that list order is preserved."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "skills": ["Zebra", "Apple", "Banana"],
    }

    profile = CandidateProfile.from_dict(raw)

    # Should preserve insertion order
    assert profile.skills == ["Zebra", "Apple", "Banana"]


def test_from_dict_years_experience_from_int():
    """Test years_experience from integer."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "years_experience": 5,
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.years_experience == 5.0


def test_from_dict_years_experience_from_float():
    """Test years_experience from float."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "years_experience": 3.5,
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.years_experience == 3.5


def test_from_dict_years_experience_from_string():
    """Test years_experience from string."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "years_experience": "7",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.years_experience == 7.0


def test_from_dict_years_experience_invalid():
    """Test years_experience with invalid value."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "years_experience": "not a number",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.years_experience is None


def test_from_dict_remote_ok_boolean():
    """Test remote_ok from boolean."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "remote_ok": True,
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.remote_ok is True


def test_from_dict_remote_ok_string():
    """Test remote_ok from string."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "remote_ok": "true",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.remote_ok is True


def test_from_dict_remote_preference_fallback():
    """Test that remote_preference works as fallback."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "remote_preference": "yes",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.remote_ok is True


def test_from_dict_work_authorization():
    """Test work_authorization normalization."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "work_authorization": "  US Citizen  ",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.work_authorization == "US Citizen"


def test_from_dict_preferred_locations():
    """Test preferred_locations normalization."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "preferred_locations": ["San Francisco", "Remote"],
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.preferred_locations == ["San Francisco", "Remote"]


def test_from_dict_resume_text():
    """Test resume_text normalization."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "resume_text": "  Experience with Python and AWS  ",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.resume_text == "Experience with Python and AWS"


def test_from_dict_missing_optional_fields():
    """Test from_dict with only required fields."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "Test User"
    assert profile.email == "test@example.com"
    assert profile.phone == "555-0000"
    assert profile.location == "NYC"
    assert profile.desired_titles == []
    assert profile.skills == []
    assert profile.years_experience is None
    assert profile.work_authorization == ""
    assert profile.preferred_locations == []
    assert profile.remote_ok is None
    assert profile.resume_text == ""


def test_from_dict_stores_raw_copy():
    """Test that from_dict stores defensive copy of raw."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "custom_field": "custom_value",
    }

    profile = CandidateProfile.from_dict(raw)

    # Should store raw
    assert "custom_field" in profile.raw
    assert profile.raw["custom_field"] == "custom_value"

    # Should be a copy, not the same object
    assert profile.raw is not raw


def test_from_dict_empty_strings_filtered_from_lists():
    """Test that empty strings are filtered from lists."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "skills": ["Python", "", "AWS", "  ", "Docker"],
        "desired_titles": ["Engineer", "", "Developer"],
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.skills == ["Python", "AWS", "Docker"]
    assert profile.desired_titles == ["Engineer", "Developer"]


def test_from_dict_newline_separated_lists():
    """Test list normalization from newline-separated string."""
    raw = {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "555-0000",
        "location": "NYC",
        "skills": "Python\nAWS\nDocker",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.skills == ["Python", "AWS", "Docker"]


def test_from_dict_complete_realistic_profile():
    """Test with complete realistic candidate profile."""
    raw = {
        "full_name": "Jane Marie Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-123-4567",
        "location": "San Francisco, CA",
        "desired_titles": ["Senior Backend Engineer", "Python Developer"],
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        "years_experience": 7.5,
        "work_authorization": "US Citizen",
        "preferred_locations": ["San Francisco", "Remote", "New York"],
        "remote_ok": True,
        "resume_text": "Experienced backend engineer with 7+ years in Python development...",
    }

    profile = CandidateProfile.from_dict(raw)

    assert profile.full_name == "Jane Marie Doe"
    assert profile.email == "jane.doe@example.com"
    assert profile.phone == "+1-555-123-4567"
    assert profile.location == "San Francisco, CA"
    assert len(profile.desired_titles) == 2
    assert len(profile.skills) == 5
    assert profile.years_experience == 7.5
    assert profile.work_authorization == "US Citizen"
    assert len(profile.preferred_locations) == 3
    assert profile.remote_ok is True
    assert len(profile.resume_text) > 0
