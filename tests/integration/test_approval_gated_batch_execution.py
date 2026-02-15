"""
Integration tests for approval-gated batch execution.

Tests the complete flow: review → approve → execute with the batch pipeline.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_openai_for_batch_run():
    """Mock OpenAI API for batch_run directive tests."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps({
        "pipeline_name": "batch_candidate_processing",
        "steps": [
            "Load candidate folders",
            "Process each candidate",
            "Generate summary and results"
        ],
        "risks": [
            "File I/O errors",
            "Invalid candidate data"
        ],
        "assumptions": [
            "Candidates directory exists",
            "Jobs file is valid JSON"
        ]
    })

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_openai_class


def test_batch_execution_with_valid_approval(tmp_path, monkeypatch, mock_openai_for_batch_run):
    """Test batch execution with valid approval succeeds."""
    from jobflow.app.core.approval_artifact import create_approval
    from jobflow.app.core.plan_executor import execute_from_directive
    from jobflow.app.services.planner import build_plan

    # Set up test environment
    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    # Mock OpenAI API key
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_1234567890")

    # Step 1: Build plan
    plan = build_plan("batch_run")

    # Verify plan structure
    assert "pipeline_name" in plan
    assert plan["pipeline_name"] == "batch_candidate_processing"

    # Step 2: Create approval artifact
    approval = create_approval(plan, "test_user")

    # Step 3: Execute with approval
    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        "match_jobs": True,
    }

    result = execute_from_directive("batch_run", approval, payload)

    # Verify execution succeeded
    assert result["status"] == "success"
    assert result["pipeline"] == "batch_candidate_processing"

    # Verify approval metadata included
    assert "_approval_metadata" in result
    approval_meta = result["_approval_metadata"]
    assert approval_meta["approved_by"] == "test_user"
    assert "approved_at" in approval_meta

    # Verify batch results
    data = result["data"]
    assert data["processed"] >= 1
    assert data["succeeded"] >= 1

    # Verify output files created
    assert Path(data["summary_path"]).exists()


def test_batch_execution_without_approval_fails(tmp_path, monkeypatch, mock_openai_for_batch_run):
    """Test that execution without approval raises PlanRejectedError."""
    from jobflow.app.core.plan_executor import PlanRejectedError, execute_from_directive

    # Set up test environment
    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    monkeypatch.setenv("OPENAI_API_KEY", "test_key_1234567890")

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    # Try to execute without approval
    with pytest.raises(PlanRejectedError, match="missing required keys"):
        execute_from_directive("batch_run", {}, payload)


def test_batch_execution_with_mismatched_approval_fails(tmp_path, monkeypatch, mock_openai_for_batch_run):
    """Test that execution with mismatched approval fails."""
    from jobflow.app.core.approval_artifact import create_approval
    from jobflow.app.core.plan_executor import PlanRejectedError, execute_from_directive
    from jobflow.app.services.planner import build_plan

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    monkeypatch.setenv("OPENAI_API_KEY", "test_key_1234567890")

    # Build plan for batch_run
    plan = build_plan("batch_run")

    # Create approval
    approval = create_approval(plan, "test_user")

    # Modify plan hash to simulate tampering
    approval["plan_hash"] = "invalid_hash_1234567890abcdef"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
    }

    # Try to execute with mismatched approval
    with pytest.raises(PlanRejectedError, match="hash mismatch"):
        execute_from_directive("batch_run", approval, payload)


def test_batch_execution_session_scope_allows_multiple_runs(tmp_path, monkeypatch, mock_openai_for_batch_run):
    """Test that session-scope approval allows multiple executions."""
    from jobflow.app.core.approval_artifact import create_approval
    from jobflow.app.core.plan_executor import execute_from_directive
    from jobflow.app.services.planner import build_plan

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir1 = tmp_path / "output1"
    out_dir2 = tmp_path / "output2"

    monkeypatch.setenv("OPENAI_API_KEY", "test_key_1234567890")

    # Build plan
    plan = build_plan("batch_run")

    # Create session-scope approval
    approval = create_approval(plan, "test_user", scope="session")

    # First execution
    payload1 = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir1),
    }

    result1 = execute_from_directive("batch_run", approval, payload1)
    assert result1["status"] == "success"

    # Second execution with same approval should succeed
    payload2 = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir2),
    }

    result2 = execute_from_directive("batch_run", approval, payload2)
    assert result2["status"] == "success"

    # Both outputs should exist
    assert Path(result1["data"]["summary_path"]).exists()
    assert Path(result2["data"]["summary_path"]).exists()


def test_batch_execution_verifies_directive_router_mapping(monkeypatch):
    """Test that directive router correctly maps batch_run."""
    from jobflow.app.core.directive_router import resolve_pipeline

    # Verify mapping exists
    pipeline_name = resolve_pipeline("batch_run")
    assert pipeline_name == "batch_candidate_processing"


def test_batch_execution_orchestrator_supports_pipeline(tmp_path):
    """Test that orchestrator can execute batch pipeline."""
    from jobflow.app.core.orchestrator import run_pipeline

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    payload = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir),
        "match_jobs": True,
    }

    result = run_pipeline("batch_candidate_processing", payload)

    # Verify result structure
    assert result["status"] == "success"
    assert result["pipeline"] == "batch_candidate_processing"
    assert "data" in result

    # Verify batch results
    data = result["data"]
    assert data["processed"] >= 1
    assert Path(data["summary_path"]).exists()


def test_batch_execution_unknown_directive_fails():
    """Test that unknown directive raises error."""
    from jobflow.app.core.directive_router import resolve_pipeline

    with pytest.raises(ValueError, match="Unknown directive"):
        resolve_pipeline("nonexistent_directive")


def test_batch_execution_deterministic(tmp_path, monkeypatch, mock_openai_for_batch_run):
    """Test that approved batch execution is deterministic."""
    from jobflow.app.core.approval_artifact import create_approval
    from jobflow.app.core.plan_executor import execute_from_directive
    from jobflow.app.services.planner import build_plan

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir1 = tmp_path / "output1"
    out_dir2 = tmp_path / "output2"

    monkeypatch.setenv("OPENAI_API_KEY", "test_key_1234567890")

    # Build plan once
    plan = build_plan("batch_run")

    # Create session approval for multiple runs
    approval = create_approval(plan, "test_user", scope="session")

    # Run twice with same inputs (different output dirs)
    payload1 = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir1),
        "match_jobs": True,
    }

    payload2 = {
        "candidates_dir": str(candidates_dir),
        "jobs": str(jobs_file),
        "out": str(out_dir2),
        "match_jobs": True,
    }

    result1 = execute_from_directive("batch_run", approval, payload1)
    result2 = execute_from_directive("batch_run", approval, payload2)

    # Results should be identical (excluding paths)
    assert result1["status"] == result2["status"]
    assert result1["data"]["processed"] == result2["data"]["processed"]
    assert result1["data"]["succeeded"] == result2["data"]["succeeded"]
    assert result1["data"]["failed"] == result2["data"]["failed"]
