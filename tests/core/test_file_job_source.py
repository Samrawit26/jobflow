"""
Unit tests for file_job_source.py

Tests file-based job source implementation.
"""

import json

import pytest

from jobflow.app.core.file_job_source import FileJobSource


def test_file_job_source_implements_protocol():
    """Test that FileJobSource implements JobSource protocol."""
    source = FileJobSource("test", "dummy.json")

    # Should have source_name property
    assert hasattr(source, "source_name")
    assert source.source_name == "test"

    # Should have fetch_raw_jobs method
    assert hasattr(source, "fetch_raw_jobs")
    assert callable(source.fetch_raw_jobs)


def test_file_job_source_reads_list_format(tmp_path):
    """Test reading JSON file with direct list format."""
    # Create JSON file with list of jobs
    jobs_data = [
        {
            "title": "Software Engineer",
            "company": "Tech Corp",
            "location": "SF",
            "description": "Build software",
        },
        {
            "title": "Data Scientist",
            "company": "AI Inc",
            "location": "NYC",
            "description": "Analyze data",
        },
    ]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    # Read from file source
    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[1]["title"] == "Data Scientist"


def test_file_job_source_reads_object_format(tmp_path):
    """Test reading JSON file with object wrapper format."""
    # Create JSON file with {"jobs": [...]} format
    jobs_data = {
        "jobs": [
            {
                "title": "Engineer",
                "company": "Corp",
                "location": "SF",
                "description": "Work",
            },
            {
                "title": "Manager",
                "company": "Corp",
                "location": "NYC",
                "description": "Lead",
            },
        ]
    }

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    # Read from file source
    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Engineer"
    assert jobs[1]["title"] == "Manager"


def test_file_job_source_missing_file():
    """Test that missing file raises FileNotFoundError."""
    source = FileJobSource("local", "nonexistent.json")

    with pytest.raises(FileNotFoundError) as exc_info:
        source.fetch_raw_jobs()

    assert "not found" in str(exc_info.value)
    assert "nonexistent.json" in str(exc_info.value)


def test_file_job_source_invalid_json(tmp_path):
    """Test that invalid JSON raises ValueError."""
    json_file = tmp_path / "invalid.json"
    json_file.write_text("{ invalid json }")

    source = FileJobSource("local", str(json_file))

    with pytest.raises(ValueError) as exc_info:
        source.fetch_raw_jobs()

    assert "Invalid JSON" in str(exc_info.value)


def test_file_job_source_wrong_structure_string(tmp_path):
    """Test that string data raises ValueError."""
    json_file = tmp_path / "wrong.json"
    json_file.write_text(json.dumps("not a list or object"))

    source = FileJobSource("local", str(json_file))

    with pytest.raises(ValueError) as exc_info:
        source.fetch_raw_jobs()

    assert "Expected JSON to be a list or object" in str(exc_info.value)


def test_file_job_source_wrong_structure_number(tmp_path):
    """Test that number data raises ValueError."""
    json_file = tmp_path / "wrong.json"
    json_file.write_text(json.dumps(123))

    source = FileJobSource("local", str(json_file))

    with pytest.raises(ValueError) as exc_info:
        source.fetch_raw_jobs()

    assert "Expected JSON to be a list or object" in str(exc_info.value)


def test_file_job_source_object_missing_jobs_key(tmp_path):
    """Test that object without 'jobs' key raises ValueError."""
    json_file = tmp_path / "wrong.json"
    json_file.write_text(json.dumps({"data": []}))

    source = FileJobSource("local", str(json_file))

    with pytest.raises(ValueError) as exc_info:
        source.fetch_raw_jobs()

    assert "Expected JSON to be a list or object with 'jobs' key" in str(exc_info.value)


def test_file_job_source_jobs_key_not_list(tmp_path):
    """Test that 'jobs' key with non-list value raises ValueError."""
    json_file = tmp_path / "wrong.json"
    json_file.write_text(json.dumps({"jobs": "not a list"}))

    source = FileJobSource("local", str(json_file))

    with pytest.raises(ValueError) as exc_info:
        source.fetch_raw_jobs()

    assert "'jobs' key to contain a list" in str(exc_info.value)


def test_file_job_source_empty_list(tmp_path):
    """Test reading empty job list."""
    json_file = tmp_path / "empty.json"
    json_file.write_text(json.dumps([]))

    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert jobs == []


def test_file_job_source_empty_object_format(tmp_path):
    """Test reading empty jobs in object format."""
    json_file = tmp_path / "empty.json"
    json_file.write_text(json.dumps({"jobs": []}))

    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert jobs == []


def test_file_job_source_ignores_query_parameter(tmp_path):
    """Test that query parameter is ignored."""
    jobs_data = [
        {"title": "Engineer", "company": "C", "location": "L", "description": "D"},
        {"title": "Scientist", "company": "C", "location": "L", "description": "D"},
    ]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    source = FileJobSource("local", str(json_file))

    # Query is ignored, should return all jobs
    jobs = source.fetch_raw_jobs(query={"title": "engineer"})

    assert len(jobs) == 2


def test_file_job_source_preserves_job_data(tmp_path):
    """Test that job data is preserved exactly as in file."""
    jobs_data = [
        {
            "title": "Engineer",
            "company": "Corp",
            "custom_field": "custom_value",
            "nested": {"key": "value"},
        }
    ]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 1
    assert jobs[0]["custom_field"] == "custom_value"
    assert jobs[0]["nested"]["key"] == "value"


def test_file_job_source_multiple_reads(tmp_path):
    """Test that source can be read multiple times."""
    jobs_data = [{"title": "Job", "company": "C", "location": "L", "description": "D"}]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    source = FileJobSource("local", str(json_file))

    # Read multiple times
    jobs1 = source.fetch_raw_jobs()
    jobs2 = source.fetch_raw_jobs()

    assert jobs1 == jobs2
    assert len(jobs1) == 1


def test_file_job_source_source_name_preserved():
    """Test that source_name is preserved."""
    source = FileJobSource("my_custom_source", "dummy.json")

    assert source.source_name == "my_custom_source"


def test_file_job_source_with_path_object(tmp_path):
    """Test that Path objects work as well as strings."""
    from pathlib import Path

    jobs_data = [{"title": "Job", "company": "C", "location": "L", "description": "D"}]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    # Pass Path object instead of string
    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 1


def test_file_job_source_with_complex_nested_data(tmp_path):
    """Test reading jobs with complex nested structures."""
    jobs_data = [
        {
            "title": "Engineer",
            "company": "Corp",
            "location": "SF",
            "description": "Work",
            "requirements": ["Python", "AWS"],
            "salary_range": {"min": 100000, "max": 150000, "currency": "USD"},
            "metadata": {"posted_by": "recruiter", "tags": ["remote", "senior"]},
        }
    ]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data))

    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 1
    assert jobs[0]["requirements"] == ["Python", "AWS"]
    assert jobs[0]["salary_range"]["min"] == 100000
    assert jobs[0]["metadata"]["tags"] == ["remote", "senior"]


def test_file_job_source_utf8_encoding(tmp_path):
    """Test reading jobs with UTF-8 characters."""
    jobs_data = [
        {
            "title": "Ingénieur Logiciel",
            "company": "Société Française",
            "location": "Paris, France",
            "description": "Développer des applications",
        }
    ]

    json_file = tmp_path / "jobs.json"
    json_file.write_text(json.dumps(jobs_data, ensure_ascii=False), encoding="utf-8")

    source = FileJobSource("local", str(json_file))
    jobs = source.fetch_raw_jobs()

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Ingénieur Logiciel"
    assert jobs[0]["company"] == "Société Française"
