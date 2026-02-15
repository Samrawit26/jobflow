"""
Unit tests for url_policy.py

Tests hybrid URL validation with ATS allowlisting and manual review flags.
"""

import pytest

from jobflow.app.core.url_policy import (
    KNOWN_ATS_DOMAINS,
    evaluate_apply_url,
    normalize_domain,
)


def test_normalize_domain_lowercase():
    """Test that normalize_domain converts to lowercase."""
    assert normalize_domain("EXAMPLE.COM") == "example.com"
    assert normalize_domain("Example.Com") == "example.com"


def test_normalize_domain_strips_whitespace():
    """Test that normalize_domain strips whitespace."""
    assert normalize_domain("  example.com  ") == "example.com"
    assert normalize_domain("\texample.com\n") == "example.com"


def test_normalize_domain_removes_www():
    """Test that normalize_domain removes www. prefix."""
    assert normalize_domain("www.example.com") == "example.com"
    assert normalize_domain("WWW.EXAMPLE.COM") == "example.com"
    assert normalize_domain("www.greenhouse.io") == "greenhouse.io"


def test_normalize_domain_preserves_subdomains():
    """Test that normalize_domain preserves non-www subdomains."""
    assert normalize_domain("boards.greenhouse.io") == "boards.greenhouse.io"
    assert normalize_domain("jobs.lever.co") == "jobs.lever.co"
    assert normalize_domain("api.example.com") == "api.example.com"


def test_evaluate_apply_url_missing_url():
    """Test that empty URLs are blocked."""
    result = evaluate_apply_url("")
    assert result["url_valid"] is False
    assert result["url_domain"] == ""
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "missing_url"

    result = evaluate_apply_url("   ")
    assert result["url_valid"] is False
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "missing_url"


def test_evaluate_apply_url_non_https():
    """Test that non-HTTPS URLs are blocked."""
    result = evaluate_apply_url("http://example.com/job")
    assert result["url_valid"] is False
    assert result["url_domain"] == ""
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "non_https"

    result = evaluate_apply_url("ftp://example.com/job")
    assert result["url_valid"] is False
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "non_https"


def test_evaluate_apply_url_malformed():
    """Test that malformed URLs are blocked."""
    # URL with no scheme gets caught by non_https check
    result = evaluate_apply_url("not a url")
    assert result["url_valid"] is False
    assert result["url_domain"] == ""
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "non_https"

    # Missing netloc
    result = evaluate_apply_url("https://")
    assert result["url_valid"] is False
    assert result["url_policy"] == "blocked"
    assert result["url_reason"] == "malformed"


def test_evaluate_apply_url_known_ats():
    """Test that known ATS domains are allowed."""
    # Test a few known ATS platforms
    for domain in ["greenhouse.io", "boards.greenhouse.io", "lever.co", "jobs.lever.co"]:
        result = evaluate_apply_url(f"https://{domain}/job/123")
        assert result["url_valid"] is True
        assert result["url_domain"] == domain
        assert result["url_policy"] == "allowed"
        assert result["url_reason"] == "known_ats"


def test_evaluate_apply_url_known_ats_case_insensitive():
    """Test that ATS domain matching is case-insensitive."""
    result = evaluate_apply_url("https://GREENHOUSE.IO/job/123")
    assert result["url_valid"] is True
    assert result["url_domain"] == "greenhouse.io"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "known_ats"

    result = evaluate_apply_url("https://Boards.Greenhouse.io/job/123")
    assert result["url_valid"] is True
    assert result["url_domain"] == "boards.greenhouse.io"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "known_ats"


def test_evaluate_apply_url_known_ats_with_www():
    """Test that www. is normalized for ATS domains."""
    result = evaluate_apply_url("https://www.greenhouse.io/job/123")
    assert result["url_valid"] is True
    assert result["url_domain"] == "greenhouse.io"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "known_ats"


def test_evaluate_apply_url_company_domain():
    """Test that company domains are allowed."""
    company_domains = {"acme.com", "techcorp.io"}

    result = evaluate_apply_url("https://acme.com/careers/job/123", company_domains)
    assert result["url_valid"] is True
    assert result["url_domain"] == "acme.com"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "company_domain"

    result = evaluate_apply_url("https://techcorp.io/jobs", company_domains)
    assert result["url_valid"] is True
    assert result["url_domain"] == "techcorp.io"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "company_domain"


def test_evaluate_apply_url_company_domain_case_insensitive():
    """Test that company domain matching is case-insensitive."""
    company_domains = {"acme.com"}

    result = evaluate_apply_url("https://ACME.COM/job", company_domains)
    assert result["url_valid"] is True
    assert result["url_domain"] == "acme.com"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "company_domain"


def test_evaluate_apply_url_company_domain_with_www():
    """Test that www. is normalized for company domains."""
    company_domains = {"acme.com"}

    result = evaluate_apply_url("https://www.acme.com/job", company_domains)
    assert result["url_valid"] is True
    assert result["url_domain"] == "acme.com"
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "company_domain"


def test_evaluate_apply_url_unknown_domain():
    """Test that unknown domains are flagged for manual review."""
    result = evaluate_apply_url("https://unknown-company.com/job/123")
    assert result["url_valid"] is True
    assert result["url_domain"] == "unknown-company.com"
    assert result["url_policy"] == "manual_review"
    assert result["url_reason"] == "unknown_domain"


def test_evaluate_apply_url_priority_ats_over_company():
    """Test that ATS domains take priority over company domains."""
    # Even if company_domains includes an ATS domain, should still return known_ats
    company_domains = {"greenhouse.io"}

    result = evaluate_apply_url("https://greenhouse.io/job", company_domains)
    assert result["url_valid"] is True
    assert result["url_policy"] == "allowed"
    assert result["url_reason"] == "known_ats"  # Should be known_ats, not company_domain


def test_evaluate_apply_url_no_company_domains():
    """Test that None company_domains is handled gracefully."""
    result = evaluate_apply_url("https://example.com/job", None)
    assert result["url_valid"] is True
    assert result["url_domain"] == "example.com"
    assert result["url_policy"] == "manual_review"
    assert result["url_reason"] == "unknown_domain"


def test_evaluate_apply_url_empty_company_domains():
    """Test that empty company_domains set is handled gracefully."""
    result = evaluate_apply_url("https://example.com/job", set())
    assert result["url_valid"] is True
    assert result["url_domain"] == "example.com"
    assert result["url_policy"] == "manual_review"
    assert result["url_reason"] == "unknown_domain"


def test_evaluate_apply_url_deterministic():
    """Test that evaluation is deterministic (no network calls)."""
    url = "https://example.com/job/123"

    # Call multiple times - should always get same result
    result1 = evaluate_apply_url(url)
    result2 = evaluate_apply_url(url)
    result3 = evaluate_apply_url(url)

    assert result1 == result2 == result3


def test_known_ats_domains_coverage():
    """Test that KNOWN_ATS_DOMAINS includes major platforms."""
    # Verify some major ATS platforms are included
    expected_platforms = [
        "greenhouse.io",
        "lever.co",
        "workday.com",
        "icims.com",
        "smartrecruiters.com",
        "taleo.net",
    ]

    for platform in expected_platforms:
        assert platform in KNOWN_ATS_DOMAINS, f"{platform} should be in KNOWN_ATS_DOMAINS"
