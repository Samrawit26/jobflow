"""
Candidate to search query builder.

Transforms candidate profiles into job search queries with intelligent
title inference and keyword extraction.
"""

import re
from typing import Any

from jobflow.app.core.candidate_profile import CandidateProfile


def build_search_query(candidate: CandidateProfile) -> dict:
    """
    Build job search query from candidate profile.

    Intelligently constructs search criteria from candidate profile:
    - Infers job titles from skills if not explicitly provided
    - Extracts keywords from skills and resume text
    - Determines remote preference and locations
    - Caps keywords at 8-20 for optimal search

    Args:
        candidate: Normalized candidate profile

    Returns:
        Search query dict with:
        - titles: list[str]
        - locations: list[str]
        - remote_ok: bool
        - keywords: list[str] (8-20 items)
        - employment_type: str | None

    Example:
        >>> candidate = CandidateProfile(
        ...     full_name="Jane Doe",
        ...     email="jane@example.com",
        ...     phone="555-1234",
        ...     location="San Francisco",
        ...     desired_titles=[],
        ...     skills=["Power BI", "SQL", "Tableau"],
        ...     preferred_locations=["Remote"],
        ...     remote_ok=True,
        ...     resume_text=""
        ... )
        >>> query = build_search_query(candidate)
        >>> "Power BI Developer" in query["titles"]
        True
    """
    # Build titles (use desired_titles or infer from skills)
    titles = _build_titles(candidate)

    # Extract keywords from skills and resume
    keywords = _extract_keywords(candidate)

    # Determine locations
    locations = _build_locations(candidate)

    # Determine remote preference
    remote_ok = _determine_remote_preference(candidate)

    # Employment type (not inferred, would need to be in candidate data)
    employment_type = None

    return {
        "titles": titles,
        "locations": locations,
        "remote_ok": remote_ok,
        "keywords": keywords,
        "employment_type": employment_type,
    }


def _build_titles(candidate: CandidateProfile) -> list[str]:
    """
    Build job titles list from candidate.

    Uses desired_titles if present, otherwise infers from skills.

    Inference rules:
    - Power BI/Tableau/SQL/DAX → BI Developer, Data Analyst
    - Python/FastAPI/Django → Python Developer, Backend Engineer
    - Data Engineer/Spark/Airflow → Data Engineer
    """
    # If desired_titles explicitly provided, use them
    if candidate.desired_titles:
        return candidate.desired_titles.copy()

    # Otherwise, infer from skills
    skills_lower = {s.lower() for s in candidate.skills}
    inferred_titles = []

    # Check for BI skillset
    bi_skills = {"power bi", "tableau", "sql", "dax"}
    if any(skill in skills_lower for skill in bi_skills):
        inferred_titles.extend(
            ["Power BI Developer", "BI Developer", "Data Analyst"]
        )

    # Check for Python backend skillset
    python_backend = {"python", "fastapi", "django"}
    if any(skill in skills_lower for skill in python_backend):
        inferred_titles.extend(["Python Developer", "Backend Engineer"])

    # Check for Data Engineering skillset
    data_eng_skills = {"data engineer", "spark", "airflow"}
    if any(skill in skills_lower for skill in data_eng_skills):
        if "Data Engineer" not in inferred_titles:
            inferred_titles.append("Data Engineer")

    # Deduplicate while preserving order
    seen = set()
    unique_titles = []
    for title in inferred_titles:
        if title.lower() not in seen:
            unique_titles.append(title)
            seen.add(title.lower())

    return unique_titles


def _extract_keywords(candidate: CandidateProfile) -> list[str]:
    """
    Extract 8-20 keywords from skills and resume text.

    - Pull from skills first
    - Extract technical terms from resume_text
    - Normalize to lowercase
    - Deduplicate while preserving order
    - Cap at 20 keywords
    """
    keywords = []
    seen = set()

    # Add skills first (already normalized)
    for skill in candidate.skills:
        skill_lower = skill.lower()
        if skill_lower not in seen:
            keywords.append(skill_lower)
            seen.add(skill_lower)

    # Extract from resume_text if present
    if candidate.resume_text:
        resume_keywords = _extract_resume_keywords(candidate.resume_text)
        for keyword in resume_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in seen:
                keywords.append(keyword_lower)
                seen.add(keyword_lower)

    # Cap at 20 keywords, ensure at least 8 if available
    if len(keywords) > 20:
        keywords = keywords[:20]

    return keywords


def _extract_resume_keywords(resume_text: str) -> list[str]:
    """
    Extract technical keywords from resume text.

    Looks for:
    - Capitalized terms (SQL, AWS, Azure)
    - Common tech terms (Python, Spark, Airflow, etc.)
    - Preserves order of first occurrence
    """
    # Common technical terms to look for
    tech_terms = {
        "sql",
        "aws",
        "azure",
        "gcp",
        "power bi",
        "tableau",
        "python",
        "java",
        "javascript",
        "react",
        "angular",
        "vue",
        "node.js",
        "django",
        "flask",
        "fastapi",
        "spark",
        "hadoop",
        "airflow",
        "kafka",
        "docker",
        "kubernetes",
        "git",
        "jenkins",
        "terraform",
        "ansible",
        "postgresql",
        "mongodb",
        "redis",
        "elasticsearch",
        "machine learning",
        "deep learning",
        "nlp",
        "computer vision",
        "data science",
        "data engineering",
        "etl",
        "api",
        "rest",
        "graphql",
        "microservices",
    }

    keywords = []
    seen = set()
    resume_lower = resume_text.lower()

    # Find tech terms in resume
    for term in tech_terms:
        if term in resume_lower and term not in seen:
            keywords.append(term)
            seen.add(term)

    # Also extract capitalized/acronym patterns (like SQL, AWS, BI)
    # Look for 2-4 letter uppercase words
    acronyms = re.findall(r"\b[A-Z]{2,4}\b", resume_text)
    for acronym in acronyms:
        acronym_lower = acronym.lower()
        if acronym_lower not in seen and len(acronym) >= 2:
            keywords.append(acronym_lower)
            seen.add(acronym_lower)
            if len(keywords) >= 20:
                break

    return keywords


def _build_locations(candidate: CandidateProfile) -> list[str]:
    """
    Build locations list from candidate preferences.

    Uses preferred_locations if provided, otherwise candidate.location.
    """
    if candidate.preferred_locations:
        return candidate.preferred_locations.copy()

    if candidate.location:
        return [candidate.location]

    return []


def _determine_remote_preference(candidate: CandidateProfile) -> bool:
    """
    Determine if candidate is open to remote work.

    Returns True if:
    - candidate.remote_ok is True
    - "remote" appears in preferred_locations (case-insensitive)

    Otherwise returns False.
    """
    # Explicit remote_ok flag
    if candidate.remote_ok is True:
        return True

    # Check if "remote" in preferred locations
    for loc in candidate.preferred_locations:
        if loc.lower() == "remote":
            return True

    return False
