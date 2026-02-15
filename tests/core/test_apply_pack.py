"""
Unit tests for apply_pack.py

Tests apply pack building from job discovery results.
"""

import pytest

from jobflow.app.core.apply_pack import build_apply_pack


def test_build_apply_pack_uses_matches():
    """Test that apply pack uses matches when available."""
    discovery_result = {
        "candidate": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "location": "NYC",
            "desired_titles": ["Software Engineer"],
            "skills": ["Python", "SQL"],
        },
        "matches": [
            {
                "job_title": "Senior Engineer",
                "job_company": "TechCorp",
                "job_location": "Remote",
                "job_url": "https://example.com/job/1",
                "source": "jobs_file",
                "overall_score": 95.0,
                "decision": "strong_fit",
                "reasons": ["Strong skills match"],
                "matched_keywords": ["python", "sql"],
                "missing_keywords": [],
                "job_fingerprint": "abc123",
            },
            {
                "job_title": "Junior Engineer",
                "job_company": "StartupCo",
                "job_location": "NYC",
                "job_url": "https://example.com/job/2",
                "source": "jobs_file",
                "overall_score": 75.0,
                "decision": "possible_fit",
                "reasons": ["Moderate match"],
                "matched_keywords": ["python"],
                "missing_keywords": ["sql"],
                "job_fingerprint": "def456",
            },
        ],
        "jobs": [],
        "counts": {"jobs": 2, "matches": 2, "errors": 0},
        "raw": {"resume_path": "/path/to/resume.txt"},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    # Verify candidate info
    assert pack["candidate"]["name"] == "John Doe"
    assert pack["candidate"]["email"] == "john@example.com"
    assert pack["candidate"]["phone"] == "555-1234"
    assert pack["candidate"]["location"] == "NYC"

    # Verify applications
    assert pack["top_n"] == 2
    assert len(pack["applications"]) == 2

    # Verify first application (highest score)
    app1 = pack["applications"][0]
    assert app1["rank"] == 1
    assert app1["job_title"] == "Senior Engineer"
    assert app1["company"] == "TechCorp"
    assert app1["score"] == 95.0
    assert app1["decision"] == "strong_fit"

    # Verify second application
    app2 = pack["applications"][1]
    assert app2["rank"] == 2
    assert app2["job_title"] == "Junior Engineer"
    assert app2["score"] == 75.0

    # Verify checklist
    assert pack["checklist"]["has_email"] is True
    assert pack["checklist"]["has_phone"] is True
    assert pack["checklist"]["has_resume"] is True
    assert pack["checklist"]["needs_manual_review"] is True  # Has non-strong_fit


def test_build_apply_pack_respects_top_n():
    """Test that apply pack caps to top_n applications."""
    matches = [
        {
            "job_title": f"Job {i}",
            "job_company": "Company",
            "job_location": "Remote",
            "job_url": f"https://example.com/job/{i}",
            "source": "jobs_file",
            "overall_score": 100 - i,  # Descending scores
            "decision": "strong_fit",
            "reasons": [],
            "matched_keywords": [],
            "missing_keywords": [],
            "job_fingerprint": f"job{i}",
        }
        for i in range(50)  # 50 matches
    ]

    discovery_result = {
        "candidate": {"name": "Test", "email": "test@example.com"},
        "matches": matches,
        "jobs": [],
        "counts": {"jobs": 50, "matches": 50, "errors": 0},
    }

    # Request top 10
    pack = build_apply_pack(discovery_result, top_n=10)

    assert pack["top_n"] == 10
    assert len(pack["applications"]) == 10

    # Verify they're the top 10 by score
    assert pack["applications"][0]["score"] == 100
    assert pack["applications"][9]["score"] == 91


def test_build_apply_pack_stable_ordering():
    """Test that apply pack has stable ordering for ties."""
    matches = [
        {
            "job_title": "ZZZ Job",
            "job_company": "Company",
            "job_location": "Remote",
            "job_url": "https://example.com/job/1",
            "source": "jobs_file",
            "overall_score": 80.0,
            "decision": "strong_fit",
            "reasons": [],
            "matched_keywords": [],
            "missing_keywords": [],
            "job_fingerprint": "zzz",
        },
        {
            "job_title": "AAA Job",
            "job_company": "Company",
            "job_location": "Remote",
            "job_url": "https://example.com/job/2",
            "source": "jobs_file",
            "overall_score": 80.0,  # Same score
            "decision": "strong_fit",
            "reasons": [],
            "matched_keywords": [],
            "missing_keywords": [],
            "job_fingerprint": "aaa",
        },
    ]

    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": matches,
        "jobs": [],
        "counts": {"jobs": 2, "matches": 2, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    # With same score, should be sorted by title (AAA before ZZZ)
    assert pack["applications"][0]["job_title"] == "AAA Job"
    assert pack["applications"][1]["job_title"] == "ZZZ Job"


def test_build_apply_pack_graceful_missing_keys():
    """Test that apply pack handles missing keys gracefully."""
    discovery_result = {
        "candidate": {},  # No candidate fields
        "matches": [
            {
                # Minimal match with missing fields
                "job_title": "Engineer",
                "overall_score": 80.0,
            }
        ],
        "counts": {"jobs": 1, "matches": 1, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    # Should not crash, use defaults
    assert pack["candidate"]["name"] == ""
    assert pack["candidate"]["email"] == ""
    assert pack["candidate"]["phone"] == ""

    app = pack["applications"][0]
    assert app["job_title"] == "Engineer"
    assert app["company"] == ""
    assert app["location"] == ""
    assert app["apply_url"] == ""
    assert app["source"] == ""
    assert app["decision"] == ""
    assert app["reasons"] == []
    assert app["matched_keywords"] == []
    assert app["missing_keywords"] == []


def test_build_apply_pack_fallback_to_jobs():
    """Test that apply pack falls back to jobs if no matches."""
    discovery_result = {
        "candidate": {"name": "Test", "email": "test@example.com"},
        "jobs": [
            {
                "title": "Software Engineer",
                "company": "TechCorp",
                "location": "Remote",
                "url": "https://example.com/job/1",
                "source": "jobs_file",
                "fingerprint": "abc123",
            },
            {
                "title": "Data Analyst",
                "company": "DataCo",
                "location": "NYC",
                "url": "https://example.com/job/2",
                "source": "jobs_file",
                "fingerprint": "def456",
            },
        ],
        "counts": {"jobs": 2, "matches": 0, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    assert pack["top_n"] == 2
    assert len(pack["applications"]) == 2

    # Jobs should be sorted by title for stability
    assert pack["applications"][0]["job_title"] == "Data Analyst"
    assert pack["applications"][1]["job_title"] == "Software Engineer"

    # Score and decision should be defaults
    for app in pack["applications"]:
        assert app["score"] == 0
        assert app["decision"] == ""


def test_build_apply_pack_empty_results():
    """Test that apply pack handles empty results gracefully."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "jobs": [],
        "counts": {"jobs": 0, "matches": 0, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    assert pack["top_n"] == 0
    assert pack["applications"] == []
    assert pack["checklist"]["needs_manual_review"] is False


def test_build_apply_pack_checklist_no_resume():
    """Test checklist correctly detects missing resume."""
    discovery_result = {
        "candidate": {
            "name": "Test",
            "email": "test@example.com",
        },
        "matches": [],
        "counts": {"jobs": 0, "matches": 0, "errors": 0},
        "raw": {},  # No resume_path or resume_text_excerpt
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    assert pack["checklist"]["has_email"] is True
    assert pack["checklist"]["has_phone"] is False
    assert pack["checklist"]["has_resume"] is False


def test_build_apply_pack_checklist_all_strong_fit():
    """Test checklist when all matches are strong_fit."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Job 1",
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
            {
                "job_title": "Job 2",
                "overall_score": 85.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 2, "matches": 2, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    # No manual review needed - all strong fits (and no manual_review URLs)
    assert pack["checklist"]["needs_manual_review"] is False


def test_build_apply_pack_url_validation_known_ats():
    """Test that URL validation works for known ATS domains."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Engineer",
                "job_company": "TechCorp",
                "job_url": "https://boards.greenhouse.io/techcorp/jobs/123",
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 1, "matches": 1, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    app = pack["applications"][0]
    assert app["url_valid"] is True
    assert app["url_domain"] == "boards.greenhouse.io"
    assert app["url_policy"] == "allowed"
    assert app["url_reason"] == "known_ats"

    # Verify url_review_summary
    assert pack["url_review_summary"]["allowed"] == 1
    assert pack["url_review_summary"]["manual_review"] == 0
    assert pack["url_review_summary"]["blocked"] == 0


def test_build_apply_pack_url_validation_unknown_domain():
    """Test that unknown domains are flagged for manual review."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Engineer",
                "job_company": "UnknownCorp",
                "job_url": "https://unknown-company.com/careers",
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 1, "matches": 1, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    app = pack["applications"][0]
    assert app["url_valid"] is True
    assert app["url_domain"] == "unknown-company.com"
    assert app["url_policy"] == "manual_review"
    assert app["url_reason"] == "unknown_domain"

    # Verify url_review_summary
    assert pack["url_review_summary"]["allowed"] == 0
    assert pack["url_review_summary"]["manual_review"] == 1
    assert pack["url_review_summary"]["blocked"] == 0

    # needs_manual_review should be True (unknown URL)
    assert pack["checklist"]["needs_manual_review"] is True


def test_build_apply_pack_url_validation_blocked():
    """Test that invalid URLs are blocked."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Engineer",
                "job_company": "BadCorp",
                "job_url": "http://bad-company.com/job",  # Non-HTTPS
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 1, "matches": 1, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    app = pack["applications"][0]
    assert app["url_valid"] is False
    assert app["url_domain"] == ""
    assert app["url_policy"] == "blocked"
    assert app["url_reason"] == "non_https"

    # Verify url_review_summary
    assert pack["url_review_summary"]["allowed"] == 0
    assert pack["url_review_summary"]["manual_review"] == 0
    assert pack["url_review_summary"]["blocked"] == 1


def test_build_apply_pack_url_validation_company_domains():
    """Test that company domains are allowed."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Engineer",
                "job_company": "AcmeCorp",
                "job_url": "https://acme.com/careers/job/123",
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 1, "matches": 1, "errors": 0},
    }

    company_domains = {"acme.com", "techcorp.io"}
    pack = build_apply_pack(discovery_result, top_n=25, company_domains=company_domains)

    app = pack["applications"][0]
    assert app["url_valid"] is True
    assert app["url_domain"] == "acme.com"
    assert app["url_policy"] == "allowed"
    assert app["url_reason"] == "company_domain"

    # Verify url_review_summary
    assert pack["url_review_summary"]["allowed"] == 1
    assert pack["url_review_summary"]["manual_review"] == 0
    assert pack["url_review_summary"]["blocked"] == 0


def test_build_apply_pack_url_validation_mixed():
    """Test URL validation with mixed policy results."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "matches": [
            {
                "job_title": "Job 1",
                "job_company": "Company1",
                "job_url": "https://greenhouse.io/job1",  # Known ATS
                "overall_score": 95.0,
                "decision": "strong_fit",
            },
            {
                "job_title": "Job 2",
                "job_company": "Company2",
                "job_url": "https://unknown.com/job2",  # Unknown
                "overall_score": 90.0,
                "decision": "strong_fit",
            },
            {
                "job_title": "Job 3",
                "job_company": "Company3",
                "job_url": "http://bad.com/job3",  # Blocked
                "overall_score": 85.0,
                "decision": "strong_fit",
            },
        ],
        "counts": {"jobs": 3, "matches": 3, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    # Verify url_review_summary counts
    assert pack["url_review_summary"]["allowed"] == 1
    assert pack["url_review_summary"]["manual_review"] == 1
    assert pack["url_review_summary"]["blocked"] == 1

    # needs_manual_review should be True (has manual_review URL)
    assert pack["checklist"]["needs_manual_review"] is True


def test_build_apply_pack_url_validation_fallback_to_jobs():
    """Test URL validation works with jobs fallback."""
    discovery_result = {
        "candidate": {"name": "Test"},
        "jobs": [
            {
                "title": "Engineer",
                "company": "TechCorp",
                "url": "https://lever.co/techcorp/job",
                "source": "jobs_file",
            },
        ],
        "counts": {"jobs": 1, "matches": 0, "errors": 0},
    }

    pack = build_apply_pack(discovery_result, top_n=25)

    app = pack["applications"][0]
    assert app["url_valid"] is True
    assert app["url_domain"] == "lever.co"
    assert app["url_policy"] == "allowed"
    assert app["url_reason"] == "known_ats"

    # Verify url_review_summary
    assert pack["url_review_summary"]["allowed"] == 1
    assert pack["url_review_summary"]["manual_review"] == 0
    assert pack["url_review_summary"]["blocked"] == 0
