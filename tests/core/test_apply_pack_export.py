"""
Unit tests for apply_pack_export.py

Tests JSON and CSV export of apply packs.
"""

import csv
import json
from pathlib import Path

import pytest

from jobflow.app.core.apply_pack_export import (
    write_apply_pack_csv,
    write_apply_pack_json,
)


def test_write_apply_pack_json_creates_file(tmp_path):
    """Test that JSON export creates file with expected content."""
    pack = {
        "candidate": {
            "name": "John Doe",
            "email": "john@example.com",
        },
        "top_n": 2,
        "applications": [
            {
                "rank": 1,
                "job_title": "Engineer",
                "company": "TechCorp",
                "score": 90.0,
            },
        ],
        "checklist": {
            "has_email": True,
            "has_resume": True,
        },
    }

    output_path = tmp_path / "pack.json"
    write_apply_pack_json(pack, str(output_path))

    # Verify file exists
    assert output_path.exists()

    # Verify content
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["candidate"]["name"] == "John Doe"
    assert loaded["top_n"] == 2
    assert len(loaded["applications"]) == 1


def test_write_apply_pack_json_creates_directories(tmp_path):
    """Test that JSON export creates parent directories."""
    output_path = tmp_path / "nested" / "dir" / "pack.json"

    pack = {"candidate": {"name": "Test"}, "applications": []}

    write_apply_pack_json(pack, str(output_path))

    assert output_path.exists()
    assert output_path.parent.exists()


def test_write_apply_pack_csv_creates_file(tmp_path):
    """Test that CSV export creates file with expected content."""
    pack = {
        "applications": [
            {
                "rank": 1,
                "score": 95.0,
                "decision": "strong_fit",
                "company": "TechCorp",
                "job_title": "Senior Engineer",
                "location": "Remote",
                "apply_url": "https://example.com/job/1",
                "source": "jobs_file",
                "reasons": ["Strong match", "Good fit"],
                "matched_keywords": ["python", "sql"],
                "missing_keywords": [],
            },
            {
                "rank": 2,
                "score": 80.0,
                "decision": "possible_fit",
                "company": "StartupCo",
                "job_title": "Engineer",
                "location": "NYC",
                "apply_url": "https://example.com/job/2",
                "source": "jobs_file",
                "reasons": ["Moderate match"],
                "matched_keywords": ["python"],
                "missing_keywords": ["sql", "aws"],
            },
        ]
    }

    output_path = tmp_path / "applications.csv"
    write_apply_pack_csv(pack, str(output_path))

    # Verify file exists
    assert output_path.exists()

    # Verify CSV content
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2

    # Verify first row
    row1 = rows[0]
    assert row1["rank"] == "1"
    assert row1["score"] == "95.0"
    assert row1["decision"] == "strong_fit"
    assert row1["company"] == "TechCorp"
    assert row1["job_title"] == "Senior Engineer"
    assert row1["location"] == "Remote"
    assert row1["apply_url"] == "https://example.com/job/1"
    assert row1["source"] == "jobs_file"
    assert row1["reasons"] == "Strong match; Good fit"
    assert row1["matched_keywords"] == "python; sql"
    assert row1["missing_keywords"] == ""

    # Verify second row
    row2 = rows[1]
    assert row2["rank"] == "2"
    assert row2["missing_keywords"] == "sql; aws"


def test_write_apply_pack_csv_headers_only(tmp_path):
    """Test that CSV export with empty applications writes headers."""
    pack = {"applications": []}

    output_path = tmp_path / "empty.csv"
    write_apply_pack_csv(pack, str(output_path))

    assert output_path.exists()

    # Verify headers exist
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == [
            "rank",
            "score",
            "decision",
            "company",
            "job_title",
            "location",
            "apply_url",
            "source",
            "url_policy",
            "url_reason",
            "reasons",
            "matched_keywords",
            "missing_keywords",
        ]
        rows = list(reader)
        assert len(rows) == 0


def test_write_apply_pack_csv_creates_directories(tmp_path):
    """Test that CSV export creates parent directories."""
    output_path = tmp_path / "nested" / "dir" / "applications.csv"

    pack = {"applications": []}

    write_apply_pack_csv(pack, str(output_path))

    assert output_path.exists()
    assert output_path.parent.exists()


def test_write_apply_pack_csv_graceful_missing_fields(tmp_path):
    """Test that CSV export handles missing fields gracefully."""
    pack = {
        "applications": [
            {
                "rank": 1,
                # Missing most fields
                "job_title": "Engineer",
            }
        ]
    }

    output_path = tmp_path / "pack.csv"
    write_apply_pack_csv(pack, str(output_path))

    assert output_path.exists()

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["rank"] == "1"
    assert row["job_title"] == "Engineer"
    assert row["company"] == ""
    assert row["score"] == ""
    assert row["reasons"] == ""


def test_write_apply_pack_csv_includes_url_policy_fields(tmp_path):
    """Test that CSV export includes url_policy and url_reason fields."""
    pack = {
        "applications": [
            {
                "rank": 1,
                "score": 95.0,
                "decision": "strong_fit",
                "company": "TechCorp",
                "job_title": "Engineer",
                "location": "Remote",
                "apply_url": "https://greenhouse.io/job/1",
                "source": "jobs_file",
                "url_policy": "allowed",
                "url_reason": "known_ats",
                "reasons": [],
                "matched_keywords": ["python"],
                "missing_keywords": [],
            },
            {
                "rank": 2,
                "score": 80.0,
                "decision": "possible_fit",
                "company": "UnknownCo",
                "job_title": "Developer",
                "location": "NYC",
                "apply_url": "https://unknown.com/job/2",
                "source": "jobs_file",
                "url_policy": "manual_review",
                "url_reason": "unknown_domain",
                "reasons": [],
                "matched_keywords": [],
                "missing_keywords": [],
            },
        ]
    }

    output_path = tmp_path / "applications.csv"
    write_apply_pack_csv(pack, str(output_path))

    # Verify CSV content includes URL fields
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2

    # Verify first row has URL policy fields
    row1 = rows[0]
    assert row1["url_policy"] == "allowed"
    assert row1["url_reason"] == "known_ats"

    # Verify second row
    row2 = rows[1]
    assert row2["url_policy"] == "manual_review"
    assert row2["url_reason"] == "unknown_domain"
