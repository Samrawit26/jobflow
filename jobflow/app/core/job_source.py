"""
Job source interface protocol.

Defines the contract for pluggable job feed implementations.
Job sources return raw job dicts that are normalized elsewhere
into canonical JobPosting instances.

This is a pure interface definition with no runtime behavior.
"""

from typing import Protocol


class JobSource(Protocol):
    """
    Protocol for job feed sources.

    Any class implementing this protocol can serve as a job source
    for aggregation pipelines. Raw job dicts are returned and
    normalized downstream using JobPosting.from_raw().

    Attributes:
        source_name: Unique identifier for this job source (e.g., "linkedin", "indeed")

    Methods:
        fetch_raw_jobs: Retrieve raw job postings matching optional query filters
    """

    @property
    def source_name(self) -> str:
        """
        Unique identifier for this job source.

        Returns:
            Source name string (e.g., "linkedin", "indeed", "greenhouse")
        """
        ...

    def fetch_raw_jobs(self, query: dict | None = None) -> list[dict]:
        """
        Fetch raw job postings from this source.

        Args:
            query: Optional filter criteria (structure is source-specific)

        Returns:
            List of raw job dicts (structure varies by source)
        """
        ...
