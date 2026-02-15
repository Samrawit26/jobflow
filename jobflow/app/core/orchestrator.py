"""
Pipeline orchestrator.

Synchronous, deterministic bridge between pipelines and execution scripts.
No async, no Redis, no workers, no agents - just function calls.
"""

from typing import Any, Dict

from execution.normalize_job_posting import normalize_job_posting


class PipelineNotFoundError(Exception):
    """Raised when an unknown pipeline is requested."""

    pass


class PipelineExecutionError(Exception):
    """Raised when a pipeline execution fails."""

    pass


def run_pipeline(pipeline_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a pipeline synchronously.

    This is a deterministic orchestrator that calls execution scripts
    directly based on the pipeline name. No async workers or queues.

    Args:
        pipeline_name: Name of the pipeline to run (e.g., "job_discovery")
        payload: Input data for the pipeline

    Returns:
        Pipeline execution result

    Raises:
        PipelineNotFoundError: If pipeline_name is not recognized
        PipelineExecutionError: If pipeline execution fails

    Example:
        >>> payload = {"title": "Software Engineer", "company": "Acme"}
        >>> result = run_pipeline("job_discovery", payload)
        >>> result["title"]
        'Software Engineer'
    """
    if pipeline_name == "job_discovery":
        return _run_job_discovery_pipeline(payload)
    elif pipeline_name == "batch_candidate_processing":
        return _run_batch_candidate_processing_pipeline(payload)
    else:
        raise PipelineNotFoundError(
            f"Unknown pipeline: {pipeline_name}. "
            f"Supported pipelines: job_discovery, batch_candidate_processing"
        )


def _run_job_discovery_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the job discovery pipeline.

    Currently simplified to just normalize the job posting.
    Future: will coordinate multiple steps (fetch, parse, deduplicate, store).

    Args:
        payload: Raw job posting data

    Returns:
        Normalized job posting data

    Raises:
        PipelineExecutionError: If normalization fails
    """
    try:
        # Step 1: Normalize job posting
        # (Future steps: fetch_jobs, parse_jobs, deduplicate_jobs, store_jobs)
        normalized = normalize_job_posting(payload)

        return {
            "status": "success",
            "pipeline": "job_discovery",
            "data": normalized,
        }

    except Exception as e:
        raise PipelineExecutionError(
            f"Job discovery pipeline failed: {str(e)}"
        ) from e


def _run_batch_candidate_processing_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the batch candidate processing pipeline.

    Processes multiple candidate folders through the job discovery workflow
    with approval-gated execution.

    Args:
        payload: Dict with candidates_dir, jobs, out, match_jobs

    Returns:
        Batch processing results with counts and file paths

    Raises:
        PipelineExecutionError: If batch processing fails
    """
    try:
        # Import and call the pipeline entrypoint
        from pipelines.batch_candidate_processing import run

        result = run(payload)

        return {
            "status": "success",
            "pipeline": "batch_candidate_processing",
            "data": result,
        }

    except Exception as e:
        raise PipelineExecutionError(
            f"Batch candidate processing pipeline failed: {str(e)}"
        ) from e
