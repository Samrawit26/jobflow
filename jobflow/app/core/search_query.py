"""
Search query builder for job matching.

Transforms normalized candidate profiles into structured job search queries.
Maps candidate preferences and skills to job search criteria.
"""

from typing import Any


def build_job_query(candidate: dict) -> dict:
    """
    Build job search query from normalized candidate profile.

    Extracts job search criteria from candidate profile, including desired
    titles, locations, remote preferences, and relevant keywords from skills.

    Input candidate dict may contain:
    - desired_title / job_title / title: primary job title
    - alternate_titles: list of alternative job titles
    - desired_locations / locations / location: list or string of locations
    - remote_ok / remote_preference: boolean for remote work preference
    - skills_years: dict of skills to years of experience
    - employment_type / employment_type_preference: e.g., "full-time"

    Output query dict contains:
    - titles: list[str] (primary + alternates, deduplicated)
    - locations: list[str] (deduplicated locations)
    - remote_ok: bool (default False)
    - keywords: list[str] (skills/tools from skills_years)
    - employment_type: str | None (optional preference)

    Args:
        candidate: Normalized candidate profile dict

    Returns:
        Structured job search query dict

    Example:
        >>> candidate = {
        ...     "desired_title": "Software Engineer",
        ...     "alternate_titles": ["Backend Engineer", "Python Developer"],
        ...     "desired_locations": ["San Francisco", "Remote"],
        ...     "remote_ok": True,
        ...     "skills_years": {"Python": 5, "AWS": 3},
        ...     "employment_type": "full-time"
        ... }
        >>> query = build_job_query(candidate)
        >>> query["titles"]
        ['Software Engineer', 'Backend Engineer', 'Python Developer']
    """
    # Extract titles (primary + alternates)
    titles = _extract_titles(candidate)

    # Extract locations
    locations = _extract_locations(candidate)

    # Extract remote preference
    remote_ok = _extract_remote_preference(candidate)

    # Extract keywords from skills
    keywords = _extract_keywords(candidate)

    # Extract employment type preference
    employment_type = _extract_employment_type(candidate)

    return {
        "titles": titles,
        "locations": locations,
        "remote_ok": remote_ok,
        "keywords": keywords,
        "employment_type": employment_type,
    }


def _extract_titles(candidate: dict) -> list[str]:
    """
    Extract job titles from candidate profile.

    Looks for primary title in: desired_title, job_title, title
    Looks for alternates in: alternate_titles

    Returns deduplicated list preserving order.
    """
    titles = []

    # Extract primary title
    primary = (
        candidate.get("desired_title")
        or candidate.get("job_title")
        or candidate.get("title")
    )
    if primary:
        normalized = str(primary).strip()
        if normalized:
            titles.append(normalized)

    # Extract alternate titles
    alternates = candidate.get("alternate_titles", [])
    if isinstance(alternates, str):
        # Split by comma if string
        alternates = [alt.strip() for alt in alternates.split(",")]
    elif isinstance(alternates, list):
        alternates = [str(alt).strip() for alt in alternates]
    else:
        alternates = []

    # Add alternates, deduplicating
    seen = set(t.lower() for t in titles)
    for alt in alternates:
        if alt and alt.lower() not in seen:
            titles.append(alt)
            seen.add(alt.lower())

    return titles


def _extract_locations(candidate: dict) -> list[str]:
    """
    Extract desired locations from candidate profile.

    Looks for: desired_locations, locations, location

    Returns deduplicated list preserving order.
    """
    locations = []

    # Try to get locations from various field names
    locs_raw = (
        candidate.get("desired_locations")
        or candidate.get("locations")
        or candidate.get("location")
    )

    if not locs_raw:
        return []

    # Handle string (comma-separated) or list
    if isinstance(locs_raw, str):
        locs_list = [loc.strip() for loc in locs_raw.split(",")]
    elif isinstance(locs_raw, list):
        locs_list = [str(loc).strip() for loc in locs_raw]
    else:
        return []

    # Deduplicate while preserving order
    seen = set()
    for loc in locs_list:
        if loc and loc.lower() not in seen:
            locations.append(loc)
            seen.add(loc.lower())

    return locations


def _extract_remote_preference(candidate: dict) -> bool:
    """
    Extract remote work preference.

    Looks for: remote_ok, remote_preference

    Returns bool (default False).
    """
    remote = candidate.get("remote_ok") or candidate.get("remote_preference")

    if remote is None:
        return False

    # Handle various truthy values
    if isinstance(remote, bool):
        return remote
    if isinstance(remote, str):
        return remote.lower() in ("true", "yes", "1")
    return bool(remote)


def _extract_keywords(candidate: dict) -> list[str]:
    """
    Extract search keywords from candidate skills.

    Extracts skill names from skills_years dict.

    Returns deduplicated list preserving order.
    """
    skills_years = candidate.get("skills_years", {})

    if not isinstance(skills_years, dict):
        return []

    # Extract skill names, strip whitespace
    keywords = []
    seen = set()

    for skill in skills_years.keys():
        skill_str = str(skill).strip()
        if skill_str and skill_str.lower() not in seen:
            keywords.append(skill_str)
            seen.add(skill_str.lower())

    return keywords


def _extract_employment_type(candidate: dict) -> str | None:
    """
    Extract employment type preference.

    Looks for: employment_type, employment_type_preference

    Returns str or None.
    """
    emp_type = candidate.get("employment_type") or candidate.get(
        "employment_type_preference"
    )

    if not emp_type:
        return None

    # Normalize to string and strip
    emp_type_str = str(emp_type).strip()
    return emp_type_str if emp_type_str else None
