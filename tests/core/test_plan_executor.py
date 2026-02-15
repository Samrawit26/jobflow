"""
Unit tests for plan_executor.py

Tests the complete planning and execution flow with approval artifact enforcement.
"""

import json
from unittest.mock import Mock, patch

import pytest

from jobflow.app.core.approval_artifact import create_approval
from jobflow.app.core.plan_executor import (
    PlanRejectedError,
    execute_from_directive,
)


@pytest.fixture
def mock_plan():
    """A valid plan returned by the planner that passes policy checks."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [],  # No risks - required for policy approval
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }


@pytest.fixture
def mock_orchestrator_result():
    """A result returned by the orchestrator."""
    return {
        "status": "success",
        "pipeline": "job_discovery",
        "normalized_job": {
            "title": "Software Engineer",
            "company": "TechCorp",
            "location": "Remote"
        }
    }


@pytest.fixture
def mock_openai_response(mock_plan):
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps(mock_plan)
    return mock_response


def test_execute_from_directive_requires_approval_parameter(mock_openai_response):
    """Test that execution fails when approval parameter is missing."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Missing approval parameter should raise TypeError
            with pytest.raises(TypeError) as exc_info:
                execute_from_directive("job_discovery")

            # Error message should mention missing parameter
            assert "approval" in str(exc_info.value).lower()


def test_execute_from_directive_rejects_invalid_approval(mock_openai_response):
    """Test that execution fails with invalid approval artifact."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Invalid approval (not a dict)
            with pytest.raises(PlanRejectedError) as exc_info:
                execute_from_directive("job_discovery", approval="invalid")

            error_message = str(exc_info.value)
            assert "Approval verification failed" in error_message
            assert "must be a dict" in error_message


def test_execute_from_directive_rejects_approval_missing_keys(
    mock_openai_response,
    mock_plan
):
    """Test that execution fails with approval missing required keys."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Approval missing plan_hash
            invalid_approval = {
                "approved_by": "policy",
                "scope": "single-run",
                "approved_at": "2025-01-01T00:00:00+00:00"
            }

            with pytest.raises(PlanRejectedError) as exc_info:
                execute_from_directive("job_discovery", approval=invalid_approval)

            error_message = str(exc_info.value)
            assert "Approval verification failed" in error_message
            assert "missing required keys" in error_message


def test_execute_from_directive_rejects_mismatched_plan_hash(
    mock_openai_response,
    mock_plan
):
    """Test that execution fails when plan hash doesn't match approval."""
    # Create approval for a different plan
    different_plan = {
        "pipeline_name": "job_discovery",
        "steps": ["different step"],
        "risks": [],
        "assumptions": []
    }
    approval = create_approval(different_plan, "policy")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(PlanRejectedError) as exc_info:
                execute_from_directive("job_discovery", approval=approval)

            error_message = str(exc_info.value)
            assert "Approval verification failed" in error_message
            assert "Plan hash mismatch" in error_message


def test_execute_from_directive_succeeds_with_valid_approval(
    mock_openai_response,
    mock_orchestrator_result,
    mock_plan
):
    """Test successful execution with valid approval artifact."""
    # Create valid approval for the plan
    approval = create_approval(mock_plan, "policy")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            mock_run_pipeline.return_value = mock_orchestrator_result

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = execute_from_directive(
                    "job_discovery",
                    approval=approval
                )

                # Verify orchestrator was called
                mock_run_pipeline.assert_called_once_with("job_discovery", {})

                # Verify result structure
                assert result["status"] == "success"
                assert result["pipeline"] == "job_discovery"
                assert "_plan_metadata" in result
                assert "_approval_metadata" in result

                # Verify approval metadata
                approval_meta = result["_approval_metadata"]
                assert approval_meta["approved_by"] == "policy"
                assert approval_meta["scope"] == "single-run"
                assert approval_meta["approved_at"] is not None


def test_execute_from_directive_preserves_rejection_reason(mock_openai_response):
    """Test that rejection reasons from approval verification are preserved."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Use invalid approval with wrong type for plan_hash
            invalid_approval = {
                "plan_hash": 12345,  # Wrong type
                "approved_by": "policy",
                "scope": "single-run",
                "approved_at": "2025-01-01T00:00:00+00:00"
            }

            with pytest.raises(PlanRejectedError) as exc_info:
                execute_from_directive("job_discovery", approval=invalid_approval)

            error_message = str(exc_info.value)
            # Should include exact reason from verify_approval
            assert "plan_hash must be a string" in error_message


def test_execute_from_directive_with_payload(
    mock_openai_response,
    mock_orchestrator_result,
    mock_plan
):
    """Test that payload is passed through to orchestrator."""
    payload = {
        "title": "Data Scientist",
        "company": "AI Corp"
    }

    approval = create_approval(mock_plan, "policy")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            mock_run_pipeline.return_value = mock_orchestrator_result

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                execute_from_directive(
                    "job_discovery",
                    approval=approval,
                    payload=payload
                )

                # Verify payload was passed to orchestrator
                mock_run_pipeline.assert_called_once_with("job_discovery", payload)


def test_execute_from_directive_includes_plan_metadata(
    mock_openai_response,
    mock_orchestrator_result,
    mock_plan
):
    """Test that plan metadata is included in result."""
    approval = create_approval(mock_plan, "admin", scope="session")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            mock_run_pipeline.return_value = mock_orchestrator_result

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = execute_from_directive(
                    "job_discovery",
                    approval=approval
                )

                # Verify plan metadata
                metadata = result["_plan_metadata"]
                assert metadata["directive_name"] == "job_discovery"
                assert metadata["pipeline_name"] == "job_discovery"
                assert len(metadata["planned_steps"]) == 4
                assert len(metadata["identified_risks"]) == 0
                assert len(metadata["assumptions"]) == 2

                # Verify approval metadata
                approval_meta = result["_approval_metadata"]
                assert approval_meta["approved_by"] == "admin"
                assert approval_meta["scope"] == "session"


def test_execute_from_directive_missing_directive(mock_plan):
    """Test that missing directive file raises FileNotFoundError."""
    approval = create_approval(mock_plan, "policy")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with pytest.raises(FileNotFoundError) as exc_info:
            execute_from_directive("nonexistent_directive", approval=approval)

        error_message = str(exc_info.value)
        assert "Directive not found" in error_message
        assert "nonexistent_directive.md" in error_message


def test_execute_from_directive_missing_api_key(mock_plan):
    """Test that missing OPENAI_API_KEY raises ValueError."""
    approval = create_approval(mock_plan, "policy")

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            execute_from_directive("job_discovery", approval=approval)

        assert "OPENAI_API_KEY" in str(exc_info.value)


def test_execute_from_directive_no_execution_without_valid_approval(
    mock_openai_response
):
    """CRITICAL TEST: Verify execution is impossible without valid approval."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Try to execute with invalid approval
                invalid_approval = {"invalid": "approval"}

                try:
                    execute_from_directive("job_discovery", approval=invalid_approval)
                except PlanRejectedError:
                    pass

                # CRITICAL: Orchestrator should NEVER be called
                mock_run_pipeline.assert_not_called()


def test_execute_from_directive_invalid_scope_rejected(
    mock_openai_response,
    mock_plan
):
    """Test that invalid scope in approval is rejected."""
    # Create approval with invalid scope
    approval = {
        "plan_hash": create_approval(mock_plan, "policy")["plan_hash"],
        "approved_by": "policy",
        "scope": "invalid-scope",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(PlanRejectedError) as exc_info:
                execute_from_directive("job_discovery", approval=approval)

            error_message = str(exc_info.value)
            assert "Invalid scope" in error_message
            assert "invalid-scope" in error_message


def test_execute_from_directive_default_payload(
    mock_openai_response,
    mock_orchestrator_result,
    mock_plan
):
    """Test that payload defaults to empty dict when not provided."""
    approval = create_approval(mock_plan, "policy")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            mock_run_pipeline.return_value = mock_orchestrator_result

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Call without payload parameter
                execute_from_directive("job_discovery", approval=approval)

                # Verify empty dict was used
                call_args = mock_run_pipeline.call_args
                assert call_args[0][1] == {}


def test_execute_from_directive_approval_metadata_structure(
    mock_openai_response,
    mock_orchestrator_result,
    mock_plan
):
    """Test that approval metadata has correct structure."""
    approval = create_approval(mock_plan, "user@example.com", scope="session")

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("jobflow.app.core.plan_executor.run_pipeline") as mock_run_pipeline:
            mock_run_pipeline.return_value = mock_orchestrator_result

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = execute_from_directive(
                    "job_discovery",
                    approval=approval
                )

                # Verify approval metadata structure
                approval_meta = result["_approval_metadata"]
                assert "approved_by" in approval_meta
                assert "approved_at" in approval_meta
                assert "scope" in approval_meta

                assert approval_meta["approved_by"] == "user@example.com"
                assert approval_meta["scope"] == "session"
                assert isinstance(approval_meta["approved_at"], str)
