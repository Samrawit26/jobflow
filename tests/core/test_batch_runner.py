"""
Unit tests for batch_runner.py

Tests batch candidate processing functionality.
"""

import csv
import json
from pathlib import Path

import pytest

from jobflow.app.core.batch_runner import (
    discover_candidate_folders,
    run_batch,
    safe_slug,
)


def test_safe_slug_basic():
    """Test basic slug sanitization."""
    assert safe_slug("John Doe") == "john_doe"
    assert safe_slug("jane@example.com") == "janeexamplecom"
    assert safe_slug("Test User 123") == "test_user_123"


def test_safe_slug_special_chars():
    """Test slug with special characters."""
    assert safe_slug("user@domain.com") == "userdomaincom"
    assert safe_slug("first.last+tag@example.com") == "firstlasttagexamplecom"
    assert safe_slug("user-name_test") == "user_name_test"  # Consecutive separators collapsed


def test_safe_slug_consecutive_separators():
    """Test slug collapses consecutive separators."""
    assert safe_slug("test   user") == "test_user"
    assert safe_slug("test---user") == "test_user"
    assert safe_slug("test___user") == "test_user"


def test_safe_slug_max_length():
    """Test slug is truncated to 80 chars."""
    long_text = "a" * 100
    slug = safe_slug(long_text)
    assert len(slug) == 80


def test_safe_slug_empty():
    """Test slug with empty input."""
    assert safe_slug("") == "unknown"
    assert safe_slug("   ") == "unknown"
    assert safe_slug("!!!") == "unknown"


def test_discover_candidate_folders_anusha():
    """Test discovering Anusha's candidate folder."""
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "candidates"

    folders = discover_candidate_folders(str(fixtures_dir))

    # Should find at least anusha
    assert len(folders) >= 1
    assert any("anusha" in f for f in folders)

    # Should be sorted
    assert folders == sorted(folders)


def test_discover_candidate_folders_empty(tmp_path):
    """Test discovering with no candidate folders."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    folders = discover_candidate_folders(str(empty_dir))

    assert folders == []


def test_discover_candidate_folders_nonexistent():
    """Test discovering with nonexistent directory."""
    folders = discover_candidate_folders("nonexistent_dir")

    assert folders == []


def test_discover_candidate_folders_filters_non_candidates(tmp_path):
    """Test that non-candidate folders are filtered out."""
    candidates_dir = tmp_path / "candidates"
    candidates_dir.mkdir()

    # Create valid candidate folder
    valid = candidates_dir / "valid"
    valid.mkdir()
    (valid / "resume.txt").write_text("Resume")

    # Create invalid folder (no resume or xlsx, just other files)
    invalid = candidates_dir / "invalid"
    invalid.mkdir()
    (invalid / "readme.pdf").write_text("Other")  # .pdf not recognized as resume

    folders = discover_candidate_folders(str(candidates_dir))

    # Should only find valid
    assert len(folders) == 1
    assert "valid" in folders[0]


def test_run_batch_single_candidate(tmp_path):
    """Test batch run with single candidate (Anusha)."""
    from jobflow.app.core.file_job_source import FileJobSource

    # Use Anusha fixture
    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    # Output to tmp
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
    )

    # Verify result structure
    assert result["processed"] >= 1
    assert result["succeeded"] >= 1
    assert result["failed"] == 0

    # Verify output files exist
    assert Path(result["summary_path"]).exists()
    assert Path(result["errors_path"]).exists()
    assert Path(result["results_dir"]).exists()

    # Verify summary CSV
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 1
    assert rows[0]["status"] == "success"
    assert rows[0]["candidate_id"] == "anusha@example.com"
    assert int(rows[0]["num_jobs"]) > 0

    # Verify errors JSON
    with open(result["errors_path"], "r", encoding="utf-8") as f:
        errors = json.load(f)

    assert errors == []  # No errors expected

    # Verify per-candidate results exist
    results_dir = Path(result["results_dir"])
    candidate_results = list(results_dir.glob("*/results.json"))
    assert len(candidate_results) >= 1

    # Verify results JSON structure
    with open(candidate_results[0], "r", encoding="utf-8") as f:
        candidate_result = json.load(f)

    assert "candidate" in candidate_result
    assert "jobs" in candidate_result
    assert "matches" in candidate_result
    assert candidate_result["candidate"]["name"] == "Anusha Kayam"


def test_run_batch_no_matching(tmp_path):
    """Test batch run without matching."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=False,  # No matching
    )

    # Verify summary has no match data
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 1
    assert rows[0]["num_matches"] == "0"
    assert rows[0]["top_score"] == ""

    # Verify results don't have matches
    results_dir = Path(result["results_dir"])
    candidate_results = list(results_dir.glob("*/results.json"))

    with open(candidate_results[0], "r", encoding="utf-8") as f:
        candidate_result = json.load(f)

    assert "matches" not in candidate_result


def test_run_batch_empty_candidates(tmp_path):
    """Test batch run with no candidates."""
    from jobflow.app.core.file_job_source import FileJobSource

    empty_dir = tmp_path / "empty_candidates"
    empty_dir.mkdir()

    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(empty_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
    )

    # Should process 0 candidates
    assert result["processed"] == 0
    assert result["succeeded"] == 0
    assert result["failed"] == 0

    # Files should still be created (empty)
    assert Path(result["summary_path"]).exists()
    assert Path(result["errors_path"]).exists()

    # Summary should have only header
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 0


def test_run_batch_creates_output_dirs(tmp_path):
    """Test that batch run creates output directories."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    # Output to nested path that doesn't exist
    out_dir = tmp_path / "nested" / "output" / "dir"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
    )

    # Should create all directories
    assert out_dir.exists()
    assert (out_dir / "results").exists()
    assert Path(result["summary_path"]).exists()


def test_run_batch_handles_errors(tmp_path):
    """Test batch run handles candidate errors gracefully."""
    from jobflow.app.core.file_job_source import FileJobSource
    from scripts.generate_xlsx_fixture import generate_application_xlsx

    # Create candidates directory
    candidates_dir = tmp_path / "candidates"
    candidates_dir.mkdir()

    # Create valid candidate
    valid = candidates_dir / "valid"
    valid.mkdir()
    generate_application_xlsx(
        str(valid / "application.xlsx"),
        {"Name": "Valid", "Email": "valid@example.com", "Phone": "555-0000", "Location": "NYC"}
    )
    (valid / "resume.txt").write_text("Resume with Python and SQL")

    # Create invalid candidate (missing required fields)
    invalid = candidates_dir / "invalid"
    invalid.mkdir()
    generate_application_xlsx(str(invalid / "application.xlsx"), {})
    # No resume - will fail

    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
    )

    # Should have processed both, but one failed
    assert result["processed"] == 2
    assert result["succeeded"] == 1
    assert result["failed"] == 1

    # Verify errors recorded
    with open(result["errors_path"], "r", encoding="utf-8") as f:
        errors = json.load(f)

    assert len(errors) == 1
    assert "invalid" in errors[0]["folder"]

    # Summary should show both
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    statuses = {r["status"] for r in rows}
    assert "success" in statuses
    assert "failed" in statuses


def test_run_batch_deterministic(tmp_path):
    """Test that batch run is deterministic."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    out_dir1 = tmp_path / "output1"
    out_dir2 = tmp_path / "output2"

    source1 = FileJobSource("jobs", str(jobs_file))
    source2 = FileJobSource("jobs", str(jobs_file))

    # Run twice
    result1 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source1],
        out_dir=str(out_dir1),
        match_jobs=True,
    )

    result2 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source2],
        out_dir=str(out_dir2),
        match_jobs=True,
    )

    # Results should be identical (excluding paths)
    assert result1["processed"] == result2["processed"]
    assert result1["succeeded"] == result2["succeeded"]
    assert result1["failed"] == result2["failed"]

    # Summary CSVs should have same content
    with open(result1["summary_path"], "r", encoding="utf-8") as f:
        rows1 = list(csv.DictReader(f))

    with open(result2["summary_path"], "r", encoding="utf-8") as f:
        rows2 = list(csv.DictReader(f))

    assert len(rows1) == len(rows2)
    for r1, r2 in zip(rows1, rows2):
        assert r1["candidate_id"] == r2["candidate_id"]
        assert r1["num_jobs"] == r2["num_jobs"]
        assert r1["num_matches"] == r2["num_matches"]


def test_run_batch_with_apply_packs(tmp_path):
    """Test that batch run creates apply pack outputs."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
        top_n=10,
    )

    # Verify apply_packs_dir in result
    assert "apply_packs_dir" in result
    apply_packs_dir = Path(result["apply_packs_dir"])
    assert apply_packs_dir.exists()

    # Verify apply pack files exist for Anusha
    candidate_dirs = list(apply_packs_dir.iterdir())
    assert len(candidate_dirs) >= 1

    # Check one candidate's apply pack
    candidate_dir = candidate_dirs[0]
    assert (candidate_dir / "applications_ready.json").exists()
    assert (candidate_dir / "applications_ready.csv").exists()

    # Verify JSON structure
    with open(candidate_dir / "applications_ready.json", "r", encoding="utf-8") as f:
        pack = json.load(f)

    assert "candidate" in pack
    assert "applications" in pack
    assert "checklist" in pack
    assert pack["top_n"] <= 10

    # Verify CSV has content
    with open(candidate_dir / "applications_ready.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    assert len(csv_rows) == len(pack["applications"])


def test_run_batch_no_apply_packs(tmp_path):
    """Test that batch run skips apply packs when disabled."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=False,
    )

    # Verify no apply_packs_dir in result
    assert "apply_packs_dir" not in result

    # Verify no apply_packs directory created
    out_path = Path(out_dir)
    assert not (out_path / "apply_packs").exists()


def test_run_batch_summary_has_fit_counts(tmp_path):
    """Test that summary CSV includes fit count columns when apply packs enabled."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Verify summary CSV has new columns
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 1
    row = rows[0]

    # Verify new columns exist
    assert "num_strong_fit" in row
    assert "num_possible_fit" in row
    assert "num_weak_fit" in row
    assert "top_score" in row

    # Verify values are numbers or empty
    assert row["num_strong_fit"].isdigit() or row["num_strong_fit"] == ""
    assert row["num_possible_fit"].isdigit() or row["num_possible_fit"] == ""
    assert row["num_weak_fit"].isdigit() or row["num_weak_fit"] == ""


def test_run_batch_summary_includes_url_counts(tmp_path):
    """Test that summary CSV includes URL count columns when apply packs enabled."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Verify summary CSV has URL count columns
    with open(result["summary_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 1
    row = rows[0]

    # Verify URL count columns exist
    assert "num_url_allowed" in row
    assert "num_url_manual_review" in row
    assert "num_url_blocked" in row

    # Verify values are numbers or empty
    assert row["num_url_allowed"].isdigit() or row["num_url_allowed"] == ""
    assert row["num_url_manual_review"].isdigit() or row["num_url_manual_review"] == ""
    assert row["num_url_blocked"].isdigit() or row["num_url_blocked"] == ""


def test_run_batch_creates_application_queue(tmp_path):
    """Test that batch run creates application queue CSV."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    result = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Verify apply packs directory exists
    apply_packs_dir = Path(result["apply_packs_dir"])
    assert apply_packs_dir.exists()

    # Verify queue files exist for each candidate
    candidate_dirs = list(apply_packs_dir.iterdir())
    assert len(candidate_dirs) >= 1

    for candidate_dir in candidate_dirs:
        queue_path = candidate_dir / "application_queue.csv"
        assert queue_path.exists()

        # Verify queue CSV structure
        with open(queue_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should have at least one row
        assert len(rows) >= 1

        # Verify columns
        assert "job_fingerprint" in rows[0]
        assert "status" in rows[0]
        assert "notes" in rows[0]
        assert "rank" in rows[0]


def test_run_batch_rerun_preserves_queue_status(tmp_path):
    """Test that rerunning batch preserves human-edited status and notes."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    # First run
    result1 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Find the queue file
    apply_packs_dir = Path(result1["apply_packs_dir"])
    candidate_dirs = list(apply_packs_dir.iterdir())
    queue_path = candidate_dirs[0] / "application_queue.csv"

    # Edit the queue - mark first job as applied with notes
    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Modify first row
    rows[0]["status"] = "applied"
    rows[0]["notes"] = "Submitted on Monday via LinkedIn"

    # Write back
    with open(queue_path, "w", encoding="utf-8", newline="") as f:
        from jobflow.app.core.application_queue import QUEUE_COLUMNS

        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Second run
    source2 = FileJobSource("jobs", str(jobs_file))
    result2 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source2],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Read queue after second run
    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows_after = list(reader)

    # Find the job we edited
    edited_job = rows_after[0]  # Should still be first due to rank

    # Verify status and notes were preserved
    assert edited_job["status"] == "applied"
    assert edited_job["notes"] == "Submitted on Monday via LinkedIn"

    # Verify apply pack files were regenerated
    assert (candidate_dirs[0] / "applications_ready.json").exists()
    assert (candidate_dirs[0] / "applications_ready.csv").exists()


def test_run_batch_rerun_updates_job_data(tmp_path):
    """Test that rerunning batch updates job data while preserving status."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidates_dir = Path(__file__).parent.parent / "fixtures" / "candidates"
    jobs_file = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    out_dir = tmp_path / "output"

    source = FileJobSource("jobs", str(jobs_file))

    # First run
    result1 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Get original queue
    apply_packs_dir = Path(result1["apply_packs_dir"])
    candidate_dirs = list(apply_packs_dir.iterdir())
    queue_path = candidate_dirs[0] / "application_queue.csv"

    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows_before = list(reader)

    first_job_fingerprint = rows_before[0]["job_fingerprint"]
    original_score = rows_before[0]["score"]

    # Edit status
    rows_before[0]["status"] = "applied"

    with open(queue_path, "w", encoding="utf-8", newline="") as f:
        from jobflow.app.core.application_queue import QUEUE_COLUMNS

        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows_before)

    # Second run (score/rank might change but shouldn't in our test fixtures)
    source2 = FileJobSource("jobs", str(jobs_file))
    result2 = run_batch(
        candidates_dir=str(candidates_dir),
        job_sources=[source2],
        out_dir=str(out_dir),
        match_jobs=True,
        export_apply_packs=True,
    )

    # Read queue after second run
    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows_after = list(reader)

    # Find the same job by fingerprint
    same_job = next(r for r in rows_after if r["job_fingerprint"] == first_job_fingerprint)

    # Status should be preserved
    assert same_job["status"] == "applied"

    # Job data should be present (score might be same in our fixtures)
    assert same_job["score"] != ""
