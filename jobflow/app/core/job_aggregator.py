"""
Job aggregator for multi-source job collection.

Orchestrates fetching from multiple job sources, normalizes raw job dicts
into canonical JobPosting instances, and deduplicates across sources.

Deterministic and pure:
- No network calls (delegates to sources)
- No database access
- No filesystem operations
- Stable ordering and deduplication strategy

Deduplication strategy:
- Uses JobPosting.fingerprint() for content-based deduplication
- Keeps first occurrence when duplicates found across sources
- Preserves source ordering and within-source job ordering
"""

from jobflow.app.core.job_model import JobPosting
from jobflow.app.core.job_source import JobSource


class JobAggregator:
    """
    Aggregates jobs from multiple sources with deduplication.

    Fetches raw job postings from each source, normalizes them into
    canonical JobPosting instances, and deduplicates based on content
    fingerprints.

    Provenance:
    - Each JobPosting's 'source' field is populated with the source_name
      if not already present in the raw data

    Ordering:
    - Sources are processed in the order provided to __init__
    - Within each source, jobs are processed in the order returned
    - Duplicate jobs (by fingerprint) are skipped silently

    Error handling:
    - aggregate() raises ValueError for invalid source responses
    - aggregate_with_errors() captures errors per-job and continues
    """

    def __init__(self, sources: list[JobSource]):
        """
        Initialize aggregator with job sources.

        Args:
            sources: List of JobSource implementations to aggregate from
        """
        self.sources = sources

    def aggregate(self, query: dict | None = None) -> list[JobPosting]:
        """
        Aggregate jobs from all sources with deduplication.

        Fetches raw jobs from each source, normalizes them, and deduplicates
        based on content fingerprints. Raises errors immediately on invalid
        source responses.

        Args:
            query: Optional filter criteria (structure is source-specific)

        Returns:
            List of deduplicated JobPosting instances, ordered by:
            1. Source order (as provided to __init__)
            2. Within-source job order (as returned by source)

        Raises:
            ValueError: If a source returns non-list or contains non-dict entries
        """
        seen_fingerprints = set()
        jobs = []

        for source in self.sources:
            # Fetch raw jobs from source
            raw_jobs = source.fetch_raw_jobs(query)

            # Validate source returned a list
            if not isinstance(raw_jobs, list):
                raise ValueError(
                    f"Source '{source.source_name}' returned non-list: "
                    f"{type(raw_jobs).__name__}"
                )

            # Process each raw job
            for raw in raw_jobs:
                # Validate each entry is a dict
                if not isinstance(raw, dict):
                    raise ValueError(
                        f"Source '{source.source_name}' returned non-dict entry: "
                        f"{type(raw).__name__}"
                    )

                # Set source provenance if not already present
                # Create a copy to avoid mutating the original
                if "source" not in raw or not raw["source"]:
                    raw = {**raw, "source": source.source_name}

                # Normalize raw dict into JobPosting
                job = JobPosting.from_raw(raw)

                # Deduplicate by content fingerprint
                fp = job.fingerprint()
                if fp not in seen_fingerprints:
                    seen_fingerprints.add(fp)
                    jobs.append(job)
                # else: duplicate, skip silently

        return jobs

    def aggregate_with_errors(
        self, query: dict | None = None
    ) -> tuple[list[JobPosting], list[dict]]:
        """
        Aggregate jobs from all sources, capturing errors instead of raising.

        Like aggregate(), but instead of raising on errors, collects them
        into a structured error list and continues processing remaining jobs.

        Args:
            query: Optional filter criteria (structure is source-specific)

        Returns:
            Tuple of (jobs, errors):
            - jobs: List of successfully normalized JobPosting instances
            - errors: List of error dicts, each containing:
                - source: str (source_name where error occurred)
                - index: int | None (index of failing job in source's list, or None for fetch errors)
                - error: str (error message)
                - raw_excerpt: str | None (first ~200 chars of raw job, or None)

        Error handling:
        - Source fetch failures are recorded with index=None
        - Per-job normalization failures are recorded with index and excerpt
        - Processing continues for remaining sources/jobs
        """
        seen_fingerprints = set()
        jobs = []
        errors = []

        for source in self.sources:
            # Try to fetch raw jobs from source
            try:
                raw_jobs = source.fetch_raw_jobs(query)

                # Validate source returned a list
                if not isinstance(raw_jobs, list):
                    raise ValueError(
                        f"Returned non-list: {type(raw_jobs).__name__}"
                    )
            except Exception as e:
                # Record source-level fetch error
                errors.append(
                    {
                        "source": source.source_name,
                        "index": None,
                        "error": str(e),
                        "raw_excerpt": None,
                    }
                )
                continue  # Skip to next source

            # Process each raw job with individual error handling
            for idx, raw in enumerate(raw_jobs):
                try:
                    # Validate entry is a dict
                    if not isinstance(raw, dict):
                        raise ValueError(f"Entry is not a dict: {type(raw).__name__}")

                    # Set source provenance if not already present
                    # Create a copy to avoid mutating the original
                    if "source" not in raw or not raw["source"]:
                        raw = {**raw, "source": source.source_name}

                    # Normalize raw dict into JobPosting
                    job = JobPosting.from_raw(raw)

                    # Deduplicate by content fingerprint
                    fp = job.fingerprint()
                    if fp not in seen_fingerprints:
                        seen_fingerprints.add(fp)
                        jobs.append(job)
                    # else: duplicate, skip silently (not an error)

                except Exception as e:
                    # Record per-job normalization error
                    raw_str = str(raw)[:200]
                    errors.append(
                        {
                            "source": source.source_name,
                            "index": idx,
                            "error": str(e),
                            "raw_excerpt": raw_str,
                        }
                    )
                    continue  # Skip to next job

        return jobs, errors
