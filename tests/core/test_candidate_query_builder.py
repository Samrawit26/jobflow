"""
Unit tests for candidate_query_builder.py

Tests candidate to search query building with title inference.
"""

import pytest

from jobflow.app.core.candidate_profile import CandidateProfile
from jobflow.app.core.candidate_query_builder import build_search_query


def test_build_query_desired_titles_respected():
    """Test that explicit desired_titles are used."""
    candidate = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        location="SF",
        desired_titles=["Senior Software Engineer", "Tech Lead"],
        skills=["Python", "AWS"],
    )

    query = build_search_query(candidate)

    assert query["titles"] == ["Senior Software Engineer", "Tech Lead"]


def test_build_query_power_bi_skillset_inference():
    """Test title inference for Power BI skillset."""
    candidate = CandidateProfile(
        full_name="John Smith",
        email="john@example.com",
        phone="555-5678",
        location="NYC",
        desired_titles=[],  # No explicit titles
        skills=["Power BI", "SQL", "Tableau", "DAX"],
    )

    query = build_search_query(candidate)

    # Should infer BI titles
    assert "Power BI Developer" in query["titles"]
    assert "BI Developer" in query["titles"]
    assert "Data Analyst" in query["titles"]


def test_build_query_python_backend_skillset_inference():
    """Test title inference for Python backend skillset."""
    candidate = CandidateProfile(
        full_name="Alice Johnson",
        email="alice@example.com",
        phone="555-9999",
        location="Boston",
        desired_titles=[],
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
    )

    query = build_search_query(candidate)

    # Should infer Python backend titles
    assert "Python Developer" in query["titles"]
    assert "Backend Engineer" in query["titles"]


def test_build_query_data_engineer_skillset_inference():
    """Test title inference for Data Engineering skillset."""
    candidate = CandidateProfile(
        full_name="Bob Jones",
        email="bob@example.com",
        phone="555-1111",
        location="Austin",
        desired_titles=[],
        skills=["Spark", "Airflow", "Python", "Kafka"],
    )

    query = build_search_query(candidate)

    # Should infer Data Engineer title
    assert "Data Engineer" in query["titles"]


def test_build_query_mixed_skillset_deduplicates_titles():
    """Test that mixed skillsets deduplicate inferred titles."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=[],
        skills=["Python", "Spark", "Airflow", "FastAPI"],  # Both backend and data eng
    )

    query = build_search_query(candidate)

    # Should have both types but deduplicated
    assert "Python Developer" in query["titles"]
    assert "Backend Engineer" in query["titles"]
    assert "Data Engineer" in query["titles"]
    # No duplicates
    assert len(query["titles"]) == len(set(t.lower() for t in query["titles"]))


def test_build_query_keywords_from_skills():
    """Test keyword extraction from skills."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python", "AWS", "Docker", "Kubernetes"],
    )

    query = build_search_query(candidate)

    assert "python" in query["keywords"]
    assert "aws" in query["keywords"]
    assert "docker" in query["keywords"]
    assert "kubernetes" in query["keywords"]


def test_build_query_keywords_from_resume_text():
    """Test keyword extraction from resume text."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
        resume_text="Experience with SQL, AWS, Azure, and PostgreSQL. Proficient in Docker and Kubernetes.",
    )

    query = build_search_query(candidate)

    # Should extract from resume
    assert "python" in query["keywords"]
    assert "sql" in query["keywords"]
    assert "aws" in query["keywords"]
    assert "azure" in query["keywords"]


def test_build_query_keywords_deduplicate():
    """Test that keywords are deduplicated."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python", "AWS"],
        resume_text="Extensive experience with Python and AWS services.",
    )

    query = build_search_query(candidate)

    # Python and AWS should appear only once
    assert query["keywords"].count("python") == 1
    assert query["keywords"].count("aws") == 1


def test_build_query_keywords_capped_at_20():
    """Test that keywords are capped at 20."""
    # Create candidate with many skills
    skills = [f"Skill{i}" for i in range(30)]
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=skills,
    )

    query = build_search_query(candidate)

    # Should cap at 20
    assert len(query["keywords"]) <= 20


def test_build_query_keywords_lowercase():
    """Test that keywords are normalized to lowercase."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python", "AWS", "Docker"],
    )

    query = build_search_query(candidate)

    # All keywords should be lowercase
    assert all(k == k.lower() for k in query["keywords"])


def test_build_query_remote_from_flag():
    """Test remote_ok from explicit flag."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
        remote_ok=True,
    )

    query = build_search_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_remote_from_preferred_locations():
    """Test remote_ok inferred from 'remote' in preferred_locations."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
        preferred_locations=["San Francisco", "Remote", "New York"],
    )

    query = build_search_query(candidate)

    assert query["remote_ok"] is True


def test_build_query_remote_false_when_not_specified():
    """Test remote_ok is False when not specified."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
    )

    query = build_search_query(candidate)

    assert query["remote_ok"] is False


def test_build_query_locations_from_preferred():
    """Test locations from preferred_locations."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
        preferred_locations=["San Francisco", "New York", "Boston"],
    )

    query = build_search_query(candidate)

    assert query["locations"] == ["San Francisco", "New York", "Boston"]


def test_build_query_locations_from_home_location():
    """Test locations fallback to home location."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="San Francisco",
        desired_titles=["Engineer"],
        skills=["Python"],
        preferred_locations=[],
    )

    query = build_search_query(candidate)

    assert query["locations"] == ["San Francisco"]


def test_build_query_locations_empty_when_none():
    """Test locations empty when neither preferred nor home specified."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="",
        desired_titles=["Engineer"],
        skills=["Python"],
        preferred_locations=[],
    )

    query = build_search_query(candidate)

    assert query["locations"] == []


def test_build_query_employment_type_none():
    """Test employment_type is None (not inferred)."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
    )

    query = build_search_query(candidate)

    assert query["employment_type"] is None


def test_build_query_complete_realistic_candidate():
    """Test with complete realistic candidate profile."""
    candidate = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        location="San Francisco",
        desired_titles=["Senior Backend Engineer"],
        skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS"],
        years_experience=7.5,
        work_authorization="US Citizen",
        preferred_locations=["San Francisco", "Remote"],
        remote_ok=True,
        resume_text="7+ years experience building scalable backend systems with Python, AWS, and microservices.",
    )

    query = build_search_query(candidate)

    # Verify all fields populated correctly
    assert "Senior Backend Engineer" in query["titles"]
    assert len(query["keywords"]) > 0
    assert "python" in query["keywords"]
    assert query["locations"] == ["San Francisco", "Remote"]
    assert query["remote_ok"] is True
    assert query["employment_type"] is None


def test_build_query_result_structure():
    """Test that query has correct structure."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Python"],
    )

    query = build_search_query(candidate)

    # Verify structure
    assert "titles" in query
    assert "locations" in query
    assert "remote_ok" in query
    assert "keywords" in query
    assert "employment_type" in query

    # Verify types
    assert isinstance(query["titles"], list)
    assert isinstance(query["locations"], list)
    assert isinstance(query["remote_ok"], bool)
    assert isinstance(query["keywords"], list)


def test_build_query_preserves_order():
    """Test that query preserves skill order in keywords."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=["Engineer"],
        skills=["Zebra", "Apple", "Banana"],
    )

    query = build_search_query(candidate)

    # Keywords should preserve skill order
    assert query["keywords"][0] == "zebra"
    assert query["keywords"][1] == "apple"
    assert query["keywords"][2] == "banana"


def test_build_query_power_bi_case_insensitive():
    """Test that skill matching is case-insensitive."""
    candidate = CandidateProfile(
        full_name="Test User",
        email="test@example.com",
        phone="555-0000",
        location="SF",
        desired_titles=[],
        skills=["POWER BI", "sql", "TaBlEaU"],  # Mixed case
    )

    query = build_search_query(candidate)

    # Should still infer BI titles
    assert "Power BI Developer" in query["titles"]
    assert "BI Developer" in query["titles"]
