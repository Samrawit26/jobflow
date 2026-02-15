"""
Unit tests for application_queue.py

Tests queue building, reading, merging, and writing with status preservation.
"""

import csv
from pathlib import Path

import pytest

from jobflow.app.core.application_queue import (
    QUEUE_COLUMNS,
    build_queue_rows,
    merge_queue,
    read_queue_csv,
    write_queue_csv,
)


def test_build_queue_rows_formats_keywords_with_semicolons():
    """Test that build_queue_rows joins keywords with semicolons."""
    apply_pack = {
        "applications": [
            {
                "rank": 1,
                "score": 90.0,
                "decision": "strong_fit",
                "company": "TechCorp",
                "job_title": "Engineer",
                "location": "Remote",
                "apply_url": "https://example.com/job/1",
                "source": "jobs",
                "job_fingerprint": "abc123",
                "matched_keywords": ["python", "sql", "docker"],
                "missing_keywords": ["aws", "k8s"],
            }
        ]
    }

    rows = build_queue_rows(apply_pack)

    assert len(rows) == 1
    row = rows[0]
    assert row["matched_keywords"] == "python; sql; docker"
    assert row["missing_keywords"] == "aws; k8s"


def test_build_queue_rows_sets_defaults():
    """Test that build_queue_rows sets default status and notes."""
    apply_pack = {
        "applications": [
            {
                "rank": 1,
                "job_title": "Engineer",
                "job_fingerprint": "abc123",
            }
        ]
    }

    rows = build_queue_rows(apply_pack)

    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "queued"
    assert row["notes"] == ""


def test_build_queue_rows_stable_ordering():
    """Test that build_queue_rows sorts by rank ascending."""
    apply_pack = {
        "applications": [
            {"rank": 3, "job_title": "Job 3", "job_fingerprint": "c"},
            {"rank": 1, "job_title": "Job 1", "job_fingerprint": "a"},
            {"rank": 2, "job_title": "Job 2", "job_fingerprint": "b"},
        ]
    }

    rows = build_queue_rows(apply_pack)

    assert len(rows) == 3
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] == 2
    assert rows[2]["rank"] == 3


def test_build_queue_rows_generates_fingerprint_if_missing():
    """Test that build_queue_rows generates fingerprint when not provided."""
    apply_pack = {
        "applications": [
            {
                "rank": 1,
                "apply_url": "https://example.com/job/1",
                "company": "TechCorp",
                "job_title": "Engineer",
                # No job_fingerprint
            }
        ]
    }

    rows = build_queue_rows(apply_pack)

    assert len(rows) == 1
    row = rows[0]
    assert row["job_fingerprint"] != ""
    assert len(row["job_fingerprint"]) == 16  # First 16 chars of SHA256


def test_build_queue_rows_fingerprint_is_deterministic():
    """Test that generated fingerprint is stable across runs."""
    apply_pack1 = {
        "applications": [
            {
                "rank": 1,
                "apply_url": "https://example.com/job/1",
                "company": "TechCorp",
                "job_title": "Engineer",
            }
        ]
    }

    apply_pack2 = {
        "applications": [
            {
                "rank": 1,
                "apply_url": "https://example.com/job/1",
                "company": "TechCorp",
                "job_title": "Engineer",
            }
        ]
    }

    rows1 = build_queue_rows(apply_pack1)
    rows2 = build_queue_rows(apply_pack2)

    assert rows1[0]["job_fingerprint"] == rows2[0]["job_fingerprint"]


def test_read_queue_csv_handles_missing_file():
    """Test that read_queue_csv returns empty list for missing file."""
    rows = read_queue_csv("nonexistent_file.csv")
    assert rows == []


def test_read_queue_csv_reads_existing_file(tmp_path):
    """Test that read_queue_csv reads existing CSV correctly."""
    queue_path = tmp_path / "queue.csv"

    # Write a queue file
    rows_to_write = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "score": 90.0,
            "decision": "strong_fit",
            "company": "TechCorp",
            "job_title": "Engineer",
            "location": "Remote",
            "apply_url": "https://example.com/job/1",
            "source": "jobs",
            "status": "applied",
            "notes": "Submitted on Monday",
            "matched_keywords": "python; sql",
            "missing_keywords": "aws",
        }
    ]

    write_queue_csv(rows_to_write, str(queue_path))

    # Read it back
    rows = read_queue_csv(str(queue_path))

    assert len(rows) == 1
    row = rows[0]
    assert row["job_fingerprint"] == "abc123"
    assert row["status"] == "applied"
    assert row["notes"] == "Submitted on Monday"


def test_read_queue_csv_ignores_extra_columns(tmp_path):
    """Test that read_queue_csv ignores extra columns gracefully."""
    queue_path = tmp_path / "queue.csv"

    # Write CSV with extra columns
    with open(queue_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = QUEUE_COLUMNS + ["extra_column"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "job_fingerprint": "abc123",
            "rank": 1,
            "extra_column": "should be ignored",
        })

    rows = read_queue_csv(str(queue_path))

    assert len(rows) == 1
    assert "extra_column" not in rows[0] or rows[0]["extra_column"] == ""


def test_merge_queue_preserves_status_and_notes():
    """Test that merge_queue preserves human-edited status and notes."""
    existing = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "score": 85.0,
            "status": "applied",
            "notes": "Submitted via LinkedIn",
            "company": "OldCompany",
        }
    ]

    new = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "score": 90.0,  # Updated score
            "status": "queued",  # Should be ignored
            "notes": "",  # Should be ignored
            "company": "NewCompany",  # Updated company
        }
    ]

    merged = merge_queue(existing, new)

    assert len(merged) == 1
    row = merged[0]
    # Preserved from existing
    assert row["status"] == "applied"
    assert row["notes"] == "Submitted via LinkedIn"
    # Updated from new
    assert row["score"] == 90.0
    assert row["company"] == "NewCompany"


def test_merge_queue_updates_rank_score_decision():
    """Test that merge_queue updates rank, score, and decision from new data."""
    existing = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "score": 80.0,
            "decision": "possible_fit",
            "status": "queued",
            "notes": "",
        }
    ]

    new = [
        {
            "job_fingerprint": "abc123",
            "rank": 2,  # Changed rank
            "score": 95.0,  # Changed score
            "decision": "strong_fit",  # Changed decision
            "status": "queued",
            "notes": "",
        }
    ]

    merged = merge_queue(existing, new)

    assert len(merged) == 1
    row = merged[0]
    assert row["rank"] == 2
    assert row["score"] == 95.0
    assert row["decision"] == "strong_fit"


def test_merge_queue_adds_new_jobs():
    """Test that merge_queue adds new jobs with default status."""
    existing = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "status": "queued",
            "notes": "",
        }
    ]

    new = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "status": "queued",
            "notes": "",
        },
        {
            "job_fingerprint": "def456",  # New job
            "rank": 2,
            "status": "queued",
            "notes": "",
        },
    ]

    merged = merge_queue(existing, new)

    assert len(merged) == 2
    # Find the new job
    new_job = next(r for r in merged if r["job_fingerprint"] == "def456")
    assert new_job["status"] == "queued"
    assert new_job["notes"] == ""


def test_merge_queue_keeps_removed_jobs():
    """Test that merge_queue keeps jobs that were removed from new results."""
    existing = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "status": "applied",
            "notes": "Already submitted",
        },
        {
            "job_fingerprint": "def456",
            "rank": 2,
            "status": "rejected",
            "notes": "Not a good fit",
        },
    ]

    new = [
        {
            "job_fingerprint": "abc123",  # Only this job in new results
            "rank": 1,
            "status": "queued",
            "notes": "",
        }
    ]

    merged = merge_queue(existing, new)

    # Both jobs should be present
    assert len(merged) == 2
    fingerprints = {r["job_fingerprint"] for r in merged}
    assert "abc123" in fingerprints
    assert "def456" in fingerprints

    # def456 should preserve its status
    removed_job = next(r for r in merged if r["job_fingerprint"] == "def456")
    assert removed_job["status"] == "rejected"
    assert removed_job["notes"] == "Not a good fit"


def test_merge_queue_deterministic_sort():
    """Test that merge_queue produces deterministic sort order."""
    existing = []

    new = [
        {"job_fingerprint": "zzz", "rank": 1, "status": "queued", "notes": ""},
        {"job_fingerprint": "aaa", "rank": 1, "status": "queued", "notes": ""},
        {"job_fingerprint": "mmm", "rank": 2, "status": "queued", "notes": ""},
    ]

    merged = merge_queue(existing, new)

    # Should be sorted by rank, then fingerprint
    assert len(merged) == 3
    assert merged[0]["job_fingerprint"] == "aaa"  # rank=1, first alphabetically
    assert merged[1]["job_fingerprint"] == "zzz"  # rank=1, second alphabetically
    assert merged[2]["job_fingerprint"] == "mmm"  # rank=2


def test_write_queue_csv_creates_file(tmp_path):
    """Test that write_queue_csv creates file with correct structure."""
    queue_path = tmp_path / "queue.csv"

    rows = [
        {
            "job_fingerprint": "abc123",
            "rank": 1,
            "score": 90.0,
            "decision": "strong_fit",
            "company": "TechCorp",
            "job_title": "Engineer",
            "location": "Remote",
            "apply_url": "https://example.com/job/1",
            "source": "jobs",
            "status": "queued",
            "notes": "",
            "matched_keywords": "python; sql",
            "missing_keywords": "aws",
        }
    ]

    write_queue_csv(rows, str(queue_path))

    assert queue_path.exists()

    # Verify structure
    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == QUEUE_COLUMNS
        csv_rows = list(reader)
        assert len(csv_rows) == 1


def test_write_queue_csv_creates_directories(tmp_path):
    """Test that write_queue_csv creates parent directories."""
    queue_path = tmp_path / "nested" / "dir" / "queue.csv"

    rows = [{"job_fingerprint": "abc123", "rank": 1, "status": "queued", "notes": ""}]

    write_queue_csv(rows, str(queue_path))

    assert queue_path.exists()
    assert queue_path.parent.exists()


def test_write_queue_csv_column_order():
    """Test that write_queue_csv writes columns in QUEUE_COLUMNS order."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_path = f.name

    try:
        rows = [
            {
                "job_fingerprint": "abc123",
                "rank": 1,
                "score": 90.0,
                "decision": "strong_fit",
                "company": "TechCorp",
                "job_title": "Engineer",
                "location": "Remote",
                "apply_url": "https://example.com/job/1",
                "source": "jobs",
                "status": "queued",
                "notes": "test",
                "matched_keywords": "python",
                "missing_keywords": "aws",
            }
        ]

        write_queue_csv(rows, temp_path)

        # Read and verify column order
        with open(temp_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == QUEUE_COLUMNS
    finally:
        Path(temp_path).unlink()
