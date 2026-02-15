"""
Candidate profile domain model.

Canonical representation of candidate profiles used for job matching.
Normalizes messy candidate data into consistent structure.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateProfile:
    """
    Canonical candidate profile model.

    Normalized representation of candidate information for job matching.
    Supports messy input normalization via from_dict() classmethod.
    """

    full_name: str
    email: str
    phone: str
    location: str
    desired_titles: list[str]
    skills: list[str]
    years_experience: float | None = None
    work_authorization: str = ""
    preferred_locations: list[str] = field(default_factory=list)
    remote_ok: bool | None = None
    sponsorship_needed: bool | None = None
    resume_text: str = ""
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "CandidateProfile":
        """
        Create CandidateProfile from messy raw input.

        Normalizes alternative key names and formats into canonical fields.
        Handles missing fields with sensible defaults.

        Args:
            raw: Raw candidate dict with potentially messy/alternative keys

        Returns:
            Normalized CandidateProfile instance
        """
        # Normalize full_name
        full_name = cls._get_first_value(
            raw, ["full_name", "name", "candidate_name"], default=""
        )
        full_name = cls._normalize_string(full_name)

        # Normalize email
        email = cls._get_first_value(
            raw, ["email", "email_address"], default=""
        )
        email = cls._normalize_string(email)

        # Normalize phone
        phone = cls._get_first_value(
            raw, ["phone", "phone_number", "mobile"], default=""
        )
        phone = cls._normalize_string(phone)

        # Normalize location
        location = cls._get_first_value(
            raw, ["location", "city", "state"], default=""
        )
        location = cls._normalize_string(location)

        # Normalize desired_titles
        desired_titles_raw = cls._get_first_value(
            raw, ["desired_titles", "target_roles", "roles"], default=[]
        )
        desired_titles = cls._normalize_list(desired_titles_raw)

        # Normalize skills
        skills_raw = cls._get_first_value(
            raw, ["skills", "primary_skills", "tech_stack"], default=[]
        )
        # Also handle skills_years dict from candidate_intake
        if not skills_raw and "skills_years" in raw:
            skills_years = raw["skills_years"]
            if isinstance(skills_years, dict):
                skills_raw = list(skills_years.keys())
        skills = cls._normalize_list(skills_raw)

        # Normalize years_experience
        years_exp_raw = cls._get_first_value(
            raw, ["years_experience", "experience_years"], default=None
        )
        years_experience = cls._parse_float(years_exp_raw)

        # Normalize work_authorization
        work_auth = cls._get_first_value(
            raw, ["work_authorization", "visa_status"], default=""
        )
        work_authorization = cls._normalize_string(work_auth)

        # Normalize preferred_locations
        pref_locs_raw = cls._get_first_value(
            raw, ["preferred_locations", "preferred_location", "desired_locations"], default=[]
        )
        preferred_locations = cls._normalize_list(pref_locs_raw)

        # Normalize remote_ok
        remote_raw = cls._get_first_value(
            raw, ["remote_ok", "remote", "remote_preference"], default=None
        )
        remote_ok = cls._parse_bool(remote_raw) if remote_raw is not None else None

        # Normalize sponsorship_needed
        sponsorship_raw = cls._get_first_value(
            raw, ["sponsorship_needed", "needs_sponsorship", "visa_sponsorship"], default=None
        )
        sponsorship_needed = cls._parse_bool(sponsorship_raw) if sponsorship_raw is not None else None

        # Normalize resume_text
        resume = cls._get_first_value(
            raw, ["resume_text", "resume"], default=""
        )
        resume_text = cls._normalize_string(resume)

        # Store defensive copy of raw
        raw_copy = raw.copy() if isinstance(raw, dict) else {}

        return cls(
            full_name=full_name,
            email=email,
            phone=phone,
            location=location,
            desired_titles=desired_titles,
            skills=skills,
            years_experience=years_experience,
            work_authorization=work_authorization,
            preferred_locations=preferred_locations,
            remote_ok=remote_ok,
            sponsorship_needed=sponsorship_needed,
            resume_text=resume_text,
            raw=raw_copy,
        )

    @staticmethod
    def _get_first_value(data: dict, keys: list[str], default: Any = None) -> Any:
        """Get first matching value from dict using list of possible keys."""
        for key in keys:
            if key in data:
                return data[key]
        return default

    @staticmethod
    def _normalize_string(value: Any) -> str:
        """
        Normalize value to stripped string with collapsed internal whitespace.
        """
        if value is None:
            return ""
        # Convert to string and strip
        text = str(value).strip()
        # Collapse internal whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        """
        Normalize value to list of non-empty strings.

        - If string: split by commas or newlines
        - If list: coerce to strings
        - Strip whitespace, deduplicate (case-insensitive), preserve order
        """
        if isinstance(value, str):
            # Split by commas or newlines
            items = re.split(r"[,\n]+", value)
        elif isinstance(value, list):
            items = value
        else:
            return []

        # Strip, deduplicate, and preserve order
        seen = set()
        normalized = []
        for item in items:
            stripped = str(item).strip()
            # Collapse internal whitespace
            stripped = re.sub(r"\s+", " ", stripped)
            if stripped and stripped.lower() not in seen:
                normalized.append(stripped)
                seen.add(stripped.lower())

        return normalized

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        """Parse value to float, return None if invalid."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse value to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value)
