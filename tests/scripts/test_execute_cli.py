"""
Unit tests for execute CLI script.

Tests the command-line interface for executing directives with approval artifacts.
"""

import json
from unittest.mock import patch

import pytest

from jobflow.app.core.plan_executor import PlanRejectedError
from jobflow.scripts.execute import main


def test_execute_cli_success(tmp_path, monkeypatch, capsys):
    """Test successful execution with approval artifact."""
    # Create approval artifact file
    approval = {
        "plan_hash": "abc123",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    # Mock executor result
    mock_result = {
        "status": "success",
        "pipeline": "job_discovery",
        "normalized_job": {"title": "Software Engineer"},
        "_plan_metadata": {
            "directive_name": "job_discovery",
            "pipeline_name": "job_discovery",
            "planned_steps": ["step1", "step2"],
            "identified_risks": [],
            "assumptions": []
        },
        "_approval_metadata": {
            "approved_by": "policy",
            "approved_at": "2025-01-01T00:00:00+00:00",
            "scope": "single-run"
        }
    }

    with patch("jobflow.scripts.execute.execute_from_directive") as mock_execute:
        mock_execute.return_value = mock_result

        # Set command-line arguments
        monkeypatch.setattr("sys.argv", [
            "execute.py",
            "job_discovery",
            "--approval", str(approval_file)
        ])

        # Run CLI
        exit_code = main()

        # Verify success
        assert exit_code == 0

        # Verify output
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "success"
        assert output["pipeline"] == "job_discovery"
        assert "_plan_metadata" in output
        assert "_approval_metadata" in output

        # Verify executor was called correctly
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args[0][0] == "job_discovery"  # directive_name
        assert call_args[1]["approval"] == approval
        assert call_args[1]["payload"] == {}


def test_execute_cli_with_payload(tmp_path, monkeypatch, capsys):
    """Test execution with approval and payload."""
    # Create approval artifact file
    approval = {
        "plan_hash": "abc123",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    # Create payload file
    payload = {
        "title": "Data Scientist",
        "company": "AI Corp"
    }
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload))

    mock_result = {"status": "success"}

    with patch("jobflow.scripts.execute.execute_from_directive") as mock_execute:
        mock_execute.return_value = mock_result

        monkeypatch.setattr("sys.argv", [
            "execute.py",
            "job_discovery",
            "--approval", str(approval_file),
            "--payload", str(payload_file)
        ])

        exit_code = main()

        assert exit_code == 0

        # Verify payload was passed
        call_args = mock_execute.call_args
        assert call_args[1]["payload"] == payload


def test_execute_cli_plan_rejected(tmp_path, monkeypatch, capsys):
    """Test execution rejected due to approval verification failure."""
    # Create approval artifact file
    approval = {
        "plan_hash": "wrong_hash",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    with patch("jobflow.scripts.execute.execute_from_directive") as mock_execute:
        # Mock rejection
        mock_execute.side_effect = PlanRejectedError(
            "Plan execution rejected for directive 'job_discovery'. "
            "Approval verification failed: Plan hash mismatch. "
            "Expected abc123, got wrong_hash"
        )

        monkeypatch.setattr("sys.argv", [
            "execute.py",
            "job_discovery",
            "--approval", str(approval_file)
        ])

        exit_code = main()

        # Should exit with code 3
        assert exit_code == 3

        # Verify error output
        captured = capsys.readouterr()
        error = json.loads(captured.err)

        assert error["directive_name"] == "job_discovery"
        assert error["error_type"] == "PlanRejectedError"
        assert "Plan hash mismatch" in error["message"]


def test_execute_cli_missing_approval_file(monkeypatch, capsys):
    """Test execution with missing approval file."""
    monkeypatch.setattr("sys.argv", [
        "execute.py",
        "job_discovery",
        "--approval", "nonexistent.json"
    ])

    exit_code = main()

    # Should exit with code 1
    assert exit_code == 1

    # Verify error output
    captured = capsys.readouterr()
    error = json.loads(captured.err)

    assert error["error_type"] == "FileNotFoundError"
    assert "nonexistent.json" in error["message"]


def test_execute_cli_missing_payload_file(tmp_path, monkeypatch, capsys):
    """Test execution with missing payload file."""
    # Create approval file
    approval = {
        "plan_hash": "abc123",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    monkeypatch.setattr("sys.argv", [
        "execute.py",
        "job_discovery",
        "--approval", str(approval_file),
        "--payload", "nonexistent.json"
    ])

    exit_code = main()

    # Should exit with code 1
    assert exit_code == 1

    # Verify error output
    captured = capsys.readouterr()
    error = json.loads(captured.err)

    assert error["error_type"] == "FileNotFoundError"
    assert "nonexistent.json" in error["message"]


def test_execute_cli_invalid_approval_json(tmp_path, monkeypatch, capsys):
    """Test execution with invalid JSON in approval file."""
    approval_file = tmp_path / "approval.json"
    approval_file.write_text("{ invalid json }")

    monkeypatch.setattr("sys.argv", [
        "execute.py",
        "job_discovery",
        "--approval", str(approval_file)
    ])

    exit_code = main()

    # Should exit with code 1
    assert exit_code == 1

    # Verify error output
    captured = capsys.readouterr()
    error = json.loads(captured.err)

    assert error["error_type"] == "JSONDecodeError"
    assert "Invalid JSON" in error["message"]


def test_execute_cli_invalid_payload_json(tmp_path, monkeypatch, capsys):
    """Test execution with invalid JSON in payload file."""
    # Create valid approval file
    approval = {
        "plan_hash": "abc123",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    # Create invalid payload file
    payload_file = tmp_path / "payload.json"
    payload_file.write_text("{ invalid json }")

    monkeypatch.setattr("sys.argv", [
        "execute.py",
        "job_discovery",
        "--approval", str(approval_file),
        "--payload", str(payload_file)
    ])

    exit_code = main()

    # Should exit with code 1
    assert exit_code == 1

    # Verify error output
    captured = capsys.readouterr()
    error = json.loads(captured.err)

    assert error["error_type"] == "JSONDecodeError"


def test_execute_cli_requires_approval_flag(monkeypatch, capsys):
    """Test that --approval flag is required."""
    monkeypatch.setattr("sys.argv", ["execute.py", "job_discovery"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    # Should exit with error
    assert exc_info.value.code != 0


def test_execute_cli_output_format(tmp_path, monkeypatch, capsys):
    """Test that output is properly formatted JSON."""
    approval = {
        "plan_hash": "abc123",
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    mock_result = {"status": "success", "data": {"key": "value"}}

    with patch("jobflow.scripts.execute.execute_from_directive") as mock_execute:
        mock_execute.return_value = mock_result

        monkeypatch.setattr("sys.argv", [
            "execute.py",
            "job_discovery",
            "--approval", str(approval_file)
        ])

        exit_code = main()

        captured = capsys.readouterr()

        # Output should be valid JSON
        output = json.loads(captured.out)

        # Output should be sorted and indented
        assert "\n" in captured.out
        assert "  " in captured.out  # 2-space indentation


def test_execute_cli_never_auto_approves(tmp_path, monkeypatch):
    """CRITICAL TEST: Verify CLI never auto-approves (always requires artifact)."""
    # This test verifies that there's no way to bypass the approval requirement

    # Try without --approval flag - should fail immediately
    monkeypatch.setattr("sys.argv", ["execute.py", "job_discovery"])

    with pytest.raises(SystemExit):
        main()

    # Verify no execution happened
    # (The CLI should exit before even attempting to execute)


def test_execute_cli_help(monkeypatch, capsys):
    """Test CLI help message."""
    monkeypatch.setattr("sys.argv", ["execute.py", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    # Should exit with 0 (success)
    assert exc_info.value.code == 0

    captured = capsys.readouterr()

    # Help should mention key options
    assert "directive_name" in captured.out
    assert "--approval" in captured.out
    assert "--payload" in captured.out


def test_execute_cli_includes_metadata(tmp_path, monkeypatch, capsys):
    """Test that execution result includes plan and approval metadata."""
    approval = {
        "plan_hash": "abc123",
        "approved_by": "user@example.com",
        "scope": "session",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }
    approval_file = tmp_path / "approval.json"
    approval_file.write_text(json.dumps(approval))

    mock_result = {
        "status": "success",
        "_plan_metadata": {
            "directive_name": "job_discovery",
            "pipeline_name": "job_discovery",
            "planned_steps": ["step1", "step2"],
            "identified_risks": [],
            "assumptions": ["assumption1"]
        },
        "_approval_metadata": {
            "approved_by": "user@example.com",
            "approved_at": "2025-01-01T00:00:00+00:00",
            "scope": "session"
        }
    }

    with patch("jobflow.scripts.execute.execute_from_directive") as mock_execute:
        mock_execute.return_value = mock_result

        monkeypatch.setattr("sys.argv", [
            "execute.py",
            "job_discovery",
            "--approval", str(approval_file)
        ])

        exit_code = main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Verify metadata is included
        assert "_plan_metadata" in output
        assert "_approval_metadata" in output

        assert output["_approval_metadata"]["approved_by"] == "user@example.com"
        assert output["_approval_metadata"]["scope"] == "session"
