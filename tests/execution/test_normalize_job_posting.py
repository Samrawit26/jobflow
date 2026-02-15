"""
Unit tests for normalize_job_posting execution script.

Tests the pure function logic for job posting normalization.
No external dependencies, database, or I/O required.
"""

import pytest
from execution.normalize_job_posting import normalize_job_posting, _extract_salary


class TestNormalizeJobPosting:
    """Test cases for normalize_job_posting function."""

    def test_normalize_basic_fields(self):
        """Test normalization of basic job posting fields."""
        raw_posting = {
            "title": "Software Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "description": "Build great software",
        }

        result = normalize_job_posting(raw_posting)

        assert result["title"] == "Software Engineer"
        assert result["company"] == "Acme Corp"
        assert result["location"] == "Remote"
        assert result["description"] == "Build great software"
        assert result["requirements"] == []
        assert result["salary_min"] is None
        assert result["salary_max"] is None
        assert result["posted_date"] is None
        assert result["url"] is None

    def test_normalize_alternative_field_names(self):
        """Test that alternative field names are handled correctly."""
        raw_posting = {
            "job_title": "Data Scientist",
            "employer": "Tech Co",
            "loc": "San Francisco, CA",
        }

        result = normalize_job_posting(raw_posting)

        assert result["title"] == "Data Scientist"
        assert result["company"] == "Tech Co"
        assert result["location"] == "San Francisco, CA"

    def test_normalize_requirements_as_list(self):
        """Test normalization when requirements are provided as a list."""
        raw_posting = {
            "title": "Backend Engineer",
            "company": "StartupXYZ",
            "requirements": [
                "3+ years Python",
                "FastAPI experience",
                "PostgreSQL knowledge",
            ],
        }

        result = normalize_job_posting(raw_posting)

        assert len(result["requirements"]) == 3
        assert "3+ years Python" in result["requirements"]
        assert "FastAPI experience" in result["requirements"]
        assert "PostgreSQL knowledge" in result["requirements"]

    def test_normalize_requirements_as_string(self):
        """Test normalization when requirements are provided as a string."""
        raw_posting = {
            "title": "Frontend Developer",
            "company": "WebCo",
            "requirements": "React experience\nTypeScript\n3+ years",
        }

        result = normalize_job_posting(raw_posting)

        assert len(result["requirements"]) == 3
        assert "React experience" in result["requirements"]
        assert "TypeScript" in result["requirements"]
        assert "3+ years" in result["requirements"]

    def test_normalize_requirements_with_semicolons(self):
        """Test normalization when requirements use semicolon separators."""
        raw_posting = {
            "title": "DevOps Engineer",
            "company": "CloudCorp",
            "requirements": "Docker; Kubernetes; AWS; CI/CD",
        }

        result = normalize_job_posting(raw_posting)

        assert len(result["requirements"]) == 4
        assert "Docker" in result["requirements"]
        assert "Kubernetes" in result["requirements"]

    def test_normalize_salary_as_integers(self):
        """Test salary normalization with integer values."""
        raw_posting = {
            "title": "Senior Engineer",
            "company": "BigTech",
            "salary_min": 100000,
            "salary_max": 150000,
        }

        result = normalize_job_posting(raw_posting)

        assert result["salary_min"] == 100000.0
        assert result["salary_max"] == 150000.0

    def test_normalize_salary_as_strings(self):
        """Test salary normalization with string values containing currency."""
        raw_posting = {
            "title": "Manager",
            "company": "Finance Inc",
            "salary_min": "$80,000",
            "salary_max": "$120,000",
        }

        result = normalize_job_posting(raw_posting)

        assert result["salary_min"] == 80000.0
        assert result["salary_max"] == 120000.0

    def test_normalize_salary_in_nested_dict(self):
        """Test salary normalization when provided in a nested salary_range dict."""
        raw_posting = {
            "title": "Analyst",
            "company": "DataCo",
            "salary_range": {"min": 60000, "max": 90000},
        }

        result = normalize_job_posting(raw_posting)

        assert result["salary_min"] == 60000.0
        assert result["salary_max"] == 90000.0

    def test_normalize_posted_date(self):
        """Test normalization of posted date."""
        raw_posting = {
            "title": "Developer",
            "company": "CodeShop",
            "posted_date": "2024-01-15",
        }

        result = normalize_job_posting(raw_posting)

        assert result["posted_date"] == "2024-01-15"

    def test_normalize_url(self):
        """Test normalization of posting URL."""
        raw_posting = {
            "title": "Engineer",
            "company": "TechFirm",
            "url": "https://example.com/jobs/123",
        }

        result = normalize_job_posting(raw_posting)

        assert result["url"] == "https://example.com/jobs/123"

    def test_normalize_empty_dict(self):
        """Test normalization of empty input."""
        raw_posting = {}

        result = normalize_job_posting(raw_posting)

        assert result["title"] == ""
        assert result["company"] == ""
        assert result["location"] == ""
        assert result["description"] == ""
        assert result["requirements"] == []
        assert result["salary_min"] is None
        assert result["salary_max"] is None

    def test_normalize_strips_whitespace(self):
        """Test that string fields are stripped of leading/trailing whitespace."""
        raw_posting = {
            "title": "  Software Engineer  ",
            "company": "  Acme Corp  ",
            "location": "  Remote  ",
        }

        result = normalize_job_posting(raw_posting)

        assert result["title"] == "Software Engineer"
        assert result["company"] == "Acme Corp"
        assert result["location"] == "Remote"


class TestExtractSalary:
    """Test cases for _extract_salary helper function."""

    def test_extract_salary_from_int(self):
        """Test extracting salary from integer."""
        assert _extract_salary(100000) == 100000.0

    def test_extract_salary_from_float(self):
        """Test extracting salary from float."""
        assert _extract_salary(95000.5) == 95000.5

    def test_extract_salary_from_string_with_dollar(self):
        """Test extracting salary from string with dollar sign."""
        assert _extract_salary("$85,000") == 85000.0

    def test_extract_salary_from_string_with_euro(self):
        """Test extracting salary from string with euro sign."""
        assert _extract_salary("€75,000") == 75000.0

    def test_extract_salary_from_plain_string(self):
        """Test extracting salary from plain numeric string."""
        assert _extract_salary("120000") == 120000.0

    def test_extract_salary_from_none(self):
        """Test extracting salary from None."""
        assert _extract_salary(None) is None

    def test_extract_salary_from_invalid_string(self):
        """Test extracting salary from non-numeric string."""
        assert _extract_salary("not a number") is None

    def test_extract_salary_from_empty_string(self):
        """Test extracting salary from empty string."""
        assert _extract_salary("") is None
