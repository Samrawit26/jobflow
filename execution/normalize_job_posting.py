"""
Normalize job posting data.

Pure function that transforms raw job posting data into a consistent format.
No external I/O, database access, API calls, or global state.
"""

from typing import Any, Dict, Optional


def normalize_job_posting(raw_posting: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw job posting into a consistent format.

    Takes variable job posting data from different sources and returns
    a standardized dictionary with consistent field names and types.

    Args:
        raw_posting: Raw job posting data with potentially inconsistent fields

    Returns:
        Normalized job posting dictionary with consistent fields:
        - title: str - Job title
        - company: str - Company name
        - location: str - Job location
        - description: str - Job description
        - requirements: list[str] - List of requirements
        - salary_min: Optional[float] - Minimum salary
        - salary_max: Optional[float] - Maximum salary
        - posted_date: Optional[str] - ISO format date string
        - url: Optional[str] - Original posting URL

    Example:
        >>> raw = {
        ...     "job_title": "Software Engineer",
        ...     "employer": "Acme Corp",
        ...     "loc": "Remote"
        ... }
        >>> normalized = normalize_job_posting(raw)
        >>> normalized["title"]
        'Software Engineer'
        >>> normalized["company"]
        'Acme Corp'
    """
    # Extract title from various possible field names
    title = (
        raw_posting.get("title")
        or raw_posting.get("job_title")
        or raw_posting.get("position")
        or ""
    )

    # Extract company from various possible field names
    company = (
        raw_posting.get("company")
        or raw_posting.get("employer")
        or raw_posting.get("company_name")
        or ""
    )

    # Extract location from various possible field names
    location = (
        raw_posting.get("location")
        or raw_posting.get("loc")
        or raw_posting.get("city")
        or ""
    )

    # Extract description
    description = (
        raw_posting.get("description")
        or raw_posting.get("desc")
        or raw_posting.get("job_description")
        or ""
    )

    # Extract requirements - handle both string and list formats
    requirements_raw = (
        raw_posting.get("requirements")
        or raw_posting.get("qualifications")
        or []
    )
    if isinstance(requirements_raw, str):
        # Simple split on newlines or semicolons for string format
        requirements = [
            req.strip()
            for req in requirements_raw.replace(";", "\n").split("\n")
            if req.strip()
        ]
    elif isinstance(requirements_raw, list):
        requirements = [str(req).strip() for req in requirements_raw if req]
    else:
        requirements = []

    # Extract salary information
    salary_min = _extract_salary(
        raw_posting.get("salary_min")
        or raw_posting.get("min_salary")
        or raw_posting.get("salary_range", {}).get("min")
    )

    salary_max = _extract_salary(
        raw_posting.get("salary_max")
        or raw_posting.get("max_salary")
        or raw_posting.get("salary_range", {}).get("max")
    )

    # Extract posted date
    posted_date = (
        raw_posting.get("posted_date")
        or raw_posting.get("date_posted")
        or raw_posting.get("created_at")
    )

    # Extract URL
    url = (
        raw_posting.get("url")
        or raw_posting.get("link")
        or raw_posting.get("posting_url")
    )

    return {
        "title": str(title).strip(),
        "company": str(company).strip(),
        "location": str(location).strip(),
        "description": str(description).strip(),
        "requirements": requirements,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "posted_date": posted_date if isinstance(posted_date, str) else None,
        "url": url if isinstance(url, str) else None,
    }


def _extract_salary(value: Any) -> Optional[float]:
    """
    Extract salary value as float.

    Args:
        value: Salary value (could be int, float, str, or None)

    Returns:
        Float salary value or None if cannot be parsed
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove common currency symbols and commas
        cleaned = value.strip().replace("$", "").replace(",", "").replace("€", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None
