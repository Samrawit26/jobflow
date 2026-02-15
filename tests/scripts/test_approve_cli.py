"""
Unit tests for approve CLI script.

Tests the command-line interface for issuing approval artifacts.
"""

import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from jobflow.scripts.approve import main


def test_approve_cli_approved_path():
    """Test CLI with approved plan - should issue approval artifact."""
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

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Should succeed
                assert exit_code == 0

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify output structure
                assert "directive_name" in output
                assert "approved" in output
                assert "reason" in output
                assert "plan_hash" in output
                assert "approval" in output

                # Verify values
                assert output["directive_name"] == "job_discovery"
                assert output["approved"] is True
                assert output["reason"] == "Auto-approved by policy"

                # Verify approval artifact structure
                approval = output["approval"]
                assert "plan_hash" in approval
                assert "approved_by" in approval
                assert "scope" in approval
                assert "approved_at" in approval

                assert approval["approved_by"] == "policy"
                assert approval["scope"] == "single-run"  # default

                # Verify plan_hash is included at top level
                assert output["plan_hash"] == approval["plan_hash"]

                # Verify mock was called correctly
                mock_review.assert_called_once_with("job_discovery", auto_approve=True)


def test_approve_cli_rejected_path():
    """Test CLI with rejected plan - should exit with code 2."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": False,
        "reason": "Plan has 2 identified risk(s). Auto-approval requires zero risks.",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": ["risk1", "risk2"],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                # Should exit with code 2 for rejection
                assert exit_code == 2

                # Parse output
                output = json.loads(mock_stdout.getvalue())

                # Verify rejection output
                assert output["directive_name"] == "job_discovery"
                assert output["approved"] is False
                assert "risk" in output["reason"].lower()

                # Should NOT include approval artifact
                assert "approval" not in output
                assert "plan_hash" not in output


def test_approve_cli_with_session_scope():
    """Test CLI with session scope."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", [
            "approve.py", "job_discovery",
            "--approved-by", "admin",
            "--auto-approve",
            "--scope", "session"
        ]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                assert exit_code == 0

                output = json.loads(mock_stdout.getvalue())
                approval = output["approval"]

                assert approval["scope"] == "session"
                assert approval["approved_by"] == "admin"


def test_approve_cli_writes_to_file(tmp_path):
    """Test CLI with --out flag writes to file."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    output_file = tmp_path / "approval.json"

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", [
            "approve.py", "job_discovery",
            "--approved-by", "policy",
            "--auto-approve",
            "--out", str(output_file)
        ]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                assert exit_code == 0

                # Verify file was written
                assert output_file.exists()

                # Verify stdout contains confirmation
                stdout_value = mock_stdout.getvalue()
                assert "Approval artifact written to" in stdout_value
                assert str(output_file) in stdout_value

                # Verify file contents
                with open(output_file, "r", encoding="utf-8") as f:
                    output = json.load(f)

                assert output["approved"] is True
                assert "approval" in output
                assert output["approval"]["approved_by"] == "policy"


def test_approve_cli_default_scope():
    """Test that default scope is single-run."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                output = json.loads(mock_stdout.getvalue())
                assert output["approval"]["scope"] == "single-run"


def test_approve_cli_without_auto_approve():
    """Test CLI without --auto-approve flag (should reject by default)."""
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

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                assert exit_code == 2  # Rejected

                output = json.loads(mock_stdout.getvalue())
                assert output["approved"] is False
                assert "Rejected by default" in output["reason"]

                # Verify review was called with auto_approve=False
                mock_review.assert_called_once_with("job_discovery", auto_approve=False)


def test_approve_cli_missing_directive():
    """Test CLI with non-existent directive."""
    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.side_effect = FileNotFoundError("Directive not found: directives/nonexistent.md")

        with patch("sys.argv", ["approve.py", "nonexistent", "--approved-by", "policy"]):
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


def test_approve_cli_missing_api_key():
    """Test CLI with missing OPENAI_API_KEY."""
    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.side_effect = ValueError("OPENAI_API_KEY environment variable is not set")

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    exit_code = main()

                    # Should fail with error
                    assert exit_code == 1

                    # Error should be in stderr
                    error = json.loads(mock_stderr.getvalue())
                    assert error["error"] == "ValueError"
                    assert "OPENAI_API_KEY" in error["message"]


def test_approve_cli_requires_approved_by():
    """Test that --approved-by is required."""
    with patch("sys.argv", ["approve.py", "job_discovery"]):
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error
            assert exc_info.value.code != 0

            stderr_value = mock_stderr.getvalue()
            assert "--approved-by" in stderr_value or "required" in stderr_value.lower()


def test_approve_cli_never_calls_orchestrator():
    """CRITICAL TEST: Verify orchestrator is NEVER called."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        # Try to import and mock orchestrator
        try:
            from jobflow.app.core import orchestrator
            orchestrator_available = True
        except ImportError:
            orchestrator_available = False

        if orchestrator_available:
            with patch("jobflow.app.core.orchestrator.run_pipeline") as mock_run_pipeline:
                with patch("sys.argv", [
                    "approve.py", "job_discovery",
                    "--approved-by", "policy",
                    "--auto-approve"
                ]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        exit_code = main()

                        # Should succeed
                        assert exit_code == 0

                        # CRITICAL: Orchestrator should NEVER be called
                        mock_run_pipeline.assert_not_called()
        else:
            with patch("sys.argv", [
                "approve.py", "job_discovery",
                "--approved-by", "policy",
                "--auto-approve"
            ]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    exit_code = main()
                    assert exit_code == 0


def test_approve_cli_help():
    """Test CLI help message."""
    with patch("sys.argv", ["approve.py", "--help"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            # argparse exits on --help
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 (success)
            assert exc_info.value.code == 0

            stdout_value = mock_stdout.getvalue()

            # Help should mention key options
            assert "directive_name" in stdout_value
            assert "--approved-by" in stdout_value
            assert "--auto-approve" in stdout_value
            assert "--scope" in stdout_value
            assert "--out" in stdout_value


def test_approve_cli_output_format():
    """Test that output is properly formatted JSON."""
    mock_result = {
        "directive_name": "job_discovery",
        "approved": True,
        "reason": "Auto-approved by policy",
        "plan": {
            "pipeline_name": "job_discovery",
            "steps": ["step1"],
            "risks": [],
            "assumptions": []
        }
    }

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", ["approve.py", "job_discovery", "--approved-by", "policy", "--auto-approve"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                stdout_value = mock_stdout.getvalue()

                # Output should be valid JSON
                output = json.loads(stdout_value)

                # Output should be sorted and indented (human-readable)
                assert "\n" in stdout_value
                assert "  " in stdout_value  # 2-space indentation


def test_approve_cli_complete_approval_output():
    """Test that approval artifact has complete structure."""
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

    with patch("jobflow.scripts.approve.review_directive") as mock_review:
        mock_review.return_value = mock_result

        with patch("sys.argv", [
            "approve.py", "job_discovery",
            "--approved-by", "user@example.com",
            "--auto-approve",
            "--scope", "session"
        ]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = main()

                output = json.loads(mock_stdout.getvalue())

                # Verify complete approval structure
                approval = output["approval"]
                assert "plan_hash" in approval
                assert "approved_by" in approval
                assert "scope" in approval
                assert "approved_at" in approval

                assert approval["approved_by"] == "user@example.com"
                assert approval["scope"] == "session"
                assert isinstance(approval["approved_at"], str)
                assert isinstance(approval["plan_hash"], str)
                assert len(approval["plan_hash"]) == 64  # SHA-256 hex
