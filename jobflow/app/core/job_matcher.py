"""
Job matcher with dimension-based scoring.

Deterministic candidate-to-job matching with explainable scoring.
"""

import re
from typing import Any

from jobflow.app.core.job_model import JobPosting
from jobflow.app.core.match_result import MatchResult


def match_job(candidate_profile: dict, job: JobPosting) -> MatchResult:
    """
    Match a candidate to a job with dimension-based scoring.

    Args:
        candidate_profile: Dict with candidate info (skills, titles, locations, etc.)
        job: JobPosting instance

    Returns:
        MatchResult with scores, decision, and reasons
    """
    # Extract candidate ID
    candidate_id = _extract_candidate_id(candidate_profile)

    # Extract keywords
    candidate_keywords = _extract_candidate_keywords(candidate_profile)
    job_keywords = _extract_job_keywords(job)

    # Normalize all keywords
    candidate_keywords = _normalize_keywords(candidate_keywords)
    job_keywords = _normalize_keywords(job_keywords)

    # Compute keyword overlap
    matched = sorted(candidate_keywords & job_keywords)
    missing = sorted(job_keywords - candidate_keywords)

    # Compute dimension scores
    skills_score = _compute_skills_score(candidate_keywords, job_keywords)
    title_score = _compute_title_score(candidate_profile, job)
    location_score = _compute_location_score(candidate_profile, job)
    seniority_score = _compute_seniority_score(candidate_profile, job)

    # Weighted overall score
    overall_score = (
        skills_score * 0.45
        + title_score * 0.25
        + location_score * 0.15
        + seniority_score * 0.15
    )

    # Decision based on thresholds
    if overall_score >= 80:
        decision = "strong_fit"
    elif overall_score >= 65:
        decision = "possible_fit"
    elif overall_score >= 45:
        decision = "weak_fit"
    else:
        decision = "reject"

    # Build dimension scores dict
    dimension_scores = {
        "skills_overlap": skills_score,
        "title_alignment": title_score,
        "location_alignment": location_score,
        "seniority_alignment": seniority_score,
    }

    # Generate stable reasons
    reasons = _build_reasons(dimension_scores, matched, missing)

    # Build metadata
    meta = {
        "candidate_keyword_count": len(candidate_keywords),
        "job_keyword_count": len(job_keywords),
        "overlap_count": len(matched),
    }

    return MatchResult(
        candidate_id=candidate_id,
        job_fingerprint=job.fingerprint(),
        overall_score=round(overall_score, 2),
        decision=decision,
        dimension_scores=dimension_scores,
        reasons=reasons,
        matched_keywords=matched,
        missing_keywords=missing,
        meta=meta,
    )


def _extract_candidate_id(candidate: dict) -> str:
    """Extract candidate identifier from profile."""
    # Try email first
    if candidate.get("email"):
        return str(candidate["email"])
    # Try full_name
    if candidate.get("full_name"):
        return str(candidate["full_name"])
    # Try name
    if candidate.get("name"):
        return str(candidate["name"])
    # Fallback to generic
    return "unknown_candidate"


def _extract_candidate_keywords(candidate: dict) -> set[str]:
    """Extract keywords from candidate profile."""
    keywords = set()

    # Skills list
    skills = candidate.get("skills", [])
    if isinstance(skills, list):
        keywords.update(skills)

    # Skills from skills_years dict
    skills_years = candidate.get("skills_years", {})
    if isinstance(skills_years, dict):
        keywords.update(skills_years.keys())

    # Desired titles
    desired_titles = candidate.get("desired_titles", [])
    if isinstance(desired_titles, list):
        for title in desired_titles:
            keywords.update(_extract_tokens(str(title)))

    # Alternate titles
    alternate_titles = candidate.get("alternate_titles", [])
    if isinstance(alternate_titles, list):
        for title in alternate_titles:
            keywords.update(_extract_tokens(str(title)))

    # Resume text (extract technical terms)
    resume_text = candidate.get("resume_text", "")
    if resume_text:
        keywords.update(_extract_technical_terms(str(resume_text)))

    return keywords


def _extract_job_keywords(job: JobPosting) -> set[str]:
    """Extract keywords from job posting."""
    keywords = set()

    # Title tokens
    keywords.update(_extract_tokens(job.title))

    # Requirements list
    keywords.update(job.requirements)

    # Description (extract technical terms)
    keywords.update(_extract_technical_terms(job.description))

    return keywords


def _extract_tokens(text: str) -> set[str]:
    """Extract word tokens from text."""
    # Split on non-alphanumeric
    tokens = re.findall(r"\b[a-zA-Z0-9+#]+\b", text.lower())
    # Filter out common stopwords
    stopwords = {"and", "or", "the", "a", "an", "in", "on", "at", "to", "for", "of", "with"}
    return {t for t in tokens if t not in stopwords and len(t) >= 2}


def _extract_technical_terms(text: str) -> set[str]:
    """Extract technical terms from text (acronyms, known tech)."""
    terms = set()

    # Known technical keywords
    tech_keywords = {
        "python", "java", "javascript", "sql", "aws", "azure", "gcp",
        "docker", "kubernetes", "react", "angular", "vue", "node",
        "postgresql", "mysql", "mongodb", "redis", "kafka", "spark",
        "airflow", "tableau", "power bi", "excel", "git", "ci/cd",
        "fastapi", "django", "flask", "spring", "tensorflow", "pytorch",
        "api", "rest", "graphql", "microservices", "agile", "scrum",
        "machine learning", "data science", "etl", "bi", "analytics"
    }

    text_lower = text.lower()

    # Match known keywords
    for keyword in tech_keywords:
        if keyword in text_lower:
            # Add as single token (replace spaces with empty)
            terms.add(keyword.replace(" ", ""))

    # Extract acronyms (2-4 uppercase letters)
    acronyms = re.findall(r"\b[A-Z]{2,4}\b", text)
    terms.update(acr.lower() for acr in acronyms)

    return terms


def _normalize_keywords(keywords: set[str]) -> set[str]:
    """Normalize keywords: lowercase, strip punctuation, collapse whitespace."""
    normalized = set()
    for kw in keywords:
        # Convert to lowercase
        kw = str(kw).lower()
        # Remove punctuation except + and #
        kw = re.sub(r"[^\w+#\s]", "", kw)
        # Collapse whitespace
        kw = re.sub(r"\s+", "", kw)
        # Strip
        kw = kw.strip()
        if kw:
            normalized.add(kw)
    return normalized


def _compute_skills_score(candidate_kw: set[str], job_kw: set[str]) -> float:
    """
    Compute skills overlap score (0-100).

    Based on keyword overlap ratio relative to job requirements.
    """
    if not job_kw:
        return 100.0  # No requirements = perfect match

    overlap = len(candidate_kw & job_kw)
    ratio = overlap / len(job_kw)

    # Scale: 0% overlap = 0, 100% overlap = 100
    # Add bonus for exceeding requirements
    if overlap > len(job_kw):
        ratio = 1.0 + min(0.2, (overlap - len(job_kw)) / len(job_kw) * 0.2)

    score = min(100.0, ratio * 100.0)
    return round(score, 2)


def _compute_title_score(candidate: dict, job: JobPosting) -> float:
    """
    Compute title alignment score (0-100).

    Based on candidate's desired titles matching job title.
    """
    # Get candidate titles
    candidate_titles = []
    candidate_titles.extend(candidate.get("desired_titles", []))
    candidate_titles.extend(candidate.get("alternate_titles", []))

    if not candidate_titles:
        # No title preference = neutral score
        return 50.0

    # Normalize job title tokens
    job_title_tokens = _extract_tokens(job.title)

    # Check each candidate title for overlap
    max_overlap = 0.0
    for title in candidate_titles:
        title_tokens = _extract_tokens(str(title))
        if not title_tokens:
            continue

        overlap = len(title_tokens & job_title_tokens)
        ratio = overlap / len(title_tokens)
        max_overlap = max(max_overlap, ratio)

    # Exact match bonus
    job_title_lower = job.title.lower()
    for title in candidate_titles:
        if str(title).lower() in job_title_lower or job_title_lower in str(title).lower():
            max_overlap = max(max_overlap, 0.9)

    score = max_overlap * 100.0
    return round(score, 2)


def _compute_location_score(candidate: dict, job: JobPosting) -> float:
    """
    Compute location alignment score (0-100).

    Based on candidate location preferences vs job location.
    """
    # Check if candidate is remote-ok
    remote_ok = candidate.get("remote_ok", False)
    if isinstance(remote_ok, str):
        remote_ok = remote_ok.lower() in {"true", "yes", "1"}

    # Check if job is remote
    job_remote = job.remote or "remote" in job.location.lower()

    # If both remote, perfect match
    if remote_ok and job_remote:
        return 100.0

    # Get candidate preferred locations
    preferred_locations = candidate.get("preferred_locations", [])
    if not isinstance(preferred_locations, list):
        preferred_locations = []

    # Check if "remote" is in preferred locations
    if any("remote" in str(loc).lower() for loc in preferred_locations):
        if job_remote:
            return 100.0

    # If no location preferences, neutral
    if not preferred_locations:
        return 50.0

    # Check for location match
    job_location_lower = job.location.lower()
    for loc in preferred_locations:
        loc_lower = str(loc).lower()
        if loc_lower in job_location_lower or job_location_lower in loc_lower:
            return 100.0

    # No match
    return 0.0


def _compute_seniority_score(candidate: dict, job: JobPosting) -> float:
    """
    Compute seniority alignment score (0-100).

    Based on years of experience vs job seniority cues.
    """
    # Extract candidate years of experience
    years_exp = candidate.get("years_experience")
    if years_exp is None:
        # No experience info = neutral
        return 50.0

    try:
        years_exp = float(years_exp)
    except (ValueError, TypeError):
        return 50.0

    # Infer job seniority from title
    job_title_lower = job.title.lower()

    # Junior: 0-2 years
    if any(keyword in job_title_lower for keyword in ["junior", "entry", "associate"]):
        if years_exp <= 2:
            return 100.0
        elif years_exp <= 4:
            return 70.0
        else:
            return 40.0  # Overqualified

    # Senior: 5+ years
    if any(keyword in job_title_lower for keyword in ["senior", "lead", "principal", "staff"]):
        if years_exp >= 5:
            return 100.0
        elif years_exp >= 3:
            return 70.0
        else:
            return 30.0  # Underqualified

    # Mid-level: 2-5 years (or no explicit level)
    if years_exp >= 2 and years_exp <= 7:
        return 100.0
    elif years_exp < 2:
        return 60.0
    else:
        return 80.0  # More experience is generally good

    return 50.0


def _build_reasons(dimension_scores: dict[str, float], matched: list[str], missing: list[str]) -> list[str]:
    """
    Build stable list of reasons explaining the match.

    Returns top 3 drivers sorted by dimension score.
    """
    reasons = []

    # Sort dimensions by score (descending)
    sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)

    # Top dimension
    if sorted_dims:
        dim_name, dim_score = sorted_dims[0]
        if dim_score >= 80:
            reasons.append(f"Strong {dim_name.replace('_', ' ')}: {dim_score:.0f}%")
        elif dim_score >= 60:
            reasons.append(f"Good {dim_name.replace('_', ' ')}: {dim_score:.0f}%")
        elif dim_score >= 40:
            reasons.append(f"Moderate {dim_name.replace('_', ' ')}: {dim_score:.0f}%")
        else:
            reasons.append(f"Weak {dim_name.replace('_', ' ')}: {dim_score:.0f}%")

    # Second dimension
    if len(sorted_dims) > 1:
        dim_name, dim_score = sorted_dims[1]
        if dim_score >= 70:
            reasons.append(f"Strong {dim_name.replace('_', ' ')}: {dim_score:.0f}%")
        elif dim_score >= 50:
            reasons.append(f"Adequate {dim_name.replace('_', ' ')}: {dim_score:.0f}%")
        else:
            reasons.append(f"Limited {dim_name.replace('_', ' ')}: {dim_score:.0f}%")

    # Keyword overlap reason
    if matched:
        top_matched = matched[:5]  # Top 5 matched keywords
        reasons.append(f"Matched skills: {', '.join(top_matched)}")

    # If weak match, mention missing keywords
    if len(reasons) < 3 and missing:
        top_missing = missing[:3]
        reasons.append(f"Missing: {', '.join(top_missing)}")

    # Ensure we have at least 1 reason
    if not reasons:
        reasons.append("Insufficient information to evaluate match")

    # Return top 3
    return reasons[:3]
