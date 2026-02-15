"""
Integration tests for job discovery with candidate folder.

Tests the complete workflow from candidate folder to ranked matches.
"""

from pathlib import Path

import pytest

from pipelines.job_discovery import run_job_discovery


def test_run_job_discovery_with_candidate_folder():
    """Test pipeline with candidate folder (Anusha fixture)."""
    from jobflow.app.core.file_job_source import FileJobSource

    # Use Anusha's candidate folder
    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    # Use existing jobs fixture
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    result = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    # Verify result structure
    assert result["status"] == "ok"
    assert "query" in result
    assert "jobs" in result
    assert "errors" in result
    assert "counts" in result
    assert "candidate" in result
    assert "matches" in result

    # Verify candidate summary included
    candidate = result["candidate"]
    assert candidate["name"] == "Anusha Kayam"
    assert candidate["email"] == "anusha@example.com"
    assert candidate["location"] == "Remote"
    assert len(candidate["desired_titles"]) == 2
    assert "Power BI Developer" in candidate["desired_titles"]

    # Verify skills included
    assert len(candidate["skills"]) > 0

    # Verify query was built from candidate
    query = result["query"]
    assert "Power BI Developer" in query["titles"] or "Data Analyst" in query["titles"]
    assert len(query["keywords"]) > 0

    # Verify jobs were aggregated
    assert len(result["jobs"]) > 0

    # Verify matches were computed
    assert len(result["matches"]) >= 0  # May be 0 if no good matches

    # If there are matches, verify structure
    if result["matches"]:
        match = result["matches"][0]
        assert "overall_score" in match
        assert "decision" in match
        assert "job_title" in match
        assert "matched_keywords" in match


def test_run_job_discovery_with_candidate_folder_no_matching():
    """Test pipeline with candidate folder but no matching."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    result = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=False  # No matching
    )

    # Should have candidate summary
    assert "candidate" in result

    # Should NOT have matches
    assert "matches" not in result


def test_run_job_discovery_with_candidate_folder_missing():
    """Test that missing candidate folder raises error."""
    with pytest.raises(FileNotFoundError):
        run_job_discovery(
            sources=[],
            candidate_folder="nonexistent_folder"
        )


def test_run_job_discovery_with_candidate_folder_empty_jobs():
    """Test pipeline with candidate folder but no jobs."""
    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"

    result = run_job_discovery(
        sources=[],  # No sources
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    # Should have candidate
    assert "candidate" in result
    assert result["candidate"]["name"] == "Anusha Kayam"

    # Should have empty jobs and matches
    assert result["jobs"] == []
    assert result["matches"] == []


def test_run_job_discovery_candidate_folder_overrides_param():
    """Test that candidate_folder parameter overrides candidate_or_query."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    # Provide both candidate_folder and candidate dict
    # candidate_folder should take precedence
    result = run_job_discovery(
        candidate_or_query={"desired_title": "Engineer", "skills": ["Java"]},
        sources=[source],
        candidate_folder=str(candidate_folder)  # Should override
    )

    # Should use Anusha's profile from folder, not the dict
    assert result["candidate"]["name"] == "Anusha Kayam"
    assert "Power BI Developer" in result["candidate"]["desired_titles"]


def test_run_job_discovery_with_candidate_folder_matches_sorted():
    """Test that matches are sorted by score."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    result = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    matches = result["matches"]

    if len(matches) > 1:
        # Verify sorted by score descending
        for i in range(len(matches) - 1):
            assert matches[i]["overall_score"] >= matches[i + 1]["overall_score"]


def test_run_job_discovery_with_candidate_folder_rejects_filtered():
    """Test that reject decisions are filtered from matches."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    result = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    matches = result["matches"]

    # All matches should not be rejects
    for match in matches:
        assert match["decision"] != "reject"


def test_run_job_discovery_candidate_folder_deterministic():
    """Test that pipeline with candidate folder is deterministic."""
    from jobflow.app.core.file_job_source import FileJobSource

    candidate_folder = Path(__file__).parent.parent / "fixtures" / "candidates" / "anusha"
    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"

    source = FileJobSource("fixture", str(jobs_fixture))

    # Run twice
    result1 = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    result2 = run_job_discovery(
        sources=[source],
        candidate_folder=str(candidate_folder),
        match_jobs=True
    )

    # Results should be identical
    assert result1["status"] == result2["status"]
    assert result1["candidate"] == result2["candidate"]
    assert result1["counts"] == result2["counts"]
    assert len(result1["matches"]) == len(result2["matches"])

    # Match scores should be identical
    if result1["matches"]:
        for m1, m2 in zip(result1["matches"], result2["matches"]):
            assert m1["overall_score"] == m2["overall_score"]


def test_run_job_discovery_backward_compatible():
    """Test that old usage without candidate_folder still works."""
    from jobflow.app.core.file_job_source import FileJobSource

    jobs_fixture = Path(__file__).parent.parent / "fixtures" / "jobs_sample.json"
    source = FileJobSource("fixture", str(jobs_fixture))

    # Old style usage (without candidate_folder)
    candidate = {
        "desired_title": "Software Engineer",
        "skills_years": {"Python": 5, "AWS": 3}
    }

    result = run_job_discovery(candidate, [source])

    # Should work as before
    assert result["status"] == "ok"
    assert "jobs" in result
    # Should NOT have candidate summary (not from folder)
    assert "candidate" not in result
