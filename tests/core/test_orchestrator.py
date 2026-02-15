"""
Unit tests for pipeline orchestrator.

Tests the synchronous orchestrator that bridges pipelines to execution scripts.
"""

import pytest
from jobflow.app.core.orchestrator import (
    run_pipeline,
    PipelineNotFoundError,
    PipelineExecutionError,
)


class TestRunPipeline:
    """Test cases for run_pipeline function."""

    def test_run_job_discovery_pipeline_basic(self):
        """Test running job_discovery pipeline with basic input."""
        payload = {
            "title": "Software Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "description": "Build great software",
        }

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        assert result["pipeline"] == "job_discovery"
        assert "data" in result
        assert result["data"]["title"] == "Software Engineer"
        assert result["data"]["company"] == "Acme Corp"
        assert result["data"]["location"] == "Remote"

    def test_run_job_discovery_pipeline_with_alternative_fields(self):
        """Test job_discovery pipeline with alternative field names."""
        payload = {
            "job_title": "Data Scientist",
            "employer": "TechCo",
            "loc": "San Francisco",
        }

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        assert result["data"]["title"] == "Data Scientist"
        assert result["data"]["company"] == "TechCo"
        assert result["data"]["location"] == "San Francisco"

    def test_run_job_discovery_pipeline_with_salary(self):
        """Test job_discovery pipeline with salary information."""
        payload = {
            "title": "Senior Engineer",
            "company": "BigTech",
            "salary_min": 120000,
            "salary_max": 180000,
        }

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        assert result["data"]["salary_min"] == 120000.0
        assert result["data"]["salary_max"] == 180000.0

    def test_run_job_discovery_pipeline_with_requirements(self):
        """Test job_discovery pipeline with requirements list."""
        payload = {
            "title": "Backend Developer",
            "company": "StartupXYZ",
            "requirements": ["Python", "FastAPI", "PostgreSQL"],
        }

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        assert len(result["data"]["requirements"]) == 3
        assert "Python" in result["data"]["requirements"]

    def test_run_job_discovery_pipeline_with_empty_payload(self):
        """Test job_discovery pipeline with empty payload."""
        payload = {}

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        assert result["data"]["title"] == ""
        assert result["data"]["company"] == ""
        assert result["data"]["requirements"] == []

    def test_run_pipeline_unknown_pipeline(self):
        """Test that unknown pipeline raises PipelineNotFoundError."""
        payload = {"title": "Test"}

        with pytest.raises(PipelineNotFoundError) as exc_info:
            run_pipeline("unknown_pipeline", payload)

        assert "Unknown pipeline: unknown_pipeline" in str(exc_info.value)
        assert "job_discovery" in str(exc_info.value)

    def test_run_pipeline_returns_deterministic_result(self):
        """Test that orchestrator is deterministic (same input → same output)."""
        payload = {
            "title": "Engineer",
            "company": "TestCorp",
            "salary_min": "$100,000",
        }

        result1 = run_pipeline("job_discovery", payload)
        result2 = run_pipeline("job_discovery", payload)

        # Same inputs should produce identical outputs
        assert result1 == result2
        assert result1["data"]["salary_min"] == 100000.0
        assert result2["data"]["salary_min"] == 100000.0


class TestJobDiscoveryPipeline:
    """Test cases specific to job_discovery pipeline implementation."""

    def test_job_discovery_normalizes_data(self):
        """Test that job_discovery pipeline normalizes data correctly."""
        payload = {
            "job_title": "  Full Stack Developer  ",
            "employer": "WebCorp",
            "salary_min": "$90,000",
        }

        result = run_pipeline("job_discovery", payload)

        # Should normalize: strip whitespace, parse salary
        assert result["data"]["title"] == "Full Stack Developer"
        assert result["data"]["company"] == "WebCorp"
        assert result["data"]["salary_min"] == 90000.0

    def test_job_discovery_returns_expected_structure(self):
        """Test that job_discovery pipeline returns expected result structure."""
        payload = {"title": "Test Job"}

        result = run_pipeline("job_discovery", payload)

        # Verify result structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "pipeline" in result
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_job_discovery_with_all_fields(self):
        """Test job_discovery pipeline with comprehensive payload."""
        payload = {
            "title": "Machine Learning Engineer",
            "company": "AI Startup",
            "location": "New York, NY",
            "description": "Build ML models",
            "requirements": ["Python", "TensorFlow", "PhD preferred"],
            "salary_min": 130000,
            "salary_max": 200000,
            "posted_date": "2024-01-20",
            "url": "https://example.com/jobs/ml-engineer",
        }

        result = run_pipeline("job_discovery", payload)

        assert result["status"] == "success"
        data = result["data"]
        assert data["title"] == "Machine Learning Engineer"
        assert data["company"] == "AI Startup"
        assert data["location"] == "New York, NY"
        assert data["description"] == "Build ML models"
        assert len(data["requirements"]) == 3
        assert data["salary_min"] == 130000.0
        assert data["salary_max"] == 200000.0
        assert data["posted_date"] == "2024-01-20"
        assert data["url"] == "https://example.com/jobs/ml-engineer"
