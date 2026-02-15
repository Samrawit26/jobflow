"""
Batch Candidate Processing Pipeline

Approval-gated pipeline for processing multiple candidate folders.
"""


def run(payload: dict) -> dict:
    """
    Execute batch candidate processing pipeline.

    This is the approval-gated entrypoint for batch processing.
    Should only be called through the executor after approval verification.

    Args:
        payload: Dict with:
            - candidates_dir (str, required): Directory with candidate folders
            - jobs (str, required): Path to jobs JSON file
            - out (str, required): Output directory
            - match_jobs (bool, optional): Enable matching (default True)

    Returns:
        Dict with:
        - status: "success" or "error"
        - payload: Echo of input payload (safe subset)
        - processed: Number of candidates processed
        - succeeded: Number of successful candidates
        - failed: Number of failed candidates
        - summary_path: Path to summary.csv
        - errors_path: Path to errors.json
        - results_dir: Path to results directory

    Raises:
        KeyError: If required payload keys missing
        FileNotFoundError: If candidates_dir or jobs file not found
    """
    from jobflow.app.core.batch_runner import run_batch
    from jobflow.app.core.file_job_source import FileJobSource

    # Validate required payload keys
    if "candidates_dir" not in payload:
        raise KeyError("payload missing required key: 'candidates_dir'")
    if "jobs" not in payload:
        raise KeyError("payload missing required key: 'jobs'")
    if "out" not in payload:
        raise KeyError("payload missing required key: 'out'")

    candidates_dir = payload["candidates_dir"]
    jobs_path = payload["jobs"]
    out_dir = payload["out"]
    match_jobs = payload.get("match_jobs", True)

    # Create job source
    job_source = FileJobSource("jobs", jobs_path)

    # Run batch processing
    batch_result = run_batch(
        candidates_dir=candidates_dir,
        job_sources=[job_source],
        out_dir=out_dir,
        match_jobs=match_jobs,
    )

    # Build response with echo of safe payload subset
    result = {
        "status": "success",
        "payload": {
            "candidates_dir": candidates_dir,
            "jobs": jobs_path,
            "out": out_dir,
            "match_jobs": match_jobs,
        },
        "processed": batch_result["processed"],
        "succeeded": batch_result["succeeded"],
        "failed": batch_result["failed"],
        "summary_path": batch_result["summary_path"],
        "errors_path": batch_result["errors_path"],
        "results_dir": batch_result["results_dir"],
    }

    return result
