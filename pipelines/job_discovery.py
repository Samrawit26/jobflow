"""
Job Discovery Pipeline

High-level workflow for discovering, parsing, and storing job postings.

IMPORTANT: This is a DESCRIPTIVE definition only.
No execution logic, imports, or side effects belong here.
Actual work is done by execution scripts coordinated by workers.
"""

# Pipeline: Job Discovery and Parsing
# Purpose: Discover new job postings from various sources and parse them into structured data
#
# Steps:
#   1. fetch_job_sources
#      - Input: List of job board URLs or API endpoints
#      - Output: Raw job posting data (HTML, JSON, etc.)
#      - Execution: /execution/fetch_jobs.py
#      - Retry: 3 attempts with exponential backoff
#      - Failure: Log and continue to next source
#
#   2. parse_job_postings
#      - Input: Raw job posting data from step 1
#      - Output: Structured job data (title, company, description, requirements, etc.)
#      - Execution: /execution/parse_jobs.py
#      - Retry: 2 attempts
#      - Failure: Mark as unparseable, continue
#
#   3. deduplicate_jobs
#      - Input: Parsed job data from step 2
#      - Output: Deduplicated job list
#      - Execution: /execution/deduplicate_jobs.py
#      - Retry: 1 attempt
#      - Failure: Skip deduplication, continue
#
#   4. store_jobs
#      - Input: Deduplicated jobs from step 3
#      - Output: Job IDs in database
#      - Execution: /execution/store_jobs.py
#      - Retry: 3 attempts
#      - Failure: Alert on failure, halt pipeline
#
# Dependencies:
#   - Steps 1-4 run sequentially
#   - Step 2 can process multiple jobs in parallel
#   - Step 4 is critical path (must succeed)
#
# Schedule:
#   - Run every 6 hours
#   - Can be triggered manually via API
#
# Configuration:
#   - max_jobs_per_run: 1000
#   - timeout_per_step: 300 seconds
#   - parallel_parsing: True
#   - parallel_workers: 5


# Pipeline: Job Discovery (Placeholder)
# Not yet implemented. No operational code below.


def get_pipeline_definition():
    """
    Return pipeline definition structure.

    This is a placeholder for future pipeline configuration.
    Currently returns None - not yet operational.

    Returns:
        None (not implemented)
    """
    return None


# ==============================================================================
# Executable Pipeline Functions
# ==============================================================================


def run_job_discovery(
    candidate_or_query=None,
    sources: list = None,
    match_jobs: bool = False,
    candidate_folder: str = None
) -> dict:
    """
    Execute job discovery pipeline for a candidate.

    Orchestrates the complete job discovery workflow:
    1. (Optional) Load candidate profile from folder
    2. Build search query from candidate profile (or use provided query)
    3. Aggregate jobs from multiple sources
    4. (Optional) Match and rank jobs by fit score
    5. Return structured results with jobs and errors

    This is a deterministic, pure function with no side effects.
    All I/O is delegated to the provided JobSource implementations.

    Args:
        candidate_or_query: One of:
            - CandidateProfile instance
            - dict with CandidateProfile fields (full_name, email, etc.)
            - dict with SearchQuery fields (titles, keywords, etc.) [legacy]
            - dict with old-style fields (desired_title, skills_years, etc.) [legacy]
            - None if using candidate_folder parameter
        sources: List of JobSource implementations to aggregate from
        match_jobs: If True, match and rank jobs by fit score (default False)
        candidate_folder: Path to folder containing application info and resume
                          (if provided, overrides candidate_or_query)

    Returns:
        Dict containing:
        - status: "ok" (always successful, errors captured separately)
        - query: Search query dict built from candidate profile
        - jobs: List of serialized job dicts (using Job.to_dict())
        - errors: List of error dicts from aggregation
        - counts: Dict with "jobs" and "errors" counts
        - matches: (if match_jobs=True) List of match result dicts, sorted by score
        - candidate: (if candidate_folder provided) Dict with candidate summary

    Example (new style):
        >>> from jobflow.app.core.candidate_profile import CandidateProfile
        >>> candidate = CandidateProfile(
        ...     full_name="Jane Doe",
        ...     email="jane@example.com",
        ...     phone="555-1234",
        ...     location="SF",
        ...     desired_titles=["Software Engineer"],
        ...     skills=["Python", "AWS"]
        ... )
        >>> result = run_job_discovery(candidate, [source])

    Example (legacy):
        >>> candidate = {
        ...     "desired_title": "Software Engineer",
        ...     "skills_years": {"Python": 5, "AWS": 3}
        ... }
        >>> result = run_job_discovery(candidate, [source])

    Example (with candidate folder):
        >>> result = run_job_discovery(
        ...     sources=[source],
        ...     candidate_folder="path/to/candidate/folder",
        ...     match_jobs=True
        ... )

    Example (with matching):
        >>> result = run_job_discovery(candidate, [source], match_jobs=True)
        >>> for match in result["matches"]:
        ...     print(f"{match['job_title']}: {match['overall_score']}")
    """
    from jobflow.app.core.candidate_profile import CandidateProfile
    from jobflow.app.core.candidate_query_builder import build_search_query
    from jobflow.app.core.job_aggregator import JobAggregator
    from jobflow.app.core.search_query import build_job_query

    # Step 0: Load candidate from folder if provided
    if candidate_folder is not None:
        from jobflow.app.core.candidate_folder_loader import load_candidate_profile
        candidate_profile = load_candidate_profile(candidate_folder)
        candidate_or_query = candidate_profile
    else:
        candidate_profile = None

    # Step 1: Build search query (handle multiple input formats)
    query = _build_query_from_input(candidate_or_query)

    # Step 2: Aggregate jobs from sources with error handling
    aggregator = JobAggregator(sources)
    jobs, errors = aggregator.aggregate_with_errors(query)

    # Step 3: Serialize jobs (convert JobPosting instances to dicts)
    serialized_jobs = [job.to_dict() for job in jobs]

    # Step 4: Build result structure
    result = {
        "status": "ok",
        "query": query,
        "jobs": serialized_jobs,
        "errors": errors,
        "counts": {
            "jobs": len(jobs),
            "errors": len(errors),
        },
    }

    # Include candidate summary if loaded from folder
    if candidate_profile is not None:
        result["candidate"] = {
            "name": candidate_profile.full_name,
            "email": candidate_profile.email,
            "location": candidate_profile.location,
            "desired_titles": candidate_profile.desired_titles,
            "skills": candidate_profile.skills[:10],  # Top 10 skills
        }

    # Step 5: (Optional) Match and rank jobs
    if match_jobs:
        # Convert candidate to profile dict for matching
        candidate_for_matching = _normalize_candidate_for_matching(candidate_or_query)

        # Match each job and collect results
        matches = _match_and_rank_jobs(candidate_for_matching, jobs)

        result["matches"] = matches
        result["counts"]["matches"] = len(matches)

    return result


def _build_query_from_input(candidate_or_query) -> dict:
    """
    Build search query from various input formats.

    Handles:
    - CandidateProfile instance → build_search_query
    - dict with CandidateProfile fields → build_search_query
    - dict with SearchQuery fields (titles, keywords) → passthrough
    - dict with legacy fields (desired_title, skills_years) → build_job_query

    Args:
        candidate_or_query: Input in one of the supported formats

    Returns:
        Search query dict
    """
    from jobflow.app.core.candidate_profile import CandidateProfile
    from jobflow.app.core.candidate_query_builder import build_search_query
    from jobflow.app.core.search_query import build_job_query

    # Handle CandidateProfile instance
    if isinstance(candidate_or_query, CandidateProfile):
        return build_search_query(candidate_or_query)

    # Handle dict
    if isinstance(candidate_or_query, dict):
        # Check if it's already a SearchQuery (has titles/keywords/remote_ok)
        if "titles" in candidate_or_query and "keywords" in candidate_or_query:
            # Already a search query, use as-is
            return candidate_or_query

        # Check if it's CandidateProfile-style (has full_name, email, etc.)
        if "full_name" in candidate_or_query or "email" in candidate_or_query:
            # Convert to CandidateProfile and build query
            profile = CandidateProfile.from_dict(candidate_or_query)
            return build_search_query(profile)

        # Otherwise, assume legacy format (desired_title, skills_years, etc.)
        # Use old build_job_query
        return build_job_query(candidate_or_query)

    # Fallback: treat as legacy dict
    return build_job_query(candidate_or_query)


def _normalize_candidate_for_matching(candidate_or_query) -> dict:
    """
    Normalize candidate input to dict format for matching.

    Converts various input formats to a consistent dict that can be
    passed to the job matcher.

    Args:
        candidate_or_query: Candidate input in any supported format

    Returns:
        Dict with candidate profile fields
    """
    from jobflow.app.core.candidate_profile import CandidateProfile

    # Handle CandidateProfile instance
    if isinstance(candidate_or_query, CandidateProfile):
        # Convert to dict using raw if available, otherwise build from fields
        if candidate_or_query.raw:
            return candidate_or_query.raw.copy()
        else:
            return {
                "full_name": candidate_or_query.full_name,
                "email": candidate_or_query.email,
                "phone": candidate_or_query.phone,
                "location": candidate_or_query.location,
                "desired_titles": candidate_or_query.desired_titles,
                "skills": candidate_or_query.skills,
                "years_experience": candidate_or_query.years_experience,
                "work_authorization": candidate_or_query.work_authorization,
                "preferred_locations": candidate_or_query.preferred_locations,
                "remote_ok": candidate_or_query.remote_ok,
                "resume_text": candidate_or_query.resume_text,
            }

    # Handle dict
    if isinstance(candidate_or_query, dict):
        # Check if it's CandidateProfile-style or legacy, return as-is
        return candidate_or_query

    # Fallback: empty dict
    return {}


def _match_and_rank_jobs(candidate_profile: dict, jobs: list) -> list[dict]:
    """
    Match candidate to jobs and return ranked results.

    Filters out rejects and sorts by overall score descending.

    Args:
        candidate_profile: Dict with candidate profile fields
        jobs: List of JobPosting instances

    Returns:
        List of match result dicts with job details, sorted by score
    """
    from jobflow.app.core.job_matcher import match_job

    matches = []

    for job in jobs:
        # Match candidate to job
        match_result = match_job(candidate_profile, job)

        # Filter out rejects
        if match_result.decision == "reject":
            continue

        # Serialize match result and include job details
        match_dict = match_result.to_dict()

        # Add job details for convenience
        match_dict["job_title"] = job.title
        match_dict["job_company"] = job.company
        match_dict["job_location"] = job.location
        match_dict["job_url"] = job.url

        matches.append(match_dict)

    # Sort by overall score descending
    matches.sort(key=lambda m: m["overall_score"], reverse=True)

    return matches
