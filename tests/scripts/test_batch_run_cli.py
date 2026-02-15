"""
Unit tests for batch_run CLI.

Tests the batch processing command line interface.
"""

import json
from pathlib import Path

import pytest


def test_batch_run_cli_success(tmp_path, monkeypatch, capsys):
    """Test successful CLI execution."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    # Mock sys.argv
    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    # Should succeed
    assert exit_code == 0

    # Verify JSON output
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["status"] == "success"
    assert result["processed"] >= 1
    assert result["succeeded"] >= 1
    assert "summary_path" in result
    assert "results_dir" in result

    # Verify files created
    assert Path(result["summary_path"]).exists()
    assert Path(result["errors_path"]).exists()


def test_batch_run_cli_no_match_flag(tmp_path, monkeypatch, capsys):
    """Test CLI with --no-match flag."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
        "--no-match",
    ]

    exit_code = main(argv)

    assert exit_code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["match_jobs"] is False


def test_batch_run_cli_no_candidates(tmp_path, monkeypatch, capsys):
    """Test CLI with empty candidates directory."""
    from jobflow.scripts.batch_run import main

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(empty_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    # Should return exit code 2
    assert exit_code == 2

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["status"] == "no_candidates"
    assert "error" in result


def test_batch_run_cli_missing_candidates_dir(tmp_path, monkeypatch, capsys):
    """Test CLI with nonexistent candidates directory."""
    from jobflow.scripts.batch_run import main

    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", "nonexistent_dir",
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    # Should return exit code 1
    assert exit_code == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_batch_run_cli_missing_jobs_file(tmp_path, monkeypatch, capsys):
    """Test CLI with nonexistent jobs file."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", "nonexistent.json",
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    assert exit_code == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_batch_run_cli_creates_output_dir(tmp_path, monkeypatch, capsys):
    """Test that CLI creates output directory if it doesn't exist."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    # Nested directory that doesn't exist
    out_dir = tmp_path / "nested" / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    assert exit_code == 0
    assert out_dir.exists()


def test_batch_run_cli_json_output_format(tmp_path, monkeypatch, capsys):
    """Test that CLI outputs valid JSON with expected keys."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    # Verify expected keys
    assert "status" in result
    assert "candidates_dir" in result
    assert "jobs_file" in result
    assert "output_dir" in result
    assert "match_jobs" in result
    assert "processed" in result
    assert "succeeded" in result
    assert "failed" in result
    assert "summary_path" in result
    assert "errors_path" in result
    assert "results_dir" in result


def test_batch_run_cli_help(monkeypatch, capsys):
    """Test CLI help message."""
    from jobflow.scripts.batch_run import main

    argv = ["--help"]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Batch process candidate folders" in captured.out
    assert "--candidates-dir" in captured.out
    assert "--jobs" in captured.out
    assert "--out" in captured.out
    assert "--no-match" in captured.out


def test_batch_run_cli_returns_int(tmp_path, monkeypatch):
    """Test that CLI returns integer exit code."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    assert isinstance(exit_code, int)
    assert exit_code == 0


def test_batch_run_cli_with_top_n_flag(tmp_path, monkeypatch, capsys):
    """Test CLI with --top-n flag."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
        "--top-n", "15",
    ]

    exit_code = main(argv)

    assert exit_code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["top_n"] == 15


def test_batch_run_cli_with_no_apply_pack_flag(tmp_path, monkeypatch, capsys):
    """Test CLI with --no-apply-pack flag."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
        "--no-apply-pack",
    ]

    exit_code = main(argv)

    assert exit_code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["export_apply_packs"] is False
    assert "apply_packs_dir" not in result


def test_batch_run_cli_default_apply_packs_enabled(tmp_path, monkeypatch, capsys):
    """Test that apply packs are enabled by default."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
    ]

    exit_code = main(argv)

    assert exit_code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert result["export_apply_packs"] is True
    assert "apply_packs_dir" in result


def test_batch_run_cli_with_company_domain_flag(tmp_path, monkeypatch, capsys):
    """Test CLI with --company-domain flag."""
    from jobflow.scripts.batch_run import main

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    argv = [
        "--candidates-dir", str(candidates_dir),
        "--jobs", str(jobs_file),
        "--out", str(out_dir),
        "--company-domain", "acme.com",
        "--company-domain", "techcorp.io",
    ]

    exit_code = main(argv)

    assert exit_code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)

    # Verify success
    assert result["status"] == "success"

    # Verify output files exist
    assert Path(result["summary_path"]).exists()
    assert Path(result["apply_packs_dir"]).exists()
