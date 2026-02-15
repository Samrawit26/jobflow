"""
File-based job source implementation.

Adapter for local fixtures and exports. Reads job postings from JSON files
for testing, development, and offline scenarios.

This is a deterministic, filesystem-based implementation of the JobSource
protocol with no network dependencies.
"""

import json
from pathlib import Path


class FileJobSource:
    """
    File-based job source for local fixtures and exports.

    Reads raw job postings from JSON files. Supports two formats:
    1. Direct list: [{"title": "...", ...}, ...]
    2. Object wrapper: {"jobs": [{"title": "...", ...}, ...]}

    This implementation is useful for:
    - Unit testing
    - Development with static fixtures
    - Offline operation with exported data
    - Integration testing with known datasets

    Attributes:
        source_name: Identifier for this source (e.g., "local_fixtures")
        path: Path to JSON file containing job data
    """

    def __init__(self, source_name: str, path: str):
        """
        Initialize file-based job source.

        Args:
            source_name: Unique identifier for this source
            path: Path to JSON file containing job postings
        """
        self._source_name = source_name
        self._path = Path(path)

    @property
    def source_name(self) -> str:
        """
        Get source name.

        Returns:
            Source identifier string
        """
        return self._source_name

    def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
        """
        Read raw job postings from JSON file.

        Supports two JSON formats:
        - Direct list: [job1, job2, ...]
        - Object wrapper: {"jobs": [job1, job2, ...]}

        Note: Query parameter is ignored for file sources. All jobs from
        the file are returned. Filtering should be done at aggregation level.

        Args:
            query: Ignored for file sources

        Returns:
            List of raw job posting dicts

        Raises:
            FileNotFoundError: If JSON file does not exist
            ValueError: If file contains invalid JSON or wrong structure
        """
        # Check file exists
        if not self._path.exists():
            raise FileNotFoundError(
                f"Job data file not found: {self._path}"
            )

        # Read and parse JSON
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in job data file {self._path}: {str(e)}"
            )

        # Handle two formats: list or {"jobs": [...]}
        if isinstance(data, list):
            jobs = data
        elif isinstance(data, dict) and "jobs" in data:
            jobs = data["jobs"]
            if not isinstance(jobs, list):
                raise ValueError(
                    f"Expected 'jobs' key to contain a list, got {type(jobs).__name__}"
                )
        else:
            raise ValueError(
                f"Expected JSON to be a list or object with 'jobs' key, "
                f"got {type(data).__name__}"
            )

        # Validate that jobs is a list
        if not isinstance(jobs, list):
            raise ValueError(
                f"Expected job data to be a list, got {type(jobs).__name__}"
            )

        return jobs
