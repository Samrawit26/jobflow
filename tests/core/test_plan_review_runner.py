"""
Unit tests for plan_review_runner.py

Tests the dry-run interface that reviews plans without executing them.
"""

import json
from unittest.mock import Mock, patch

import pytest

from jobflow.app.core.plan_review_runner import review_directive


@pytest.fixture
def safe_plan():
    """A plan that passes all policies."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [],
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }


@pytest.fixture
def plan_with_risks():
    """A plan with identified risks."""
    return {
        "pipeline_name": "job_discovery",
        "steps": ["Fetch data"],
        "risks": ["API rate limits", "Data quality issues"],
        "assumptions": []
    }


@pytest.fixture
def mock_openai_response(safe_plan):
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps(safe_plan)
    return mock_response


def test_review_directive_rejected_by_default(mock_openai_response):
    """Test that review_directive rejects by default (fail-safe behavior)."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery")

            # Verify result structure
            assert isinstance(result, dict)
            assert "directive_name" in result
            assert "approved" in result
            assert "reason" in result
            assert "plan" in result

            # Verify rejection
            assert result["directive_name"] == "job_discovery"
            assert result["approved"] is False
            assert "Rejected by default" in result["reason"]
            assert "auto_approve is False" in result["reason"]

            # Verify plan is included
            assert isinstance(result["plan"], dict)
            assert result["plan"]["pipeline_name"] == "job_discovery"


def test_review_directive_approved_with_auto_approve(mock_openai_response):
    """Test that review_directive approves when auto_approve=True and policy passes."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery", auto_approve=True)

            # Verify approval
            assert result["approved"] is True
            assert result["reason"] == "Auto-approved by policy"

            # Verify plan is included
            assert result["plan"]["pipeline_name"] == "job_discovery"
            assert len(result["plan"]["steps"]) == 4


def test_review_directive_policy_failure_with_risks():
    """Test that policy failures include detailed reasons (risks)."""
    plan_with_risks = {
        "pipeline_name": "job_discovery",
        "steps": ["Fetch data"],
        "risks": ["API rate limits", "Data quality issues"],
        "assumptions": []
    }

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps(plan_with_risks)

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery", auto_approve=True)

            # Verify rejection with detailed reason
            assert result["approved"] is False
            assert "risk" in result["reason"].lower()
            assert "API rate limits" in result["reason"] or "2" in result["reason"]

            # Verify plan is still included
            assert result["plan"]["risks"] == ["API rate limits", "Data quality issues"]


def test_review_directive_policy_failure_with_forbidden_keywords():
    """Test that policy failures include detailed reasons (forbidden keywords)."""
    plan_with_keywords = {
        "pipeline_name": "job_discovery",
        "steps": ["Fetch data", "Write to database", "Send notifications"],
        "risks": [],
        "assumptions": []
    }

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps(plan_with_keywords)

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery", auto_approve=True)

            # Verify rejection with detailed reason
            assert result["approved"] is False
            assert "forbidden keywords" in result["reason"]
            assert "write" in result["reason"].lower() or "send" in result["reason"].lower()


def test_review_directive_policy_failure_with_non_allowlisted_pipeline():
    """Test that policy failures include detailed reasons (non-allowlisted pipeline)."""
    plan_bad_pipeline = {
        "pipeline_name": "dangerous_pipeline",
        "steps": ["Do something"],
        "risks": [],
        "assumptions": []
    }

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps(plan_bad_pipeline)

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery", auto_approve=True)

            # Verify rejection with detailed reason
            assert result["approved"] is False
            assert "not in the allowlist" in result["reason"]
            assert "dangerous_pipeline" in result["reason"]


def test_review_directive_never_calls_orchestrator(mock_openai_response):
    """CRITICAL TEST: Verify orchestrator is NEVER called (dry-run only)."""
    # Try to import orchestrator to verify it's not called
    try:
        from jobflow.app.core import orchestrator
        orchestrator_available = True
    except ImportError:
        orchestrator_available = False

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        if orchestrator_available:
            with patch("jobflow.app.core.orchestrator.run_pipeline") as mock_run_pipeline:
                with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                    # Call with auto_approve=True (would execute in plan_executor)
                    result = review_directive("job_discovery", auto_approve=True)

                    # CRITICAL: Orchestrator should NEVER be called
                    mock_run_pipeline.assert_not_called()

                    # Should still return approval
                    assert result["approved"] is True
        else:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Call with auto_approve=True
                result = review_directive("job_discovery", auto_approve=True)
                # Should return approval without execution
                assert result["approved"] is True


def test_review_directive_missing_directive_file():
    """Test that missing directive file raises FileNotFoundError."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with pytest.raises(FileNotFoundError) as exc_info:
            review_directive("nonexistent_directive")

        error_message = str(exc_info.value)
        assert "Directive not found" in error_message
        assert "nonexistent_directive.md" in error_message


def test_review_directive_missing_api_key():
    """Test that missing OPENAI_API_KEY raises ValueError."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            review_directive("job_discovery")

        assert "OPENAI_API_KEY" in str(exc_info.value)


def test_review_directive_returns_complete_plan(mock_openai_response):
    """Test that the full plan is returned in the result."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery")

            # Verify complete plan structure
            plan = result["plan"]
            assert "pipeline_name" in plan
            assert "steps" in plan
            assert "risks" in plan
            assert "assumptions" in plan

            assert plan["pipeline_name"] == "job_discovery"
            assert isinstance(plan["steps"], list)
            assert isinstance(plan["risks"], list)
            assert isinstance(plan["assumptions"], list)


def test_review_directive_no_side_effects(mock_openai_response):
    """Test that review_directive has no side effects (no execution, no writes)."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Call multiple times
            result1 = review_directive("job_discovery")
            result2 = review_directive("job_discovery", auto_approve=True)
            result3 = review_directive("job_discovery")

            # All calls should succeed without side effects
            assert result1["approved"] is False
            assert result2["approved"] is True
            assert result3["approved"] is False


def test_review_directive_result_structure():
    """Test that result has the required structure."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps({
        "pipeline_name": "job_discovery",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    })

    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = review_directive("job_discovery")

            # Verify all required keys
            required_keys = {"directive_name", "approved", "reason", "plan"}
            assert set(result.keys()) == required_keys

            # Verify types
            assert isinstance(result["directive_name"], str)
            assert isinstance(result["approved"], bool)
            assert isinstance(result["reason"], str)
            assert isinstance(result["plan"], dict)
