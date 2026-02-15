"""
Unit tests for review CLI script.

Tests the command-line interface for reviewing directives.
"""

import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from jobflow.scripts.review import main


def test_review_cli_default_rejection():
    """Test CLI with default (no auto-approve) - should reject."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": False,
        "reason": "Rejected by default (auto_approve is False)",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["review.py", "job_discovery"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Should succeed (exit code 0 even though rejected)
                assert exit_code == 0

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify output structure
                assert "directive_name" in output
                assert "approved" in output
                assert "reason" in output
                assert "plan" in output

                # Verify values
                assert output["directive_name"] == "job_discovery"
                assert output["approved"] is False
                assert "Rejected by default" in output["reason"]

                # Verify mock was called correctly
                mock_review.assert_called_once_with("job_discovery", auto_approve=False)


def test_review_cli_with_auto_approve():
    """Test CLI with --auto-approve flag."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1", "step2"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["review.py", "job_discovery", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Should succeed
                assert exit_code == 0

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify approval
                assert output["approved"] is True
                assert output["reason"] == "Auto-approved by policy"

                # Verify mock was called with auto_approve=True
                mock_review.assert_called_once_with("job_discovery", auto_approve=True)


def test_review_cli_policy_failure():
    """Test CLI with policy failure (risks present)."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": False,
        "reason": "Plan has 2 identified risk(s). Auto-approval requires zero risks. Risks: ['API rate limits', 'Data quality issues']",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": ["API rate limits", "Data quality issues"],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["review.py", "job_discovery", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Should still succeed (rejection is not a failure)
                assert exit_code == 0

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify rejection with detailed reason
                assert output["approved"] is False
                assert "risk" in output["reason"].lower()
                assert "API rate limits" in output["reason"]


def test_review_cli_output_format():
    """Test that CLI output is properly formatted JSON."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": False,
        "reason": "Test reason",
        "plan": {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["review.py", "job_discovery"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                stdout_value = mock_stdout.getvalue()

                # Output should be valid JSON
                output = json.loads(stdout_value)

                # Output should be sorted and indented (human-readable)
                # Check for indentation by looking for multiple lines
                assert "\n" in stdout_value
                assert "  " in stdout_value  # 2-space indentation


def test_review_cli_never_calls_orchestrator():
    """CRITICAL TEST: Verify orchestrator is NEVER called from CLI."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {"pipeline_name": "job_discovery", "steps": [], "risks": [], "assumptions": []}
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        # Try to import and mock orchestrator
        try:
            from jobflow.app.core import orchestrator
            orchestrator_available = True
        except ImportError:
            orchestrator_available = False

        if orchestrator_available:
            with patch("jobflow.app.core.orchestrator.run_pipeline") as mock_run_pipeline:
                with patch("sys.argv", ["review.py", "job_discovery", "--auto-approve"]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        exit_code = main()

                        # Should succeed
                        assert exit_code == 0

                        # CRITICAL: Orchestrator should NEVER be called
                        mock_run_pipeline.assert_not_called()
        else:
            with patch("sys.argv", ["review.py", "job_discovery", "--auto-approve"]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    exit_code = main()
                    assert exit_code == 0


def test_review_cli_missing_directive_file():
    """Test CLI with non-existent directive."""
    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.side_effect = FileNotFoundError("Directive not found: directives/nonexistent.md")

        with patch("sys.argv", ["review.py", "nonexistent"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    exit_code = main()

                    # Should fail with error
                    assert exit_code == 1

                    # Error should be in stderr
                    error = json.loads(mock_stderr.getvalue())
                    assert "error" in error
                    assert error["error"] == "FileNotFoundError"
                    assert "directive_name" in error


def test_review_cli_missing_api_key():
    """Test CLI with missing OPENAI_API_KEY."""
    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.side_effect = ValueError("OPENAI_API_KEY environment variable is not set")

        with patch("sys.argv", ["review.py", "job_discovery"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    exit_code = main()

                    # Should fail with error
                    assert exit_code == 1

                    # Error should be in stderr
                    error = json.loads(mock_stderr.getvalue())
                    assert error["error"] == "ValueError"
                    assert "OPENAI_API_KEY" in error["message"]


def test_review_cli_help():
    """Test CLI help message."""
    with patch("sys.argv", ["review.py", "--help"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            # argparse exits on --help, so we need to catch SystemExit
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 (success)
            assert exc_info.value.code == 0

            stdout_value = mock_stdout.getvalue()

            # Help should be in stdout
            assert "directive_name" in stdout_value
            assert "--auto-approve" in stdout_value
            assert "dry-run" in stdout_value.lower()


def test_review_cli_complete_plan_output():
    """Test that CLI outputs the complete plan structure."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1", "step2", "step3"],
            "risks": [],
            "assumptions": ["assumption1", "assumption2"]
        }
    }

    with patch("jobflow.scripts.review.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["review.py", "job_discovery", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify complete plan structure
                assert "plan" in output
                plan = output["plan"]
                assert "pipeline_name" in plan
                assert "steps" in plan
                assert "risks" in plan
                assert "assumptions" in plan

                assert len(plan["steps"]) == 3
                assert len(plan["assumptions"]) == 2
