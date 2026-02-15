"""
Apply URL policy enforcement with hybrid ATS validation.

Validates job application URLs using an allowlist approach:
- Known ATS platforms (Greenhouse, Lever, etc.) are automatically allowed
- Unknown domains are flagged for manual review
- Invalid/malformed URLs are blocked
"""

from urllib.parse import urlparse


# Known ATS (Applicant Tracking System) domains
# These are automatically allowed as trusted application platforms
KNOWN_ATS_DOMAINS = {
    "boards.greenhouse.io",
    "greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "myworkdayjobs.com",
    "workday.com",
    "icims.com",
    "smartrecruiters.com",
    "taleo.net",
}


def normalize_domain(domain: str) -> str:
    """
    Normalize domain name for comparison.

    Args:
        domain: Raw domain name

    Returns:
        Normalized domain (lowercase, stripped, www. removed)

    Examples:
        "WWW.Example.COM" -> "example.com"
        "  greenhouse.io  " -> "greenhouse.io"
    """
    # Strip whitespace and lowercase
    normalized = domain.strip().lower()

    # Remove leading www.
    if normalized.startswith("www."):
        normalized = normalized[4:]

    return normalized


def evaluate_apply_url(
    url: str,
    company_domains: set[str] | None = None
) -> dict:
    """
    Evaluate apply URL against policy.

    Policy (Hybrid):
        - Empty URL: blocked (missing_url)
        - Non-HTTPS: blocked (non_https)
        - Malformed: blocked (malformed)
        - Known ATS domain: allowed
        - Company domain (if provided): allowed
        - Unknown domain: manual_review (unknown_domain)

    Args:
        url: Application URL to evaluate
        company_domains: Optional set of known company domains to allow

    Returns:
        Dict with:
            - url_valid: bool (True if usable, False if blocked)
            - url_domain: str (normalized domain, or empty if invalid)
            - url_policy: "allowed" | "manual_review" | "blocked"
            - url_reason: str (explanation)

    Notes:
        - Deterministic: no network calls, no DNS lookups
        - Case-insensitive domain matching
        - www. prefix is normalized away
    """
    if company_domains is None:
        company_domains = set()

    # Normalize company domains
    normalized_company_domains = {normalize_domain(d) for d in company_domains}

    # Check for empty URL
    if not url or not url.strip():
        return {
            "url_valid": False,
            "url_domain": "",
            "url_policy": "blocked",
            "url_reason": "missing_url",
        }

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return {
            "url_valid": False,
            "url_domain": "",
            "url_policy": "blocked",
            "url_reason": "malformed",
        }

    # Check scheme
    if parsed.scheme != "https":
        return {
            "url_valid": False,
            "url_domain": "",
            "url_policy": "blocked",
            "url_reason": "non_https",
        }

    # Extract and normalize domain
    domain = parsed.netloc
    if not domain:
        return {
            "url_valid": False,
            "url_domain": "",
            "url_policy": "blocked",
            "url_reason": "malformed",
        }

    normalized_domain = normalize_domain(domain)

    # Check against known ATS domains
    if normalized_domain in KNOWN_ATS_DOMAINS:
        return {
            "url_valid": True,
            "url_domain": normalized_domain,
            "url_policy": "allowed",
            "url_reason": "known_ats",
        }

    # Check against company domains
    if normalized_domain in normalized_company_domains:
        return {
            "url_valid": True,
            "url_domain": normalized_domain,
            "url_policy": "allowed",
            "url_reason": "company_domain",
        }

    # Unknown domain - flag for manual review
    return {
        "url_valid": True,
        "url_domain": normalized_domain,
        "url_policy": "manual_review",
        "url_reason": "unknown_domain",
    }
