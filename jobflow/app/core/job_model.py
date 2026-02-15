"""
Job domain model.

Canonical representation of job postings used across aggregation,
matching, approvals, and execution pipelines.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobPosting:
    """
    Canonical job posting model.

    Normalized representation of job postings from various sources.
    Supports messy input normalization via from_raw() classmethod.
    """

    title: str
    company: str
    location: str
    description: str
    requirements: list[str]
    url: str | None = None
    source: str | None = None
    posted_date: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    employment_type: str | None = None
    remote: bool | None = None
    tags: list[str] = field(default_factory=list)
    raw: dict | None = None

    @classmethod
    def from_raw(cls, raw: dict) -> "JobPosting":
        """
        Create JobPosting from messy raw input.

        Normalizes alternative key names and formats into canonical fields.

        Args:
            raw: Raw job posting dict with potentially messy/alternative keys

        Returns:
            Normalized JobPosting instance
        """
        # Normalize title
        title = cls._get_first_value(
            raw, ["title", "job_title", "position"], default=""
        )
        title = cls._normalize_string(title)

        # Normalize company
        company = cls._get_first_value(
            raw, ["company", "employer", "company_name"], default=""
        )
        company = cls._normalize_string(company)

        # Normalize location
        location = cls._get_first_value(
            raw, ["location", "loc", "job_location"], default=""
        )
        location = cls._normalize_string(location)

        # Normalize description
        description = cls._get_first_value(
            raw, ["description", "job_description", "summary"], default=""
        )
        description = cls._normalize_string(description)

        # Normalize requirements
        requirements_raw = cls._get_first_value(
            raw, ["requirements", "skills", "qualifications"], default=[]
        )
        requirements = cls._normalize_requirements(requirements_raw)

        # Normalize URL
        url = cls._get_first_value(
            raw, ["url", "job_url", "apply_url", "link"], default=None
        )
        url = cls._normalize_string(url) if url else None

        # Normalize source
        source = cls._get_first_value(raw, ["source", "provider"], default=None)
        source = cls._normalize_string(source) if source else None

        # Normalize posted_date
        posted_date = cls._get_first_value(
            raw, ["posted_date", "date_posted"], default=None
        )
        posted_date = cls._normalize_string(posted_date) if posted_date else None

        # Normalize salary and currency
        salary_min, salary_max, currency = cls._normalize_salary(raw)

        # Normalize employment_type
        employment_type = raw.get("employment_type")
        employment_type = (
            cls._normalize_string(employment_type) if employment_type else None
        )

        # Normalize remote
        remote = raw.get("remote")
        if remote is not None:
            remote = bool(remote)

        # Normalize tags
        tags_raw = raw.get("tags", [])
        tags = cls._normalize_tags(tags_raw)

        return cls(
            title=title,
            company=company,
            location=location,
            description=description,
            requirements=requirements,
            url=url,
            source=source,
            posted_date=posted_date,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            employment_type=employment_type,
            remote=remote,
            tags=tags,
            raw=raw,  # Store original for auditability
        )

    @staticmethod
    def _get_first_value(
        data: dict, keys: list[str], default: Any = None
    ) -> Any:
        """Get first matching value from dict using list of possible keys."""
        for key in keys:
            if key in data:
                return data[key]
        return default

    @staticmethod
    def _normalize_string(value: Any) -> str:
        """Normalize value to stripped string."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _normalize_requirements(value: Any) -> list[str]:
        """
        Normalize requirements to list of non-empty strings.

        - If string: split by newlines or semicolons
        - If list: coerce to strings
        - Strip whitespace and remove empty items
        """
        if isinstance(value, str):
            # Split by newlines or semicolons
            items = re.split(r"[;\n]+", value)
        elif isinstance(value, list):
            items = value
        else:
            return []

        # Strip and filter empty items
        normalized = []
        for item in items:
            stripped = str(item).strip()
            if stripped:
                normalized.append(stripped)

        return normalized

    @staticmethod
    def _normalize_tags(value: Any) -> list[str]:
        """
        Normalize tags to lowercase, deduplicated list.

        - If string: split by commas
        - Lowercase + trimmed
        - Deduplicate while preserving first occurrence order
        """
        if isinstance(value, str):
            items = value.split(",")
        elif isinstance(value, list):
            items = value
        else:
            return []

        # Lowercase, strip, and deduplicate
        seen = set()
        normalized = []
        for item in items:
            tag = str(item).strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                normalized.append(tag)

        return normalized

    @staticmethod
    def _normalize_salary(raw: dict) -> tuple[float | None, float | None, str | None]:
        """
        Normalize salary information.

        Handles:
        - Direct salary_min/salary_max keys
        - Nested salary_range dict
        - String formats like "$80,000" or "€75,000"
        """
        salary_min = None
        salary_max = None
        currency = None

        # Check for nested salary_range
        if "salary_range" in raw and isinstance(raw["salary_range"], dict):
            salary_range = raw["salary_range"]
            salary_min = JobPosting._parse_salary_value(salary_range.get("min"))
            salary_max = JobPosting._parse_salary_value(salary_range.get("max"))
            currency = salary_range.get("currency")
        else:
            # Check for direct keys
            salary_min = JobPosting._parse_salary_value(raw.get("salary_min"))
            salary_max = JobPosting._parse_salary_value(raw.get("salary_max"))
            currency = raw.get("currency")

        # Normalize currency
        if currency:
            currency = str(currency).strip()

        return salary_min, salary_max, currency

    @staticmethod
    def _parse_salary_value(value: Any) -> float | None:
        """
        Parse salary value from various formats.

        Handles:
        - int/float: direct conversion
        - string: "$80,000", "€75,000", "80000"
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r"[^\d.]", "", value)
            if cleaned:
                try:
                    return float(cleaned)
                except ValueError:
                    return None

        return None

    def to_dict(self) -> dict:
        """
        Convert to JSON-serializable dict.

        Includes 'raw' key only when raw is not None.
        """
        result = {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "requirements": self.requirements.copy(),  # Defensive copy
            "url": self.url,
            "source": self.source,
            "posted_date": self.posted_date,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "currency": self.currency,
            "employment_type": self.employment_type,
            "remote": self.remote,
            "tags": self.tags.copy(),  # Defensive copy
        }

        if self.raw is not None:
            result["raw"] = self.raw

        return result

    def fingerprint(self) -> str:
        """
        Generate deterministic SHA-256 fingerprint.

        Fingerprint is based on core job content only, excluding provenance
        and metadata fields. This enables content-based deduplication across
        different sources.

        Included fields (core content):
        - title, company, location, description
        - requirements
        - salary_min, salary_max, currency
        - employment_type, remote

        Excluded fields (provenance/metadata):
        - source (provenance: which feed)
        - url (source-specific identifier)
        - posted_date (temporal metadata)
        - tags (internal classification)
        - raw (original data)

        Returns:
            64-character hex string (SHA-256 hash)
        """
        # Create canonical dict with core content only
        canonical = {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "requirements": self.requirements,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "currency": self.currency,
            "employment_type": self.employment_type,
            "remote": self.remote,
        }

        # Create deterministic JSON representation
        canonical_json = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )

        # Hash with SHA-256
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
