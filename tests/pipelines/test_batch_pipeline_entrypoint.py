"""
Unit tests for batch_candidate_processing pipeline entrypoint.

Tests the approval-gated batch processing pipeline.
"""

from pathlib import Path

import pytest


def test_batch_pipeline_run_basic(tmp_path):
    """Test basic batch pipeline execution."""
    from pipelines.batch_candidate_processing import run

    # Use fixtures
    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        "match_jobs": True,
    }

    result = run(payload)

    # Verify result structure
    assert result["status"] == "success"
    assert "payload" in result
    assert "processed" in result
    assert "succeeded" in result
    assert "failed" in result
    assert "summary_path" in result
    assert "errors_path" in result
    assert "results_dir" in result

    # Verify payload echo
    assert result["payload"]["candidates_dir"] == str(candidates_dir)
    assert result["payload"]["jobs"] == str(jobs_file)
    assert result["payload"]["out"] == str(out_dir)
    assert result["payload"]["match_jobs"] is True

    # Verify counts
    assert result["processed"] >= 1
    assert result["succeeded"] >= 1

    # Verify output files exist
    assert Path(result["summary_path"]).exists()
    assert Path(result["errors_path"]).exists()
    assert Path(result["results_dir"]).exists()


def test_batch_pipeline_run_no_matching(tmp_path):
    """Test batch pipeline with matching disabled."""
    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        "match_jobs": False,
    }

    result = run(payload)

    assert result["status"] == "success"
    assert result["payload"]["match_jobs"] is False


def test_batch_pipeline_run_missing_required_key():
    """Test that missing required keys raise KeyError."""
    from pipelines.batch_candidate_processing import run

    # Missing candidates_dir
    with pytest.raises(KeyError, match="candidates_dir"):
        run({"jobs": "jobs.json", "out": "out"})

    # Missing jobs
    with pytest.raises(KeyError, match="jobs"):
        run({"candidates_dir": "candidates", "out": "out"})

    # Missing out
    with pytest.raises(KeyError, match="out"):
        run({"candidates_dir": "candidates", "jobs": "jobs.json"})


def test_batch_pipeline_run_default_match_jobs(tmp_path):
    """Test that match_jobs defaults to True."""
    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        # match_jobs not specified
    }

    result = run(payload)

    # Should default to True
    assert result["payload"]["match_jobs"] is True


def test_batch_pipeline_creates_output_dir(tmp_path):
    """Test that pipeline creates output directory if needed."""
    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    # Nested dir that doesn't exist
    out_dir = tmp_path / "nested" / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    result = run(payload)

    assert result["status"] == "success"
    assert out_dir.exists()


def test_batch_pipeline_output_files_exist(tmp_path):
    """Test that all expected output files are created."""
    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    result = run(payload)

    # summary.csv should exist
    summary_path = Path(result["summary_path"])
    assert summary_path.exists()
    assert summary_path.name == "summary.csv"

    # errors.json should exist
    errors_path = Path(result["errors_path"])
    assert errors_path.exists()
    assert errors_path.name == "errors.json"

    # results/ subdirectory should exist
    results_dir = Path(result["results_dir"])
    assert results_dir.exists()
    assert results_dir.is_dir()

    # Should have at least one candidate result
    candidate_results = list(results_dir.glob("*/results.json"))
    assert len(candidate_results) >= 1


def test_batch_pipeline_summary_csv_format(tmp_path):
    """Test that summary.csv has correct format."""
    import csv

    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    result = run(payload)

    # Read summary CSV
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have at least one row
    assert len(rows) >= 1

    # Check headers (includes fit counts and URL counts since apply packs are enabled by default)
    expected_headers = {
        "candidate_id",
        "folder",
        "num_jobs",
        "num_matches",
        "top_score",
        "num_strong_fit",
        "num_possible_fit",
        "num_weak_fit",
        "num_url_allowed",
        "num_url_manual_review",
        "num_url_blocked",
        "num_errors",
        "status",
    }
    assert set(rows[0].keys()) == expected_headers

    # Check data types
    row = rows[0]
    assert row["status"] in {"success", "failed"}
    assert row["num_jobs"].isdigit()


def test_batch_pipeline_errors_json_format(tmp_path):
    """Test that errors.json has correct format."""
    import json

    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    result = run(payload)

    # Read errors JSON
    with open(result["errors_path"], "r", encoding="utf-8") as f:
        errors = json.load(f)

    # Should be a list
    assert isinstance(errors, list)

    # If successful run, should be empty
    if result["failed"] == 0:
        assert errors == []


def test_batch_pipeline_results_json_structure(tmp_path):
    """Test that per-candidate results have correct structure."""
    import json

    from pipelines.batch_candidate_processing import run

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        "match_jobs": True,
    }

    result = run(payload)

    # Find a candidate result
    results_dir = Path(result["results_dir"])
    candidate_results = list(results_dir.glob("*/results.json"))
    assert len(candidate_results) >= 1

    # Read first result
    with open(candidate_results[0], "r", encoding="utf-8") as f:
        candidate_result = json.load(f)

    # Check structure
    assert "status" in candidate_result
    assert "candidate" in candidate_result
    assert "jobs" in candidate_result
    assert "matches" in candidate_result  # match_jobs=True
    assert "query" in candidate_result
    assert "counts" in candidate_result

    # Check candidate structure
    candidate = candidate_result["candidate"]
    assert "name" in candidate
    assert "email" in candidate
