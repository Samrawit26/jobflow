"""
Unit tests for job_source.py

Tests the JobSource protocol interface definition.
"""

from typing import runtime_checkable

import pytest

from jobflow.app.core.job_source import JobSource


class MockJobSource:
    """Mock implementation of JobSource protocol."""

    def __init__(self, name: str):
        self._source_name = name

    @property
    def source_name(self) -> str:
        return self._source_name

    def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
        """Mock fetch that returns dummy data."""
        return [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco",
                "description": "Build great software",
            },
            {
                "title": "Data Scientist",
                "company": "AI Inc",
                "location": "Remote",
                "description": "Analyze data",
            },
        ]


class MockJobSourceWithQuery:
    """Mock implementation that uses query parameter."""

    @property
    def source_name(self) -> str:
        return "mock_with_query"

    def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
        """Mock fetch that filters based on query."""
        if query is None:
            return []

        # Simple filter by title keyword
        if "title" in query:
            return [
                {
                    "title": query["title"],
                    "company": "Test Corp",
                    "location": "Anywhere",
                    "description": "Test job",
                }
            ]

        return []


class IncompleteJobSource:
    """Incomplete implementation missing fetch_raw_jobs method."""

    @property
    def source_name(self) -> str:
        return "incomplete"

    # Missing: fetch_raw_jobs method


def test_mock_job_source_implements_protocol():
    """Test that MockJobSource implements JobSource protocol."""
    source = MockJobSource("test_source")

    # Should have source_name property
    assert hasattr(source, "source_name")
    assert source.source_name == "test_source"

    # Should have fetch_raw_jobs method
    assert hasattr(source, "fetch_raw_jobs")
    assert callable(source.fetch_raw_jobs)


def test_mock_job_source_fetch_returns_list():
    """Test that fetch_raw_jobs returns list of dicts."""
    source = MockJobSource("test_source")

    jobs = source.fetch_raw_jobs()

    assert isinstance(jobs, list)
    assert len(jobs) == 2
    assert all(isinstance(job, dict) for job in jobs)


def test_mock_job_source_fetch_with_none_query():
    """Test fetch_raw_jobs with None query."""
    source = MockJobSource("test_source")

    jobs = source.fetch_raw_jobs(query=None)

    assert isinstance(jobs, list)
    assert len(jobs) == 2


def test_mock_job_source_fetch_with_empty_query():
    """Test fetch_raw_jobs with empty dict query."""
    source = MockJobSource("test_source")

    jobs = source.fetch_raw_jobs(query={})

    assert isinstance(jobs, list)
    assert len(jobs) == 2


def test_mock_job_source_with_query_implementation():
    """Test mock implementation that uses query parameter."""
    source = MockJobSourceWithQuery()

    # Fetch with query
    jobs = source.fetch_raw_jobs(query={"title": "Engineer"})

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Engineer"


def test_mock_job_source_with_query_none():
    """Test mock implementation returns empty list for None query."""
    source = MockJobSourceWithQuery()

    jobs = source.fetch_raw_jobs(query=None)

    assert jobs == []


def test_job_source_protocol_has_source_name():
    """Test that JobSource protocol requires source_name."""
    # This test verifies the protocol definition has source_name
    assert hasattr(JobSource, "source_name")


def test_job_source_protocol_has_fetch_raw_jobs():
    """Test that JobSource protocol requires fetch_raw_jobs."""
    # This test verifies the protocol definition has fetch_raw_jobs
    assert hasattr(JobSource, "fetch_raw_jobs")


def test_multiple_implementations_with_different_names():
    """Test multiple implementations with different source names."""
    source1 = MockJobSource("linkedin")
    source2 = MockJobSource("indeed")

    assert source1.source_name == "linkedin"
    assert source2.source_name == "indeed"


def test_fetch_raw_jobs_signature():
    """Test that fetch_raw_jobs has correct signature."""
    source = MockJobSource("test")

    # Should accept no arguments (query defaults to None)
    jobs = source.fetch_raw_jobs()
    assert isinstance(jobs, list)

    # Should accept query argument
    jobs = source.fetch_raw_jobs(query={"keyword": "python"})
    assert isinstance(jobs, list)


def test_raw_jobs_are_dicts():
    """Test that raw jobs returned are dicts."""
    source = MockJobSource("test")

    jobs = source.fetch_raw_jobs()

    for job in jobs:
        assert isinstance(job, dict)
        # Typical fields in raw jobs
        assert "title" in job
        assert "company" in job


def test_protocol_allows_different_implementations():
    """Test that protocol allows different implementation strategies."""

    class MinimalSource:
        """Minimal implementation."""

        @property
        def source_name(self) -> str:
            return "minimal"

        def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
            return []

    class RichSource:
        """Rich implementation with additional features."""

        def __init__(self):
            self._name = "rich"
            self._cache = []

        @property
        def source_name(self) -> str:
            return self._name

        def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
            # Additional logic
            if self._cache:
                return self._cache
            return [{"title": "Cached job"}]

    minimal = MinimalSource()
    rich = RichSource()

    # Both should work as JobSource
    assert minimal.source_name == "minimal"
    assert rich.source_name == "rich"
    assert minimal.fetch_raw_jobs() == []
    assert len(rich.fetch_raw_jobs()) == 1


def test_source_name_is_string():
    """Test that source_name returns a string."""
    source = MockJobSource("test_source")

    name = source.source_name

    assert isinstance(name, str)
    assert len(name) > 0


def test_incomplete_implementation_missing_method():
    """Test that incomplete implementation is missing required method."""
    source = IncompleteJobSource()

    # Has source_name
    assert hasattr(source, "source_name")
    assert source.source_name == "incomplete"

    # Missing fetch_raw_jobs
    assert not hasattr(source, "fetch_raw_jobs")
